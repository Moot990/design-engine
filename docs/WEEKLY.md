# One-hour weekly routine

Use Friday at a time you prefer in Egypt. Setup/approval work is separate
from this steady-state routine. Do not treat the schedule as an income guarantee.

| Time | What you do | Result |
|---|---|---|
| 0-10 min | GitHub > Actions: inspect failed runs, daily result summaries and `reports/weekly-latest.md`. Check earned credits, artifact storage and upcoming OAuth/PAT expiries. | Resolve or pause failures before more publishing. |
| 10-25 min | Review recent Pins and Shorts. Inspect furniture geometry, lighting, Arabic phrasing, practical value, pacing and link relevance. Review every new product-pack page before selling. | Keep useful designs; remove misleading/broken posts on the actual platform. |
| 25-40 min | Open `data/products.csv` on GitHub > pencil icon. Manually check a small set of Amazon.eg products, add canonical Amazon.eg product URLs (or ASINs/search queries), mark `active=true` and today's `reviewed_on`. Adjust one style/palette/teaching point in `config/engine.yaml` based on evidence. | Commit clear changes to `main`. Stale product rows fall back to search inspiration. |
| 40-50 min | Pinterest Analytics: record impressions/views, saves and outbound clicks. YouTube Studio: record views, retention/swipe results and profile traffic if available. Amazon/Gumroad: record real earnings and store traffic. | Edit `data/metrics.csv`; put unavailable metrics in notes, not invented zeroes. |
| 50-60 min | Download wanted artifacts before expiry. If APIs are unavailable, manually upload/schedule the prepared files in Pinterest/Studio. Check existing platform posts against state IDs first. | Queue the best content, skip poor work, record one change for next week. |

During an API approval delay, manually reviewing/uploading 28 Pins and 7 Shorts
may exceed 10 minutes. Keep only the strongest items or temporarily reduce the
output; do not promise one-hour operation while approvals are missing.

## Product CSV notes

Header: `item_id,style_id,product_url,asin,search_query,label_en,label_ar,active,reviewed_on`.
Use YAML item/style IDs. Blank `style_id` means all styles. Prefer a canonical
`https://www.amazon.eg/dp/B012345678` link in `product_url` (illustrative ASIN;
not a verified product). `/gp/product/ASIN` is also accepted. No shortened URLs.
The link must match `AFFILIATE_PROGRAM`; a wrong-market active row is rejected.
The exporter removes old tracking parameters and applies your configured tracking ID.
Optional ASIN-only rows remain supported; ASINs are ten uppercase letters/digits.
An active matching row reviewed within 14 days wins (URL before ASIN, then search).
Stale rows fall back to a generic Amazon.eg search. Use ISO review dates.
Review actual availability and link format in Egypt SiteStripe before real use.

Default audience is Egypt and the Arab world: review natural, simple Arabic first,
then English. Defaults are three Arabic Pins, one English Pin and an Arabic Short.
Confirm each social channel is listed in your Egypt Associates account; Pinterest
eligibility needs account-level confirmation. Keep prominent disclosure in your
profile and each post, including Arabic ad wording and the Amazon Associate statement.

Generated objects are not exact catalog products. Never label them as the exact
sofa/rug/lamp pictured. Keep the disclosure and similar-item wording.

## Metrics row example (illustration only)

`2026-11-06,pinterest,<actual-id>,warm-minimal,1200,24,8,0,recorded manually`

Use actual metrics; the example is not a result. Earnings can be tracked at
platform/week level when item attribution is unavailable. Do not double-count
the same Associate earnings under several posts/platforms.

## Pausing and recovery

- Repository Settings > Secrets and variables > Actions > Variables: set
  `ENGINE_ENABLED=false` to pause cron; set platform publish flags false to stop
  uploads while retaining generation/export tests.
- Check `state/history.json` for `published`, `inflight` or `unknown`. Look up the
  actual Pin/video in the platform. Record a discovered remote ID and status in
  state rather than issuing another request blindly.
- Same-date reruns stop. Partial output remains in that run's artifact. If a
  run failed before reserving a date, fixing credentials and retrying is safe;
  once reserved, inspect state before any reset.
- A failed state push stops publishing. Resolve branch permissions or concurrent
  changes first; never disable the durable checkpoint to bypass the error.
- Check monthly archives/downloads before retention expiry. Artifacts are not
  permanent backups. Keep wanted outputs in your own chosen storage manually.

At day 90 fill [DAY-90.md](DAY-90.md) with evidence and keep/change/cut decisions.

## Optional local FreeVideo preview

ffmpeg is still the default. See [FREEVIDEO.md](FREEVIDEO.md) for the local-only
adapter, five-second Light/Medium clips, quota, time cap and cooldown settings.
This feature needs the laptop running; standard cloud runners cannot reach it.

Before any manual upload, in **YouTube Studio > Details > Altered content**, choose
**Yes** for these realistic AI interiors. Keep the written AI disclosure in every
Pin and video description. FreeVideo clips additionally identify MiniMax H3.
Check current worldwide output rights before publishing FreeVideo previews; being
in Egypt alone does not resolve the license's excluded-territory restriction.
