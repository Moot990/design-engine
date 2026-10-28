"""Assemble a reviewed daily export with the optional LOCAL FreeVideo backend.

No account publishing, new image generation, model install or model downloads.
The existing cloud daily workflow remains the default production entry point.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from engine.affiliate import AI_NOTICE
from engine.common import EngineError, config, read_csv, save_json, write_csv
from engine.media import render_short


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, help="Extracted daily-batch artifact folder")
    parser.add_argument("--output", default="output/weekly")
    parser.add_argument("--local-preview", action="store_true", help="Local-only preview; does not establish worldwide publication rights")
    parser.add_argument("--allow-fixtures", action="store_true", help="Cloud tests only; fixture input always disables AI generation")
    args = parser.parse_args()
    batch, output = Path(args.batch).resolve(), Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    pins = read_csv(batch / "pinterest-upload-manifest.csv")
    if not pins:
        raise EngineError("Batch contains no accepted images")
    fixture = any(p.get("status") == "fixture" for p in pins)
    if fixture and not args.allow_fixtures:
        raise EngineError("Test fixtures are not publishable; choose a real batch")
    copy = json.loads((batch / "short-copy.json").read_text(encoding="utf-8"))
    if not isinstance(copy.get("captions"), list) or not 4 <= len(copy["captions"]) <= 6:
        raise EngineError("Batch needs a validated four-to-six-scene Short script")
    sources = [batch / p["image_file"] for p in pins]
    sources.extend(p for p in sorted((batch / "image-archive").glob("*.jpg")) if p not in sources)
    images = [p.resolve() for p in sources[:len(copy["captions"])]]
    if len(images) != len(copy["captions"]) or any(not p.is_relative_to(batch) or not p.is_file() for p in images):
        raise EngineError("Batch image paths are invalid or incomplete")
    manifests = read_csv(batch / "youtube-upload-manifest.csv")
    if not manifests:
        raise EngineError("Batch is missing video language/description metadata")
    metadata = dict(manifests[0])
    settings = config()
    video, warnings = render_short(images, copy, settings, metadata["language"], output / "video", fixture=fixture, variant=date.today().toordinal(), publishing=not args.local_preview)
    if AI_NOTICE not in metadata["description"]:
        metadata["description"] = AI_NOTICE + "\n" + metadata["description"]
    ai_report = output / "video/freevideo/freevideo-result.json"
    report = json.loads(ai_report.read_text(encoding="utf-8")) if ai_report.exists() else {}
    used_ai = bool(report.get("used_ai_clips"))
    if used_ai:
        metadata["description"] += "\nAI video animation: MiniMax H3 via FreeVideo."
    metadata.update(video_file="video/short.mp4", status="fixture" if fixture else "local-preview-only" if args.local_preview else "ready-for-manual-review", contains_synthetic_media=True)
    write_csv(output / "youtube-upload-manifest.csv", [metadata], list(metadata))
    save_json(output / "weekly-result.json", {"video": str(video), "requested_backend": settings.get("video_backend", "ffmpeg"), "ai_clips_used": report.get("used_ai_clips", 0), "warnings": warnings, "fixture": fixture, "local_preview_only": args.local_preview, "publication_cleared": not used_ai or report.get("publication_cleared") is True})
    (output / "UPLOAD-REMINDER.txt").write_text("Review before publishing. In YouTube Studio > Details > Altered content select Yes for realistic AI interiors. Descriptions include AI disclosure. Local-preview and fixture videos must not be uploaded. No platform upload was performed.\n", encoding="utf-8")
    print(json.dumps({"video": str(video), "warnings": warnings, "ai_clips_used": report.get("used_ai_clips", 0)}))


if __name__ == "__main__":
    try:
        main()
    except EngineError as error:
        print("BLOCKED: " + str(error))
        raise SystemExit(2)
    except Exception as error:
        print("FAILED: " + type(error).__name__)
        raise SystemExit(1)
