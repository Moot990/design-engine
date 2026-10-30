# Cloud test evidence

The optional FreeVideo update has separate [local measurements and cloud tests](FREEVIDEO-TEST.md).

All behavioral tests and rendering ran on GitHub-hosted standard Ubuntu runners.
For the original cloud engine, the laptop only ran syntax checks and downloaded
small QA files. The owner subsequently authorized one local FreeVideo sample;
that exception is recorded separately above.

## First run

[Run 40777964811](https://github.com/Moot990/design-engine/actions/runs/40777964811)
on commit `1c4cfd7`: **success**.

- 10 behavioral tests passed.
- Four 1000x1500 synthetic test images exported with Pin manifests.
- Real ffmpeg produced a 24-second 720x1280 sample Short with Arabic captions.
- Actual ReportLab generation produced three sample PDF types; Poppler rendered
  their preview pages. English/Arabic caption images and PDF previews were visually
  inspected after downloading the workflow artifact.
- Live Pollinations without a key returned **HTTP 401**.
- Live Edge TTS failed with the original pinned client version.

The test cards say TEST FIXTURE and are not photographs or generated interiors.
They must not be published or sold. A green fixture test is not a live API test.

## Follow-up run

[Run 40778453919](https://github.com/Moot990/design-engine/actions/runs/40778453919)
on commit `bbb88d7`: **success**.

- All original tests and sample media/PDF rendering passed again.
- Edge TTS updated to 7.3.1; the live English synthesis probe succeeded with
  3.792 seconds of audio.
- Official GitHub actions were updated and pinned to verified commit hashes.
- Pollinations no-key generation again returned HTTP 401.

## Final code verification

[Run 40780001411](https://github.com/Moot990/design-engine/actions/runs/40780001411)
on commit `5256d9b`: **success**. [Download its sample output](https://github.com/Moot990/design-engine/actions/runs/40780001411/artifacts/12856935580)
before 4 November 2026.

- **15 tests passed**, including the complete publishing control flow with mocked
  providers, durable duplicate prevention, payload disclosure/private status,
  token-rotation ordering and manifest publication IDs. Mocked API tests are not
  evidence that your real accounts are authorized.
- Live English and then-configured ar-SA Arabic TTS (historical run) both succeeded (3.792s / 5.592s probes).
- A separate actual 24-second ffmpeg sample used live narration and contained an
  audio stream, with no TTS fallback warning.
- Four fixture images, bilingual overlays and all three PDF types rendered.
- The live public model catalog resolved `zimage` to `tongyi-mai/z-image-turbo`;
  fixed pricing and earned-credit eligibility metadata were checked. This does
  not test authenticated generation or prove enough earned credits exist.
- No-key Pollinations generation still returned HTTP 401.

[Weekly report run 40779530564](https://github.com/Moot990/design-engine/actions/runs/40779530564):
**success**, including an actual state/report commit to main (`4c13022`).

[Setup preflight run 40779523339](https://github.com/Moot990/design-engine/actions/runs/40779523339):
**blocked as expected**, exit 2, because `GEMINI_API_KEY`, `POLLINATIONS_API_KEY`,
`AMAZON_ASSOCIATE_TAG`, `GEMINI_FREE_TIER_CONFIRMED` and
`POLLINATIONS_QUEST_ONLY` are not configured. The readiness artifact and summary
were uploaded. No generation or publishing was attempted by that run.

## Still needs your accounts

- Genuine Pollinations image generation and earned-balance/model compatibility.
- Gemini text and AI visual review on real interiors.
- Pinterest app approval, real Pin creation and actual OAuth/secret rotation.
- YouTube OAuth authorization, processing, actual uploads and channel policy checks.
- Amazon Egypt approval, permitted placements and actual commission attribution.
- Genuine monthly archive collection and store listings/payouts.
- GitHub confirmation that this ongoing production workload is permitted.

No views, sales, commissions or ad eligibility are claimed. Credentials have not
been invented or borrowed, and no paid endpoint has been substituted.

## Egypt correction — 30 October 2026

[Run 41060533239](https://github.com/Moot990/design-engine/actions/runs/41060533239)
on commit `07e11b9`: **success**.
[Download the fixture artifact](https://github.com/Moot990/design-engine/actions/runs/41060533239/artifacts/12977244982)
before 6 November 2026.

- All **26 behavioral tests passed**, including market override, wrong-market
  product URL rejection, canonical URL retagging, URL safety and Arabic-first mix.
- Four placeholder Pin rows: three Arabic, one English, all using Amazon.eg
  search links and a nonfunctional `fixture-eg` tracking placeholder. No real
  catalog products, account identity or commission tracking were used.
- Daily ffmpeg and `run_weekly.py --allow-fixtures` rendered 24-second Shorts;
  weekly result has zero AI clips, no warnings and `publication_cleared=false`.
- Separate live speech probes succeeded in English and Egyptian Arabic. The
  complete Arabic narrated fixture Short contains audio, with no warnings.
  Its source overlay frame was visually inspected after artifact download.
- The initial Egypt run (41060189497) correctly fell back to captions only for
  an overlong Arabic narration. The sample and Arabic generation prompt were
  shortened before the successful rerun. Actual Gemini copy is still untested.
- Fixture PDFs and previews rendered again. The live no-key image probe returned
  HTTP 401; authenticated image generation was not attempted.

Downloaded results are under ignored `output/egypt-dry-run/`: `smoke/` holds image
cards and both CSVs; `weekly-test/` holds the ffmpeg reassembly/result and video
manifest; `voiced-ar-test/short.mp4` is the narrated Arabic placeholder preview.
All are test fixtures, never publish or sell. This is one daily export reassembled
by the weekly command, not a full seven-day real weekly batch.

Not tested: actual Amazon Egypt product availability, accepted social placements
or attribution; live Gemini/Pollinations generation; publishing/OAuth; a real
seven-day batch; store/payout operations; any new local FreeVideo clip or Medium
benchmark. FreeVideo remains off by default and publication-gated pending written
clarification about worldwide output distribution. No publishing or schedules
were enabled for this correction. Existing persistent state/outbox was preserved.

## First real provider batch — 30 October 2026

[Live run 41078579807](https://github.com/Moot990/design-engine/actions/runs/41078579807):
**success**, four genuine Pollinations images, Gemini visual review and copy,
and a 24-second Arabic-narrated ffmpeg Short. No warnings, fixture=false. No
platform publishing occurred; persistent publication outbox remains empty.
[Original cloud artifact](https://github.com/Moot990/design-engine/actions/runs/41078579807/artifacts/12987948200)
expires 6 November 2026. Local reviewed files are under `output/first-real-batch/`.

Earlier attempts are preserved in state/history.json:
- Run 41076413634 accepted zero images: Gemini 2.5 Flash returned 404 for this
  account; two image requests also exceeded Pollinations' signed seed range.
- Switched to the documented free-tier Gemini 3.1 Flash-Lite; bounded image seeds
  to 0..2147483647 and added a tiny live readiness check before image spending.
- Run 41077362688 accepted two images; optional malformed hashtags discarded two
  otherwise reviewed images. Normalize valid tags and omit malformed optional
  tags; enforce Arabic script for Arabic text.
- The successful run reused the two accepted images, repaired text and generated
  only two missing scenes. All rejected ideas and old failure records remain.

All four final images were visually inspected after download. The cloud recovery
mix was two Arabic/two English Pins. During editorial review, the fourth Pin in
the local CSV was translated to simple Arabic, giving the intended three Arabic/
one English mix; provenance language and ledger were updated. Images and Arabic
video were unchanged. The original cloud artifact remains the original export.
The recovery selector now preserves the configured language mix, with a regression
check. See the latest cloud test run for that code change.

Amazon.eg search links include the configured public tracking ID; no manually
reviewed catalog products were supplied. Descriptions retain AI/affiliate notices.
No paid credits, model downloads, FreeVideo generation or schedule activation.

Still NOT tested: accepted Amazon social placements or commission attribution,
real Pinterest/YouTube uploads and OAuth, payouts, a full seven-day real batch,
commercial audio permissions, or any new FreeVideo/Medium benchmark. Passing AI
visual checks is not proof of originality, exact product matches or monetization.
