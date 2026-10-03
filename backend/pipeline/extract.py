"""Module A: automated rule extraction.

For every document (starter corpus + link-only sources fetched once + any extra
document added later, e.g. a new jurisdiction's ordinances) we:
  1. split it into overlapping chunks and skip chunks with no housing-law signal,
  2. ask Claude for candidate rule records (structured output, fixed schema),
  3. verify every quoted_span against the source text and snap it to the exact
     characters in the document; candidates whose quote can't be found are dropped,
  4. cache by (doc sha, chunk, prompt version) and log everything to the audit log.
"""

import asyncio
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass

from . import llm
from .paths import AUDIT_LOG, CORPUS_DIR, EXTRA_DIR, EXTRACT_CACHE, MANIFEST
from .textmatch import _norm, verify_span  # noqa: F401  (re-exported for selfcheck)

PROMPT_VERSION = "v3"
CHUNK_CHARS = 22000
OVERLAP = 1500
CATEGORIES = [
    "rent_increase_limits", "just_cause_eviction", "security_deposits",
    "application_screening_fees", "screening_restrictions", "algorithmic_rent_setting",
]
KEYWORDS = re.compile(
    r"rent|evict|deposit|screen|application fee|algorithm|criminal|source of income|"
    r"just cause|tenant|landlord|lease|housing provider|pricing", re.I)

