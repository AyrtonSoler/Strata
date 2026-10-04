"""End-to-end pipeline: extract -> reconcile -> lookups -> changes.

    uv run python -m pipeline.run_all              # full run (uses cache)
    uv run python -m pipeline.run_all --no-llm     # reuse cached extraction only
    uv run python -m pipeline.run_all --as-of 2027-07-02
"""

import argparse
import asyncio
import datetime as dt
import json

from . import cells, dates, extract, llm, open_questions, reconcile, translate, verify
from .changes import run_test
from .engine import lookup, parse_date, public_rows
from .paths import (ADDRESSES_RESOLVED, CHANGE_TESTS, CHANGES_OUT, DEFAULT_AS_OF, EXTENSION_OUT,
                    EXTENSION_RESOLVED, EXTRA_DIR,
                    LOOKUPS_OUT, RULES_OUT, SUBMISSION)


def load_tests() -> list[dict]:
    tests = json.loads(CHANGE_TESTS.read_text())
    extra = EXTRA_DIR / "change_tests_extra.json"  # optional extra change cases
    if extra.exists():
        tests += json.loads(extra.read_text())
    return tests


async def main(as_of: str, use_llm: bool) -> None:
    as_of_d = parse_date(as_of)
    candidates = await extract.run()
    cell_candidates, grid = await cells.run()
    print(f"extracted {len(candidates)} per-document + {len(cell_candidates)} per-cell verified candidates "
          f"(spent ${llm.spent_usd():.2f})")
    candidates += cell_candidates
    rules, no_rule, supplementary = await reconcile.run(candidates, as_of_d, use_llm=use_llm, grid=grid)
    print(f"reconciled into {len(rules)} rules + {len(supplementary)} supplementary (spent ${llm.spent_usd():.2f})")
    if use_llm:
        await verify.run(rules)
        print(f"verified {len(rules)} rules: {sum(r['verification']['verdict'] == 'review' for r in rules)} "
              f"flagged for review (spent ${llm.spent_usd():.2f})")
        await dates.classify(rules)
        await translate.add_spanish(rules)
    print(f"open questions surfaced on {open_questions.flag(rules)} rules")

    SUBMISSION.mkdir(exist_ok=True)
    RULES_OUT.write_text(json.dumps({"as_of": as_of, "rules": rules, "no_rule_findings": no_rule,
                                     "coverage_grid": grid, "supplementary_rules": supplementary},
                                    indent=1, ensure_ascii=False), encoding="utf-8")

    addrs = json.loads(ADDRESSES_RESOLVED.read_text())
    lookups = {a["address_id"]: public_rows(lookup(a, rules, as_of_d)) for a in addrs}
    LOOKUPS_OUT.write_text(json.dumps({"as_of": as_of, "lookups": lookups}, indent=1, ensure_ascii=False),
                           encoding="utf-8")

    if EXTENSION_RESOLVED.exists():  # stretch goal: new jurisdiction, kept out of the official lookups.json
        ext = json.loads(EXTENSION_RESOLVED.read_text())
        EXTENSION_OUT.write_text(json.dumps({
            "as_of": as_of, "jurisdiction": "Oakland, CA",
            "note": "Extension sample (Alameda County Secured Tax Roll); not part of the supplied 500 addresses.",
            "lookups": {a["address_id"]: public_rows(lookup(a, rules, as_of_d)) for a in ext}},
            indent=1, ensure_ascii=False), encoding="utf-8")

    changes = {t["test_id"]: run_test(t, rules, addrs) for t in load_tests()}
    CHANGES_OUT.write_text(json.dumps(changes, indent=1, ensure_ascii=False), encoding="utf-8")
    for tid, c in changes.items():
        print(f"{tid}: {len(c['affected_address_ids'])} affected, {len(c['conflict_flag_address_ids'])} flagged | {c['notes'][:160]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=DEFAULT_AS_OF)
    ap.add_argument("--no-llm", action="store_true", help="deterministic reconcile (extraction cache still used)")
    args = ap.parse_args()
    asyncio.run(main(args.as_of, not args.no_llm))
