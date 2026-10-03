"""Cell-based, retrieval-augmented extraction (the backbone of Module A).

The rule set is a grid: every jurisdiction x every category. For each cell we
retrieve the most relevant passages from the whole corpus (BM25), then ask Claude
one focused question: which rules of THIS jurisdiction level exist in THIS
category, or does the law say there are none? This gives one record per legal
instrument, an explicit answer for every cell (including "no rule at this
level"), and quotes that come from the official corpus whenever it has them.
The per-document extraction (extract.py) still runs as a second, independent
signal; agreement between the two raises confidence.
"""

import asyncio
import csv
import hashlib
import json
import sys

from . import llm
from .extract import CATEGORIES, RULE_SCHEMA, SYSTEM as DOMAIN, audit, load_docs, verify_span
from .paths import EXTRA_DIR, WORK
from .retrieve import BM25, build_passages

PROMPT_VERSION = "cells-v1"
CACHE = WORK / "cells_cache"

STATE_NAMES = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}
CITIES = ["Los Angeles, CA", "San Francisco, CA", "San Diego, CA", "Berkeley, CA", "Santa Ana, CA",
          "Jersey City, NJ", "Hoboken, NJ", "Newark, NJ", "Boston, MA", "Cambridge, MA"]
EXTRA_CITIES: list[str] = []  # new jurisdictions (e.g. "Oakland, CA") are appended by the extension step

CATEGORY_QUERY = {
    "rent_increase_limits": "rent increase cap limit maximum allowable annual adjustment rent control stabilization CPI percent covered units",
    "just_cause_eviction": "just cause eviction terminate tenancy grounds notice relocation assistance no-fault owner move-in",
    "security_deposits": "security deposit maximum month rent return interest refund upfront charges",
    "application_screening_fees": "application screening fee tenant applicant charge cap receipt refund broker fee credit report",
    "screening_restrictions": "criminal history background check source of income voucher screening applicant fair chance discriminate",
    "algorithmic_rent_setting": "algorithm algorithmic device software rent pricing competitor nonpublic data coordinate price fixing",
}

CELL_RULES = """

You are now answering ONE CELL of the jurisdiction x category grid, from retrieved passages labeled [P1], [P2], ...
- Return only rules that belong to the cell's jurisdiction AT ITS LEVEL. For a city cell, return city ordinances, not the state laws a city page may describe. For a state cell, return state law, not city ordinances.
- One record per legal instrument in this category (merge sections of the same ordinance/statute into one record citing its principal section or chapter). Pending bills and failed/struck measures are separate records with their status.
- Set passage_id to the passage your quoted_span is copied from. The quote must be copied exactly from that passage.
- cell_status: "rules_found" if you return at least one rule; "no_rule_stated" if a passage states this jurisdiction has no such rule or is barred from adopting one (fill no_rule_finding with its exact quote); "silent" if the passages simply do not address it (return no rules, and no_rule_finding null).
- Laws that bar or preempt regulation (e.g. a state ban on local rent control) are no_rule findings, not rules."""

CELL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["cell_status", "rules", "no_rule_finding"],
    "properties": {
        "cell_status": {"type": "string", "enum": ["rules_found", "no_rule_stated", "silent"]},
        "rules": {"type": "array", "items": {
            **RULE_SCHEMA,
            "required": RULE_SCHEMA["required"] + ["passage_id"],
            "properties": {**RULE_SCHEMA["properties"], "passage_id": {"type": "string"}},
        }},
        "no_rule_finding": {"anyOf": [{"type": "null"}, {
            "type": "object", "additionalProperties": False,
            "required": ["finding", "passage_id", "quoted_span"],
            "properties": {"finding": {"type": "string"}, "passage_id": {"type": "string"},
                           "quoted_span": {"type": "string"}}}]},
    },
}


