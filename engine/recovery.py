"""Restore accepted images from a reviewed, incomplete generate-only artifact."""
import json
import shutil
from pathlib import Path

from .affiliate import validate_affiliate_url
from .common import EngineError, read_csv
from .providers import fingerprint, pin_text


def restore_batch(settings, batch, day, rows, history, archive):
    batch = Path(batch).resolve()
    ready = json.loads((batch / "readiness.json").read_text(encoding="utf-8"))
    if ready.get("mode") != "generate" or ready.get("fixture") is not False or ready.get("date") != day:
        raise EngineError("Resume requires a genuine generate-only artifact from this date")
    pins = read_csv(batch / "pinterest-upload-manifest.csv")
    old = history["runs"][day]
    if not 0 < len(pins) == old.get("accepted") == old.get("pins_exported") < settings["pins_per_day"]:
        raise EngineError("Resume artifact does not match the recorded incomplete batch")
    ledger = {r["idea_id"]: r for r in rows if r["date"] == day and r["status"] == "accepted"}
    if len({p["idea_id"] for p in pins}) != len(pins):
        raise EngineError("Resume artifact repeats an image")
    accepted, restored_pins = [], []
    for pin in pins:
        row = ledger.get(pin["idea_id"])
        image = (batch / pin["image_file"]).resolve()
        if not row or not image.is_relative_to(batch) or not image.is_file() or pin["status"] != "ready-for-manual-upload" or not validate_affiliate_url(pin["link"], settings.get("AFFILIATE_PROGRAM")):
            raise EngineError("Resume source is invalid or has publication outcomes")
        provenance = json.loads(image.with_suffix(".json").read_text(encoding="utf-8"))
        known = history["images"].get(fingerprint(image), {})
        if provenance.get("fixture") is not False or provenance.get("vision_approved") is not True or provenance.get("id") != row["idea_id"] or known.get("id") != row["idea_id"]:
            raise EngineError("Resume image provenance or fingerprint does not match state")
        idea = {"id": row["idea_id"], "language": row["language"]}
        for key in ("room", "style", "palette", "item", "format"):
            idea[key] = next((v for v in settings[key + "s"] if v["id"] == row[key]), None)
            if idea[key] is None:
                raise EngineError("Resume concept no longer exists in configuration")
        # Repair text without spending credits regenerating accepted images.
        copy = pin_text(settings, idea)
        destination = archive / image.name
        shutil.copy2(image, destination)
        shutil.copy2(image.with_suffix(".json"), destination.with_suffix(".json"))
        accepted.append({"idea": idea, "image": destination, "copy": copy, "link": pin["link"]})
        restored_pins.append({**pin, "title": copy["title"], "description": copy["description"]})
    return accepted, restored_pins
