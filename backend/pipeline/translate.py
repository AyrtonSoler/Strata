"""Stretch goal: renter-facing Spanish view. One cached call translates each rule's
title and plain-language requirement; citations and quotes stay in the original."""

import hashlib
import json

from . import llm
from .extract import audit
from .paths import WORK

SYSTEM = ("Translate U.S. rental-housing rule summaries into clear, plain Latin American Spanish that a renter "
          "can act on. Keep numbers, dollar amounts, dates and legal citations exactly as written. Do not add "
          "advice. Return one item per input id.")
SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "title_es", "requirement_es", "key_value_es"],
        "properties": {"id": {"type": "string"}, "title_es": {"type": "string"},
                       "requirement_es": {"type": "string"},
                       "key_value_es": {"type": ["string", "null"]}}}}},
}


async def add_spanish(rules: list[dict]) -> None:
    payload = json.dumps([{"id": r["team_rule_id"], "title": r["title"], "requirement": r["requirement"],
                           "key_value": r.get("key_value")} for r in rules], ensure_ascii=False)
    key = hashlib.sha256(f"{SYSTEM}|{json.dumps(SCHEMA)}|{payload}".encode()).hexdigest()[:20]
    cache = WORK / "translate_cache" / f"es_{key}.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            data, meta = await llm.structured_call(SYSTEM, payload, SCHEMA, effort="low")
        except (llm.BudgetExceeded, RuntimeError, ValueError) as e:
            audit({"event": "translate_skipped", "error": repr(e)})
            return
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        audit({"event": "llm_translate", **meta, "n": len(data["items"])})
    by_id = {i["id"]: i for i in data["items"]}
    for r in rules:
        if r["team_rule_id"] in by_id:
            r["title_es"] = by_id[r["team_rule_id"]]["title_es"]
            r["requirement_es"] = by_id[r["team_rule_id"]]["requirement_es"]
            r["key_value_es"] = by_id[r["team_rule_id"]].get("key_value_es")
