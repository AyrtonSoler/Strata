# Strata — Method Note

*Rental Housing Law Navigator · Hack-Nation 7 · RealPage challenge (v5 guide). Not legal advice.*

**Question.** For any apartment address: which housing rules apply on the query date, and how do the five supplied change cases affect the answer? **Principle: AI reads, code decides.** The language model only reads and normalizes legal text. Every result is decided by deterministic, reproducible code, and every answer traces back to a quoted source.

## Pipeline

| Step | What happens | Technique |
|---|---|---|
| **1. Extract (A)** | Two independent passes over the 87-document corpus. **Per-cell:** each of the 14 × 6 jurisdiction × category cells retrieves its top passages with BM25, giving official-corpus passages reserved slots, then asks Claude for that cell's rules, an explicit "no rule at this level", or "silent". **Per-document:** every relevant chunk is read in full. | Retrieval-augmented, schema-first extraction (Claude Sonnet 5, JSON-Schema structured outputs) |
| **Grounding** | Every `quoted_span` must be found in its source document (exact, whitespace/quote-normalized, or ≥ 0.9 fuzzy) and is snapped to the source characters. Unverifiable quotes are rejected. | String alignment |
| **Reconcile** | Per state, an LLM merges descriptions of the same law. Cell records form the backbone and official text beats secondary pages. Preemption and conflicting dates are flagged. Citations are canonicalized by rule ("Civil Code section 1947.12" → "Cal. Civ. Code § 1947.12"). A doc-only record is set aside as supplementary when its cell says no rule exists, or when the cell already has the governing rule. | Entity resolution + deterministic canonicalizer |
| **Verify** | (a) Code checks that the effective date and key figures appear in the source. (b) A second LLM pass checks requirement, citation, date and status against the quote plus surrounding text. Disagreements are flagged for human review and never silently fixed. | Chain-of-verification |
| **Confidence** | Calibrated from objective signals rather than model self-report: official source, exact quote, both passes agree, number of sources, verifier result, grounded fields. The UI shows the signals. | Rule-based calibration |
| **2. Resolve (B)** | Census Geocoder → incorporated place → **state › county › city** stack. The mailing city is not the legal city: Van Nuys → Los Angeles, Dorchester → Boston, an "Oakland" mailing address → Emeryville. | Public geocoding |
| **3. Apply (B)** | Coverage tests per rule: unit thresholds, certificate-of-occupancy and year-built cutoffs, rolling new-construction exemptions, owner-type exemptions, local-over-state supersession. A missing fact gives **unknown**, never a guess. | Deterministic engine |
| **4. Explain** | Plain-language requirement (EN/ES), structured ✓/✕/? checks, and an **audit view** for every answer: source, retrieval date, as-of date, status reason, facts used, AI steps vs code steps, and the **reasoning boundary** (what was not verified). | — |
| **5. Track (C)** | Every answer can be recomputed for any as-of date. Amendments keep their prior version in force. Pending bills never count as law, and failed measures are never reported. T1–T5 run from `dev/change_tests.json`. | Temporal status logic |

## Data and terms
- **Starter corpus and address sample** as supplied. **Link-only sources** (e.g. the Hoboken and Jersey City algorithmic-pricing ordinances, which T2 needs) were read once per URL with no crawling, which is consistent with the guide's "read freely, no bulk scraping". They are marked secondary, their confidence is lower, and they are not republished. Sites that block automated access (Justia, mass.gov, oaklandca.gov) were skipped.
- **Building facts:** assessor unit counts; lower bounds from use classes (NJ class 4C ⇒ 5+, Boston "A" ⇒ 7+); NJ descriptions parsed ("6B-20U" ⇒ 20 units); and San Diego's SANDAG parcel effective year, used only as an upper bound on construction year (it can prove "old enough", never "too new"). No owner names or non-public data.

## Uncertainty and responsible design
"Unknown" when coverage depends on a fact not in the data (owner type, exact certificate-of-occupancy date, subsidy status). Conflicts and verifier disagreements are flagged for human review. Each answer shows its as-of date. Enacted, pending, not-yet-effective and failed laws are kept separate. Every LLM call (request id, tokens, cost), rejected quote, merge decision and set-aside record is in `data/work/audit_log.jsonl`. Every screen carries a not-legal-advice label.

## Results (self-check; the judges' `score.py` is not shared with participants)
60 rules, all valid against `rule_record.schema.json`, every quote found verbatim in its source. 53 of 60 were found independently by both passes, and 59 of 60 passed the verifier (1 flagged). 500/500 addresses have lookups, and **90 %** of "applies" answers cite a starter-corpus document. T1–T5 match the expected behavior (T3 with conflict flags on all 90 Jersey City / Hoboken addresses). 21/21 known-answer tests drawn from the brief and guide pass. LLM cost for the full build was about **$10** with every call cached, so reruns are free.

## Extension: one new jurisdiction (stretch)
**Oakland, CA**, built with the same pipeline and no Oakland-specific code: 6 official city documents → 3 extracted rules (rent adjustment O.M.C. 8.22, just cause O.M.C. 8.22.360, Fair Chance Housing O.M.C. 8.25), plus 30 multifamily parcels from Alameda County's public tax roll. Results are in `submission/extension_oakland.json`, separate from the official 500-address `lookups.json`.

## Limits
The corpus has not been reviewed by counsel. Coverage is limited to the 6 categories and to the supplied documents and links. Local exemption filings and registrations are not checked. Some unknowns remain where public data lacks year built (Berkeley, much of NJ).

## Reproduce
```
cd backend
uv run python -m pipeline.geocode && uv run python -m pipeline.enrich
uv run python -m pipeline.fetch_links && uv run python -m pipeline.oakland
uv run python -m pipeline.run_all && uv run python -m pipeline.selfcheck
```
