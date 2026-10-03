"""Module A, step 2: merge per-chunk candidates into one record per rule.

Several sources describe the same law (an official page and a law-firm alert,
or two chunks of one statute). One LLM call per state groups duplicates, picks the
best-supported primary record (official source, exact quote), and flags
preemption/conflicts between levels. A deterministic fallback (group by
jurisdiction + category + cited section) runs if the LLM is unavailable.
"""

import datetime as dt
import hashlib
import json
import re
from collections import defaultdict

from . import llm
from .canon import canon_citation
from .engine import status_as_of
from .extract import audit
from .paths import WORK

STATES = ("CA", "NJ", "MA")
CITIES = {
    "Los Angeles": "CA", "San Francisco": "CA", "San Diego": "CA", "Berkeley": "CA", "Santa Ana": "CA",
    "Oakland": "CA",
    "Jersey City": "NJ", "Hoboken": "NJ", "Newark": "NJ", "Boston": "MA", "Cambridge": "MA",
}
STATE_NAMES = {"california": "CA", "new jersey": "NJ", "massachusetts": "MA"}


def canonical_jurisdiction(j: str) -> str | None:
    j = (j or "").strip()
    if j.upper() in STATES:
        return j.upper()
    if j.lower() in STATE_NAMES:
        return STATE_NAMES[j.lower()]
    name = re.split(r",", j)[0].strip()
    name = re.sub(r"^(city of|city and county of)\s+", "", name, flags=re.I).strip()
    for city, st in CITIES.items():
        if name.lower() == city.lower():
            return f"{city}, {st}"
    return None


def state_of(j: str) -> str:
    return j if j in STATES else j.split(", ")[1]


