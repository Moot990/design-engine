# Project working rules

- Work directly on `main`. Use clear commits and push after each major step.
- Run only quick syntax checks locally. Execute behavior tests, image/video
  generation, ffmpeg rendering and PDF rendering on GitHub Actions.
- Do not install heavy software on the laptop.
- Store credentials only in GitHub Secrets; never log request headers, OAuth
  responses, bearer tokens or signed upload-session URLs.
- Generated affiliate links intentionally expose the public Associates tag;
  do not commit those generated exports or tags to source/state files.
- Preserve the persistent idea ledger, image fingerprints and publication outbox.
  Never blindly retry a publishing request whose remote result is unknown.
- Do not enable production schedules without confirming GitHub's current terms,
  earned-only image access, and the user's review of real output.
- Do not claim a feature works without a relevant GitHub Actions run. Clearly
  distinguish synthetic fixture tests, live provider tests and actual publishing.

## Ruflo integration

For multi-file tasks, discover available Ruflo MCP tools before starting.
If they are not exposed in the session, report their absence when relevant and
continue with the available tools. Do not install a new runtime just for this.