def jurisdictions() -> list[str]:
    """Supplied jurisdictions plus any new city added through data/extra (e.g. Oakland)."""
    extra = list(EXTRA_CITIES)
    manifest = EXTRA_DIR / "extra_manifest.csv"
    if manifest.exists():
        with open(manifest, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                j = row["jurisdictions"]
                if "," in j and j not in CITIES and j not in extra:
                    extra.append(j)
    return list(STATE_NAMES) + CITIES + extra


def _allow(jur: str):
    if jur in STATE_NAMES:
        st = jur
        return lambda p: p.doc.jurisdictions == st or p.doc.jurisdictions.endswith(f", {st}")
    city = jur.split(",")[0].lower()
    return lambda p: p.doc.jurisdictions == jur or city in p.text.lower()


def _retrieve(index: BM25, jur: str, category: str, k: int = 10, per_doc: int = 3):
    name = STATE_NAMES.get(jur, jur.split(",")[0])
    hits = index.search(f"{CATEGORY_QUERY[category]} {name} {name}", _allow(jur), k=80)
    # Prefer the jurisdiction's own documents and the official corpus over
    # secondary pages that merely mention the place.
    hits = sorted(((s * (1.8 if p.doc.jurisdictions == jur else 1.0)
                    * (1.4 if p.doc.origin == "starter_corpus" else 1.0), p) for s, p in hits),
                  key=lambda x: -x[0])
    # Reserve most slots for the official starter corpus, then fill with
    # secondary sources (law-firm alerts repeat keywords and would crowd it out).
    out, per = [], {}

    def take(pool, limit):
        for _, p in pool:
            if len(out) >= limit:
                return
            if p in out or per.get(p.doc.doc_id, 0) >= per_doc:
                continue
            per[p.doc.doc_id] = per.get(p.doc.doc_id, 0) + 1
            out.append(p)

    take([h for h in hits if h[1].doc.origin == "starter_corpus"], 6)
    take(hits, k)
    return out


def _user_message(jur: str, category: str, passages) -> str:
    level = "state" if jur in STATE_NAMES else "city"
    parts = [f"CELL: jurisdiction = {jur} ({level} level), category = {category}\n"]
    for i, p in enumerate(passages, 1):
        d = p.doc
        parts.append(f"[P{i}] doc {d.doc_id} | {d.jurisdictions} | {d.source_type} | {d.url} | retrieved {d.retrieved_at}\n"
                     f"{p.text}\n")
    return "\n".join(parts)


async def extract_cell(index: BM25, jur: str, category: str, sem: asyncio.Semaphore) -> dict:
    passages = _retrieve(index, jur, category)
    key = hashlib.sha256((f"{PROMPT_VERSION}|{llm.MODEL}|{jur}|{category}|"
                          + "|".join(p.pid + p.text[:200] for p in passages)).encode()).hexdigest()[:20]
    cache = CACHE / f"{jur.replace(', ', '_').replace(' ', '')}_{category}_{key}.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    elif not passages:
        data = {"cell_status": "silent", "rules": [], "no_rule_finding": None}
    else:
        async with sem:
            data, meta = await llm.structured_call(DOMAIN + CELL_RULES, _user_message(jur, category, passages),
                                                   CELL_SCHEMA, effort="medium")
        audit({"event": "llm_cell", "cell": f"{jur} x {category}", **meta, "status": data["cell_status"],
               "n_rules": len(data["rules"]), "passages": [p.pid for p in passages]})
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"jurisdiction": jur, "category": category, "passages": passages, **data}


def _passage(passages, pid: str):
    try:
        return passages[int(pid.strip().lstrip("[Pp").rstrip("]")) - 1]
    except (ValueError, IndexError):
        return None


def to_candidates(cell: dict) -> list[dict]:
    out = []
    jur, passages = cell["jurisdiction"], cell["passages"]
    for r in cell["rules"]:
        p = _passage(passages, r["passage_id"])
        docs = ([p.doc] if p else []) + [q.doc for q in passages]
        exact = None
        for d in docs:
            exact, score = verify_span(r["quoted_span"], d.text)
            if exact:
                break
        if not exact:
            audit({"event": "span_rejected", "cell": f"{jur} x {cell['category']}", "citation": r["citation"]})
            continue
        if r["jurisdiction"].split(",")[0].strip().lower() != jur.split(",")[0].strip().lower() \
                and STATE_NAMES.get(jur, "").lower() != r["jurisdiction"].strip().lower():
            audit({"event": "cell_wrong_level", "cell": f"{jur} x {cell['category']}", "got": r["jurisdiction"]})
            continue
        out.append({**{k: v for k, v in r.items() if k != "passage_id"}, "jurisdiction": jur,
                    "category": cell["category"], "quoted_span": exact, "span_match": round(score, 3),
                    "source_doc_id": d.doc_id, "source_url": d.url, "source_type": d.source_type,
                    "source_origin": d.origin, "retrieved_at": d.retrieved_at, "origin": "cell"})
    nf = cell.get("no_rule_finding")
    if cell["cell_status"] == "no_rule_stated" and nf:
        p = _passage(passages, nf["passage_id"])
        for d in ([p.doc] if p else []) + [q.doc for q in passages]:
            exact, _ = verify_span(nf["quoted_span"], d.text)
            if exact:
                out.append({"no_rule_finding": True, "jurisdiction": jur, "category": cell["category"],
                            "finding": nf["finding"], "quoted_span": exact, "source_doc_id": d.doc_id,
                            "source_url": d.url, "retrieved_at": d.retrieved_at, "origin": "cell"})
                break
    return out


async def run(only: list[str] | None = None, concurrency: int = 6) -> tuple[list[dict], dict]:
    docs = load_docs()
    index = BM25(build_passages(docs))
    sem = asyncio.Semaphore(concurrency)
    jurs = [j for j in jurisdictions() if not only or j in only]
    cells = await asyncio.gather(*(extract_cell(index, j, c, sem) for j in jurs for c in CATEGORIES),
                                 return_exceptions=True)
    candidates, grid = [], {}
    for cell in cells:
        if isinstance(cell, Exception):
            audit({"event": "cell_error", "error": repr(cell)})
            print(f"  ! cell error: {cell!r}", file=sys.stderr)
            continue
        grid[f"{cell['jurisdiction']}|{cell['category']}"] = cell["cell_status"]
        candidates += to_candidates(cell)
    return candidates, grid


if __name__ == "__main__":
    cands, grid = asyncio.run(run(sys.argv[1:] or None))
    from collections import Counter
    print(Counter(grid.values()))
    print(len([c for c in cands if not c.get("no_rule_finding")]), "rules,",
          len([c for c in cands if c.get("no_rule_finding")]), "no-rule findings; spent", round(llm.spent_usd(), 2))
