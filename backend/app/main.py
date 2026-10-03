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
                            EXTENSION_RESOLVED, EXTRA_DIR, LOOKUPS_OUT, MANIFEST, RULES_OUT, WORK)
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
    """The 500 supplied addresses plus the extension sample (new jurisdiction)."""
    return _load(ADDRESSES_RESOLVED, []) + (_load(EXTENSION_RESOLVED, []) or [])


def _as_of(value: str | None):
    d = parse_date(value or DEFAULT_AS_OF)
    if not d:
        raise HTTPException(400, "as_of must be YYYY-MM-DD")
    return d


def _public_address(a: dict) -> dict:
    keep = ("address_id", "street_address", "postal_city", "state", "zip", "year_built", "units", "units_min",
            "units_basis", "use_code", "use_description", "jurisdiction_state", "jurisdiction_county", "jurisdiction_city",
            "year_built_max", "year_built_max_basis", "extension",
            "resolution_method", "source_dataset")
    out = {k: a.get(k) for k in keep}
    out["matched_address"] = (a.get("geocode") or {}).get("matched_address")
    out["census_place"] = (a.get("geocode") or {}).get("place")
    return out


EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "claude-sonnet-5")


def _status_reason(rule: dict, status: str, as_of) -> str:
    eff = rule.get("effective_date")
    inst = rule.get("instrument_status", "enacted")
    if inst == "pending":
        return f"A bill or proposal, not law on {as_of}. It never counts as in force."
    if status == "not_yet_effective":
        return f"Enacted, but takes effect {eff}, after {as_of}."
    if eff and parse_date(eff) and parse_date(eff) > as_of and rule.get("prior_version_in_force"):
        return (f"The cited version takes effect {eff}; on {as_of} the earlier version of this rule applies "
                f"({rule.get('effective_date_note') or 'amendment or annual adjustment'}).")
    return f"In force on {as_of}" + (f" (effective {eff})." if eff else " (no effective date stated in the source).")


def _boundary(rule: dict, addr: dict) -> list[str]:
    """What this answer did NOT verify: the edge of the system's reasoning."""
    cov = rule.get("coverage") or {}
    out = []
    if cov.get("age_cutoff_basis") == "certificate_of_occupancy" and (cov.get("built_on_or_before") or cov.get("built_after")):
        out.append("The certificate-of-occupancy date is approximated by the assessor's year built.")
    if cov.get("owner_exemption_max_units") or cov.get("owner_exemption_any_size"):
        out.append("Owner identity and type are not in public data, so owner-based exemptions were not checked.")
    if cov.get("other_unknown_factor"):
        out.append(f"Not checked: {cov['other_unknown_factor']}.")
    if addr.get("year_built") is None and addr.get("year_built_max"):
        out.append(f"Year built is unknown; {addr.get('year_built_max_basis')}. Used only to confirm a building is old enough.")
    if addr.get("units") is None and addr.get("units_min"):
        out.append(f"Unit count is a lower bound inferred from {addr.get('units_basis')}.")
    if rule.get("source_origin") != "starter_corpus":
        out.append("Source is a secondary or publisher page read once; confirm against the official code.")
    if rule.get("verification", {}).get("verdict") == "review":
        out.append("An automated check disagreed with this record; a person should review it before relying on it.")
    out.append("Registrations, exemption filings and recent amendments not in the corpus were not checked.")
    return out


