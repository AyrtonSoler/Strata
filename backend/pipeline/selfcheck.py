"""Self-check of the submission files (the organizers' score.py was not in the
participant pack, so this reproduces the checks we can verify ourselves).

    uv run python -m pipeline.selfcheck
"""

import json
import sys
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
    # Link-only pages fetched once are not redistributed in the repo (publisher terms); a fresh
    # checkout verifies every quote whose source text it has and reports the rest separately.
    checkable = [r for r in rules if r["source_doc_id"] in docs]
    verified = sum(1 for r in checkable if _norm(r["quoted_span"]) in _norm(docs[r["source_doc_id"]].text))
    line("quoted spans found verbatim in their source document", f"{verified}/{len(checkable)}", verified == len(checkable))
    if len(checkable) < len(rules):
        print(f"         {len(rules) - len(checkable)} more cite link-only pages whose text is not redistributed; "
              "they were verified when the pipeline fetched them")
    starter = sum(1 for r in rules if r.get("source_origin") == "starter_corpus")
    print(f"         {starter} from the starter corpus, {len(rules) - starter} from link-only sources fetched once")
    print(f"         by status: {dict(Counter(r['status'] for r in rules))}")
    print(f"         by category: {dict(Counter(r['category'] for r in rules))}")
    open_q = [r for r in rules if r.get("open_questions")]
    print(f"         open questions flagged for review: {len(open_q)} "
          f"({', '.join(r['citation'] for r in open_q) or 'none'})")
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

    print("\nKnown-answer tests (from the brief's illustrative output and the participant guide)")
    passed, total = known_answers(rules, lk, addrs)
    line("known answers", f"{passed}/{total}", passed == total)

    print("\nOVERALL:", "ALL CHECKS PASS" if ok else "SOME CHECKS FAILED")
    if not ok:
        sys.exit(1)


def known_answers(rules, lookups, addrs) -> tuple[int, int]:
    """Expectations stated in the challenge materials, checked against our lookups."""
    import re as _re

    def find(city, pred):
        return next((a for a in addrs if a["jurisdiction_city"] == city and pred(a)), None)

    def result(addr, jur, cat, cite=None):
        rows = [x for x in lookups[addr["address_id"]] if (r := by_id[x["team_rule_id"]])["jurisdiction"] == jur
                and r["category"] == cat and (not cite or _re.search(cite, r["citation"]))]
        order = ["applies", "unknown", "not_yet_effective", "pending", "superseded"]
        return min((x["result"] for x in rows), key=order.index) if rows else "absent"

    by_id = {r["team_rule_id"]: r for r in rules}
    sf_old = find("San Francisco, CA", lambda a: a["year_built"] and a["year_built"] < 1979 and (a["units"] or 0) >= 5)
    sf_new = find("San Francisco, CA", lambda a: a["year_built"] and a["year_built"] > 1985)
    la_old = find("Los Angeles, CA", lambda a: a["year_built"] and a["year_built"] < 1978)
    la_mid = find("Los Angeles, CA", lambda a: a["year_built"] and 1980 <= a["year_built"] <= 2005)
    sd = find("San Diego, CA", lambda a: a["year_built"] is None and not a.get("year_built_max"))
    sd_old = find("San Diego, CA", lambda a: a["year_built"] is None and (a.get("year_built_max") or 9999) < 2000)
    jc, hob, nwk = (find(c, lambda a: True) for c in ("Jersey City, NJ", "Hoboken, NJ", "Newark, NJ"))
    bos, cam = find("Boston, MA", lambda a: True), find("Cambridge, MA", lambda a: True)
    cases = [
        ("SF pre-1979, 5+ units: SF Rent Ordinance applies", sf_old, "San Francisco, CA", "rent_increase_limits", r"37", "applies"),
        ("SF pre-1979: CA § 1947.12 cap yields to local rent control", sf_old, "CA", "rent_increase_limits", r"1947\.12", "superseded"),
        ("SF: just cause under S.F. Admin. Code § 37.9 applies", sf_old, "San Francisco, CA", "just_cause_eviction", r"37\.9", "applies"),
        ("SF: CA § 1946.2 just cause yields to local ordinance", sf_old, "CA", "just_cause_eviction", r"1946\.2", "superseded"),
        ("SF 20-unit: deposit cap applies (small-landlord exception can't apply)", sf_old, "CA", "security_deposits", r"1950\.5", "applies"),
        ("SF: screening fee cap § 1950.6 applies", sf_old, "CA", "application_screening_fees", r"1950\.6", "applies"),
        ("SF: local algorithmic ban § 37.10C applies", sf_old, "San Francisco, CA", "algorithmic_rent_setting", r"37\.10C", "applies"),
        ("SF post-1979: SF rent control does not cover it", sf_new, "San Francisco, CA", "rent_increase_limits", r"37", "absent"),
        ("LA pre-1978: RSO applies", la_old, "Los Angeles, CA", "rent_increase_limits", r"151", "applies"),
        ("LA 1980-2005: RSO does not cover it", la_mid, "Los Angeles, CA", "rent_increase_limits", r"151", "absent"),
        ("LA 1980-2005: state cap § 1947.12 applies instead", la_mid, "CA", "rent_increase_limits", r"1947\.12", "applies"),
        ("San Diego, no year built and no parcel match: state cap is unknown", sd, "CA", "rent_increase_limits", r"1947\.12", "unknown"),
        ("San Diego, parcel effective year pre-2000: older than 15 years, state cap applies", sd_old, "CA", "rent_increase_limits", r"1947\.12", "applies"),
        ("Jersey City: JC algorithmic ban applies", jc, "Jersey City, NJ", "algorithmic_rent_setting", None, "applies"),
        ("Hoboken: Hoboken algorithmic ban applies", hob, "Hoboken, NJ", "algorithmic_rent_setting", None, "applies"),
        ("Newark: no local algorithmic ban", nwk, "Newark, NJ", "algorithmic_rent_setting", None, "absent"),
        ("NJ: FAIR Act not yet effective on 2026-10-01", nwk, "NJ", "algorithmic_rent_setting", None, "not_yet_effective"),
        ("NJ: deposit cap N.J.S.A. 46:8-21.x applies", jc, "NJ", "security_deposits", r"46:8-21", "applies"),
        ("Boston: no rent cap reported", bos, "MA", "rent_increase_limits", None, "absent"),
        ("Cambridge: MA algorithmic bills reported as pending", cam, "MA", "algorithmic_rent_setting", None, "pending"),
        ("Boston: deposit rule M.G.L. c. 186, § 15B applies", bos, "MA", "security_deposits", r"15B", "applies"),
    ]
    passed = 0
    for desc, addr, jur, cat, cite, expected in cases:
        got = result(addr, jur, cat, cite) if addr else "no matching address"
        ok = got == expected
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}" + ("" if ok else f" (expected {expected}, got {got})")
              + (f" [{addr['address_id']}]" if addr else ""))
    return passed, len(cases)


if __name__ == "__main__":
    main()
