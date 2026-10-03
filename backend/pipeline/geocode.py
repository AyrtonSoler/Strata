"""Module B, step 1: resolve each sample address to its legal jurisdiction stack.

The postal city is not the legal city (Van Nuys is inside Los Angeles, Dorchester
inside Boston), so every address goes through the Census Geocoder and we read the
Incorporated Place it falls in. Results are cached so reruns are free.
"""

import asyncio
import csv
import json
import re

import httpx

from .paths import ADDRESSES, ADDRESSES_RESOLVED, GEOCODE_CACHE

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"
CENSUS_ONELINE_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
PARAMS = {
    "benchmark": "Public_AR_Current",
    "vintage": "Current_Current",
    "layers": "Incorporated Places,Counties",
    "format": "json",
}

# Cities in scope, keyed by (state, Census place name). Anything else resolves to
# "state only" (no city layer in our corpus).
CITY_BY_PLACE = {
    ("CA", "Los Angeles city"): "Los Angeles, CA",
    ("CA", "San Francisco city"): "San Francisco, CA",
    ("CA", "San Diego city"): "San Diego, CA",
    ("CA", "Berkeley city"): "Berkeley, CA",
    ("CA", "Santa Ana city"): "Santa Ana, CA",
    ("CA", "Oakland city"): "Oakland, CA",
    ("NJ", "Jersey City city"): "Jersey City, NJ",
    ("NJ", "Hoboken city"): "Hoboken, NJ",
    ("NJ", "Newark city"): "Newark, NJ",
    ("MA", "Boston city"): "Boston, MA",
    ("MA", "Cambridge city"): "Cambridge, MA",
}

# County for each city in scope (used when the geocoder can't match an address).
COUNTY_BY_CITY = {
    "Los Angeles, CA": "Los Angeles County", "San Francisco, CA": "San Francisco County",
    "San Diego, CA": "San Diego County", "Berkeley, CA": "Alameda County", "Oakland, CA": "Alameda County",
    "Santa Ana, CA": "Orange County", "Jersey City, NJ": "Hudson County", "Hoboken, NJ": "Hudson County",
    "Newark, NJ": "Essex County", "Boston, MA": "Suffolk County", "Cambridge, MA": "Middlesex County",
}

# Postal names that sit inside a legal city. Used only when the geocoder fails.
POSTAL_FALLBACK = {
    ("CA", "San Ysidro"): "San Diego, CA",
    **{("MA", n): "Boston, MA" for n in [
        "Allston", "Brighton", "Dorchester", "East Boston", "Hyde Park",
        "Jamaica Plain", "Mattapan", "Roxbury", "South Boston", "Charlestown",
        "Roslindale", "West Roxbury", "Boston",
    ]},
}


def clean_street(street: str) -> str:
    s = street.strip()
    # "1031-1035 CLINTON ST" / "322-322.5 Western Ave" -> first number only;
    # Census can't match ranges.
    s = re.sub(r"^(\d+)[A-Z]?\s*-\s*[\d.]+[A-Z]?(?=\s)", r"\1", s)
    # "397 05TH AV" -> "397 5TH AV"
    s = re.sub(r"\b0+(\d+(ST|ND|RD|TH))\b", r"\1", s)
    return s


def parse_match(data: dict) -> dict | None:
    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    m = matches[0]
    geo = m.get("geographies", {})
    places = geo.get("Incorporated Places", [])
    counties = geo.get("Counties", [])
    return {
        "matched_address": m.get("matchedAddress"),
        "lat": m["coordinates"]["y"],
        "lon": m["coordinates"]["x"],
        "place": places[0]["NAME"] if places else None,
        "place_geoid": places[0]["GEOID"] if places else None,
        "county": counties[0]["NAME"] if counties else None,
    }