SYSTEM = """You reconcile candidate rental-housing rule records extracted (by another model) from many documents about one U.S. state and its cities. Each candidate has an id. Produce the final rule list.

- Target granularity: ONE rule per jurisdiction x category x legal instrument. Merge all candidates from the same statute section family, ordinance or code chapter in the same category into one group (e.g. all sections of a city's rent control chapter -> one rent_increase_limits rule; all sections of one just-cause ordinance -> one just_cause_eviction rule; a statute and its amendment -> one rule with the current effective date). Keep separate only genuinely different instruments: different laws (a source-of-income law vs a criminal-history law), a pending bill vs an enacted law, two different pending bills, an enacted ordinance vs a failed measure. A state law and a city ordinance are never the same rule.
- An enacted ordinance that some sources still describe as "proposed" or "pending" is ONE enacted rule (official adoption wins); do not keep a separate pending copy.
- Laws that BAR or PREEMPT regulation rather than imposing a rule on landlords (e.g. a state ban on local rent control, a clause forbidding local ordinances) are not rules: put their ids in no_rule_ids. Council motions/policy orders that only request a study are not rules: reject them.
- For each group pick primary_id: prefer an official source (government site, statute text) over law-firm/news pages, then the clearest quote and most specific citation.
- canonical_citation: the most precise official citation supported by the group, in conventional form.
- effective_date / instrument_status: the best-supported values across the group (official text wins). If sources disagree, keep the official one and describe the disagreement in conflict_note with conflict_flag true.
- conflict_flag true also when a state law may preempt or conflict with a city rule of the same category (e.g. a statewide ban that may preempt local bans once effective), or when the rule's applicability is legally unsettled. Explain in conflict_note.
- interaction: one sentence on how this rule interacts with rules at the other level in the same category (e.g. "State cap does not apply to units covered by local rent control"), or null.
- yields_to_local: true if this STATE rule does not apply where a local rule of the same category covers the unit.
- Candidates come from two independent extractions: origin="cell" (asked per jurisdiction x category, already at the target granularity) and origin="doc" (read document by document). Use cell candidates as the backbone; attach matching doc candidates to the same group as corroboration. Keep a doc-only candidate as its own group only if it is a real in-scope rule the cell pass missed.
- reject_ids: candidates that are not real in-scope rules for the six categories (e.g. general fair-housing statements, procedural notices, rules for other places, or duplicated noise). Every candidate id must appear in exactly one of: one group's member_ids, reject_ids, or no_rule_ids."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["groups", "reject_ids", "no_rule_ids"],
    "properties": {
        "groups": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["member_ids", "primary_id", "canonical_citation", "effective_date",
                         "instrument_status", "conflict_flag", "conflict_note", "interaction", "yields_to_local"],
            "properties": {
                "member_ids": {"type": "array", "items": {"type": "string"}},
                "primary_id": {"type": "string"},
                "canonical_citation": {"type": "string"},
                "effective_date": {"type": ["string", "null"]},
                "instrument_status": {"type": "string", "enum": ["enacted", "pending", "failed"]},
                "conflict_flag": {"type": "boolean"},
                "conflict_note": {"type": ["string", "null"]},
                "interaction": {"type": ["string", "null"]},
                "yields_to_local": {"type": "boolean"},
            }}},
        "reject_ids": {"type": "array", "items": {"type": "string"}},
        "no_rule_ids": {"type": "array", "items": {"type": "string"}},
    },
}


def _compact(c: dict) -> dict:
    return {k: c.get(k) for k in ("id", "jurisdiction", "category", "instrument_status", "citation", "title",
                                   "key_value", "effective_date", "requirement", "source_doc_id", "origin",
                                   "source_type", "confidence", "conflict_note")} | {
        "quote": c["quoted_span"][:240], "yields_to_local": c["coverage"]["yields_to_local"]}


async def reconcile_state(state: str, cands: list[dict]) -> tuple[list[dict], list[dict]]:
    payload = json.dumps([_compact(c) for c in cands], ensure_ascii=False)
    key = hashlib.sha256(f"{SYSTEM}|{llm.MODEL}|{payload}".encode()).hexdigest()[:20]
    cache_file = WORK / "reconcile_cache" / f"{state}_{key}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        data, meta = await llm.structured_call(
            SYSTEM, f"STATE: {state}\nCANDIDATES:\n{payload}", SCHEMA, effort="medium")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        audit({"event": "llm_reconcile", "state": state, **meta, "n_candidates": len(cands),
               "n_groups": len(data["groups"]), "n_rejected": len(data["reject_ids"]),
               "n_no_rule": len(data["no_rule_ids"])})
    by_id = {c["id"]: c for c in cands}
    no_rule = [{"jurisdiction": by_id[i]["jurisdiction"], "category": by_id[i]["category"],
                "finding": f"{by_id[i]['title']}: {by_id[i]['requirement']}", "quoted_span": by_id[i]["quoted_span"],
                "source_doc_id": by_id[i]["source_doc_id"], "source_url": by_id[i]["source_url"],
                "citation": by_id[i]["citation"]} for i in data["no_rule_ids"] if i in by_id]
    out = []
    seen = set(data["no_rule_ids"])
    for g in data["groups"]:
        members = [m for m in g["member_ids"] if m in by_id and m not in seen]
        if not members:
            continue
        seen.update(members)
        primary = by_id.get(g["primary_id"]) if g["primary_id"] in members else by_id[members[0]]
        out.append(_merge(primary, [by_id[m] for m in members], g))
    for rid in data["reject_ids"]:
        if rid in by_id:
            audit({"event": "candidate_rejected", "id": rid, "citation": by_id[rid]["citation"],
                   "jurisdiction": by_id[rid]["jurisdiction"]})
    # Anything the model forgot to place keeps its own group (never silently lost).
    for c in cands:
        if c["id"] not in seen and c["id"] not in data["reject_ids"]:
            out.append(_merge(c, [c], None))
    return out, no_rule


COVERAGE_FIELDS = ("min_units", "max_units", "built_on_or_before", "built_after", "age_cutoff_basis",
                   "exclude_if_newer_than_years", "owner_exemption_max_units", "other_unknown_factor")


def _merge_coverage(primary: dict, members: list[dict]) -> dict:
    """Primary's coverage, with gaps filled from other members (official sources first).
    An announcement page may omit the coverage cutoff that the ordinance text states."""
    cov = dict(primary["coverage"])
    ranked = sorted(members, key=lambda m: (m["source_type"] != "official", -(m.get("confidence") or 0)))
    for field in COVERAGE_FIELDS:
        if cov.get(field) in (None, ""):
            for m in ranked:
                if m["coverage"].get(field) not in (None, ""):
                    cov[field] = m["coverage"][field]
                    break
    # Merging e.g. a pre-1978 ordinance with its post-1978 companion yields a window
    # nothing can satisfy; fall back to the primary's own cutoffs (or none = all years).
    b, a = cov.get("built_on_or_before"), cov.get("built_after")
    if b and a and str(a)[:7] >= str(b)[:7]:
        if primary["category"] == "rent_increase_limits":
            cov["built_after"] = None  # rent control covers the older stock
        else:
            own = primary["coverage"]
            cov["built_on_or_before"], cov["built_after"] = own.get("built_on_or_before"), own.get("built_after")
            if cov["built_on_or_before"] and cov["built_after"]:
                cov["built_on_or_before"] = cov["built_after"] = None
    if cov.get("built_on_or_before") and not cov.get("age_cutoff_basis"):
        cov["age_cutoff_basis"] = next((m["coverage"]["age_cutoff_basis"] for m in ranked
                                        if m["coverage"].get("age_cutoff_basis")), None)
    return cov


def _merge(primary: dict, members: list[dict], g: dict | None) -> dict:
    rec = dict(primary)
    rec["coverage"] = _merge_coverage(primary, members)
    rec["supporting_sources"] = sorted({(m["source_doc_id"], m["source_url"]) for m in members})
    if g:
        rec["citation"] = g["canonical_citation"] or rec["citation"]
        rec["effective_date"] = g["effective_date"] if g["effective_date"] is not None else rec["effective_date"]
        rec["instrument_status"] = g["instrument_status"]
        rec["conflict_flag"] = g["conflict_flag"]
        rec["conflict_note"] = g["conflict_note"] or rec.get("conflict_note")
        rec["interaction"] = g["interaction"]
        rec["coverage"] = {**rec["coverage"], "yields_to_local": g["yields_to_local"] and rec["level"] == "state"}
    else:
        rec["conflict_flag"] = bool(rec.get("conflict_note"))
        rec["interaction"] = None
    rec["merged_candidate_ids"] = [m["id"] for m in members]
    rec["origins"] = sorted({m.get("origin", "doc") for m in members})
    rec["penalty"] = rec.get("penalty") or next((m.get("penalty") for m in members if m.get("penalty")), None)
    return rec


def _section_key(citation: str) -> str:
    nums = re.findall(r"\d+[\w.:-]*", citation)
    return nums[0] if nums else citation.lower()


def reconcile_deterministic(cands: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for c in cands:
        groups[(c["jurisdiction"], c["category"], c["instrument_status"], _section_key(c["citation"]))].append(c)
    out = []
    for members in groups.values():
        members.sort(key=lambda m: (m["source_origin"] != "starter_corpus", -m["confidence"]))
        out.append(_merge(members[0], members, None))
    return out


def clean_citation(c: str) -> str:
    """'Cal. Civ. Code § 1947.12 (Tenant Protection Act)' -> 'Cal. Civ. Code § 1947.12'.
    Keeps subsection markers like '(n)' or '4(10)' and any parenthetical that is the
    only place a number appears."""
    descriptive = r"\s+\([^()]*\s[^()]*\)\s*$"  # space before and inside the parens
    base = re.sub(descriptive, "", c).strip()
    while base != c and re.search(r"\d", base):
        c = base
        base = re.sub(descriptive, "", c).strip()
    return c


def to_schema(rec: dict, rid: str, as_of: dt.date) -> dict:
    status = status_as_of(rec, as_of)
    conf = rec.get("confidence") or 0.7
    if rec.get("source_origin") != "starter_corpus":
        conf = min(conf, 0.75)
    return {
        "team_rule_id": rid,
        "jurisdiction": rec["jurisdiction"],
        "level": rec["level"],
        "category": rec["category"],
        "status": status,
        "title": rec["title"],
        "requirement": rec["requirement"],
        "key_value": rec.get("key_value"),
        "coverage_conditions": rec.get("coverage_conditions"),
        "exemptions": rec.get("exemptions"),
        "overrides": [],
        "interaction": rec.get("interaction"),
        "effective_date": rec.get("effective_date"),
        "citation": canon_citation(clean_citation(rec["citation"])),
        "penalty": rec.get("penalty"),
        "source_doc_id": rec["source_doc_id"],
        "source_url": rec["source_url"],
        "quoted_span": rec["quoted_span"],
        "confidence": round(conf, 2),
        "conflict_flag": bool(rec.get("conflict_flag")),
        "conflict_note": rec.get("conflict_note"),
        # Extensions used by the lookup engine and UI (ignored by the schema).
        "instrument_status": rec["instrument_status"],
        "coverage": rec["coverage"],
        "retrieved_at": rec.get("retrieved_at"),
        "source_origin": rec.get("source_origin"),
        "extraction_origins": rec.get("origins", ["doc"]),
        "span_match": rec.get("span_match"),
        "source_type": rec.get("source_type"),
        "supporting_sources": [{"doc_id": d, "url": u} for d, u in rec.get("supporting_sources", [])],
    }


def link_overrides(rules: list[dict]) -> None:
    """Fill `overrides` both ways for state rules that yield to local rules."""
    for r in rules:
        if r["level"] == "state" and r["coverage"].get("yields_to_local"):
            locals_ = [x for x in rules if x["level"] == "city" and x["category"] == r["category"]
                       and state_of(x["jurisdiction"]) == r["jurisdiction"]
                       and x["instrument_status"] == "enacted"]
            r["overrides"] = [x["team_rule_id"] for x in locals_]
            if locals_ and not r["interaction"]:
                r["interaction"] = "Yields to the listed local rules where they cover the unit."
            for x in locals_:
                x["overrides"] = sorted(set(x["overrides"]) | {r["team_rule_id"]})
                x["interaction"] = x["interaction"] or f"Governs over state rule {r['team_rule_id']} where it covers the unit."


def prune_with_grid(merged: list[dict], grid: dict) -> tuple[list[dict], list[dict]]:
    """The cell pass is the backbone. A rule only the per-document pass found is set
    aside as supplementary when its cell says there is no rule at that level, or when
    the cell pass already found an enacted rule for that cell."""
    kept, extra = [], []
    cell_enacted = {(r["jurisdiction"], r["category"]) for r in merged
                    if "cell" in r.get("origins", []) and r["instrument_status"] == "enacted"}
    for r in merged:
        key = (r["jurisdiction"], r["category"])
        doc_only = r.get("origins", ["doc"]) == ["doc"]
        status = grid.get(f"{key[0]}|{key[1]}")
        if doc_only and (status == "no_rule_stated"
                         or (r["instrument_status"] == "enacted" and key in cell_enacted)):
            r["supplementary_reason"] = ("cell pass found no rule at this level" if status == "no_rule_stated"
                                         else "cell pass already found the governing enacted rule")
            extra.append(r)
            audit({"event": "set_aside_supplementary", "jurisdiction": key[0], "category": key[1],
                   "citation": r["citation"], "reason": r["supplementary_reason"]})
        else:
            kept.append(r)
    return kept, extra


async def run(candidates: list[dict], as_of: dt.date, use_llm: bool = True,
              grid: dict | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    rules_in, findings = [], []
    for i, c in enumerate(candidates):
        if c.get("no_rule_finding"):
            j = canonical_jurisdiction(c["jurisdiction"])
            if j:
                findings.append({**c, "jurisdiction": j})
            continue
        j = canonical_jurisdiction(c["jurisdiction"])
        if not j:
            audit({"event": "out_of_scope", "jurisdiction": c["jurisdiction"], "citation": c["citation"]})
            continue
        level = "state" if j in STATES else "city"
        rules_in.append({**c, "jurisdiction": j, "level": level, "id": f"c{i:04d}"})

    merged, preempt_findings = [], []
    for st in STATES:
        cands = [c for c in rules_in if state_of(c["jurisdiction"]) == st]
        if not cands:
            continue
        if use_llm:
            try:
                rules_st, nr = await reconcile_state(st, cands)
                merged += rules_st
                preempt_findings += nr
                continue
            except (llm.BudgetExceeded, RuntimeError, ValueError) as e:
                audit({"event": "reconcile_fallback", "state": st, "error": repr(e)})
        merged += reconcile_deterministic(cands)

    order = {c: i for i, c in enumerate(("rent_increase_limits", "just_cause_eviction", "security_deposits",
                                         "application_screening_fees", "screening_restrictions",
                                         "algorithmic_rent_setting"))}
    merged, supplementary = prune_with_grid(merged, grid or {})
    merged.sort(key=lambda r: (state_of(r["jurisdiction"]), r["level"] != "state", r["jurisdiction"],
                               order[r["category"]], r["citation"]))
    rules = [to_schema(r, f"r-{i + 1:04d}", as_of) for i, r in enumerate(merged)]
    link_overrides(rules)
    no_rule = preempt_findings + [
        {"jurisdiction": f["jurisdiction"], "category": f["category"], "finding": f["finding"],
         "quoted_span": f["quoted_span"], "source_doc_id": f["source_doc_id"],
         "source_url": f["source_url"]} for f in findings]
    extra = [to_schema(r, f"s-{i + 1:04d}", as_of) | {"supplementary_reason": r["supplementary_reason"]}
             for i, r in enumerate(supplementary)]
    return rules, no_rule, extra