def _audit(row: dict, addr: dict, stack: list[str], as_of) -> dict:
    rule = row["_rule"]
    v = rule.get("verification", {})
    origins = rule.get("extraction_origins", ["doc"])
    ai = [f"Extracted from {rule.get('source_doc_id')} by {EXTRACT_MODEL} into the rule schema"
          + (" by both the per-cell and per-document passes" if set(origins) >= {"cell", "doc"} else
             f" by the per-{origins[0]} pass") + ".",
          "The quoted span was checked character by character against the source."]
    if v.get("verdict"):
        ai.append(f"Independent verifier: {v['verdict']}"
                  + (f" — {'; '.join(v.get('review_reasons') or [])}" if v.get("review_reasons") else
                     f" (requirement {v.get('requirement_supported', '?')}, date {v.get('date_supported', '?')}, "
                     f"status {v.get('status_supported', '?')}).") )
    code = [f"Resolved the address to {' > '.join(stack)} with the Census Geocoder ({addr.get('resolution_method')}).",
            f"Status on {as_of}: {row.get('_status', '').replace('_', ' ')}.",
            "Applied the coverage tests below; any missing fact makes the answer “unknown”."]
    if row["result"] == "superseded":
        code.append("A local rule of the same category covers this unit, so this state rule yields to it.")
    return {
        "as_of": str(as_of),
        "source": {"doc_id": rule.get("source_doc_id"), "url": rule["source_url"],
                   "retrieved_at": rule.get("retrieved_at"), "type": rule.get("source_type"),
                   "official_corpus": rule.get("source_origin") == "starter_corpus"},
        "status_reason": _status_reason(rule, row.get("_status", ""), as_of),
        "facts_used": {"year_built": addr.get("year_built"), "year_built_max": addr.get("year_built_max"),
                       "units": addr.get("units"),
                       "units_min": addr.get("units_min"), "units_basis": addr.get("units_basis"),
                       "use": addr.get("use_description")},
        "checks": row.get("_checks", []),
        "ai_steps": ai,
        "code_steps": code,
        "boundary": _boundary(rule, addr),
        "confidence": rule.get("confidence"),
        "confidence_signals": rule.get("confidence_signals", []),
    }


def _answer(addr: dict, as_of) -> dict:
    rules = rules_doc()["rules"]
    rows = lookup(addr, rules, as_of)
    stack = jurisdiction_stack(addr)
    items = []
    for r in rows:
        rule = r["_rule"]
        items.append({**{k: v for k, v in r.items() if not k.startswith("_")},
                      "category": rule["category"], "category_label": CATEGORY_LABELS[rule["category"]],
                      "jurisdiction": rule["jurisdiction"], "level": rule["level"], "title": rule["title"],
                      "requirement": rule["requirement"], "requirement_es": rule.get("requirement_es"),
                      "title_es": rule.get("title_es"), "key_value_es": rule.get("key_value_es"),
                      "key_value": rule.get("key_value"), "citation": rule["citation"],
                      "quoted_span": rule["quoted_span"], "source_url": rule["source_url"],
                      "source_doc_id": rule.get("source_doc_id"), "retrieved_at": rule.get("retrieved_at"),
                      "effective_date": rule.get("effective_date"), "status": rule["status"],
                      "confidence": rule.get("confidence"), "conflict_note": rule.get("conflict_note"),
                      "interaction": rule.get("interaction"), "source_origin": rule.get("source_origin"),
                      "penalty": rule.get("penalty"), "confidence_signals": rule.get("confidence_signals", []),
                      "verification": rule.get("verification", {}),
                      "audit": _audit(r, addr, stack, as_of)})
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
def lookup_address(address_id: str, as_of: str | None = None, year_built: int | None = None,
                   units: int | None = None):
    """Lookup for a sample address. year_built / units are a "what if": they replace
    the public-record facts so the user can see which missing fact decides an answer."""
    addr = next((a for a in addresses() if a["address_id"] == address_id), None)
    if not addr:
        raise HTTPException(404, "unknown address_id")
    if year_built is None and units is None:
        return _answer(addr, _as_of(as_of))
    what_if = dict(addr)
    edited = []
    if year_built is not None:
        what_if.update(year_built=year_built, year_built_max=None)
        edited.append("year_built")
    if units is not None:
        what_if.update(units=units, units_min=units, units_basis="entered in what-if")
        edited.append("units")
    answer = _answer(what_if, _as_of(as_of))
    answer["what_if"] = {"edited": edited, "original": {"year_built": addr.get("year_built"),
                                                         "units": addr.get("units"),
                                                         "units_min": addr.get("units_min")}}
    return answer


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
            "use_code": "", "use_description": "", "jurisdiction_state": state,
            "jurisdiction_county": hit.get("county"), "jurisdiction_city": city,
            "resolution_method": method, "source_dataset": "Census Geocoder (live)", "geocode": hit}
    return _answer(addr, _as_of(as_of))


@app.get("/api/rules")
def list_rules(jurisdiction: str | None = None, category: str | None = None):
    doc = rules_doc()
    rules = [r for r in doc["rules"] if (not jurisdiction or r["jurisdiction"] == jurisdiction)
             and (not category or r["category"] == category)]
    return {"as_of": doc.get("as_of"), "rules": rules, "no_rule_findings": doc.get("no_rule_findings", []),
            "coverage_grid": doc.get("coverage_grid", {}), "supplementary_rules": doc.get("supplementary_rules", []),
            "disclaimer": DISCLAIMER}


