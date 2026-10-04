"""Surface open questions in the law (participant guide, section 9).

Deterministic: it compares what our own sources say and flags a rule for human review when
  - documents that support the same rule state different dollar figures with none in common, or
  - a local ordinance's effective date comes only from a secondary source, because the official
    text in the corpus does not state it (state statutes have default effective dates; local ones don't).
A flag never changes an answer. It marks the rule's own lookup rows and adds a plain note; unlike
preemption flags it is not spread to rules at other levels.
"""
import csv

from .paths import EXTRA_DIR, PACK


def _source_types() -> dict[str, str]:
    types = {}
    for path in (PACK / "corpus" / "corpus_manifest.csv", EXTRA_DIR / "extra_manifest.csv"):
        if path.exists():
            with path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("doc_id") and row.get("source_type"):
                        types.setdefault(row["doc_id"], row["source_type"])
    return types


def _official(source_type: str | None) -> bool:
    return (source_type or "official").startswith("official")


def flag(rules: list[dict]) -> int:
    types = _source_types()
    flagged = 0
    for r in rules:
        notes = []

        figures = {doc: set(v) for doc, v in (r.get("source_figures") or {}).items() if v}
        if len(figures) > 1 and not set.intersection(*figures.values()):
            by_amount: dict[str, list[str]] = {}
            for doc, v in sorted(figures.items()):
                by_amount.setdefault(", ".join(sorted(v)), []).append(doc)
            said = " vs ".join(f"{amount} ({', '.join(docs)})" for amount, docs in by_amount.items())
            notes.append(f"Open question: sources state different amounts ({said}), so there is no single "
                         "official figure; verify the current amount with the issuing agency.")

        secondary = [s["doc_id"] for s in r.get("supporting_sources", []) if not _official(types.get(s["doc_id"]))]
        date_check = (r.get("verification") or {}).get("date_supported")
        if (r["level"] == "city" and r.get("effective_date") and date_check != "yes" and secondary
                and _official(types.get(r["source_doc_id"], r.get("source_type")))):
            notes.append(f"Open question: the effective date {r['effective_date']} comes from a secondary source "
                         f"({', '.join(secondary)}); the official text in the corpus does not state it, so answers "
                         "for dates near it need review.")

        if notes:
            r["open_questions"] = notes
            r["conflict_flag"] = True
            r["conflict_note"] = " ".join(n for n in [r.get("conflict_note"), *notes] if n)
            flagged += 1
    return flagged
