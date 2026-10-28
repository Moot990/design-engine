# Personal setup checklist

Only you can accept platform agreements, sign into accounts, prove identity,
authorize channel access and enter payout details. Do not send credentials in
chat. All account keys below go directly from the provider into GitHub Secrets.
Buttons may move; use the linked official page if the wording changes.

## 1. Confirm the free operating conditions

The repository is now public. In GitHub: profile photo > Settings > Billing and
licensing > Budgets and alerts. Set Actions paid spending to zero and enable the
available stop-usage control. Do not enable larger runners, paid storage overage,
Gemini billing, purchased Pollen or auto-recharge.

Open [GitHub Support](https://support.github.com/contact). Ask whether Actions is
allowed for this specific ongoing workload under the
[current additional product terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features).
Suggested text, which you send yourself:

> I maintain a public Python software repository. I want to run one small daily
> batch generating four interior images through an external API, rendering a
> 24-second video, and publishing affiliate content to my own social accounts,
> plus one monthly PDF batch. Is ongoing production use of standard hosted
> Actions permitted for this workload? Artifacts would be temporary downloads,
> not public hosting. I understand software development tests are a separate use.

Do not enable production cron unless GitHub confirms it is allowed. Code tests
and one-off development integration tests are available meanwhile.

## 2. Create Pinterest Business account and boards

1. Open [Pinterest Business](https://business.pinterest.com/) and choose Create
   account, or Settings > Account management > Convert to business.
2. Use your chosen design brand name and complete the profile.
3. Create a public board called **Living Room Ideas | أفكار غرف المعيشة**.
   Describe it as original AI-generated residential design concepts and practical
   styling lessons. Add the bilingual affiliate disclosure from the README/code
   to your profile or a clearly linked disclosure page.
4. Create the YouTube channel in step 4, then register both complete profile URLs
   in your Saudi Associates site list (step 6) before affiliate publishing.
5. In [Pinterest Developers > My apps](https://developers.pinterest.com/apps/),
   choose Create app. Enter accurate purpose/contact details and the requested
   website/privacy-policy details. Do not invent a business or claim endorsement.
   You must supply a genuine accessible privacy policy if Pinterest requires it;
   the repository README is not automatically a suitable policy or redirect page.
6. Request the access needed to create Pins on your own boards. Use scopes
   `boards:read,pins:read,pins:write`. Check the app's actual Trial/Standard status.
   Follow the current review instructions; approval is not guaranteed.
7. Use the app's Generate access token / API explorer, if available for your
   approved access, to obtain your own token. Store it directly as
   `PINTEREST_ACCESS_TOKEN`. A development token can be short-lived.
8. With the authenticated explorer, call GET `/v5/boards`. Copy the ID of your
   living-room board directly into GitHub Secret `PINTEREST_BOARD_ID`.
   The board URL name is not the numeric API board ID.

If access is pending, leave `PINTEREST_PUBLISH` unset/false. You can download the
daily files, choose Create Pin, upload the JPEGs, copy each manifest's fields,
choose the board and use Pinterest's own scheduling controls.

## 3. Optional: make Pinterest token renewal automatic

Complete this only after your app supports the
[official Authorization Code flow](https://developer.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/).
Pinterest must accept your real HTTPS redirect URI; it is not supplied by this
batch engine. A dashboard-generated test token alone is not a continuous refresh
token. If the dashboard does not provide a way to authorize your app, pause this
optional step and use manual exports until we can configure the redirect together.

1. In your Pinterest app, set your actual HTTPS redirect URI, authorize your own
   Pinterest user with the scopes above, and exchange the authorization code
   through Pinterest's documented token endpoint using the same redirect URI.
   Keep the response in the provider's secure tooling, never a public file/chat.
2. Store app ID as `PINTEREST_CLIENT_ID`, app secret as
   `PINTEREST_CLIENT_SECRET`, and the returned continuous refresh token as
   `PINTEREST_REFRESH_TOKEN`, directly in GitHub Secrets.
3. Open GitHub profile > Settings > Developer settings > Personal access tokens >
   Fine-grained tokens > Generate new token. Choose your account as resource
   owner, select **Only select repositories > design-engine**, and give only
   repository **Secrets: read and write** permission (metadata is implicit).
   Choose an expiry you will track; do not grant full repository administration.
4. Copy the token directly into Secret `REPO_SECRETS_TOKEN`. Do not download it.
   It lets the workflow encrypt and save a rotated Pinterest refresh token back
   into GitHub Secrets. It is not the built-in `GITHUB_TOKEN`.

The adapter refreshes once per process and persists a changed refresh token
before Pin creation. If renewal or secret update fails, it stops API publishing
and retains exports. Reauthorization or PAT expiry still needs you personally.
This optional OAuth setup has not been live-tested on your account.

## 4. Create YouTube channel and authorize uploads

1. Sign into [YouTube](https://www.youtube.com/) > profile picture > Create a
   channel. Choose a brand name/handle. In YouTube Studio > Customization >
   Profile, explain that these are AI interior concepts and add the affiliate
   disclosure. Complete the channel's verification/feature checks as requested.
2. Add a relevant disclosed affiliate/store destination under channel profile
   Links. Shorts description URLs are not clickable. Initially one relevant
   Amazon.sa search or your approved Associates page is more honest than a
   claim that the profile contains every exact product in every design.
3. Open [Google Cloud Console](https://console.cloud.google.com/) > project
   selector > New project. Name it Design Engine Uploads. Do not enable billing.
4. APIs & Services > Library > search YouTube Data API v3 > Enable.
5. Google Auth Platform > Branding: enter app name, your user-support email and
   required contact details. Audience > External. Add your Google account as a
   test user while developing. Under Data Access add
   `https://www.googleapis.com/auth/youtube.upload`.
6. APIs & Services > Credentials > Create credentials > OAuth client ID > Web
   application. Add authorized redirect URI
   `https://developers.google.com/oauthplayground`. Create it. Copy the client ID
   and client secret directly into `YOUTUBE_CLIENT_ID` and
   `YOUTUBE_CLIENT_SECRET` in GitHub Secrets; do not download a JSON key file.
7. Open [Google OAuth Playground](https://developers.google.com/oauthplayground/).
   Gear icon > Use your own OAuth credentials. Enter that client ID/secret there.
   Choose server-side flow, offline access and a consent prompt if offered.
   Enter scope `https://www.googleapis.com/auth/youtube.upload`, then Authorize
   APIs. Sign into the exact Google/channel account you want to upload to.
8. Click Exchange authorization code for tokens. Copy the refresh token directly
   into GitHub Secret `YOUTUBE_REFRESH_TOKEN`. Do not paste it in chat or save
   screenshots of it. Clear the Playground session after storing it.
9. Testing-mode refresh tokens normally expire after 7 days. For unattended use,
   follow Google's requirements for a Production OAuth app and any verification
   it requests, then authorize again. Do not assume changing the switch grants
   verification or removes channel/API restrictions.
10. Keep `youtube_privacy: private` in `config/engine.yaml` for the first real
    upload. Check the correct channel, video processing, audio, description,
    audience and altered-content flag in Studio before changing privacy.

If authorization or uploads are restricted, keep `YOUTUBE_PUBLISH=false`. The
fallback video/manifest is ready for YouTube Studio > Create > Upload videos.
Select the altered/synthetic content disclosure for these realistic AI images.

## 5. Get free text/image access

**Gemini**: open [AI Studio API keys](https://aistudio.google.com/apikey) > Create
API key in a project with **no Cloud Billing account**. Confirm its Free tier and
the selected model in the dashboard. Copy directly into `GEMINI_API_KEY`.
Set repository variable `GEMINI_FREE_TIER_CONFIRMED=true` only after checking.
Free quotas vary; an exhausted quota causes a stopped/partial batch, not payment.

**Pollinations**: open [the key dashboard](https://enter.pollinations.ai/keys) and
sign in personally. Check [Quests](https://enter.pollinations.ai/quests), complete
eligible tasks and claim earned rewards if available. Do not buy Pollen or attach
auto-recharge. If you cannot obtain enough earned credits, daily no-cost image
generation is blocked; there is no working no-key promise.
Create a server-side secret key with only the image model you choose, a small
spending budget, and read-only `account:usage` for balance checking. Store it as
`POLLINATIONS_API_KEY`. Set variable `POLLINATIONS_QUEST_ONLY=true` only when using
earned credits and zero paid balance. Check the live model catalog; update
`image_model` in the YAML if `zimage` is not available on your account.

## 6. Sign up for Amazon.sa Associates

1. Open [Saudi Associates](https://affiliate-program.amazon.sa/) > Sign up.
   Sign in, then enter your own accurate identity, contact and payout/tax details.
2. In the websites/mobile-app list enter your actual Pinterest profile URL and
   YouTube channel URL. Describe the original design content truthfully.
3. Read the Saudi agreement and confirm those social placements, direct product
   links and tagged search links are allowed for your account. Complete any
   application/review requirements shown there.
4. Copy your approved Saudi tracking tag ending in `-21` directly into GitHub
   Secret `AMAZON_ASSOCIATE_TAG`. Do not invent an approved tag.
5. Put the required Associate identification on your social profiles and retain
   the bilingual #ad disclosure near every published affiliate link.
6. Each week open a few products manually on Amazon.sa. Add the 10-character
   ASIN (from `/dp/ASIN`) to `data/products.csv`, set the matching item/style,
   `active=true`, and `reviewed_on=YYYY-MM-DD`. No scraping and no prices.
   Rows older than 14 days are ignored; search inspiration is the fallback.
7. Check actual clicks/earnings in Associates reporting after publication.
   A correctly formatted link alone does not prove approved attribution.

## 7. Add the exact GitHub Secrets and variables

Open [repository Actions secrets](https://github.com/Moot990/design-engine/settings/secrets/actions).
For each: **New repository secret > Name > Secret > Add secret**.

| Secret name | Needed for |
|---|---|
| `GEMINI_API_KEY` | Live text and visual review |
| `POLLINATIONS_API_KEY` | Earned-only live image generation |
| `AMAZON_ASSOCIATE_TAG` | Saudi affiliate export/publication |
| `PINTEREST_BOARD_ID` | Pinterest API destination |
| `PINTEREST_ACCESS_TOKEN` | Simple Pinterest API authorization |
| `PINTEREST_CLIENT_ID` | Optional continuous Pinterest OAuth |
| `PINTEREST_CLIENT_SECRET` | Optional continuous Pinterest OAuth |
| `PINTEREST_REFRESH_TOKEN` | Optional continuous Pinterest OAuth |
| `REPO_SECRETS_TOKEN` | Save rotated Pinterest refresh token securely |
| `YOUTUBE_CLIENT_ID` | YouTube OAuth |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth |
| `YOUTUBE_REFRESH_TOKEN` | YouTube upload authorization |

The built-in workflow `GITHUB_TOKEN` is supplied automatically. Do not create a
Secret for it. When continuous Pinterest OAuth is configured the static access
token is optional. No Gumroad key, paid API key or Amazon PA-API key is needed.

Choose **Variables > New repository variable** on the same settings page:

| Variable | Set only when |
|---|---|
| `GEMINI_FREE_TIER_CONFIRMED=true` | Gemini project has no billing |
| `POLLINATIONS_QUEST_ONLY=true` | Earned credits available; no paid funds |
| `PINTEREST_PUBLISH=true` | App/token approved and you want API Pin creation |
| `YOUTUBE_PUBLISH=true` | Correct channel OAuth verified and you want API uploads |
| `PUBLISHING_REVIEWED=true` | You reviewed a real generated batch |
| `ACTIONS_PRODUCTION_APPROVED=true` | GitHub confirmed this production use |
| `ENGINE_ENABLED=true` | All conditions above are met and daily cron is wanted |
| `AUTO_PUBLISH=true` | Daily cron should publish instead of just exporting |

Leave the publishing/schedule flags unset or false during setup. In repository
Settings > Actions > General, allow the pinned official GitHub actions used here
and permit the workflows' requested write access to repository contents. Protected
branch rules must allow the workflow's state commits; if they do not, the durable
checkpoint deliberately stops publishing.

## 8. Run your first real development test

1. Open [Actions](https://github.com/Moot990/design-engine/actions) > Daily content
   engine > Run workflow > branch main > mode **preflight** > Run workflow.
2. A missing setup entry produces a red result and a precise readiness list in
   the summary. This is intentional; it does not consume image credits.
3. After the three generation Secrets and two free-access variables are ready,
   run mode **generate** once. This generates a development test batch without
   platform uploads. Open the run summary and download its daily-batch artifact.
4. Review all images, Arabic/English text, suggested destinations, narration,
   video pacing and disclosures. Reject distorted or repetitive work.
5. After production-use confirmation and personal approval, set only the platform
   publishing flag(s) you need. On the next Saudi date run **publish**, initially
   with private YouTube output. Verify actual platform IDs and Studio/board output.
6. Only then enable `ENGINE_ENABLED` and `AUTO_PUBLISH` if wanted. A same-date rerun
   is deliberately blocked to avoid duplicates. A failed upload with unknown
   results must be reconciled before any manual retry.

## 9. Create Gumroad account and upload products later

Open [Gumroad](https://gumroad.com/) > Start selling > create your account.
Complete the identity/payout checks and confirm Saudi payout availability. No
monthly subscription is required; per-sale fees still apply. Keep it empty until
you have real, reviewed packs. After a month, download the monthly-product-pack
artifact within 7 days, review every page, provide a truthful AI disclosure and
usage license, choose your price, and upload the PDFs manually.

After the listing is live, put its HTTPS URL in `digital_product_url` in
`config/engine.yaml`. Pins then include the store link as well as their affiliate
destination. Update your YouTube channel profile link manually. Etsy is omitted
because its listing/payment fees do not meet the strict zero-upfront budget.

## 10. Maintain one hour per week

Follow [WEEKLY.md](WEEKLY.md) and fill [DAY-90.md](DAY-90.md) on your review date.
Account approval delays, earned-credit shortages or mandatory identity checks can
take longer during setup. Those cannot be automated or resolved by invented data.
