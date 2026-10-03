"""Self-check of the submission files (the organizers' score.py was not in the
participant pack, so this reproduces the checks we can verify ourselves).

    uv run python -m pipeline.selfcheck
"""

import json
from collections import Counter

import jsonschema

from .extract import _norm, load_docs
from .paths import ADDRESSES_RESOLVED, CHANGES_OUT, LOOKUPS_OUT, PACK, RULES_OUT

VALID_RESULTS = {"applies", "unknown", "superseded", "not_yet_effective", "pending"}


def main() -> None:
    schema = json.loads((PACK / "schema" / "rule_record.schema.json").read_text())
    rules = json.loads(RULES_OUT.read_text(encoding="utf-8"))["rules"]
    lookups = json.loads(LOOKUPS_OUT.read_text(encoding="utf-8"))
    changes = json.loads(CHANGES_OUT.read_text(encoding="utf-8"))
    addrs = json.loads(ADDRESSES_RESOLVED.read_text())
    docs = {d.doc_id: d for d in load_docs()}
    by_id = {r["team_rule_id"]: r for r in rules}
    ok = True

    def line(label, value, good=True):
        nonlocal ok
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] {label}: {value}")

    print("Module A - extraction (rules.json)")
    errors = [(r["team_rule_id"], e.message) for r in rules
              for e in jsonschema.Draft202012Validator(schema).iter_errors(r)]
    line("rule records valid against rule_record.schema.json", f"{len(rules) - len({e[0] for e in errors})}/{len(rules)}", not errors)
    for rid, msg in errors[:5]:
        print(f"         {rid}: {msg}")
    verified = sum(1 for r in rules if r["source_doc_id"] in docs
                   and _norm(r["quoted_span"]) in _norm(docs[r["source_doc_id"]].text))
    line("quoted spans found verbatim in their source document", f"{verified}/{len(rules)}", verified == len(rules))
    starter = sum(1 for r in rules if r.get("source_origin") == "starter_corpus")
    print(f"         {starter} from the starter corpus, {len(rules) - starter} from link-only sources fetched once")
    print(f"         by status: {dict(Counter(r['status'] for r in rules))}")
    print(f"         by category: {dict(Counter(r['category'] for r in rules))}")
    print(f"         jurisdictions: {len({r['jurisdiction'] for r in rules})} "
          f"({', '.join(sorted({r['jurisdiction'] for r in rules}))})")

    print("\nModule B - address lookups (lookups.json)")
    lk = lookups["lookups"]
    line("addresses covered", f"{len(lk)}/{len(addrs)}", len(lk) == len(addrs))
    rows = [x for v in lk.values() for x in v]
    bad = [x for x in rows if x["result"] not in VALID_RESULTS or x["team_rule_id"] not in by_id]
    line("result values and rule ids valid", f"{len(rows) - len(bad)}/{len(rows)}", not bad)
    applies = [x for x in rows if x["result"] == "applies"]
    backed = sum(1 for x in applies if by_id[x["team_rule_id"]]["quoted_span"] and by_id[x["team_rule_id"]]["source_url"])
    line("'applies' answers backed by a source + quoted span", f"{backed}/{len(applies)}", backed == len(applies))
    from_corpus = sum(1 for x in applies if by_id[x["team_rule_id"]].get("source_origin") == "starter_corpus")
    print(f"         {from_corpus / max(1, len(applies)):.0%} of 'applies' answers cite a starter-corpus document")
    print(f"         results: {dict(Counter(x['result'] for x in rows))}")
    resolved = Counter(a["resolution_method"] for a in addrs)
    print(f"         jurisdiction resolution: {dict(resolved)}")
    ma = [x for a in addrs if a["state"] == "MA" for x in lk[a["address_id"]]
          if by_id[x["team_rule_id"]]["category"] == "rent_increase_limits" and x["result"] in ("applies", "unknown")]
    line("no rent cap reported for any Boston/Cambridge address", f"{len(ma)} found", not ma)

    print("\nModule C - change tracking (changes.json)")
    state_ids = {s: {a["address_id"] for a in addrs if a["state"] == s} for s in ("CA", "NJ", "MA")}
    city_ids = lambda c: {a["address_id"] for a in addrs if a["jurisdiction_city"] == c}  # noqa: E731
    expect = {
        "T1": (state_ids["CA"], set()),
        "T2": (city_ids("Hoboken, NJ") | city_ids("Jersey City, NJ"), set()),
        "T3": (state_ids["NJ"], city_ids("Hoboken, NJ") | city_ids("Jersey City, NJ")),
        "T4": (state_ids["MA"], set()),
        "T5": (set(), set()),
    }
    for tid, (aff, flag) in expect.items():
        got = changes.get(tid, {})
        ga, gf = set(got.get("affected_address_ids", [])), set(got.get("conflict_flag_address_ids", []))
        inter = len(ga & aff)
        jacc = 1.0 if not ga and not aff else inter / len(ga | aff)
        fj = 1.0 if not gf and not flag else len(gf & flag) / len(gf | flag)
        line(f"{tid} affected-set overlap with expected behavior", f"{jacc:.0%} ({len(ga)} vs {len(aff)})"
             + (f", conflict flags {fj:.0%}" if flag else ""), jacc == 1.0 and fj == 1.0)
    for tid in sorted(set(changes) - set(expect)):
        print(f"  [INFO] {tid}: {len(changes[tid]['affected_address_ids'])} affected - {changes[tid]['notes'][:120]}")

    print("\nOVERALL:", "ALL CHECKS PASS" if ok else "SOME CHECKS FAILED")


if __name__ == "__main__":
    main()
