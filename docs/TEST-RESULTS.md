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
