# FreeVideo verification - 29 October 2026

## Local sample

Hardware was read from NVIDIA's driver: RTX 5070 Ti Laptop, 12,227 MiB VRAM.
The installed agent reported API v1, FreeVideo 0.4.21, ready, and first-frame
generation support. No model or CUDA download was performed.

| Measurement | Result |
|---|---|
| Requested generation | One 5-second Light clip, 544x960, supplied first frame |
| First attempt | Failed after 283.33 seconds / 4m43s |
| Diagnosed cause | All-zero generated PyTorch/Inductor Python cache source |
| Repair | Quarantined eight confirmed all-zero `.py` cache files; no weights deleted or changed |
| Retry | Resumed the same job; succeeded in 291.20 seconds / 4m51s |
| Raw output | 544x960, 5.175 seconds (the model uses a frame grid) |
| Final local preview | Exactly 5.000 seconds, generated audio removed, AI/MiniMax H3 label, edge-tts narration |
| Local narration | English Aria voice, 3.768 seconds; ffmpeg padded remaining audio time |
| Successful-attempt GPU samples | 58 samples; 42-74 C |
| Thermal issues | One software thermal-slowdown flag at 74 C on retry; first attempt also had one at 73 C |
| Hardware thermal slowdown | Not observed in the sampled flags |
| Shutdown | The server started for this test was stopped afterwards |

These wall-clock timings include media upload, model startup/loading, compilation,
job polling and download, rather than just the denoising kernel. The two render
attempts total 574.53 seconds, excluding repair and other development work. The
five-second raw length follows the model's frame grid and is trimmed for assembly.

The source was an **existing low-resolution generated contact-sheet preview**
from this installation, not a production-approved design-engine photograph.
The sample verifies first-frame operation, not fidelity across a production batch.
No sample has been uploaded to YouTube, Pinterest or public GitHub artifacts.

Local outputs, intentionally ignored by Git:

- `output/freevideo-sample/light-preview-narrated-5s.mp4`: labelled final sample.
- `output/freevideo-sample/light-sample.mp4`: untrimmed original, includes model audio.
- `output/freevideo-sample/measurement.json`: successful attempt and GPU samples.
- `output/freevideo-sample/initial-failure.json`: first attempt's measurements.
- `output/freevideo-sample/caption-ar-local.png`: inspected Windows Arabic caption.

The app interpreter did not have edge-tts or RAQM. A separate **36.1 MiB** project
runtime was created under `.local/video-runtime`, using only the small assembly
requirements. Windows Arabic fallback was visually checked. This installed no
torch, ComfyUI, CUDA or model weights, and left the app's environment unchanged.

## Cloud code tests

[Run 40783902183](https://github.com/Moot990/design-engine/actions/runs/40783902183)
on code commit `c4430cf` passed, including:

- 24 behavioral tests: original engine tests plus FreeVideo defaults, loopback
  credential isolation, publishing/hosted-runner gates, temperature gate, attempt
  quota, cooldown, timeout cancellation and persistent fallback behavior.
- Real ffmpeg mixed moving-clip/still-image assembly with caption overlays.
- `run_weekly.py` using its default ffmpeg backend on an isolated fixture batch.
- Bilingual caption rendering, including a forced non-RAQM Arabic path.
- Existing full sample batch/PDF renders and separate live TTS probes.

The real model inference happened locally, as specifically requested. The cloud
tests mock the local agent rather than downloading model weights onto a runner.

## Not tested or unresolved

- **Medium was not generated locally.** The official community table reports a
  6.6-second Medium clip in 291 seconds at 960x544 on matching GPU/VRAM/RAM; this
  is not a measured five-second runtime on this laptop.
- No full week of real AI content, production image batch, unattended scheduler,
  long-run temperature test or real account upload was performed.
- The exact `animate_selected` generation loop is covered with a mocked API in
  cloud tests. Actual local authentication/readiness and the documented agent
  upload/plan/job/poll/download flow were exercised against the live installation.
- CPU/hotspot/VRAM-junction temperatures and fan sensors were not recorded.
- The 82 C cutoff was not reached locally; its cancellation path was exercised
  with controlled test inputs, not by intentionally heating the laptop.
- Worldwide monetized output permission remains unresolved; do not infer it from
  a successful technical test. `publication_cleared` stays false and ffmpeg is the
  default backend. See [the license findings](FREEVIDEO.md#license-and-monetization).
