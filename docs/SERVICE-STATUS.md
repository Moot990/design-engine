# Service and terms check - 29 October 2026

These findings change the original brief. They are not a promise of free,
uninterrupted production access or revenue.

## Images

[Pollinations official API documentation](https://github.com/pollinations/pollinations/blob/main/APIDOCS.md)
requires an API key. The cloud no-key probe returned HTTP 401.
[The official Pollen FAQ](https://github.com/pollinations/pollinations/blob/main/enter.pollinations.ai/POLLEN_FAQ.md)
describes earned Quest Pollen and purchased Pollen, with changing Quest availability.
Free earned credits do not establish a reliable daily 3-10-image allowance.

The adapter uses a secret key, the documented balance/model endpoints, rejects
paid balances and paid-only/unknown models, and checks before every generation.
It requires `account:usage` read access. Do not buy credits, attach auto-recharge,
or enable a paid billing method. Use a small key budget and only earned credits.
If enough earned credits are not available, this architecture cannot promise
daily free generation. It stops rather than switching to a paid service.

## Text and visual checking

[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) offers model-specific
free access; [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) depend
on the actual project. The configurable default is `gemini-2.5-flash`.
Create a project without billing and confirm its free tier in AI Studio. Failed
quotas do not trigger a paid fallback. AI visual checks are imperfect and cannot
guarantee designer quality or originality.

## Pinterest

[Official developer setup](https://developers.pinterest.com/docs/getting-started/connect-app/)
and [v5 API specification](https://github.com/pinterest/api-description)
govern API access, board selection, scopes and Pin creation. Trial access is not
a guarantee of production access; check the actual app's permissions/approval.
[Commercial/affiliate guidelines](https://policy.pinterest.com/en/commercial-and-branded-content-guidelines)
require transparency and original value, and warn against repetitive/large-volume
affiliate posting. Four daily Pins is an initial content choice, not a policy safe harbor.

The fallback is downloadable JPEGs and a local manifest for manual creation and
scheduling. It is not a one-click native bulk import or a media hosting service.
[Access tokens expire](https://developer.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/);
the adapter can exchange your continuous refresh token when configured. Invalid
or expired account authorization still needs your personal sign-in.

## YouTube

[Current videos.insert documentation](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
currently says unverified API projects are **not** restricted to private viewing.
Older statements about mandatory private uploads should not be assumed current.
The engine nevertheless defaults to private while channel/API behavior is tested.
The request sends `status.containsSyntheticMedia=true` for these realistic AI concepts.

[Shorts description/comment URLs are not clickable](https://support.google.com/youtube/answer/13748639).
Put a relevant, disclosed destination in channel profile links. Each video still
exports item links, but do not claim description clicks are a reliable funnel.
[Inauthentic content rules](https://support.google.com/youtube/answer/1311392)
exclude mass-produced/repetitive content from monetization; voice/visual variation
alone does not guarantee originality, YPP eligibility, views or ad revenue.

[Google OAuth tokens for external apps in Testing](https://developers.google.com/identity/protocols/oauth2)
normally expire after 7 days with the upload scope. Production publishing status,
OAuth verification and YouTube API/account reviews are separate matters.

## Amazon.sa

Use the [Saudi Associates agreement](https://affiliate-program.amazon.sa/help/operating/agreement)
and [Saudi program policies](https://affiliate-program.amazon.sa/help/operating/policies)
shown in your account. Declare your actual social channels, disclose affiliate
links, verify that your particular social placements and search links are allowed,
and check your tracking tag in Associates reporting.

The [old PA-API locale list](https://webservices.amazon.eu/paapi5/documentation/common-request-parameters.html)
listed Saudi Arabia, so 'Saudi is unsupported' is not a valid assumption.
[Amazon's documentation now redirects to its PA-API deprecation/Creators API notice](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation).
This engine does not depend on PA-API or scrape Amazon. It uses your manually
reviewed ASINs or tagged search URLs. Search links and generated furniture are
clearly described as similar-item inspiration, without prices or availability claims.

## GitHub Actions

[Billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
says standard hosted-runner minutes are free for public repositories; artifact
storage still has limits. The repository was changed from private to public by
the owner during setup and its public status was verified through GitHub's API.

[Additional product terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)
restrict hosted Actions to activities related to the software project and caution
against using it as a serverless application/CDN. Development tests are run here.
Continuous commercial content production is not assumed permitted. Ask GitHub
Support whether this exact small daily batch workload is allowed before enabling
production. Cron requires `ACTIONS_PRODUCTION_APPROVED=true` only after confirmation.
No artificial commits are made merely to keep schedules alive.

## Speech and products

[edge-tts](https://github.com/rany2/edge-tts) is an unofficial client for Edge's online
speech service. It has no guaranteed availability or blanket commercial-use license.
Review the service's applicable terms before using its audio commercially. Failure
keeps captions-only output, marked for review. No copyrighted music is used.

[Gumroad has no monthly fee](https://gumroad.com/help/article/66-gumroads-fees), but
fees are deducted from sales. Zero subscriptions does not mean fee-free selling.
Confirm [Saudi payout availability and verification](https://gumroad.com/help/article/13-getting-paid)
in your own account. Etsy listing/payment fees conflict with a strict zero-upfront
budget, so Etsy is not provisioned. No store account, price or product listing is
created automatically. These steps require your identity, payout details and review.
