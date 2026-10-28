# Optional FreeVideo backend

ffmpeg remains the default. This is an optional **local** backend, not a free GPU
inside GitHub Actions. It needs the laptop and the installed FreeVideo server on.
No self-hosted GitHub runner, remote exposure, new model download or paid service
is configured. Local sample generation was explicitly requested by the owner.

## What was found on this laptop

- GPU: NVIDIA GeForce RTX 5070 Ti Laptop, 12,227 MiB VRAM; 32 GB system RAM.
- Installed API reports FreeVideo **0.4.21**, build `2026.10.24.212504`.
- App/data: `C:\Users\Moot\FreeVideo`; models/runtime under `FreeVideo-engine`.
- The existing Downloads installer is 74 MiB and its Windows signature is valid.
- Approximately **94 GiB / 101 GB** in the engine tree, including 56.77 GiB model
  files, 21.35 GiB prepared weights, 7.41 GiB environments, 7.07 GiB download cache
  and about 1.5 GiB other files. This includes optional image/prompt models.
- C: had approximately **300.5 GiB free** before the sample. No install was needed
  and no model downloads were requested. The already-installed models were used.

For a future reinstall, check the launcher's own missing-file estimate before
starting: versions, quantizations and reused models change the download. Major
existing components include a 14.61 GiB text encoder, about 9.7 GiB video decoder,
0.56 GiB audio decoder, 0.64 GiB upscaler and 21.35 GiB prepared int8 weights.
Do not treat the 74 MiB installer as the installed size or download a second set
of models automatically. Do not remove caches without understanding what they do.

## Agent interface and first frames

