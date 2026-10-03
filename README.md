# Strata

> Which housing rules apply at this address today, and what is about to change? Every answer is cited to the source text.

At a given address, housing law piles up in **layers**: state law, then city ordinances. Some layers displace others, and each one is laid down at a point in time. Strata resolves those layers for one building on any date.

**Hack-Nation 7 · Challenge 2 (RealPage)** · ⚖ *Not legal advice. This prototype summarizes public law for research.*

For any apartment address in California, New Jersey or Massachusetts, the system:

1. **Extracts** rules from the provided corpus of state and city law using an LLM. The output is structured rule records in the official schema, and every quote is machine-verified against the source.
2. **Resolves** the address to its legal jurisdiction (state › city) with the Census Geocoder. The postal city is not the legal city: Van Nuys belongs to Los Angeles and Dorchester to Boston.
3. **Applies** each rule's coverage tests (unit count, year built vs. certificate-of-occupancy cutoffs, rolling new-construction exemptions, owner-type exemptions) on any **as-of date**. Each rule gets one of `applies`, `unknown`, `superseded`, `not_yet_effective` or `pending`.
4. **Tracks change** by reporting which addresses a law change affects and flagging possible preemption conflicts for human review.

## What makes Strata different

* **Time Machine.** Every sample property sits on a map, and every rule is recomputed for any date. You can scrub or play the timeline from 2024 to 2028 and watch laws switch on building by building: California's AB 325 on Jan 1, 2026, and NJ's FAIR Act in July 2027, with Jersey City and Hoboken flagged for preemption review. Events can be clicked to jump to their date, region and category. Amendments and annual adjustments keep their prior version in force, so going back in time never shows long-standing rent control as "not yet effective".
* **Evidence, not assertions.** Each answer opens the official source document at the exact quoted passage, highlighted. Third-party pages we read once are not republished; their verified quote and link are shown instead.
* **Renter summary (EN/ES).** A one-page, printable "your rules at a glance" for any building. It lists the governing rule in each category in plain language, with citations, uncertain items called out and upcoming changes.

## Results

`uv run python -m pipeline.selfcheck` checks everything we can verify ourselves. The judges' `score.py` was not included in the participant pack.

| Check | Result |
|---|---|
| Rule records valid against `rule_record.schema.json` | **61/61** |
| Quoted spans found verbatim in their source document | **61/61** |
| Addresses with lookups | **500/500** |
| `applies` answers backed by source + quoted span | **4,670/4,670** |
| Rent cap reported for any Boston/Cambridge address | **0** (correct) |
| T1 CA AB 325 / SB 763: not yet effective on 2025-12-31, applies on 2026-01-02 | 250/250 CA addresses |
| T2 Hoboken vs Jersey City algorithmic bans | 40 Hoboken + 50 JC, 0 Newark |
| T3 NJ FAIR Act: not yet effective now, applies 2027-07-02 | 140 NJ addresses, 90 JC/Hoboken flagged for preemption review |
| T4 MA S.2983 / H.5222 | reported as `pending`, 110 MA addresses would be affected |
| T5 MA rent-control ballot question (struck) | recorded as `failed`, affected set empty |

The full extraction and reconciliation run cost **≈ $4.60** with Claude Sonnet 5. Every call is cached, so reruns cost nothing.

## Architecture

```
corpus/*.txt ──► extract.py ──► candidates ──► reconcile.py ──► rules.json
(87 docs +        LLM, structured    (verified      LLM per state:       (61 rules, schema-valid)
 link-only         JSON output,       quotes only)   merge duplicates,          │
 sources fetched   quote check                       official > secondary,      ▼
 once)                                               flag conflicts      engine.py ◄── geocode.py
                                                                         (deterministic)  (Census Geocoder:
                                                                              │            address → place)
                                                                              ▼
                                                                lookups.json · changes.json
                                                                              │
                                                                   FastAPI ──► React UI
```

* **The LLM is used only where it adds value:** reading law, merging duplicate descriptions and translating summaries. Coverage logic, dates and supersession are plain code, so every answer is reproducible and explainable. The UI shows the "Why" for each result.
* **Quote verification:** a candidate whose `quoted_span` can't be found in its document (after whitespace and quote normalization, or a ≥ 0.9 fuzzy match) is rejected and logged.
* **"Unknown" over guessing:**
  * A building in a certificate-of-occupancy cutoff year comes back `unknown`.
  * So do missing year-built data (San Diego, Berkeley, much of NJ) and owner-type exemptions that could apply.
  * Unit counts are never invented. Lower bounds come only from the assessor classification: NJ class 4C means 5+ units, and Boston land use `A` means 7+ units. NJ building descriptions such as `6B-20U-G` are parsed for the count.
