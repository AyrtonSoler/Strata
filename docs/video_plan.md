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
About Ayrton and why he picked this challenge, not a second product pitch. Ayrton on camera (phone,
landscape, 1080p, window light, eye level). The edit adds a name lower-third, two or three short app
cutaways, captions, the music bed and the end card. Fill in the [brackets] with your own words; keep the
total around 130 words (about 50 seconds).

> Hi, I'm Ayrton Soler, [what you do: e.g. a software engineering student / a developer] from Mexico.
> I usually build with Spring Boot and React, and I took on this challenge solo.
>
> I picked housing law because [your personal reason: e.g. the first time I rented, I signed a lease
> without knowing which rules protected me, and finding out meant reading legal text I couldn't follow].
> The answers exist, but they're scattered across state, county and city codes, and they keep changing.
>
> What hooked me is that it's a problem where AI helps but can't be trusted blindly. So I let the model
> read the law, made plain code make every decision, and made every answer show its source.
>
> The hardest part was [your answer: e.g. getting the AI to quote the law exactly instead of paraphrasing it].
> What I'm taking away is [one lesson]. Thanks for watching.

Recording tips: two or three takes, pause one second before and after, look at the lens, and don't
read the brackets literally; say it the way you would tell a friend.