SYSTEM = """You extract structured rental-housing rules from public U.S. legal and government text for a prototype ("Rental Housing Law Navigator"). Output is reviewed by humans and is not legal advice.

Scope: three states (CA, NJ, MA) and ten cities (Los Angeles, San Francisco, San Diego, Berkeley, Santa Ana in CA; Jersey City, Hoboken, Newark in NJ; Boston, Cambridge in MA). Only these six rule categories:
- rent_increase_limits: caps/formulas on rent increases; local rent control/stabilization coverage.
- just_cause_eviction: limits on terminating tenancies to listed causes, notice, relocation tied to no-fault evictions.
- security_deposits: maximum deposit, upfront-charge limits, deposit interest or return rules.
- application_screening_fees: caps/limits on application or screening fees and related receipts/refunds; broker/upfront fee limits that apply at application.
- screening_restrictions: limits on using criminal history, source of income (incl. vouchers), or other applicant screening criteria.
- algorithmic_rent_setting: bans/limits on algorithmic or AI rent-setting / pricing devices or coordinated pricing.

What to return, for the CHUNK of ONE document you are given:
- One candidate record per distinct legal rule (one statute/ordinance section or one bill, per category). If one instrument covers two categories, return two records. Do not split one rule into many sub-records (no separate record per eviction cause or per exemption).
- Only rules the text itself states or clearly describes. Never invent rules, numbers, dates or citations. If the chunk has no in-scope rule, return an empty list.
- Pending bills (introduced, in committee, not signed) -> instrument_status "pending". Ballot questions or proposals that were struck, withdrawn or defeated -> "failed". Signed/adopted law -> "enacted" even if its effective date is in the future.
- Attribute the jurisdiction the rule belongs to (a law-firm article may describe several cities; tag each rule with its own city or state). jurisdiction is a state code ("CA","NJ","MA") for state law, or "City, ST" (e.g. "San Francisco, CA") for city law. level is "state" or "city". County rules: use the city they apply to only if the text says so; otherwise skip.
- citation: the official cite in conventional form, e.g. "Cal. Civ. Code § 1947.12", "Cal. Gov. Code § 12955", "Cal. Bus. & Prof. Code § 16729", "N.J.S.A. 46:8-21.2", "P.L.2025, c.405", "M.G.L. c. 186, § 15B", "M.G.L. c. 40P, § 4", "S.F. Admin. Code § 37.9", "L.A.M.C. § 151.06", "San Diego Mun. Code § 98.0701", "Berkeley Mun. Code ch. 13.76", "Jersey City Code § 218-12", "Hoboken Code ch. 158, Art. II", "Mass. S.2983 (2026)". For bills use the bill number and session. Use the most specific section the text supports.
- quoted_span: copy 1-3 consecutive sentences EXACTLY, character for character, from the chunk, that best support the rule (at least 20 characters, at most ~600). Do not paraphrase, fix typos, or join non-adjacent text. It will be machine-checked against the source.
- effective_date: the date the rule takes/took effect as YYYY-MM-DD (or YYYY-MM / YYYY if that is all the text gives); null if the text gives none. enacted_date similarly for signing/adoption when stated. If the text gives two different effective dates, use the one in the official text and explain the other in conflict_note.
- penalty: the sanction or remedy for violating the rule as the text states it (fines, damages, civil action, rent reduction), or null if not stated.
- requirement: one or two plain-language sentences a renter can understand. key_value: the headline number/formula (e.g. "5% + CPI, max 10%", "1 month's rent", "$50") or null.
- coverage: machine-readable coverage for multifamily apartment buildings (the address sample is mostly 5+ unit buildings):
  - min_units / max_units: the rule covers only buildings with at least / at most this many units (null if no such test).
  - built_on_or_before / built_after: date cutoffs (YYYY-MM-DD) on building age; age_cutoff_basis says whether the test uses the certificate of occupancy date ("certificate_of_occupancy") or construction/build date ("year_built").
  - exclude_if_newer_than_years: rolling exemption for recently built housing (e.g. housing that received a certificate of occupancy within the previous 15 years -> 15).
  - owner_exemption_max_units: if an exemption depends on who the owner is (natural person, small landlord, owner-occupant) and can only apply to buildings with at most N units, put N. Null if none.
  - owner_exemption_any_size: true only if an owner-type exemption could apply to a building of any size.
  - Encode exemptions in these fields whenever they can be expressed there: "units that first obtained a certificate of occupancy after June 13, 1979 are exempt" means built_on_or_before "1979-06-13" with age_cutoff_basis "certificate_of_occupancy". If the text states the coverage limits of a rule in another category (e.g. an eviction page saying which units are exempt from the rent increase limits), also return a record for that rule with those limits.
  - other_unknown_factor: a fact not normally in assessor data that decides coverage of an ordinary multifamily building (e.g. "whether the unit is subsidized/deed-restricted affordable housing", "whether the owner filed a new-construction exemption"); null if none.
  - yields_to_local: true for a state rule that by its own terms does not apply (or is displaced) where a stricter local rule of the same kind covers the unit (e.g. a state rent cap that exempts units under local rent control).
- conflict_note: note conflicting dates/figures, possible preemption between levels, or ambiguity; null otherwise.
- confidence: 0-1, your confidence that the record is accurate and correctly attributed.
- no_rule_findings: statements in the text that a jurisdiction has NO rule of a category or that local rules are barred (e.g. a state ban on local rent control), each with an exact quoted_span.

Default query date is 2026-10-01; report dates as written, the system computes status."""

DATE = {"type": ["string", "null"]}
RULE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category", "jurisdiction", "level", "instrument_status", "title", "requirement",
                 "key_value", "coverage_conditions", "exemptions", "effective_date", "enacted_date",
                 "penalty", "citation", "quoted_span", "coverage", "conflict_note", "confidence"],
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "jurisdiction": {"type": "string"},
        "level": {"type": "string", "enum": ["state", "city"]},
        "instrument_status": {"type": "string", "enum": ["enacted", "pending", "failed"]},
        "title": {"type": "string"},
        "requirement": {"type": "string"},
        "key_value": {"type": ["string", "null"]},
        "coverage_conditions": {"type": "string"},
        "exemptions": {"type": ["string", "null"]},
        "effective_date": DATE,
        "enacted_date": DATE,
        "penalty": {"type": ["string", "null"]},
        "citation": {"type": "string"},
        "quoted_span": {"type": "string"},
        "coverage": {
            "type": "object",
            "additionalProperties": False,
            "required": ["min_units", "max_units", "built_on_or_before", "built_after", "age_cutoff_basis",
                         "exclude_if_newer_than_years", "owner_exemption_max_units",
                         "owner_exemption_any_size", "other_unknown_factor", "yields_to_local"],
            "properties": {
                "min_units": {"type": ["integer", "null"]},
                "max_units": {"type": ["integer", "null"]},
                "built_on_or_before": DATE,
                "built_after": DATE,
                "age_cutoff_basis": {"anyOf": [{"type": "string", "enum": ["certificate_of_occupancy", "year_built"]},
                                               {"type": "null"}]},
                "exclude_if_newer_than_years": {"type": ["integer", "null"]},
                "owner_exemption_max_units": {"type": ["integer", "null"]},
                "owner_exemption_any_size": {"type": "boolean"},
                "other_unknown_factor": {"type": ["string", "null"]},
                "yields_to_local": {"type": "boolean"},
            },
        },
        "conflict_note": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rules", "no_rule_findings"],
    "properties": {
        "rules": {"type": "array", "items": RULE_SCHEMA},
        "no_rule_findings": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["jurisdiction", "category", "finding", "quoted_span"],
            "properties": {
                "jurisdiction": {"type": "string"},
                "category": {"type": "string", "enum": CATEGORIES},
                "finding": {"type": "string"},
                "quoted_span": {"type": "string"},
            }}},
    },
}


