"""Ingest new documents and change tests (e.g. the hour-16 ordinance) and rerun.

    # pull the organizers' Drive folder again and pick up anything new
    uv run python -m pipeline.ingest --drive

    # or add one document by hand
    uv run python -m pipeline.ingest --file new.txt --doc-id H16 --jurisdiction "Cambridge, MA" --url https://...
    uv run python -m pipeline.ingest --tests t6.json

Extraction stays automated: new documents go through the same LLM extraction,
quote verification and reconciliation as the starter corpus.
"""

import argparse
import asyncio
import csv
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import CHANGE_TESTS, CORPUS_DIR, EXTRA_DIR, PACK, ROOT

DRIVE_URL = "https://drive.google.com/drive/folders/14TT6AEH8TStzoT5c5fZ45Bt4grODsowR"
EXTRA_MANIFEST = EXTRA_DIR / "extra_manifest.csv"
EXTRA_TESTS = EXTRA_DIR / "change_tests_extra.json"
FIELDS = ["doc_id", "jurisdictions", "url", "source_type", "retrieved_at"]


def add_document(path: Path, doc_id: str, jurisdiction: str, url: str, source_type: str = "official") -> None:
    EXTRA_DIR.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8", errors="replace")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if not text.startswith("SOURCE:"):
        text = f"SOURCE: {url}\nRETRIEVED: {now}\n\n{text}"
    (EXTRA_DIR / f"{doc_id}.txt").write_text(text, encoding="utf-8")
    rows = []
    if EXTRA_MANIFEST.exists():
        with open(EXTRA_MANIFEST, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["doc_id"] != doc_id]
    rows.append({"doc_id": doc_id, "jurisdictions": jurisdiction, "url": url, "source_type": source_type,
                 "retrieved_at": now})
    with open(EXTRA_MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"added {doc_id} ({jurisdiction}) from {path}")


def add_tests(path: Path) -> None:
    new = json.loads(path.read_text(encoding="utf-8"))
    new = new if isinstance(new, list) else [new]
    base_ids = {t["test_id"] for t in json.loads(CHANGE_TESTS.read_text())}
    existing = json.loads(EXTRA_TESTS.read_text()) if EXTRA_TESTS.exists() else []
    merged = {t["test_id"]: t for t in existing}
    for t in new:
        if t["test_id"] not in base_ids:
            merged[t["test_id"]] = t
    EXTRA_DIR.mkdir(parents=True, exist_ok=True)
    EXTRA_TESTS.write_text(json.dumps(list(merged.values()), indent=1))
    print(f"change tests now include: {sorted(merged)}")


def guess_jurisdiction(text: str) -> str:
    for city in ("Cambridge, MA", "Boston, MA", "Jersey City, NJ", "Hoboken, NJ", "Newark, NJ",
                 "San Francisco, CA", "Los Angeles, CA", "San Diego, CA", "Berkeley, CA", "Santa Ana, CA"):
        if city.split(",")[0].lower() in text[:3000].lower():
            return city
    return "Cambridge, MA"


def from_drive() -> None:
    dest = ROOT / "data" / "drive_latest"
    shutil.rmtree(dest, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "gdown", "--folder", DRIVE_URL, "-O", str(dest)], check=False)
    known_text = {p.name for p in CORPUS_DIR.glob("*.txt")}
    known_names = {p.name for p in PACK.rglob("*")}
    for p in dest.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix == ".json" and re.search(r"change|test|T6", p.name, re.I):
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, (list, dict)) and "test_id" in json.dumps(data)[:2000]:
                add_tests(p)
        elif p.suffix in (".txt", ".md") and p.name not in known_text and p.name not in known_names \
                and p.name.lower() not in ("readme.md",):
            text = p.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^SOURCE:\s*(\S+)", text, re.M)
            add_document(p, p.stem.replace(" ", "_")[:24], guess_jurisdiction(text),
                         m.group(1) if m else f"drive:{p.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", action="store_true")
    ap.add_argument("--file", type=Path)
    ap.add_argument("--doc-id")
    ap.add_argument("--jurisdiction")
    ap.add_argument("--url", default="")
    ap.add_argument("--tests", type=Path)
    ap.add_argument("--no-run", action="store_true")
    args = ap.parse_args()
    if args.drive:
        from_drive()
    if args.file:
        add_document(args.file, args.doc_id or args.file.stem, args.jurisdiction or "Cambridge, MA", args.url)
    if args.tests:
        add_tests(args.tests)
    if not args.no_run:
        from . import run_all
        asyncio.run(run_all.main(run_all.DEFAULT_AS_OF, True))


if __name__ == "__main__":
    main()
