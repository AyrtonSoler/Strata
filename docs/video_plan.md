# Strata: video plan (3 videos, 60 s max each)

Rule: every shot of the product is a **real** screenshot or screen recording of the app (captured with
`media/capture.py` at 1920x1080 @2x; the self-check is the real `pipeline.selfcheck` output replayed by `media/terminal.py`).
Higgsfield provides the cinematic b-roll (GPT Image keyframes animated with Kling 3.0), the AI narrator
(Seed Audio, voice "Cillian") and the edit (Higgsedit, `media/edit/*.jsx`). The music bed is synthesized
from scratch (`media/edit/music.py`), so there are no third-party rights.

## Video 1: Demo (58.5 s) — `strata_demo_v2.mp4`
| t | Visual | Narration |
|---|---|---|
| 0–7 | Kling: translucent law layers settle onto a 1920s SF building; "State · County · City" | "Every apartment in America sits under layers of law. State. County. City." |
| 7–15 | Kling: renter holds a rent-increase letter; still: letter + code book | "So when the rent goes up nine percent, is that even legal? Today, finding out means reading statutes by hand." |
| 15–24 | Logo drop, then the real app: type "3515 Fillmore", answer appears | "Meet Strata. Type an address. Strata finds the legal city, stacks every jurisdiction, and checks each rule against the building itself." |
| 24–31 | Rent card: SF ordinance Applies, CA cap Superseded | "Here in San Francisco, the city's rent ordinance applies, and the state cap steps aside." |
| 31–35 | Evidence sheet, statute passage highlighted | "Every answer opens the law itself, at the exact passage." |
| 35–44 | Time Machine playback: LA turns green on Jan 1, 2026 | "Move through time. On January first, 2026, California's algorithmic pricing ban switches on, building by building." |
| 44–50 | Berkeley: Unknown, then What if… 1960 | "When public records can't decide, Strata says unknown, and shows which fact would." |
| 50–52 | Renter summary in Spanish | "In plain English, or Spanish." |
| 52–58.5 | Kling aerial of SF, app-icon logo, tagline, URL | "Strata. Every rule. Every address. Every date." |

## Video 2: Tech (59.5 s) — `strata_tech_v2.mp4`
| t | Visual | Narration |
|---|---|---|
| 0–5 | Kling: legal pages snap into a grid of rule cells; "AI reads. Code decides." | "Strata runs on one principle: AI reads, code decides." |
| 5–17 | Method page; chips: Pass 1 (cell + BM25), Pass 2 (per document), 60/60 quotes verbatim | "Claude reads the corpus twice … Every quote is then matched, character by character, against its source." |
| 17–24 | Audit panel; chips: verifier 59/60, "what we did not verify" | "A second pass fact-checks each rule …" |
| 24–33 | OAK07: mailing Oakland, legal Emeryville (dashed city layer) | "The Census Geocoder finds the legal city, not the mailing one …" |
| 33–42 | Coverage matrix | "Then a deterministic engine stacks state, county and city law …" |
| 42–52 | Real self-check run; cards 500 / 60 / 5/5 / 21/21 | "Five hundred addresses. Sixty schema-valid rules …" |
| 52–59.5 | End card: logo, "AI reads. Code decides.", 287 model calls · ~$10, GitHub | "Reproducible, auditable, and about ten dollars of model calls. That's Strata." |

## Video 3: Team (≤ 60 s)
Ayrton on camera (phone, landscape, 1080p, window light), reading the script below; the edit adds
lower-thirds, real app b-roll, captions, the music bed and the end card.

> Hi, I'm Ayrton Soler, and I built Strata for Hack-Nation 7, Challenge 2 with RealPage.
> Why housing law? Because renters and landlords make real decisions, a rent increase, an eviction notice,
> a deposit, under rules they can't see. The law is split across state, county and city, and it changes on its own schedule.
> In twenty-four hours I built a pipeline where AI reads the law and code decides: sixty verified rules,
> five hundred addresses, every answer traced to the exact passage, in English and Spanish.
> Next: a living map of housing law for every address in the country, so anyone can know their rights
> before they sign, pay or move. Strata. Every rule. Every address. Every date.
