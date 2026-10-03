# Strata

> Which housing rules apply at this address today, and how do the supplied changes affect the answer? Every answer is cited to the source text.

At any address, housing law comes in **layers**: state, county and city. Some layers displace others, and each takes effect at a point in time. Strata works out those layers for one building on any date and shows the evidence behind every answer.

**Hack-Nation 7 · RealPage Rental Housing Law Navigator (v5 participant guide)** · Live demo: **https://strata-jet-tau.vercel.app**

⚖ *Not legal advice. Summaries of public law for research; verify with the cited source.*

📄 **[One-page method note → METHOD.md](METHOD.md)**

## What it does

| Module | Strata |
|---|---|
| **A · Extract** | Automated extraction of the corpus into schema-valid rule records (category, jurisdiction, requirement, coverage, exemptions, effective date, status, **penalty**, citation, quoted span), using two independent AI passes plus verification |
| **B · Resolve + Apply** | Census-geocoded **state › county › city** stack; deterministic coverage tests; local-over-state supersession; **unknown** when a fact is missing |
| **C · Track** | T1–T5 from `dev/change_tests.json`; any **as-of date** in the API and UI |
| Stretch: plain language EN/ES | Renter-facing explanations and a printable renter summary in English and Spanish |
| Stretch: confidence + conflict | Calibrated confidence with visible signals; conflicts and verifier disagreements flagged for human review |
| Stretch: new jurisdiction | **Oakland, CA** through the same pipeline: official city documents → rules → 30 public tax-roll parcels |
| Stretch: audit view | Every answer shows its source, retrieval date, as-of date, status reason, facts used, coverage checks, AI vs code steps and the **reasoning boundary** |

**Differentiators**
* **Time Machine:** a map of every property, recomputed for any date. Scrub from 2024 to 2028 and watch AB 325 switch on across California on Jan 1, 2026, and the NJ FAIR Act in 2027 with preemption flags.
* **Evidence view:** opens the official document at the exact quoted passage, highlighted.
* **Coverage matrix:** for advocates and agencies, which protections exist where, across all 14 jurisdictions.

## How it works (AI reads, code decides)

```
corpus ─┬─► per-cell extraction (BM25 retrieval → Claude, one question per jurisdiction × category)
        └─► per-document extraction (Claude reads every relevant chunk)
              │  quotes verified against the source text
              ▼
        reconcile (merge, official > secondary, canonical citations, preemption flags)
              ▼
        verify (field grounding in code + independent LLM fact-check) → calibrated confidence
              ▼
        rules.json ──► deterministic engine ◄── Census Geocoder + parcel data
                              ▼
                 lookups.json · changes.json · API · UI
```

Full details, data sources and limits are in **[METHOD.md](METHOD.md)**.

## Results

`uv run python -m pipeline.selfcheck`. The judges' `score.py` and answer key are not shared with participants, so this is our own validation:

| Check | Result |
|---|---|
| Rule records valid against `rule_record.schema.json` | **60/60** |
| Quoted spans found verbatim in their source document | **60/60** |
| Rules found independently by both extraction passes | 53/60 |
| Verifier pass (others flagged for human review) | 59/60 |
| Addresses with lookups | **500/500** |
| `applies` answers that cite a starter-corpus document | **90 %** |
| Rent cap reported for any Boston/Cambridge address | **0** |
| T1 CA AB 325 / SB 763 | 250/250 CA addresses: not yet effective on 2025-12-31 → applies on 2026-01-02 |
| T2 Hoboken vs Jersey City bans | 40 Hoboken + 50 Jersey City, 0 Newark |
| T3 NJ FAIR Act | 140 NJ addresses; 90 Jersey City/Hoboken flagged for possible preemption |
| T4 MA S.2983 / H.5222 | both `pending`; 110 MA addresses affected if enacted |
| T5 MA ballot question (struck) | `failed`; affected set empty |
| Known-answer tests from the brief and guide | **21/21** |

## Run it

Requirements: Node 20+, [uv](https://docs.astral.sh/uv/). The starter pack lives in `data/pack` (the corpus text is committed; the rest comes from the organizers' Drive folder).

```bash
npm install && npm run setup             # frontend deps + backend venv
cp backend/.env.example backend/.env      # ANTHROPIC_API_KEY, only needed to re-extract
npm run dev                               # API :8000, UI :5173 (uses the committed outputs)

cd backend                                # full rebuild (cached calls cost nothing)
uv run python -m pipeline.geocode && uv run python -m pipeline.enrich
uv run python -m pipeline.fetch_links && uv run python -m pipeline.oakland
uv run python -m pipeline.run_all && uv run python -m pipeline.selfcheck
```

## Outputs (`submission/`)

| File | Contents |
|---|---|
| `rules.json` | 60 rule records (official schema plus `penalty` and audit extensions), `no_rule_findings`, the 84-cell `coverage_grid` and `supplementary_rules` |
| `lookups.json` | `{as_of, lookups: {address_id: [{team_rule_id, result, explanation, conflict_flag}]}}` for all 500 supplied addresses |
| `changes.json` | T1–T5: affected and conflict-flagged address ids, notes, rule mapping, per-address before/after |
| `extension_oakland.json` | Stretch goal: lookups for 30 Oakland parcels (not part of the supplied sample) |
| `addresses_resolved.json` | Geocode, Census place, county, jurisdiction stack and the basis for unit and year facts |

## Stack

React + Vite + TypeScript + Tailwind + Leaflet · FastAPI (Python 3.12, uv) · Claude Sonnet 5 via the Anthropic SDK (structured outputs) · Census Geocoder · SANDAG and Alameda County public parcel data · Vercel.

## Team

- Ayrton Soler
