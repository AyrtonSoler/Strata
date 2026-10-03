from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data" / "pack"
CORPUS_DIR = PACK / "corpus" / "text"
MANIFEST = PACK / "corpus" / "corpus_manifest.csv"
ADDRESSES = PACK / "data" / "sample_addresses.csv"
CHANGE_TESTS = PACK / "dev" / "change_tests.json"

# Extra documents dropped in later (e.g. the hour-16 ordinance) go here as
# <doc_id>.txt plus a row in extra_manifest.csv with the same columns.
EXTRA_DIR = ROOT / "data" / "extra"

WORK = ROOT / "data" / "work"
GEOCODE_CACHE = WORK / "geocode_cache.json"
EXTRACT_CACHE = WORK / "extract_cache"
AUDIT_LOG = WORK / "audit_log.jsonl"

SUBMISSION = ROOT / "submission"
ADDRESSES_RESOLVED = SUBMISSION / "addresses_resolved.json"
RULES_OUT = SUBMISSION / "rules.json"
LOOKUPS_OUT = SUBMISSION / "lookups.json"
CHANGES_OUT = SUBMISSION / "changes.json"

DEFAULT_AS_OF = "2026-10-01"
