"""Verification and calibrated confidence for every reconciled rule.

1. Field-level grounding (code): is the effective date, and are the numbers in the
   key value, actually present in the source document?
2. Chain-of-verification (LLM): a second, independent pass reads each rule next to
   its quote and surrounding text and checks the requirement, citation, date and
   status. It does not rewrite anything; disagreements mark the rule for review.
3. Calibrated confidence from objective signals instead of the extractor's
   self-reported number. The signals are kept so the UI can show why.
"""

import datetime as dt
import hashlib
import json
import re

from . import llm
from .extract import audit, load_docs
from .paths import WORK
from .textmatch import locate_span

CONTEXT = 1500
BATCH = 12

SYSTEM = """You are a careful legal fact-checker. For each extracted rule you get the claimed fields and the source passage (the exact quote plus surrounding text from the official or cited document). Judge ONLY from the passage:
- requirement_supported: "yes" if the passage supports the plain-language requirement, "partial" if it supports part of it, "no" if it does not.
- citation_consistent: "yes" if the citation matches the law the passage is from or describes, "no" if it is clearly a different law, "unclear" otherwise.
- date_supported: "yes" if the passage states or clearly implies the claimed effective date, "no" if it states a different date, "not_stated" if no date is given in the passage.
- status_supported: "yes" if the passage supports the claimed status (enacted / pending bill / failed measure), "no" if it contradicts it, "unclear" otherwise.
- issue: one short sentence describing any problem, or null.
Do not give legal advice; do not rewrite the rule."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "requirement_supported", "citation_consistent", "date_supported", "status_supported", "issue"],
        "properties": {
            "id": {"type": "string"},
            "requirement_supported": {"type": "string", "enum": ["yes", "partial", "no"]},
            "citation_consistent": {"type": "string", "enum": ["yes", "no", "unclear"]},
            "date_supported": {"type": "string", "enum": ["yes", "no", "not_stated"]},
            "status_supported": {"type": "string", "enum": ["yes", "no", "unclear"]},
            "issue": {"type": ["string", "null"]},
        }}}},
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def _date_forms(iso: str) -> list[str]:
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$", iso or "")
    if not m:
        return []
    y, mo, d = m[1], m[2], m[3]
    if not mo:
        return [y]
    month = MONTHS[int(mo) - 1]
    if not d:
        return [f"{month} {y}", f"{month}, {y}", f"{int(mo)}/{y}"]
    return [f"{month} {int(d)}, {y}", f"{month} {int(d)} {y}", f"{int(mo)}/{int(d)}/{y}",
            f"{int(mo)}/{int(d)}/{y[2:]}", f"{y}-{mo}-{d}", f"{int(d)} {month} {y}"]


def ground_fields(rule: dict, text: str) -> dict:
    out = {}
    if rule.get("effective_date"):
        forms = _date_forms(rule["effective_date"])
        low = text.lower()
        if any(f.lower() in low for f in forms[:-1] or forms):
            out["date_in_source"] = "exact"
        elif rule["effective_date"][:4] in text:
            out["date_in_source"] = "year_only"
        else:
            out["date_in_source"] = "absent"
    nums = re.findall(r"\d+(?:\.\d+)?", rule.get("key_value") or "")
    nums = [n for n in nums if not re.fullmatch(r"(19|20)\d\d", n)]
    if nums:
        found = [n for n in nums if re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", text)]
        out["key_value_in_source"] = "all" if len(found) == len(nums) else ("some" if found else "none")
    return out


def calibrate(rule: dict) -> tuple[float, list[str]]:
    v = rule.get("verification", {})
    signals, score = [], 0.35
    if rule.get("source_origin") == "starter_corpus":
        score += 0.20
        signals.append("+ official text from the starter corpus")
    else:
        signals.append("· secondary source read once (not in the starter corpus)")
    if rule.get("span_match") == 1.0:
        score += 0.10
        signals.append("+ quote matches the source exactly")
    if set(rule.get("extraction_origins", [])) >= {"cell", "doc"}:
        score += 0.15
        signals.append("+ found independently by both extraction passes")
    if len(rule.get("supporting_sources", [])) >= 2:
        score += 0.10
        signals.append(f"+ supported by {len(rule['supporting_sources'])} sources")
    req = v.get("requirement_supported")
    if req == "yes":
        score += 0.10
        signals.append("+ verifier: quote supports the requirement")
    elif req == "partial":
        score += 0.04
        signals.append("· verifier: quote partly supports the requirement")
    if v.get("date_in_source") == "exact" or not rule.get("effective_date"):
        score += 0.05
    elif v.get("date_in_source") == "absent":
        signals.append("− effective date not found in the source text")
    if v.get("key_value_in_source") == "none":
        score -= 0.10
        signals.append("− key figure not found in the source text")
    if v.get("verdict") == "review":
        score -= 0.25
        signals.append("− verifier flagged it for human review")
    return round(min(0.97, max(0.05, score)), 2), signals


async def run(rules: list[dict]) -> None:
    docs = {d.doc_id: d for d in load_docs()}
    items = []
    for r in rules:
        d = docs.get(r.get("source_doc_id") or "")
        context = ""
        if d:
            span = locate_span(r["quoted_span"], d.text)
            a, b = span if span else (0, 0)
            context = d.text[max(0, a - CONTEXT): b + CONTEXT]
            r["verification"] = ground_fields(r, d.text)
        else:
            r["verification"] = {}
        items.append({"id": r["team_rule_id"], "jurisdiction": r["jurisdiction"], "level": r["level"],
                      "category": r["category"], "citation": r["citation"], "title": r["title"],
                      "requirement": r["requirement"], "key_value": r.get("key_value"),
                      "effective_date": r.get("effective_date"), "status": r.get("instrument_status"),
                      "quote": r["quoted_span"], "passage": context[:3200]})

    results = {}
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        payload = json.dumps(batch, ensure_ascii=False)
        key = hashlib.sha256(f"{SYSTEM}|{json.dumps(SCHEMA)}|{llm.MODEL}|{payload}".encode()).hexdigest()[:20]
        cache = WORK / "verify_cache" / f"{key}.json"
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
        else:
            try:
                data, meta = await llm.structured_call(SYSTEM, payload, SCHEMA, effort="medium")
            except (llm.BudgetExceeded, RuntimeError, ValueError) as e:
                audit({"event": "verify_skipped", "error": repr(e)})
                continue
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            audit({"event": "llm_verify", **meta, "n": len(batch)})
        results.update({x["id"]: x for x in data["items"]})

    for r in rules:
        v = results.get(r["team_rule_id"])
        if v:
            r["verification"].update({k: v[k] for k in ("requirement_supported", "citation_consistent",
                                                         "date_supported", "status_supported", "issue")})
        flags = []
        ver = r["verification"]
        if ver.get("requirement_supported") == "no":
            flags.append("quote does not support the stated requirement")
        if ver.get("citation_consistent") == "no":
            flags.append("citation does not match the source")
        if ver.get("date_supported") == "no":
            flags.append("source states a different effective date")
        if ver.get("status_supported") == "no":
            flags.append("source contradicts the stated status")
        ver["verdict"] = "review" if flags else "pass"
        ver["review_reasons"] = flags
        ver["checked_at"] = dt.date.today().isoformat()
        r["model_confidence"] = r.get("confidence")
        r["confidence"], r["confidence_signals"] = calibrate(r)
