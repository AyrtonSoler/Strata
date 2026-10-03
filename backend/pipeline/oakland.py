"""Stretch goal: extend Strata to one new jurisdiction (Oakland, CA) with the same
extraction and coverage pipeline.

    uv run python -m pipeline.oakland          # fetch sources + sample, geocode, rerun everything

1. Sources: official City of Oakland documents (rent program info sheets, the
   2020 amendment to O.M.C. ch. 8.22, the Fair Chance Housing ordinance), each read
   once. www.oaklandca.gov blocks automated access, so we use the city's document
   store on its CMS host, plus one copy of the Fair Chance ordinance PDF hosted by a
   rental-housing association. Nothing is hand-coded: rules come from extraction.
2. Sample: 30 multifamily parcels (Alameda County use codes 7200/7700/7800, the same
   classes as the Berkeley rows of the starter sample) from the county's public
   Secured Tax Roll. Only situs address and use code are requested, no owner data.
3. Everything else (cells, reconcile, verify, lookups) is the unchanged pipeline.
   Oakland lookups go to submission/extension_oakland.json; the official
   lookups.json keeps the 500 supplied addresses only.
"""

import asyncio
import csv
import datetime as dt
import io
import json

import httpx
from pypdf import PdfReader

from . import geocode
from .ingest import add_document
from .paths import ROOT

EXT_DIR = ROOT / "data" / "extension"
ADDR_CSV = EXT_DIR / "oakland_addresses.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
CMS = "https://oaklandca.prelive.opencities.com/files/assets/city/v/1/housing-comm-dev/documents"
SOURCES = [
    ("O001", f"{CMS}/rental-laws/info-sheet_rent-levels-and-rent-regulation_en_10.6.24_final.pdf", "official"),
    ("O002", f"{CMS}/rental-laws/info-sheet_allowable-annual-rent-increase_en_10.6.24_final.pdf", "official"),
    ("O003", f"{CMS}/tenants/13608-cms.pdf", "official"),
    ("O004", f"{CMS}/landlords/view-revised-supplemental-legislation-4242023.pdf", "official"),
    ("O005", f"{CMS}/fair-chance/fair-chance-ordinance.tenant-notice.10.5.2020.pdf", "official"),
    ("O006", "https://assets-002.noviams.com/novi-file-uploads/ebrha/pdfs-and-documents/"
             "ordinance_no__13581_c_m_s__o_m_c__8_25-cc6d7722.pdf", "official text (third-party copy)"),
]
TAX_ROLL = ("https://services5.arcgis.com/ROBnTHSNjoZ2Wm1P/ArcGIS/rest/services/"
            "Assessor_Office_Secured_Tax_Roll_2025_to_2026/FeatureServer/0/query")


def fetch_sources() -> None:
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=60) as client:
        for doc_id, url, kind in SOURCES:
            r = client.get(url)
            r.raise_for_status()
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
            tmp = EXT_DIR / f"{doc_id}.txt"
            tmp.write_text(text, encoding="utf-8")
            add_document(tmp, doc_id, "Oakland, CA", url, kind)


def fetch_sample(n: int = 30) -> list[dict]:
    with httpx.Client(timeout=60) as client:
        total = client.get(TAX_ROLL, params={
            "where": "Situs_City='OAKLAND' AND Use_Code IN ('7200','7700','7800') AND Situs_Street_Number IS NOT NULL",
            "returnCountOnly": "true", "f": "json"}).json()["count"]
        rows, step = [], max(1, total // n)
        for i in range(n):  # evenly spaced through the roll, so the sample spans the city
            feats = client.get(TAX_ROLL, params={
                "where": "Situs_City='OAKLAND' AND Use_Code IN ('7200','7700','7800') AND Situs_Street_Number IS NOT NULL",
                "outFields": "Situs_Street_Number,Situs_Street_Name,Situs_Zip,Use_Code",
                "orderByFields": "Print_Parcel", "resultOffset": i * step, "resultRecordCount": 1,
                "f": "json"}).json().get("features", [])
            if feats:
                a = feats[0]["attributes"]
                rows.append({"address_id": f"OAK{i + 1:02d}",
                             "street_address": f"{a['Situs_Street_Number']} {a['Situs_Street_Name']}".strip(),
                             "postal_city": "Oakland", "state": "CA", "zip": (a.get("Situs_Zip") or "")[:5],
                             "year_built": "", "units": "", "use_code": a["Use_Code"],
                             "use_description": "Alameda County use code (5+ units)",
                             "source_dataset": "Alameda County Assessor Secured Tax Roll 2025-26",
                             "retrieved_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")})
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    with open(ADDR_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


async def resolve_sample() -> list[dict]:
    with open(ADDR_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    async with httpx.AsyncClient() as client:
        geos = await asyncio.gather(*(geocode.geocode_one(client, r) for r in rows))
    out = []
    for row, geo in zip(rows, geos):
        city, method = geocode.resolve_city(row, geo)
        units, umin, basis = geocode.infer_units(row)
        out.append({**row, "year_built": None, "units": units, "units_min": umin, "units_basis": basis,
                    "jurisdiction_state": "CA", "jurisdiction_county": geo.get("county") or "Alameda County",
                    "jurisdiction_city": city, "resolution_method": method, "geocode": geo, "extension": True})
    (EXT_DIR / "oakland_resolved.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    fetch_sources()
    rows = fetch_sample()
    resolved = asyncio.run(resolve_sample())
    from collections import Counter
    print(len(rows), "sample rows;", Counter((r["jurisdiction_city"], r["resolution_method"]) for r in resolved))
