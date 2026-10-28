from __future__ import annotations

import hashlib
import itertools
import random

from .common import EngineError


def candidates(settings, day, previous, count=None):
    count = count or settings["pins_per_day"]
    used = {row["idea_id"] for row in previous}
    options = list(itertools.product(*(settings[key] for key in ("rooms", "styles", "palettes", "items", "formats"))))
    random.Random(day).shuffle(options)
    selected = []
    for room, style, palette, item, format_ in options:
        key = "|".join(part["id"] for part in (room, style, palette, item, format_))
        idea_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        if idea_id in used:
            continue
        # Distinct daily styles, palettes, featured items and teaching points.
        if len(selected) < min(count, len(settings["styles"]), len(settings["palettes"]), len(settings["items"]), len(settings["formats"])):
            if any(any(idea[k]["id"] == part["id"] for k, part in (("style", style), ("palette", palette), ("item", item), ("format", format_))) for idea in selected):
                continue
        language = "ar" if (int(day.replace("-", "")) + len(selected)) % 2 else "en"
        selected.append(dict(id=idea_id, room=room, style=style, palette=palette, item=item, format=format_, language=language))
        if len(selected) == count:
            return selected
    raise EngineError("Not enough unused ideas; add styles/palettes/items/formats to config")


def ledger_row(idea, day, status):
    return dict(idea_id=idea["id"], date=day, status=status, language=idea["language"], **{k: idea[k]["id"] for k in ("room", "style", "palette", "item", "format")})


def image_prompt(idea):
    return (
        f"Original realistic editorial interior photograph, residential {idea['room']['en']}, "
        f"{idea['style']['en']} design, {idea['palette']['en']} palette, "
        f"feature a clearly visible {idea['item']['en']}. Design lesson: {idea['format']['tip']} "
        "Believable furniture proportions, coherent perspective, practical circulation, "
        "physically plausible joinery and materials, daylight, refined designer styling, "
        "full room view, architectural photography, vertical 2:3 composition. "
        "No people, no text, no logos, no watermark, no copies of existing photographs, "
        "no impossible structures, no floating furniture, no duplicated objects."
    )