The [README](https://github.com/FlashML-org/FreeVideo) describes the engine and
ComfyUI integration. The
[agent client](https://github.com/FlashML-org/FreeVideo/blob/main/freevideo_engine/agent/client.py),
[CLI](https://github.com/FlashML-org/FreeVideo/blob/main/freevideo_engine/agent/cli.py),
and [agent guide](https://github.com/FlashML-org/FreeVideo/blob/main/freevideo_engine/agent/guide.py)
provide a dedicated authenticated REST API, CLI and MCP interface. Raw ComfyUI
workflows are not required for this adapter.

- Origin: `http://127.0.0.1:8188`; API prefix `/freevideo/agent/v1`.
- Read status and the installed guide/schema/OpenAPI first.
- POST `/media` with image bytes; use its returned `file` in `media.first.file`.
- POST `/plan`, then POST `/jobs` with prompt, 5 seconds, Light/Medium, dimensions,
  seed and a stable `ref`. The first image is the frame at time zero (`i2va`).
- Poll GET `/jobs/{id}`. Download `result.video.url` with the same authorization.
  POST `/jobs/{id}/cancel` cancels that job only.
- The CLI exposes `freevideo agent status`, `upload`, `plan`, `submit`, `job`,
  `wait`, and `cancel`. The public agent guide also documents MCP tools.

The app's existing `agent/token` is read only into memory; it is never printed or
copied into this repository. Optional environment overrides: `FREEVIDEO_HOME`,
`FREEVIDEO_URL` (loopback only), `FREEVIDEO_AGENT_TOKEN`. No token is needed in chat.
The adapter will not bind to the LAN or open a public endpoint.

## Running the weekly assembler

There was no `run_weekly.py` previously; this change adds it as a standalone
assembler for the existing daily export. It does not generate new ideas/images
or publish accounts. Extract a real daily-batch artifact and point `--batch` at
the folder containing the manifests and `short-copy.json`.

In `config/engine.yaml` change only when you want a local preview:

```yaml
video_backend: freevideo
freevideo:
  quality: light # or medium
  width: 544
  height: 960
  clip_seconds: 5
  max_ai_clips_per_week: 2
  max_minutes_per_run: 12
  cooldown_seconds: 30
  max_gpu_temperature_c: 82
  publication_cleared: false
```

With the installed app running:

```powershell
python run_weekly.py --batch output/daily --output output/weekly --local-preview
```

Use a Python environment with this project's small Python dependencies and
existing ffmpeg/ffprobe. Windows Arial/Segoe UI fonts are supported; Arabic text
still requires a Pillow build with RAQM. Nothing is installed automatically.

Remove `--local-preview` only when preparing publication output. With
`publication_cleared: false`, publication mode falls back to ffmpeg. Change that
flag only after obtaining clarification/permission covering your intended public
distribution. It is a record of your review, not a grant of legal rights.

Standard GitHub-hosted runs always fall back to ffmpeg, even if a copied config
requests FreeVideo. A localhost URL in Actions refers to the hosted runner,
not your laptop. The workflow is not changed into an unattended laptop worker.

## Limits, cancellation and fallback

- `.local/freevideo-budget.json` keeps weekly counts in Saudi ISO weeks.
  Attempts, including failed requests, count before submission. Do not delete it
  to obtain more clips. A lock prevents concurrent runs; a crash lock requires
  checking the app queue before manual recovery.
- The AI phase uses `max_minutes_per_run`, including uploads, polling, downloads
  and cooldowns. This bounds the adapter's generation wait; final ffmpeg assembly
  and TTS are separate. GPU cancellation is cooperative: a current kernel can
  finish after cancellation is requested. It is not a guaranteed hardware cutoff.
- Failed/unavailable services, malformed output, quota exhaustion, high observed
  GPU temperature and timeouts return to still-image ffmpeg rendering. Ambiguous
  requests are not automatically resubmitted. Check the app queue after a failure.
- Any generation-stage failure discards AI selections for that batch. A later
  ffmpeg processing failure falls back for the affected scene. Model sound is
  always removed; edge-tts supplies narration, with the existing captions fallback.
- Generated blocks follow FreeVideo's frame grid and may exceed exactly five
  seconds. Assembly trims them to five seconds, then holds the last frame to fill
  a longer scene. Other scenes retain the original slow-zoom effect.
- `video/freevideo/freevideo-result.json` records attempts, elapsed time, available
  GPU temperature/power/thermal flags and fallback warnings. No credentials appear.
- This monitors NVIDIA-reported GPU data, not CPU temperatures or chassis/fan
  sensors. It does not alter power modes, clocks, fan speeds or cooling settings.

## License and monetization

Read the [MiniMax H3 Community License and Exhibit A](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE).
Saudi Arabia is included. EU, UK, South Korea and US are excluded; section V.4
also restricts outputs outside the permitted territory. Worldwide YouTube/
Pinterest distribution is therefore unresolved, not automatically permitted by
your Saudi location. Ask MiniMax for written clarification before monetized
global distribution; no request has been sent for you.

Commercial terms require prominent MiniMax H3 identification on a commercial
product/service interface; whether a social channel/video is that interface is
unclear. The adapter conservatively adds MiniMax H3 credit when used. Above
US$20 million annual commercial revenue, separate written authorization is needed.
Model redistribution has additional license/notice duties, distinct from outputs.

Exhibit A requires prominent machine-generation disclosure in public content and
bars harmful, deceptive, infringing and fake-engagement uses. Every description
keeps bilingual AI disclosure; use YouTube's altered-content setting too. Neither
credit nor platform disclosure resolves territorial permission. FreeVideo's
Apache code license does not replace the model license.

## Timing and test evidence

The [official community table](https://github.com/FlashML-org/FreeVideo/blob/main/docs/community-results.md)
includes a matching 5070 Ti Laptop / 12 GB / 32 GB entry: **291 seconds for a
6.6-second Medium clip at 960x544**. It is a community measurement, not a benchmark
on this particular laptop. First-run loading, resolution, storage, power and
temperature matter. Do not scale it into a guaranteed five-second runtime.

See the measured sample results in `docs/FREEVIDEO-TEST.md`. Medium is not claimed
tested when only the one requested Light sample is generated.