@dataclass
class Doc:
    doc_id: str
    jurisdictions: str
    url: str
    source_type: str
    retrieved_at: str
    text: str
    origin: str  # "starter_corpus" | "fetched_link" | "extra"

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()[:16]


def _header_date(text: str) -> str:
    m = re.search(r"^RETRIEVED:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def load_docs() -> list[Doc]:
    docs = []
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    for row in manifest:
        if row["status"] == "ok":
            text = (CORPUS_DIR.parent / row["text_file"]).read_text(encoding="utf-8")
            docs.append(Doc(row["doc_id"], row["jurisdictions"], row["url"], row["source_type"],
                            row["retrieved_at"], text, "starter_corpus"))
    report = EXTRA_DIR / "fetch_report.json"
    if report.exists():
        for row in json.loads(report.read_text()):
            p = EXTRA_DIR / f"{row['doc_id']}.txt"
            if row["fetch_status"] == "ok" and p.exists():
                text = p.read_text(encoding="utf-8")
                docs.append(Doc(row["doc_id"], row["jurisdictions"], row["url"], row["source_type"],
                                row["retrieved_at"], text, "fetched_link"))
    extra_manifest = EXTRA_DIR / "extra_manifest.csv"
    if extra_manifest.exists():
        with open(extra_manifest, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                text = (EXTRA_DIR / f"{row['doc_id']}.txt").read_text(encoding="utf-8")
                docs.append(Doc(row["doc_id"], row["jurisdictions"], row["url"],
                                row.get("source_type", "official"),
                                row.get("retrieved_at") or _header_date(text), text, "extra"))
    return docs


def chunks(text: str) -> list[str]:
    if len(text) <= CHUNK_CHARS:
        return [text]
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + CHUNK_CHARS)
        if end < len(text):  # break on a line boundary
            nl = text.rfind("\n", start + CHUNK_CHARS // 2, end)
            end = nl if nl > 0 else end
        out.append(text[start:end])
        if end >= len(text):
            break
        start = end - OVERLAP
    return out


STRONG = re.compile(
    r"rent control|rent leveling|rent stabiliz|rent increase|maximum (allowable )?rent|security deposit|"
    r"just cause|evict|algorithm|criminal|source of income|application fee|screening fee|"
    r"tenant screening|rent[- ]setting|pricing", re.I)


def relevant(chunk: str) -> bool:
    hits = KEYWORDS.findall(chunk)
    strong = STRONG.findall(chunk)
    return len(hits) >= 3 and len(strong) >= 2 and len(hits) * 1500 >= len(chunk) * 0.5


def audit(event: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _user_message(doc: Doc, chunk: str, i: int, n: int) -> str:
    return (f"DOCUMENT {doc.doc_id} (chunk {i + 1} of {n})\n"
            f"Manifest jurisdiction(s): {doc.jurisdictions}\n"
            f"Source type: {doc.source_type}\nURL: {doc.url}\nRetrieved: {doc.retrieved_at}\n\n"
            f"<document>\n{chunk}\n</document>")


async def extract_chunk(doc: Doc, chunk: str, i: int, n: int, sem: asyncio.Semaphore) -> dict:
    key = hashlib.sha256(f"{PROMPT_VERSION}|{llm.MODEL}|{doc.doc_id}|{chunk}".encode()).hexdigest()[:20]
    cache_file = EXTRACT_CACHE / f"{doc.doc_id}_{i:02d}_{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    async with sem:
        data, meta = await llm.structured_call(SYSTEM, _user_message(doc, chunk, i, n), OUTPUT_SCHEMA)
    result = {"doc_id": doc.doc_id, "chunk": i, "meta": meta, **data}
    EXTRACT_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    audit({"event": "llm_extract", "doc_id": doc.doc_id, "chunk": i, **meta,
           "n_rules": len(data["rules"]), "prompt_version": PROMPT_VERSION})
    return result


async def extract_doc(doc: Doc, sem: asyncio.Semaphore) -> list[dict]:
    parts = chunks(doc.text)
    # Short curated documents always go through; the filter only trims long codes.
    todo = [(i, c) for i, c in enumerate(parts) if len(parts) == 1 or relevant(c)]
    results = await asyncio.gather(*(extract_chunk(doc, c, i, len(parts), sem) for i, c in todo),
                                   return_exceptions=True)
    candidates = []
    for (i, _), res in zip(todo, results):
        if isinstance(res, Exception):
            audit({"event": "extract_error", "doc_id": doc.doc_id, "chunk": i, "error": repr(res)})
            print(f"  ! {doc.doc_id} chunk {i}: {res!r}", file=sys.stderr)
            continue
        for r in res["rules"]:
            exact, score = verify_span(r["quoted_span"], doc.text)
            if exact is None:
                audit({"event": "span_rejected", "doc_id": doc.doc_id, "citation": r["citation"],
                       "score": round(score, 3), "span": r["quoted_span"][:200]})
                continue
            candidates.append({
                **r, "quoted_span": exact, "span_match": round(score, 3),
                "source_doc_id": doc.doc_id, "source_url": doc.url, "source_type": doc.source_type,
                "source_origin": doc.origin, "retrieved_at": doc.retrieved_at, "origin": "doc",
            })
        for nf in res.get("no_rule_findings", []):
            exact, _ = verify_span(nf["quoted_span"], doc.text)
            if exact:
                candidates.append({"no_rule_finding": True, **nf, "quoted_span": exact,
                                   "source_doc_id": doc.doc_id, "source_url": doc.url,
                                   "retrieved_at": doc.retrieved_at})
    return candidates


async def run(doc_ids: list[str] | None = None, concurrency: int = 6) -> list[dict]:
    docs = [d for d in load_docs() if not doc_ids or d.doc_id in doc_ids]
    sem = asyncio.Semaphore(concurrency)
    per_doc = await asyncio.gather(*(extract_doc(d, sem) for d in docs))
    return [c for cands in per_doc for c in cands]


def plan() -> None:
    """Print how many chunks would be sent, without calling the API."""
    total_chars = n_chunks = 0
    for d in load_docs():
        parts = chunks(d.text)
        rel = [c for c in parts if relevant(c)]
        total_chars += sum(map(len, rel))
        n_chunks += len(rel)
        print(f"{d.doc_id:5} {d.origin:15} {len(d.text):7} chars  {len(rel)}/{len(parts)} chunks  {d.jurisdictions}")
    print(f"\n{n_chunks} chunks, ~{total_chars / 4 / 1000:.0f}k input tokens")


if __name__ == "__main__":
    if sys.argv[1:] == ["plan"]:
        plan()
    else:
        out = asyncio.run(run(sys.argv[1:] or None))
        print(json.dumps(out, indent=1, ensure_ascii=False)[:3000])
        print(f"{len(out)} candidates; spent so far ${llm.spent_usd():.2f}")
