from __future__ import annotations

import json
import os
import shutil
from datetime import date
from pathlib import Path

from . import publish
from .affiliate import AI_NOTICE, DISCLOSURE, affiliate_link, affiliate_program
from .common import ROOT, EngineError, checkpoint, read_csv, save_json, write_csv
from .ideas import candidates, image_prompt, ledger_row
from .media import render_short
from .providers import fixture_image, fingerprint, gemini, generate_image, is_duplicate, pin_text, vision_review
from .reporting import weekly

IDEA_FIELDS = ["idea_id", "date", "room", "style", "palette", "item", "format", "language", "status"]
PIN_FIELDS = ["idea_id", "image_file", "title", "description", "link", "board", "board_id", "language", "status", "remote_id"]


def readiness(settings, publishing=False):
    missing = [name for name in ("GEMINI_API_KEY", "POLLINATIONS_API_KEY", "AMAZON_ASSOCIATE_TAG") if not os.environ.get(name)]
    for flag in ("GEMINI_FREE_TIER_CONFIRMED", "POLLINATIONS_QUEST_ONLY"):
        if os.environ.get(flag) != "true":
            missing.append(flag + "=true (repository variable)")
    if publishing:
        if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("ACTIONS_PRODUCTION_APPROVED") != "true":
            missing.append("ACTIONS_PRODUCTION_APPROVED=true only after GitHub confirms this production use")
        if not any(os.environ.get(p + "_PUBLISH") == "true" for p in ("PINTEREST", "YOUTUBE")):
            missing.append("Enable PINTEREST_PUBLISH or YOUTUBE_PUBLISH after platform setup")
        pinterest_names = ["PINTEREST_BOARD_ID"] + (["PINTEREST_CLIENT_ID", "PINTEREST_CLIENT_SECRET", "PINTEREST_REFRESH_TOKEN", "REPO_SECRETS_TOKEN"] if os.environ.get("PINTEREST_REFRESH_TOKEN") else ["PINTEREST_ACCESS_TOKEN"])
        for platform, names in (("PINTEREST", pinterest_names), ("YOUTUBE", ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"])):
            if os.environ.get(platform + "_PUBLISH") == "true":
                missing.extend(name for name in names if not os.environ.get(name))
        if os.environ.get("PUBLISHING_REVIEWED") != "true":
            missing.append("PUBLISHING_REVIEWED=true after reviewing real output")
    return missing


def short_copy(settings, accepted, language, fixture=False):
    if fixture:
        return {"hook": "تفاصيل لغرفة المعيشة" if language == "ar" else "Four details for a calmer living room",
                "captions": ["توازن الأثاث", "تنويع الخامات", "إضاءة هادئة", "مسار واضح"][:len(accepted)] if language == "ar" else [a["idea"]["format"]["tip"] for a in accepted],
                "script": "راجع مقاسات الأثاث قبل الشراء، وسيب طريق مريح للحركة. جرّب خامة ناعمة جنب خامة منسوجة، وضيف إضاءة جانبية هادئة. اختار قطع تناسب مساحة غرفة المعيشة، وقلل الزحمة." if language == "ar" else "Compare the furniture scale before buying. Mix smooth and woven textures. Add soft lighting and leave a clear walking route. These simple checks help you assess a room before choosing your next piece."}
    concepts = [{"style": a["idea"]["style"]["en"], "lesson": a["idea"]["format"]["tip"]} for a in accepted]
    value = gemini(settings, f"Write a useful, original {'Arabic' if language == 'ar' else 'English'} interior design Short for {settings.get('audience', 'Egypt and the Arab world')}. Use natural, simple Arabic understandable across the Arab world, with light Egyptian phrasing when Arabic; English is secondary. Return JSON: hook (max 55 characters), captions (array of {len(accepted)} scene-specific practical tips, each max 80 characters), script ({'25-30' if language == 'ar' else '35-45'} spoken words total for 24 seconds, concise enough for unhurried speech). Scenes in order: {json.dumps(concepts)}. Connect the lessons naturally, no invented experience, brand names, prices or product match claims. No links. Teach something, do not just list aesthetic words.")
    if not isinstance(value, dict) or not isinstance(value.get("hook"), str) or not 1 <= len(value["hook"]) <= 55 or not isinstance(value.get("captions"), list) or len(value["captions"]) != len(accepted) or any(not isinstance(c, str) or not 1 <= len(c) <= 80 for c in value["captions"]) or not isinstance(value.get("script"), str) or not 25 <= len(value["script"].split()) <= 55:
        raise EngineError("Short narration/caption response failed validation")
    return value


def record_publication(history, state_file, day, key, platform, callback):
    if key in history["publications"]:
        return  # Published, inflight and unknown all require deliberate reconciliation.
    value = {"date": day, "platform": platform, "status": "inflight"}
    history["publications"][key] = value
    save_json(state_file, history)
    checkpoint("Reserve platform upload " + key)
    try:
        remote_id, privacy = callback()
        value.update(status="published", remote_id=remote_id, privacy=privacy)
    except EngineError:
        value.update(status="unknown")
        save_json(state_file, history)
        checkpoint("Record upload requiring reconciliation " + key)
        raise
    save_json(state_file, history)
    checkpoint("Record confirmed platform upload " + key)


def run(settings, mode, day, output, state_dir):
    settings = {**settings, "AFFILIATE_PROGRAM": affiliate_program(settings.get("AFFILIATE_PROGRAM"))}
    fixture = mode == "smoke"
    output, state_dir = Path(output).resolve(), Path(state_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    missing = [] if fixture else readiness(settings, mode == "publish")
    save_json(output / "readiness.json", {"mode": mode, "date": day, "ready": not missing, "missing": missing, "fixture": fixture, "note": "A ready configuration is not proof that remote APIs or account approvals work."})
    if mode == "preflight":
        if missing:
            raise EngineError("Setup incomplete: " + ", ".join(missing))
        print("Configuration is present. Run generate to test live providers; publishing remains separate.")
        return
    if missing:
        raise EngineError("Setup incomplete; see readiness.json: " + ", ".join(missing))
    if fixture:
        state_dir.mkdir(parents=True, exist_ok=True)
        if not (state_dir / "ideas.csv").exists():
            write_csv(state_dir / "ideas.csv", [], IDEA_FIELDS)
            save_json(state_dir / "history.json", {"images": {}, "publications": {}, "runs": {}})
    state_file = state_dir / "history.json"
    history = json.loads(state_file.read_text(encoding="utf-8"))
    rows = read_csv(state_dir / "ideas.csv")
    if day in history["runs"]:
        raise EngineError("This date is already reserved; do not rerun blindly. Check state and platform results first")
    history["runs"][day] = {"status": "started", "warnings": [], "fixture": fixture}
    save_json(state_file, history)
    if not fixture:
        checkpoint("Reserve daily content batch " + day)
    warnings = history["runs"][day]["warnings"]
    accepted, pins = [], []
    archive = output / "image-archive"
    archive.mkdir(exist_ok=True)
    try:
        idea_count = max(4, settings["pins_per_day"])
        selected = candidates(settings, day, rows, idea_count)
        for n, idea in enumerate(selected):
            row = ledger_row(idea, day, "reserved")
            rows.append(row)
            write_csv(state_dir / "ideas.csv", rows, IDEA_FIELDS)
            if not fixture:
                checkpoint("Reserve design idea " + idea["id"])
            image = archive / (idea["id"] + ".jpg")
            try:
                if fixture:
                    fixture_image(image, n)
                else:
                    generate_image(settings, image_prompt(idea), int(idea["id"][:8], 16), image)
                hash_ = fingerprint(image)
                if not fixture and is_duplicate(hash_, history["images"]):
                    raise EngineError("Image rejected as a perceptual duplicate")
                approved = fixture or (settings["require_vision_review"] and vision_review(settings, image, idea))
                if not approved:
                    raise EngineError("Image failed the required AI visual review")
                copy = pin_text(settings, idea, fixture)
                tag = "fixture-eg" if fixture else os.environ["AMAZON_ASSOCIATE_TAG"]
                link = affiliate_link(idea, tag, ROOT / "data/products.csv", date.fromisoformat(day), program=settings.get("AFFILIATE_PROGRAM"))
                product_url = settings.get("digital_product_url", "")
                if product_url:
                    from urllib.parse import urlparse
                    if urlparse(product_url).scheme != "https":
                        raise EngineError("Digital product URL must use HTTPS")
                    copy["description"] += "\nDesign pack: " + product_url
                    if len(copy["description"]) > 800:
                        raise EngineError("Digital product link makes the Pin description too long")
                entry = {"id": idea["id"], "file": image.name, "source": "fixture" if fixture else "pollinations", "fixture": fixture, "vision_approved": not fixture, "style": idea["style"]["en"], "palette_name": idea["palette"]["en"], "colors": idea["palette"]["colors"], "tip": idea["format"]["tip"], "prompt": image_prompt(idea), "model": "fixture" if fixture else settings["image_model"], "date": day, "language": idea["language"]}
                save_json(archive / (idea["id"] + ".json"), entry)
                accepted.append({"idea": idea, "image": image, "copy": copy, "link": link})
                history["images"][hash_] = {"id": idea["id"], "date": day}
                row["status"] = "accepted"
                pins.append({"idea_id": idea["id"], "image_file": "image-archive/" + image.name, "title": copy["title"], "description": copy["description"], "link": link, "board": "أفكار لغرفة المعيشة" if idea["language"] == "ar" else "Living Room Ideas", "board_id": os.environ.get("PINTEREST_BOARD_ID", ""), "language": idea["language"], "status": "fixture" if fixture else "ready-for-manual-upload"})
            except EngineError as error:
                row["status"] = "rejected"
                image.unlink(missing_ok=True)
                warnings.append(idea["id"] + ": " + str(error))
            write_csv(state_dir / "ideas.csv", rows, IDEA_FIELDS)
            save_json(state_file, history)
        write_csv(output / "pinterest-upload-manifest.csv", pins[:settings["pins_per_day"]], PIN_FIELDS)
        # Preserve only accepted source images/metadata for monthly products.
        if not fixture:
            checkpoint("Record generated images and quality outcomes " + day)
        video = None
        short_meta = None
        if len(accepted) >= 4:
            scenes = accepted[:6]
            language = settings.get("primary_language", "ar")
            try:
                copy = short_copy(settings, scenes, language, fixture)
                video, media_warnings = render_short([a["image"] for a in scenes], copy, settings, language, output / "video", fixture=fixture, variant=date.fromisoformat(day).toordinal(), publishing=mode == "publish")
                warnings.extend(media_warnings)
                if not fixture:
                    for frame in (output / "video").glob("frame-*.png"):
                        frame.unlink()
                description = f"{DISCLOSURE}\n{AI_NOTICE}\n{copy['script']}\n\nمنتجات مشابهة للإلهام / Similar-item inspiration:\n" + "\n".join(a["link"] for a in scenes) + "\nروابط المنتجات في وصف Shorts غير قابلة للنقر؛ استخدم روابط القناة. Product links in Shorts descriptions are not clickable; use the channel profile. #Shorts"
                ai_report = output / "video/freevideo/freevideo-result.json"
                if ai_report.exists() and json.loads(ai_report.read_text(encoding="utf-8")).get("used_ai_clips", 0):
                    description += "\nAI video animation: MiniMax H3 via FreeVideo."
                short_meta = {"video_file": "video/short.mp4", "title": copy["hook"], "description": description, "language": language, "privacy": settings["youtube_privacy"], "contains_synthetic_media": True, "status": "fixture" if fixture else "ready-for-manual-upload"}
                write_csv(output / "youtube-upload-manifest.csv", [short_meta], list(short_meta))
                save_json(output / "short-copy.json", copy)
            except EngineError as error:
                warnings.append("Short: " + str(error))
        else:
            warnings.append("Short skipped: fewer than four accepted distinct images")
        if mode == "publish":
            for pin, item in zip(pins[:settings["pins_per_day"]], accepted):
                if os.environ.get("PINTEREST_PUBLISH") == "true":
                    try:
                        record_publication(history, state_file, day, "pin-" + pin["idea_id"], "pinterest", lambda p=pin, i=item: (publish.pinterest(i["image"], p["title"], p["description"], p["link"], os.environ["PINTEREST_BOARD_ID"], program=settings.get("AFFILIATE_PROGRAM")), "public"))
                    except EngineError as error:
                        warnings.append(str(error))
                        break  # Avoid a batch of ambiguous requests after platform failure.
            if video and os.environ.get("YOUTUBE_PUBLISH") == "true":
                try:
                    record_publication(history, state_file, day, "short-" + day, "youtube", lambda: publish.youtube(video, short_meta["title"], short_meta["description"], settings["youtube_privacy"], short_meta["language"]))
                except EngineError as error:
                    warnings.append(str(error))
        # Exports must reflect actual API outcomes so manual fallback cannot invite
        # a second upload of an already-published or ambiguous item.
        for pin in pins:
            result = history["publications"].get("pin-" + pin["idea_id"])
            if result:
                pin.update(status=result["status"], remote_id=result.get("remote_id", ""))
        write_csv(output / "pinterest-upload-manifest.csv", pins[:settings["pins_per_day"]], PIN_FIELDS)
        if short_meta:
            result = history["publications"].get("short-" + day)
            if result:
                short_meta.update(status=result["status"], remote_id=result.get("remote_id", ""), privacy=result.get("privacy", short_meta["privacy"]))
            write_csv(output / "youtube-upload-manifest.csv", [short_meta], list(short_meta))
        history["runs"][day]["status"] = "complete" if len(pins) >= settings["pins_per_day"] and video else "partial"
        if warnings:
            history["runs"][day]["status"] = "needs-review"
        history["runs"][day].update(accepted=len(accepted), pins_exported=min(len(pins), settings["pins_per_day"]), video_ready=bool(video))
    except Exception:
        history["runs"][day]["status"] = "failed"
        raise
    finally:
        save_json(state_file, history)
        save_json(output / "result.json", history["runs"][day])
        report_dir = output if fixture else ROOT / "reports"
        report_dir.mkdir(exist_ok=True)
        weekly(state_dir, report_dir / "weekly-latest.md", day)
        if not fixture:
            checkpoint("Record daily content results " + day)
    (output / "UPLOAD-INSTRUCTIONS.txt").write_text(
        "TEST FIXTURES: DO NOT PUBLISH OR SELL.\n" if fixture else
        "Review images first. In Pinterest choose Create Pin, upload the listed JPEG, and copy title, description, destination and board from the manifest. This CSV is a local upload manifest, not a native bulk-import CSV (that needs hosted media URLs).\nIn YouTube Studio choose Create > Upload videos and upload short.mp4; use the manifest, check altered-content disclosure and audience, and schedule manually. Check state/history.json first to avoid re-uploading items already sent by the API.\n",
        encoding="utf-8",
    )
    print(json.dumps({"mode": mode, **history["runs"][day]}, ensure_ascii=False))
    if history["runs"][day]["status"] != "complete":
        raise EngineError("Batch incomplete or requires review; usable exports are retained in the artifact")
