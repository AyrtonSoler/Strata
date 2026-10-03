"""Enrich missing building facts from public parcel data (allowed by the guide:
"Public parcel data: building facts such as year built, units and use code").

San Diego rows in the sample have no year built. SANDAG's public parcel layer
has the assessor's *effective* year, which moves later when a building is
remodeled. So it is used only as an upper bound ("built in or before year X"):
it can confirm that a building is older than a cutoff, never that it is newer.
Missing matches stay unknown.

    uv run python -m pipeline.enrich
"""

import asyncio
import json
import re

import httpx

from .paths import ADDRESSES_RESOLVED, WORK

SANDAG = "https://geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0/query"
CACHE = WORK / "enrich_sandag.json"
DIRS = {"N", "S", "E", "W"}


def parse_street(street: str) -> tuple[int, str | None, str] | None:
    m = re.match(r"^(\d+)[A-Z]?(?:\s*-\s*\d+)?\s+(.*)$", street.strip().upper())
    if not m:
        return None
    words = m[2].split()
    pre = words.pop(0) if len(words) > 1 and words[0] in DIRS else None
    if len(words) > 1:
        words = words[:-1]  # drop the suffix (ST, AVE, ...)
    return int(m[1]), pre, " ".join(words)


def to_year(v) -> int | None:
    if v in (None, "", "0", "00"):
        return None
    y = int(str(v).strip())
    if y < 100:
        y += 2000 if y <= 26 else 1900  # two-digit assessor years; data as of 2026
    return y if 1800 < y < 2100 else None


async def lookup(client: httpx.AsyncClient, addr: dict) -> dict:
    parsed = parse_street(addr["street_address"])
    if not parsed:
        return {"status": "unparsed"}
    num, pre, name = parsed
    where = f"situs_address={num} AND situs_street='{name.replace(chr(39), '')}'"
    if pre:
        where += f" AND situs_pre_dir='{pre}'"
    if addr.get("zip"):
        where += f" AND situs_zip LIKE '{addr['zip'][:5]}%'"
    try:
        r = await client.get(SANDAG, params={"where": where, "outFields": "apn,unitqty,year_effective",
                                             "returnGeometry": "false", "f": "json"}, timeout=30)
        feats = r.json().get("features", [])
    except (httpx.HTTPError, ValueError):
        return {"status": "error"}
    years = [to_year(f["attributes"].get("year_effective")) for f in feats]
    years = [y for y in years if y]
    if not years:
        return {"status": "no_match" if not feats else "no_year"}
    # Several parcels at one address: the latest effective year is the safe upper bound.
    return {"status": "matched", "year_effective_max": max(years), "apns": [f["attributes"]["apn"] for f in feats],
            "unitqty": [f["attributes"].get("unitqty") for f in feats]}


async def run() -> None:
    addrs = json.loads(ADDRESSES_RESOLVED.read_text())
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [a for a in addrs if a["jurisdiction_city"] == "San Diego, CA" and a["year_built"] is None
            and a["address_id"] not in cache]
    sem = asyncio.Semaphore(6)
    async with httpx.AsyncClient() as client:
        async def work(a):
            async with sem:
                cache[a["address_id"]] = await lookup(client, a)
        await asyncio.gather(*(work(a) for a in todo))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1))
    n = 0
    for a in addrs:
        hit = cache.get(a["address_id"])
        if hit and hit.get("status") == "matched":
            a["year_built_max"] = hit["year_effective_max"]
            a["year_built_max_basis"] = (f"SANDAG parcel effective year {hit['year_effective_max']} "
                                         f"(APN {', '.join(hit['apns'][:2])}); built in or before that year")
            n += 1
    ADDRESSES_RESOLVED.write_text(json.dumps(addrs, indent=1))
    from collections import Counter
    print(f"enriched {n} addresses;", Counter(v["status"] for v in cache.values()))


if __name__ == "__main__":
    asyncio.run(run())
