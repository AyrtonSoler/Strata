"""Module C: change tracking.

Each test names answer-key rule ids such as "CA-ALG-01", "HOB-ALG-01" or
"MA-ALG-P2". We map those to our own extracted rules by jurisdiction + category
(+ pending/failed status for P-suffixed ids), then compare per-address results
across dates, or report who a pending/failed instrument would affect.
"""

import datetime as dt
import re

from .engine import evaluate_coverage, jurisdiction_stack, lookup, parse_date

JUR_CODES = {
    "CA": "CA", "NJ": "NJ", "MA": "MA",
    "LA": "Los Angeles, CA", "SF": "San Francisco, CA", "SD": "San Diego, CA", "BER": "Berkeley, CA",
    "BERK": "Berkeley, CA", "SA": "Santa Ana, CA", "JC": "Jersey City, NJ", "HOB": "Hoboken, NJ",
    "NWK": "Newark, NJ", "NEW": "Newark, NJ", "BOS": "Boston, MA", "CAM": "Cambridge, MA",
    "CAMB": "Cambridge, MA",
}
CAT_CODES = {
    "RENT": "rent_increase_limits", "RC": "rent_increase_limits", "JC": "just_cause_eviction",
    "JCE": "just_cause_eviction", "EVIC": "just_cause_eviction", "EVICT": "just_cause_eviction",
    "DEP": "security_deposits", "FEE": "application_screening_fees", "APP": "application_screening_fees",
    "SCR": "screening_restrictions", "SCREEN": "screening_restrictions", "ALG": "algorithmic_rent_setting",
}


def map_rule_id(key_id: str, rules: list[dict]) -> list[dict]:
    m = re.match(r"^([A-Z]+)-([A-Z]+)-(P?)(\d+)$", key_id)
    if not m:
        return []
    jur, cat = JUR_CODES.get(m[1]), CAT_CODES.get(m[2])
    is_p, n = m[3] == "P", int(m[4])
    cands = [r for r in rules if r["jurisdiction"] == jur and r["category"] == cat]
    if is_p:
        cands = [r for r in cands if r["instrument_status"] in ("pending", "failed")]
        # P1, P2: order by citation so S.2983 / H.5222 are stable.
        cands.sort(key=lambda r: r["citation"])
        return cands[n - 1: n] if len(cands) >= n else cands[-1:]
    enacted = [r for r in cands if r["instrument_status"] == "enacted"]
    return enacted or cands


def _results(addrs, rules, as_of, ids):
    out = {}
    for a in addrs:
        rows = lookup(a, rules, as_of)
        out[a["address_id"]] = {r["team_rule_id"]: r for r in rows if r["team_rule_id"] in ids}
    return out


def run_test(test: dict, rules: list[dict], addrs: list[dict]) -> dict:
    mapped = {k: map_rule_id(k, rules) for k in test["rule_ids"]}
    ids = {r["team_rule_id"] for rs in mapped.values() for r in rs}
    sel = [r for r in rules if r["team_rule_id"] in ids]
    states = set(test.get("states") or [])
    pool = [a for a in addrs if not states or a["state"] in states]
    mapping_note = "; ".join(f"{k} -> {', '.join(r['team_rule_id'] + ' (' + r['citation'] + ')' for r in v) or 'NO MATCH'}"
                             for k, v in mapped.items())
    affected, flagged, detail = [], [], {}
    t = test["type"]

    if t == "as_of":
        before = _results(pool, rules, parse_date(test["as_of_before"]), ids)
        after = _results(pool, rules, parse_date(test["as_of_after"]), ids)
        for a in pool:
            aid = a["address_id"]
            b = {k: v["result"] for k, v in before[aid].items()}
            f = {k: v["result"] for k, v in after[aid].items()}
            if b != f and f:
                affected.append(aid)
                detail[aid] = {"before": b, "after": f}
        conflict_rules = {r["team_rule_id"] for k in test.get("conflict_with", []) for r in map_rule_id(k, rules)}
        if conflict_rules:
            later = _results(pool, rules, parse_date(test["as_of_after"]), conflict_rules)
            flagged = [aid for aid in affected if later[aid]]
        notes = (f"Compared results on {test['as_of_before']} vs {test['as_of_after']}. {len(affected)} addresses change. "
                 f"Mapping: {mapping_note}.")
        if conflict_rules:
            notes += (f" {len(flagged)} addresses are also covered by {sorted(conflict_rules)}: flagged for human review "
                      "of possible preemption.")

    elif t in ("boundary", "negative"):
        as_of = parse_date(test["as_of"])
        res = _results(pool if states else addrs, rules, as_of, ids)
        for aid, rows in res.items():
            if any(r["result"] in ("applies", "unknown") for r in rows.values()):
                affected.append(aid)
                detail[aid] = {k: v["result"] for k, v in rows.items()}
        if t == "negative":
            statuses = sorted({r["instrument_status"] for r in sel})
            notes = (f"Instrument status: {statuses or ['not extracted']}. A failed or struck measure never applies, "
                     f"so the affected set is {'empty' if not affected else 'NOT empty - review'}. Mapping: {mapping_note}.")
        else:
            by_rule = {}
            for aid, d in detail.items():
                for k in d:
                    by_rule[k] = by_rule.get(k, 0) + 1
            notes = f"Rule coverage by address as of {test['as_of']}: {by_rule}. Mapping: {mapping_note}."

    elif t == "pending":
        as_of = parse_date(test["as_of"])
        for a in pool:
            if not set(jurisdiction_stack(a)) & {r["jurisdiction"] for r in sel}:
                continue
            covs = [evaluate_coverage(r, a, as_of)[0] for r in sel
                    if r["jurisdiction"] in jurisdiction_stack(a)]
            if any(c != "not_covered" for c in covs):
                affected.append(a["address_id"])
        notes = (f"Pending, not in force on {test['as_of']}; lookups report 'pending'. Listed addresses would be "
                 f"covered if enacted. Mapping: {mapping_note}.")

    else:  # e.g. a new ordinance: who does it cover once effective?
        rule_dates = [parse_date(r.get("effective_date")) for r in sel if r.get("effective_date")]
        as_of = parse_date(test.get("as_of_after") or test.get("as_of")) or \
            (max(rule_dates) + dt.timedelta(days=1) if rule_dates else dt.date(2026, 10, 1))
        res = _results(pool, rules, as_of, ids)
        for aid, rows in res.items():
            if rows:
                affected.append(aid)
                detail[aid] = {k: v["result"] for k, v in rows.items()}
        notes = f"Coverage as of {as_of}. Mapping: {mapping_note}."

    return {"affected_address_ids": sorted(affected), "conflict_flag_address_ids": sorted(flagged),
            "notes": notes, "mapped_rules": {k: [r["team_rule_id"] for r in v] for k, v in mapped.items()},
            "detail": detail}
