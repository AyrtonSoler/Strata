"""End-to-end pipeline: extract -> reconcile -> lookups -> changes.

    uv run python -m pipeline.run_all              # full run (uses cache)
    uv run python -m pipeline.run_all --no-llm     # reuse cached extraction only
    uv run python -m pipeline.run_all --as-of 2027-07-02
"""

import argparse
import asyncio
import datetime as dt
import json

from . import dates, extract, llm, reconcile, translate
from .changes import run_test
from .engine import lookup, parse_date, public_rows
from .paths import (ADDRESSES_RESOLVED, CHANGE_TESTS, CHANGES_OUT, DEFAULT_AS_OF, EXTRA_DIR,
                    LOOKUPS_OUT, RULES_OUT, SUBMISSION)


def load_tests() -> list[dict]:
    tests = json.loads(CHANGE_TESTS.read_text())
    extra = EXTRA_DIR / "change_tests_extra.json"  # e.g. T6 released at hour 16
    if extra.exists():
        tests += json.loads(extra.read_text())
    return tests


async def main(as_of: str, use_llm: bool) -> None:
    as_of_d = parse_date(as_of)
    candidates = await extract.run()
    print(f"extracted {len(candidates)} verified candidates (spent ${llm.spent_usd():.2f})")
    rules, no_rule = await reconcile.run(candidates, as_of_d, use_llm=use_llm)
    print(f"reconciled into {len(rules)} rules (spent ${llm.spent_usd():.2f})")
    if use_llm:
        await dates.classify(rules)
        await translate.add_spanish(rules)

    SUBMISSION.mkdir(exist_ok=True)
    RULES_OUT.write_text(json.dumps({"as_of": as_of, "rules": rules, "no_rule_findings": no_rule},
                                    indent=1, ensure_ascii=False), encoding="utf-8")

    addrs = json.loads(ADDRESSES_RESOLVED.read_text())
    lookups = {a["address_id"]: public_rows(lookup(a, rules, as_of_d)) for a in addrs}
    LOOKUPS_OUT.write_text(json.dumps({"as_of": as_of, "lookups": lookups}, indent=1, ensure_ascii=False),
                           encoding="utf-8")

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
