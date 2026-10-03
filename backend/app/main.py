import json
import os
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from pipeline.engine import RESULT_ORDER, jurisdiction_stack, lookup, parse_date, public_rows
from pipeline.geocode import CENSUS_ONELINE_URL, PARAMS, parse_match, resolve_city
from pipeline.paths import (ADDRESSES_RESOLVED, AUDIT_LOG, CHANGE_TESTS, CHANGES_OUT, CORPUS_DIR, DEFAULT_AS_OF,
                            EXTRA_DIR, LOOKUPS_OUT, MANIFEST, RULES_OUT, WORK)
from pipeline.textmatch import locate_span

load_dotenv()

DISCLAIMER = ("Not legal advice. This prototype summarizes public law for research and may be incomplete "
              "or out of date. Verify with the cited source or a qualified professional.")
CATEGORY_LABELS = {
    "rent_increase_limits": "Rent increases",
    "just_cause_eviction": "Just-cause eviction",
    "security_deposits": "Security deposits",
    "application_screening_fees": "Application & screening fees",
    "screening_restrictions": "Screening restrictions",
    "algorithmic_rent_setting": "Algorithmic rent-setting",
}

app = FastAPI(title="Rental Housing Law Navigator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: dict[str, tuple[float, object]] = {}


def _load(path: Path, default=None):
    if not path.exists():
        return default
    mtime = path.stat().st_mtime
    hit = _cache.get(str(path))
    if hit and hit[0] == mtime:
        return hit[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    _cache[str(path)] = (mtime, data)
    return data


def rules_doc() -> dict:
    return _load(RULES_OUT, {"rules": [], "no_rule_findings": []})


def addresses() -> list[dict]:
    return _load(ADDRESSES_RESOLVED, [])


def _as_of(value: str | None):
    d = parse_date(value or DEFAULT_AS_OF)
    if not d:
        raise HTTPException(400, "as_of must be YYYY-MM-DD")
    return d


def _public_address(a: dict) -> dict:
    keep = ("address_id", "street_address", "postal_city", "state", "zip", "year_built", "units", "units_min",
            "units_basis", "use_code", "use_description", "jurisdiction_state", "jurisdiction_city",
            "resolution_method", "source_dataset")
    out = {k: a.get(k) for k in keep}
    out["matched_address"] = (a.get("geocode") or {}).get("matched_address")
    out["census_place"] = (a.get("geocode") or {}).get("place")
    return out


def _answer(addr: dict, as_of) -> dict:
    rules = rules_doc()["rules"]
    rows = lookup(addr, rules, as_of)
    stack = jurisdiction_stack(addr)
    items = []
    for r in rows:
        rule = r["_rule"]
        items.append({**{k: v for k, v in r.items() if k != "_rule"},
                      "category": rule["category"], "category_label": CATEGORY_LABELS[rule["category"]],
                      "jurisdiction": rule["jurisdiction"], "level": rule["level"], "title": rule["title"],
                      "requirement": rule["requirement"], "requirement_es": rule.get("requirement_es"),
                      "title_es": rule.get("title_es"), "key_value_es": rule.get("key_value_es"),
                      "key_value": rule.get("key_value"), "citation": rule["citation"],
                      "quoted_span": rule["quoted_span"], "source_url": rule["source_url"],
                      "source_doc_id": rule.get("source_doc_id"), "retrieved_at": rule.get("retrieved_at"),
                      "effective_date": rule.get("effective_date"), "status": rule["status"],
                      "confidence": rule.get("confidence"), "conflict_note": rule.get("conflict_note"),
                      "interaction": rule.get("interaction"), "source_origin": rule.get("source_origin")})
    findings = [f for f in rules_doc().get("no_rule_findings", []) if f["jurisdiction"] in stack]
    covered = {i["category"] for i in items}
    gaps = [{"category": c, "category_label": l} for c, l in CATEGORY_LABELS.items() if c not in covered]
    return {"as_of": str(as_of), "disclaimer": DISCLAIMER, "address": _public_address(addr),
            "jurisdiction_stack": stack, "results": items, "no_rule_findings": findings,
            "categories_without_rules": gaps,
            "summary": dict(Counter(i["result"] for i in items))}


@app.get("/api/health")
def health():
    return {"status": "ok", "rules": len(rules_doc()["rules"]), "addresses": len(addresses())}


@app.get("/api/meta")
def meta():
    rules = rules_doc()["rules"]
    spend = _load(WORK / "llm_spend.json", {})
    return {
        "default_as_of": DEFAULT_AS_OF, "disclaimer": DISCLAIMER, "categories": CATEGORY_LABELS,
        "n_rules": len(rules), "n_addresses": len(addresses()),
        "rules_by_status": dict(Counter(r["status"] for r in rules)),
        "rules_by_jurisdiction": dict(Counter(r["jurisdiction"] for r in rules)),
        "llm": {k: spend.get(k) for k in ("calls", "input_tokens", "output_tokens")},
    }


@app.get("/api/addresses")
def search_addresses(q: str = "", city: str | None = None, limit: int = 30):
    ql = q.lower().strip()
    out = []
    for a in addresses():
        if city and a.get("jurisdiction_city") != city:
            continue
        hay = f"{a['address_id']} {a['street_address']} {a['postal_city']} {a['zip']} {a.get('jurisdiction_city')}".lower()
        if ql and not all(t in hay for t in ql.split()):
            continue
        out.append({k: a.get(k) for k in ("address_id", "street_address", "postal_city", "state", "zip",
                                           "jurisdiction_city", "year_built", "units", "units_min")})
        if len(out) >= limit:
            break
    return out


@app.get("/api/lookup")
def lookup_address(address_id: str, as_of: str | None = None):
    addr = next((a for a in addresses() if a["address_id"] == address_id), None)
    if not addr:
        raise HTTPException(404, "unknown address_id")
    return _answer(addr, _as_of(as_of))


@app.get("/api/lookup_free")
async def lookup_free(address: str = Query(min_length=5), as_of: str | None = None,
                      year_built: int | None = None, units: int | None = None):
    """Any U.S. address: geocode live; building facts only if the user supplies them."""
    async with httpx.AsyncClient() as client:
        r = await client.get(CENSUS_ONELINE_URL, params={"address": address, **PARAMS}, timeout=30)
    hit = parse_match(r.json()) if r.status_code == 200 else None
    if not hit:
        raise HTTPException(404, "The Census Geocoder could not match that address.")
    state = hit["matched_address"].split(",")[-2].strip()
    if state not in ("CA", "NJ", "MA"):
        raise HTTPException(422, f"Address resolves to {state}; this prototype covers CA, NJ and MA.")
    row = {"state": state, "postal_city": hit["matched_address"].split(",")[1].strip(), "use_description": ""}
    city, method = resolve_city(row, {"status": "matched", **hit})
    addr = {"address_id": "live", "street_address": hit["matched_address"], "postal_city": row["postal_city"],
            "state": state, "zip": hit["matched_address"].split(",")[-1].strip(), "year_built": year_built,
            "units": units, "units_min": units, "units_basis": "entered by user" if units else "no unit information",
            "use_code": "", "use_description": "", "jurisdiction_state": state, "jurisdiction_city": city,
            "resolution_method": method, "source_dataset": "Census Geocoder (live)", "geocode": hit}
    return _answer(addr, _as_of(as_of))


@app.get("/api/rules")
def list_rules(jurisdiction: str | None = None, category: str | None = None):
    doc = rules_doc()
    rules = [r for r in doc["rules"] if (not jurisdiction or r["jurisdiction"] == jurisdiction)
             and (not category or r["category"] == category)]
    return {"as_of": doc.get("as_of"), "rules": rules, "no_rule_findings": doc.get("no_rule_findings", []),
            "disclaimer": DISCLAIMER}


@app.get("/api/changes")
def changes():
    tests = {t["test_id"]: t for t in _load(CHANGE_TESTS, [])}
    extra = CHANGE_TESTS.parents[2] / "extra" / "change_tests_extra.json"
    for t in _load(extra, []) or []:
        tests[t["test_id"]] = t
    results = _load(CHANGES_OUT, {})
    return [{"test": tests.get(tid, {"test_id": tid}), **{k: v for k, v in res.items() if k != "detail"},
             "detail": res.get("detail", {})} for tid, res in results.items()]


@app.get("/api/audit")
def audit(limit: int = 200):
    events = []
    if AUDIT_LOG.exists():
        lines = AUDIT_LOG.read_text(encoding="utf-8").splitlines()[-limit:]
        events = [json.loads(ln) for ln in lines if ln.strip()]
    spend = _load(WORK / "llm_spend.json", {})
    return {"events": events[::-1], "llm": spend,
            "lookups_generated": LOOKUPS_OUT.exists(), "changes_generated": CHANGES_OUT.exists()}


# ---------- Time machine: every sample address on a map, on any date ----------

def _category_result(rows: list[dict]) -> dict[str, str]:
    """Strongest result per category for one address ('applies' beats 'unknown', ...)."""
    best: dict[str, str] = {}
    for r in rows:
        cat = r["_rule"]["category"]
        if cat not in best or RESULT_ORDER[r["result"]] < RESULT_ORDER[best[cat]]:
            best[cat] = r["result"]
    return best


@app.get("/api/map")
def map_points(as_of: str | None = None):
    d = _as_of(as_of)
    rules = rules_doc()["rules"]
    points, counts = [], {c: Counter() for c in CATEGORY_LABELS}
    for a in addresses():
        geo = a.get("geocode") or {}
        best = _category_result(lookup(a, rules, d))
        for c in CATEGORY_LABELS:
            counts[c][best.get(c, "none")] += 1
        if geo.get("lat") is None:
            continue
        points.append({"id": a["address_id"], "lat": round(geo["lat"], 5), "lon": round(geo["lon"], 5),
                       "street": a["street_address"], "city": a.get("jurisdiction_city"), "r": best})
    return {"as_of": str(d), "points": points, "counts": {c: dict(v) for c, v in counts.items()},
            "not_mapped": len(addresses()) - len(points)}


@app.get("/api/timeline")
def timeline():
    """Dated events from the extracted rules: when each rule took or takes effect."""
    events = []
    for r in rules_doc()["rules"]:
        if r.get("instrument_status") == "enacted" and r.get("effective_date"):
            d = parse_date(r["effective_date"])
            if d and d.year >= 2024:
                events.append({"date": str(d), "rule_id": r["team_rule_id"], "jurisdiction": r["jurisdiction"],
                               "category": r["category"], "category_label": CATEGORY_LABELS[r["category"]],
                               "title": r["title"], "citation": r["citation"], "conflict": r["conflict_flag"]})
    pending = [{"rule_id": r["team_rule_id"], "jurisdiction": r["jurisdiction"], "title": r["title"],
                "citation": r["citation"], "status": r["instrument_status"],
                "category_label": CATEGORY_LABELS[r["category"]]}
               for r in rules_doc()["rules"] if r.get("instrument_status") in ("pending", "failed")]
    return {"events": sorted(events, key=lambda e: e["date"]), "not_law": pending}


# ---------- Evidence: open the source document at the quoted passage ----------

def _doc_text(doc_id: str) -> tuple[str, str] | None:
    """(text, origin). Third-party pages fetched by the team are not redistributed."""
    p = CORPUS_DIR / f"{doc_id}.txt"
    if p.exists():
        return p.read_text(encoding="utf-8"), "starter_corpus"
    p = EXTRA_DIR / f"{doc_id}.txt"
    if p.exists():
        return p.read_text(encoding="utf-8"), "extra"
    return None


@app.get("/api/source/{rule_id}")
def source(rule_id: str):
    rule = next((r for r in rules_doc()["rules"] if r["team_rule_id"] == rule_id), None)
    if not rule:
        raise HTTPException(404, "unknown rule")
    base = {"rule_id": rule_id, "doc_id": rule.get("source_doc_id"), "url": rule["source_url"],
            "retrieved_at": rule.get("retrieved_at"), "citation": rule["citation"], "title": rule["title"],
            "quoted_span": rule["quoted_span"], "source_origin": rule.get("source_origin")}
    found = _doc_text(rule.get("source_doc_id") or "")
    if not found:
        return {**base, "available": False, "text": None, "highlight": None}
    text, _ = found
    # Drop the SOURCE/RETRIEVED header lines; keep offsets consistent with the body.
    body_start = text.find("\n\n") + 2 if text.startswith("SOURCE:") else 0
    body = text[body_start:]
    return {**base, "available": True, "text": body, "highlight": locate_span(rule["quoted_span"], body)}