* **Supersession:** state rules that yield to local law (CA Civ. Code § 1947.12 / § 1946.2) are reported as `superseded` where a local rule applies, and as `unknown` where local coverage itself is unknown.
* **Enacted vs pending vs failed:**
  * A pending bill is reported as `pending`, never as law.
  * A struck ballot measure is `failed` and never reported.
  * Laws that *bar* regulation (e.g. M.G.L. c. 40P) become "no rule at this level" findings rather than rules.
* **Audit trail:** every LLM call (request id, tokens, cost), rejected quote and merge decision is written to `data/work/audit_log.jsonl`. The **Pipeline & audit** tab in the UI shows it.

### Sources beyond the text corpus

The Hoboken and Jersey City algorithmic-pricing ordinances, which T2 tests, are **link-only** in the starter pack. `pipeline/fetch_links.py` reads each link-only URL in the manifest exactly once, with no crawling, and keeps its retrieval date. Rules from those pages are marked `source_origin: fetched_link`, and their confidence is capped at 0.75. 13 of the 61 rules come from them. Pages that block scripts (Justia, mass.gov) are skipped.

## Run it

Requirements: Node 20+, [uv](https://docs.astral.sh/uv/).

```bash
npm install && npm run setup           # frontend deps + backend venv
uvx gdown --folder https://drive.google.com/drive/folders/14TT6AEH8TStzoT5c5fZ45Bt4grODsowR -O data/starter
#   then move the downloaded "participant-final-…" folder to data/pack
cp backend/.env.example backend/.env    # add ANTHROPIC_API_KEY (only needed for new extraction)

cd backend
uv run python -m pipeline.geocode       # Module B step 1: addresses → jurisdictions
uv run python -m pipeline.fetch_links   # read link-only sources once
uv run python -m pipeline.run_all       # extract → reconcile → lookups → changes (cached)
uv run python -m pipeline.selfcheck     # validation report
cd .. && npm run dev                    # API :8000, UI :5173
```

Other dates: `uv run python -m pipeline.run_all --as-of 2027-07-02`. The UI and API also take any `as_of`.

### Hour-16 ordinance

```bash
cd backend
uv run python -m pipeline.ingest --drive     # re-pull the Drive folder, ingest new docs + tests, rerun
# or explicitly:
uv run python -m pipeline.ingest --file path/to/ordinance.txt --doc-id H16 \
    --jurisdiction "Cambridge, MA" --url <source url> --tests path/to/T6.json
```

New documents go through the same automated extraction. Nothing is hand-coded. We rehearsed this with a fictional Cambridge fee ordinance: the system extracted it unaided (effective 2027-03-01, $25 cap, 6+ units) and listed exactly the 45 Cambridge buildings with 6+ units.

## Outputs (`submission/`)

| File | Contents |
|---|---|
| `rules.json` | 61 rule records in the official schema, plus `no_rule_findings` and engine extensions (`coverage`, `instrument_status`, Spanish `title_es` / `requirement_es`) |
| `lookups.json` | `{as_of, lookups: {address_id: [{team_rule_id, result, explanation, conflict_flag}]}}` for all 500 addresses |
| `changes.json` | T1–T5: `affected_address_ids`, `conflict_flag_address_ids`, notes, rule mapping, per-address before/after |
| `addresses_resolved.json` | Each address with its geocode, Census place, jurisdiction stack and unit basis |

## Responsible design

* "Not legal advice" appears on every screen and in every API answer. Every answer carries an **as-of date**.
* Each rule shows its citation, source URL, retrieval date, exact quote and confidence.
* Conflicts are flagged for human review rather than resolved silently. Examples: NJ FAIR Act vs local bans, Berkeley's two published effective dates, LA's RSO formula dates.
* No customer, resident or pricing data is used; only public law and public assessor/Census data. No owner names.
* The tool never suggests ways to avoid a rule.

## Scaling to new jurisdictions

Adding a city takes three steps: drop its ordinance texts into `data/extra` with `pipeline.ingest`, add its Census place name to `CITY_BY_PLACE` in `geocode.py`, and rerun. Extraction, reconciliation and coverage evaluation are jurisdiction-agnostic. The coverage schema (units, cutoff dates, rolling exemptions, owner exemptions, yields-to-local) is the part that generalizes.

## Stack

React + Vite + TypeScript + Tailwind · FastAPI (Python 3.12, uv) · Claude Sonnet 5 via the Anthropic SDK (structured outputs) · Census Geocoder · deployed on Vercel.

## Team

- Ayrton Soler
