"""Effective-date semantics for time travel.

Many extracted effective dates are amendments or annual adjustments of a rule
that already existed (e.g. San Francisco's 2026 allowable increase, an amended
deposit cap). Querying an earlier date must not report such a rule as "not yet
effective". One cached call classifies each dated rule; the engine then treats
an earlier date as covered by the prior version of the rule.
"""

import hashlib
import json

from . import llm
from .extract import audit
from .paths import WORK

SYSTEM = """For each rental-housing rule below, decide what its effective_date means.

prior_version_in_force = true when a rule with the same basic requirement already applied before effective_date, i.e. the date is an amendment, an annual adjustment of a figure, a re-codification, or a new rate for an existing program (e.g. a city's annual allowable rent increase under long-standing rent control; a deposit cap that was lowered by a later bill).
prior_version_in_force = false when the requirement itself is new as of effective_date (e.g. a newly enacted ban on algorithmic rent-setting, a first-ever fee cap).

Base the answer on the rule text, title and quote given. When unsure, answer false. Give a short reason."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "prior_version_in_force", "reason"],
        "properties": {"id": {"type": "string"}, "prior_version_in_force": {"type": "boolean"},
                       "reason": {"type": "string"}}}}},
}


async def classify(rules: list[dict]) -> None:
    dated = [r for r in rules if r.get("effective_date") and r.get("instrument_status") == "enacted"]
    if not dated:
        return
    payload = json.dumps([{"id": r["team_rule_id"], "jurisdiction": r["jurisdiction"], "title": r["title"],
                           "citation": r["citation"], "effective_date": r["effective_date"],
                           "requirement": r["requirement"], "quote": r["quoted_span"][:400]} for r in dated],
                         ensure_ascii=False)
    key = hashlib.sha256(f"{SYSTEM}|{payload}".encode()).hexdigest()[:20]
    cache = WORK / "dates_cache" / f"{key}.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            data, meta = await llm.structured_call(SYSTEM, payload, SCHEMA, effort="low")
        except (llm.BudgetExceeded, RuntimeError, ValueError) as e:
            audit({"event": "dates_skipped", "error": repr(e)})
            return
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        audit({"event": "llm_dates", **meta, "n": len(data["items"])})
    by_id = {i["id"]: i for i in data["items"]}
    for r in rules:
        item = by_id.get(r["team_rule_id"])
        if item:
            r["prior_version_in_force"] = item["prior_version_in_force"]
            r["effective_date_note"] = item["reason"]
