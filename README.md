# Design Engine

Arabic/English residential interior content: start with living rooms, export
Pinterest Pins and faceless Shorts, add Saudi affiliate links, and prepare monthly
digital product drafts. Python 3.12. All media processing runs in the cloud.

**Current status:** code deployed; fixture cloud tests pass. Real AI generation,
platform uploads and affiliate attribution require your accounts and are not yet
verified. Production schedules are off. No paid service has been enabled.

Start with the [numbered personal setup checklist](docs/SETUP.md).
See [current service/terms findings](docs/SERVICE-STATUS.md),
[the one-hour weekly routine](docs/WEEKLY.md),
[day-90 review sheet](docs/DAY-90.md), and
[cloud test evidence](docs/TEST-RESULTS.md).

## What it does

1. Chooses unused room/style/palette/item/lesson combinations from
   `config/engine.yaml`, reserving every idea in `state/ideas.csv`.
2. Generates 1000x1500 Pollinations images only when earned Quest Pollen access can
   be checked. No no-key endpoint, purchased credits or paid-only models.
3. Rejects invalid, blank and perceptually repeated images, then asks Gemini to
   check geometry, visible featured furniture and design quality. AI checks can
   miss defects; your weekly review is still necessary.
4. Writes original SEO text with bilingual affiliate/AI disclosure. Links use a
   recently reviewed `data/products.csv` ASIN or a tagged Amazon.sa search.
   Everything is labelled similar-item inspiration; no prices or exact-match claims.
5. Exports 4 Pins/day by default (configurable 3-10) and a 24-second 720x1280 Short
   using 4-6 accepted images, varied framing, teaching points, hooks and voices.
   There is no music. Edge TTS failure retains a captions-only video and marks the
   batch as needing review; it is not described as a successful narrated video.
6. Optionally sends Pins through Pinterest API v5 and Shorts through YouTube Data
   API, with `containsSyntheticMedia=true` and private YouTube uploads by default.
7. Builds up to 16 curated mood-board, palette and style-guide pages monthly from
   the previous month's genuine accepted images. Products are drafts for your
   review and manual store upload, not guaranteed sale-ready products.
8. Commits sanitized state/reports to `main`. A durable outbox checkpoint precedes
   each publish request. An ambiguous upload is marked unknown and not auto-retried.

## Workflow buttons

Open [Actions](https://github.com/Moot990/design-engine/actions).

| Workflow | Purpose | Credentials |
|---|---|---|
| Cloud tests | Behavior tests, synthetic batch, actual ffmpeg/PDF render, service probes | None |
| Daily content engine / preflight | List missing setup | None; missing setup deliberately fails |
| Daily content engine / generate | One development integration batch; export files | Gemini, earned Pollinations, Saudi tag |
| Daily content engine / publish | Batch plus enabled platform uploads | Generation credentials + selected platform credentials + production-use confirmation |
| Weekly review | Commit report and day-90 template | Built-in workflow token |
| Monthly digital products | Build draft packs from previous-month source archives | Built-in workflow token |

Daily cron is around 09:17 Saudi time. Weekly review is Friday around 10:43.
Monthly products run on the first around 10:37. GitHub schedules can be late and
public-repository schedules can disable after 60 days without activity. All cron
jobs require both `ENGINE_ENABLED=true` and `ACTIONS_PRODUCTION_APPROVED=true`.

## Output and storage

- `daily-batch-*`: JPEGs, CSV manifests, video, narration/copy, result/readiness.
  Download within **7 days**. These CSVs are local upload manifests, not Pinterest
  native bulk-import CSVs: native bulk import needs publicly hosted media URLs.
- `image-archive-YYYY-MM-DD`: source images and provenance; retained **32 days**
  for monthly assembly. No OAuth tokens, Gemini key or Pollinations key in artifacts.
- `monthly-product-pack-*`: three PDF drafts, board JPGs, provenance and preview;
  download within **7 days**, then review and upload to your own store.
- `cloud-test-output`: clearly labelled test cards, never publish or sell.

Daily archives are capped at 6 MB (sources) / 14 MB (full batch); monthly packs at
40 MB. A repository-wide 350 MB artifact cutoff stops new generation. GitHub's
included storage is shared with other account usage, so also set a zero spending
budget and review the account billing page. Do not use artifacts as a public CDN.

The affiliate tag is configured through a Secret, but it is intentionally public
inside published affiliate URLs and generated upload manifests. That identifier
is not an account access credential. Actual credentials stay in memory/environment.

## Optional local video backend

`run_weekly.py` can reassemble an extracted daily batch using a running local
FreeVideo agent. `video_backend: ffmpeg` remains the default. The optional adapter
uses five-second first-frame clips, a persistent weekly attempt budget, a deadline,
cooldowns, temperature monitoring and ffmpeg fallback. It never installs software
or fetches models. See [local setup, limits and license findings](docs/FREEVIDEO.md).
The owner separately authorized one laptop sample; normal cloud operation stays
as described above. FreeVideo public output is gated pending territorial clarity.

## Editing and recovery

Edit YAML/CSV with GitHub's pencil button, then Commit changes to `main`.
Use clear messages. A new room can be added to `rooms` after reviewing the living
room series. Do not delete history to obtain more daily content.

Only one real batch per Saudi date is reserved. Re-running the same date stops
instead of issuing duplicate posts or generation requests. If a batch failed,
download its partial output and inspect state first. Do not reset an unknown
publication until you have checked the actual Pinterest board/YouTube Studio.
Fix or reconcile state deliberately, then use the next daily batch.

HTTP reads use bounded retries/backoff. Pin creation, image generation and final
video upload are not blindly retried after a timeout: they can already have
succeeded remotely. Missing permissions/quotas produce explicit failures and
retain whatever manual exports were completed.

## Laptop rule

Only `python -m compileall -q engine scripts tests` runs locally. Do not run the
pipeline, install media tools or perform full tests on the laptop. Use Actions.
Work on `main`, commit clearly, push after each major change. Never paste credentials
into chat, code, CSVs, reports or GitHub issue comments.