async def geocode_one(client: httpx.AsyncClient, row: dict) -> dict:
    street = clean_street(row["street_address"])
    attempts = [
        (CENSUS_URL, {"street": street, "city": row["postal_city"], "state": row["state"], "zip": row["zip"]}),
        # Some ZIPs in the sample are wrong (e.g. Newark rows with NY ZIPs).
        (CENSUS_URL, {"street": street, "city": row["postal_city"], "state": row["state"]}),
        (CENSUS_ONELINE_URL, {"address": f"{street}, {row['postal_city']}, {row['state']}"}),
    ]
    for url, q in attempts:
        for _ in range(3):
            try:
                r = await client.get(url, params={**q, **PARAMS}, timeout=30)
                r.raise_for_status()
                hit = parse_match(r.json())
                if hit:
                    return {"status": "matched", **hit}
                break
            except (httpx.HTTPError, ValueError):
                await asyncio.sleep(1.5)
    return {"status": "no_match"}


def resolve_city(row: dict, geo: dict) -> tuple[str | None, str]:
    """Return (city jurisdiction or None, method)."""
    state = row["state"]
    if geo.get("status") == "matched":
        place = geo.get("place")
        if place:
            return CITY_BY_PLACE.get((state, place)), "census_place"
        return None, "census_unincorporated"
    fallback = POSTAL_FALLBACK.get((state, row["postal_city"]))
    if fallback:
        return fallback, "postal_fallback"
    city = f"{row['postal_city']}, {state}"
    if city in CITY_BY_PLACE.values():
        return city, "postal_fallback"
    return None, "unresolved"


def infer_units(row: dict) -> tuple[int | None, int | None, str]:
    """Return (units_exact, units_min, basis). Never invents an exact count the
    record doesn't state; a lower bound comes only from the use classification."""
    if row["units"]:
        n = int(row["units"])
        return n, n, "assessor unit count"
    desc, code, state = row["use_description"], row["use_code"], row["state"]
    # NJ MOD-IV building descriptions often embed the count: "6B-20U-G", "3S-F-D-6U".
    # "UG" means garage units, so it is not a dwelling-unit count.
    # Multi-building parcels ("3B-7U/4B-24U-G") list one count per building.
    counts = [int(x) for x in re.findall(r"(\d+)U(?!G)\b", desc.replace("1OU", "10U"))]
    if state == "NJ" and counts:
        n = sum(counts)
        return n, n, f"parsed from building description '{desc}'"
    if desc.lower().startswith("five or more"):
        return None, 5, f"use description '{desc}'"
    if state == "NJ" and code == "4C":
        return None, 5, "NJ property class 4C = apartment building with 5+ units"
    if state == "MA" and code.startswith("A/1"):
        return None, 7, f"Boston land use 'A' ({desc}) = 7+ unit apartment"
    m = re.search(r"\(?(\d+)\+ units\)?|(\d+) or more|Apartment (\d+) to|APT (\d+)-", desc, re.I)
    if m:
        return None, int(next(g for g in m.groups() if g)), f"use description '{desc}'"
    return None, None, "no unit information"


def load_rows() -> list[dict]:
    with open(ADDRESSES, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


async def run(concurrency: int = 8) -> list[dict]:
    rows = load_rows()
    cache = json.loads(GEOCODE_CACHE.read_text()) if GEOCODE_CACHE.exists() else {}
    todo = [r for r in rows if cache.get(r["address_id"], {}).get("status") != "matched"]
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        async def work(row):
            async with sem:
                cache[row["address_id"]] = await geocode_one(client, row)

        await asyncio.gather(*(work(r) for r in todo))

    GEOCODE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    GEOCODE_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))

    resolved = []
    for row in rows:
        geo = cache.get(row["address_id"], {"status": "no_match"})
        city, method = resolve_city(row, geo)
        units, units_min, units_basis = infer_units(row)
        resolved.append({
            **row,
            "year_built": int(row["year_built"]) if row["year_built"] else None,
            "units": units,
            "units_min": units_min,
            "units_basis": units_basis,
            "jurisdiction_state": row["state"],
            "jurisdiction_county": geo.get("county") or COUNTY_BY_CITY.get(city or ""),
            "jurisdiction_city": city,
            "resolution_method": method,
            "geocode": geo,
        })
    ADDRESSES_RESOLVED.parent.mkdir(parents=True, exist_ok=True)
    ADDRESSES_RESOLVED.write_text(json.dumps(resolved, indent=1))
    return resolved


if __name__ == "__main__":
    out = asyncio.run(run())
    from collections import Counter
    print(Counter((r["state"], r["jurisdiction_city"], r["resolution_method"]) for r in out).most_common())