@app.get("/api/changes")
def changes():
    tests = {t["test_id"]: t for t in _load(CHANGE_TESTS, [])}
    extra = CHANGE_TESTS.parents[2] / "extra" / "change_tests_extra.json"
    for t in _load(extra, []) or []:
        tests[t["test_id"]] = t
    results = _load(CHANGES_OUT, {})
    sample = _load(ADDRESSES_RESOLVED, [])  # the 500 supplied addresses only
    city_of = {a["address_id"]: a.get("jurisdiction_city") or a["state"] for a in sample}
    rules = {r["team_rule_id"]: r for r in rules_doc()["rules"]}
    out = []
    for tid, res in results.items():
        test = tests.get(tid, {"test_id": tid})
        affected = res.get("affected_address_ids", [])
        flagged = res.get("conflict_flag_address_ids", [])
        expected, expected_flags = _expected_sets(test, sample)
        exp_ok = set(affected) == expected and (not expected_flags or set(flagged) == expected_flags)
        out.append({
            "test": test, **{k: v for k, v in res.items() if k != "detail"},
            "by_city": dict(Counter(city_of.get(a, "?") for a in affected).most_common()),
            "flagged_by_city": dict(Counter(city_of.get(a, "?") for a in flagged).most_common()),
            "groups": {c: sorted(a for a in affected if city_of.get(a, "?") == c)
                       for c, _ in Counter(city_of.get(a, "?") for a in affected).most_common()},
            "transition": _transition(test, res, rules),
            "check": {"expected_count": len(expected), "matches": exp_ok},
            "detail": res.get("detail", {}),
        })
    return out


_CITY_CODE = {"HOB": "Hoboken, NJ", "JC": "Jersey City, NJ", "NWK": "Newark, NJ", "SF": "San Francisco, CA",
              "LA": "Los Angeles, CA", "SD": "San Diego, CA", "BER": "Berkeley, CA", "BOS": "Boston, MA",
              "CAM": "Cambridge, MA", "OAK": "Oakland, CA"}


def _expected_sets(test: dict, sample: list[dict]) -> tuple[set, set]:
    """Address sets implied by the supplied test definition (same reading as selfcheck)."""
    states = set(test.get("states") or [])
    in_states = {a["address_id"] for a in sample if a["state"] in states}
    kind = test.get("type")
    if kind == "negative":
        return set(), set()
    if kind == "boundary":
        cities = {_CITY_CODE.get(r.split("-")[0]) for r in test.get("rule_ids", [])}
        return {a["address_id"] for a in sample if a.get("jurisdiction_city") in cities}, set()
    flags = set()
    if test.get("conflict_with"):
        cities = {_CITY_CODE.get(r.split("-")[0]) for r in test["conflict_with"]}
        flags = {a["address_id"] for a in sample if a.get("jurisdiction_city") in cities}
    return in_states, flags


def _transition(test: dict, res: dict, rules: dict) -> dict:
    """A compact before -> after summary for the UI."""
    kind = test.get("type")
    if kind == "as_of":
        before = after = None
        for d in res.get("detail", {}).values():
            if d.get("before") is not None and d.get("after"):
                before = next(iter(d["before"].values()), "absent") if d["before"] else "absent"
                after = next(iter(d["after"].values()))
                break
        return {"kind": "as_of", "from": before or "not_yet_effective", "to": after or "applies",
                "from_date": test.get("as_of_before"), "to_date": test.get("as_of_after")}
    if kind == "boundary":
        # Unique affected addresses per city of the state, including cities with none (e.g. Newark).
        sample = _load(ADDRESSES_RESOLVED, [])
        city_of = {a["address_id"]: a.get("jurisdiction_city") for a in sample}
        states = {rules[i]["jurisdiction"].split(", ")[-1] for ids in res.get("mapped_rules", {}).values()
                  for i in ids if i in rules}
        cities = sorted({a.get("jurisdiction_city") for a in sample if a["state"] in states and a.get("jurisdiction_city")})
        hits = Counter(city_of.get(a) for a in res.get("affected_address_ids", []))
        return {"kind": "boundary", "rules": [{"jurisdiction": c, "count": hits.get(c, 0)} for c in cities]}
    if kind == "pending":
        return {"kind": "pending", "from": "pending", "to": "applies"}
    return {"kind": kind or "other", "from": "failed", "to": "never"}


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
