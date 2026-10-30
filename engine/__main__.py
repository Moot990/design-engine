from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .common import ROOT, EngineError, config
from .pipeline import run
from .products import product_pack
from .reporting import day90, weekly


def main():
    parser = argparse.ArgumentParser(description="Cloud-only design content pipeline")
    parser.add_argument("command", choices=["run", "pack", "report"])
    parser.add_argument("--mode", choices=["preflight", "generate", "publish", "smoke"], default="preflight")
    parser.add_argument("--day")
    parser.add_argument("--output", default="output/daily")
    parser.add_argument("--state", default="state")
    parser.add_argument("--images", default="output/daily/image-archive")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--retry-empty", action="store_true", help="Explicit generate-only recovery of a reviewed zero-output failure; preserve all history")
    args = parser.parse_args()
    settings = config()
    day = args.day or datetime.now(ZoneInfo(settings["timezone"])).date().isoformat()
    datetime.strptime(day, "%Y-%m-%d")
    try:
        if args.command == "run":
            if args.mode == "smoke" and Path(args.state).resolve() == (ROOT / "state").resolve():
                raise EngineError("Smoke tests must use an isolated --state directory")
            run(settings, args.mode, day, args.output, args.state, retry_empty=args.retry_empty)
        elif args.command == "pack":
            entries = []
            for path in sorted(Path(args.images).rglob("*.json")):
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict) or "file" not in value:
                    continue
                image = (path.parent / value["file"]).resolve()
                if not image.is_relative_to(Path(args.images).resolve()) or not image.is_file():
                    raise EngineError("Product source path is invalid")
                entries.append({**value, "path": str(image)})
            # Keep monthly packs curated and within the artifact storage budget.
            entries.sort(key=lambda e: (e.get("date", ""), e.get("id", "")), reverse=True)
            chosen, per_style = [], {}
            for entry in entries:
                style = entry.get("style", "")
                if per_style.get(style, 0) >= 4:
                    continue
                chosen.append(entry)
                per_style[style] = per_style.get(style, 0) + 1
                if len(chosen) == 16:
                    break
            paths = product_pack(chosen, args.output, fixture=args.fixture)
            print("Created " + ", ".join(path.name for path in paths))
        else:
            Path(args.output).mkdir(parents=True, exist_ok=True)
            weekly(args.state, Path(args.output) / "weekly-latest.md", day)
            day90(Path(args.output) / "day-90-review.md")
    except EngineError as error:
        print("BLOCKED: " + str(error))
        raise SystemExit(2)
    except Exception as error:
        print("FAILED: " + type(error).__name__ + "; no credential-bearing exception details are printed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
