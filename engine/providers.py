from __future__ import annotations

import base64
import io
import json
import math
import os
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageStat

from .affiliate import AI_NOTICE, DISCLOSURE
from .common import EngineError, request, response_json, secret


def gemini(settings, instruction, images=()):
    if os.environ.get("GEMINI_FREE_TIER_CONFIRMED") != "true":
        raise EngineError("Confirm a Gemini project with no billing in repository variable GEMINI_FREE_TIER_CONFIRMED")
    parts = [{"text": instruction}]
    for path in images:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(Path(path).read_bytes()).decode()}})
    payload = {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.55}}
    response = request("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{quote(settings['gemini_model'], safe='')}:generateContent", service="Gemini", retry_safe=True, headers={"x-goog-api-key": secret("GEMINI_API_KEY")}, json=payload)
    data = response_json(response, "Gemini")
    try:
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        return json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError):
        raise EngineError("Gemini returned blocked or malformed content") from None


def image_account_ready(settings):
    if os.environ.get("POLLINATIONS_QUEST_ONLY") != "true":
        raise EngineError("Image generation needs earned Quest Pollen and POLLINATIONS_QUEST_ONLY=true; no purchases allowed")
    headers = {"Authorization": "Bearer " + secret("POLLINATIONS_API_KEY")}
    balance = response_json(request("GET", "https://gen.pollinations.ai/account/balance", service="Pollinations balance", retry_safe=True, headers=headers), "Pollinations balance")
    try:
        account = balance["accountBalance"]
        tier, paid, key_balance = float(account["tier"]), float(account["paid"]), float(balance["balance"])
        if not all(math.isfinite(v) for v in (tier, paid, key_balance)) or paid != 0 or tier <= 0 or key_balance <= 0:
            raise EngineError("Pollinations requires positive earned balance and zero paid balance; generation stopped")
    except (KeyError, TypeError, ValueError):
        raise EngineError("Pollinations balance cannot prove earned-only access; enable read-only account:usage on the key") from None
    models = response_json(request("GET", "https://gen.pollinations.ai/image/models", service="Pollinations models", retry_safe=True, headers=headers), "Pollinations models")
    if not isinstance(models, list):
        raise EngineError("Image model catalog format changed; generation stopped")
    model = next((m for m in models if isinstance(m, dict) and (m.get("name") == settings["image_model"] or m.get("id") == settings["image_model"] or settings["image_model"] in m.get("aliases", []))), None)
    if model is None or model.get("paid_only") is not False or model.get("community") is not False or model.get("category") != "image":
        raise EngineError("Selected image model is unavailable or not explicitly eligible for earned Pollen")
    # Only a documented, single fixed per-image price can establish a useful
    # pre-request credit bound. Do not guess token/resolution-dependent costs.
    pricing = model.get("pricing", {})
    try:
        cost = float(pricing["completionImageTokens"])
    except (KeyError, TypeError, ValueError):
        raise EngineError("Image price is unknown; generation stopped") from None
    if model.get("flat_rate") is not True or model.get("pricing_dimensions") or model.get("pricing_units") or set(pricing) != {"currency", "completionImageTokens"} or pricing["currency"] != "pollen" or not math.isfinite(cost) or cost < 0:
        raise EngineError("Image model does not have an unambiguous fixed per-image price")
    if min(tier, key_balance) < max(cost * 2, .001):
        raise EngineError("Insufficient earned/key budget for the next image with safety margin")
    return headers


def generate_image(settings, prompt, seed, destination):
    headers = image_account_ready(settings)  # Recheck balance before EVERY generation.
    response = request("GET", "https://gen.pollinations.ai/image/" + quote(prompt, safe=""), service="Pollinations image", headers=headers, params={"model": settings["image_model"], "width": 1000, "height": 1500, "seed": seed})
    if not response.headers.get("Content-Type", "").startswith("image/") or len(response.content) > 15_000_000:
        raise EngineError("Image service did not return a supported image")
    try:
        with Image.open(io.BytesIO(response.content)) as original:
            original.load()
            if original.width < 800 or original.height < 1200 or abs(original.width / original.height - 2 / 3) > .06:
                raise EngineError("Image dimensions/composition do not meet the vertical requirement")
            image = original.convert("RGB").resize((1000, 1500), Image.Resampling.LANCZOS)
            image.save(destination, "JPEG", quality=88, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise EngineError("Image decoding failed") from None


def fixture_image(destination, number):
    """Synthetic test cards only: never accepted for publication or sale."""
    image = Image.new("RGB", (1000, 1500), (224 - number * 13, 212, 192 + number * 5))
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 120, 940, 1000), fill=(60 + number * 30, 83, 94))
    for index in range(12):
        x = 80 + ((index * 79 + number * 53) % 800)
        y = 180 + ((index * 131 + number * 97) % 700)
        draw.ellipse((x, y, x + 75, y + 75), fill=(160, 130 + index * 7, 80 + number * 13))
    draw.text((90, 1120), "TEST FIXTURE - NOT A GENERATED INTERIOR", fill="black", font_size=28)
    image.save(destination, quality=85)


def fingerprint(path):
    with Image.open(path) as image:
        image.load()
        if image.size != (1000, 1500):
            raise EngineError("Image is not 1000x1500")
        gray = image.convert("L")
        if ImageStat.Stat(gray).stddev[0] < 12:
            raise EngineError("Image is blank or has insufficient contrast")
        small = gray.resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())
        value = 0
        for y in range(8):
            for x in range(8):
                value = (value << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
        return f"{value:016x}"


def is_duplicate(hash_, history, threshold=6):
    return any((int(hash_, 16) ^ int(old, 16)).bit_count() <= threshold for old in history)


def vision_review(settings, path, idea):
    result = gemini(settings, (
        "Review this AI interior image strictly. Return JSON: "
        '{"approved":boolean,"geometry_ok":boolean,"no_text_or_watermarks":boolean,'
        '"featured_item_visible":boolean,"designer_quality":integer,"reason":string}. '
        f"Featured item must visibly be {idea['item']['en']}. Reject distorted furniture, impossible "
        "perspective, floating objects, duplicated items, text/logos, implausible lighting, or poor styling. "
        "Designer quality score is 1 to 5; approval requires at least 4."
    ), [path])
    if not isinstance(result, dict):
        raise EngineError("Visual review returned an invalid response")
    approved = all(result.get(k) is True for k in ("approved", "geometry_ok", "no_text_or_watermarks", "featured_item_visible"))
    return approved and isinstance(result.get("designer_quality"), int) and result["designer_quality"] >= 4


def pin_text(settings, idea, fixture=False):
    language = idea["language"]
    if fixture:
        value = dict(title=f"TEST {idea['style']['en']} living room", description="Synthetic fixture for cloud tests only.", hashtags=["#InteriorDesign"], script="Test one design detail. Compare a smooth surface with a woven texture and check the room proportions before buying.")
        if language == "ar":
            value.update(title=f"اختبار: غرفة معيشة بطابع {idea['style']['ar']}", description="عينة اختبار فقط: راجع المقاسات وسيب مساحة للحركة قبل اختيار الأثاث.", script="جرّب تنسيق الخامات بهدوء، وقارن مقاسات الأثاث بمساحة الغرفة قبل الشراء. سيب طريق واضح للحركة وضيف إضاءة جانبية مريحة للمساء. الصور دي عينات اختبار وليست تصميمات حقيقية أو منتجات مطابقة.", hashtags=["#ديكور", "#غرفة_المعيشة"])
    else:
        value = gemini(settings, (
            f"Audience: {settings.get('audience', 'Egypt and the Arab world')}. When writing Arabic, use natural, simple Arabic with light Egyptian phrasing, understandable across the Arab world; avoid stiff translations. English is secondary. "
            f"Write original residential interior design content in {'Arabic' if language == 'ar' else 'English'}. "
            f"Concept: {idea['style']['en']} {idea['room']['en']}, {idea['palette']['en']}, "
            f"{idea['item']['en']}. Teaching point: {idea['format']['tip']}. "
            "Return JSON with title (under 100 characters), description (under 260 characters, "
            "natural search keywords), hashtags (array, maximum 4), script (a practical 35-45 word lesson). "
            "No prices, brand names, product-match claims, unverifiable claims, fake personal experiences, "
            "affiliate links, medical or structural advice. Do not describe it as a real built project."
        ))
    required = ("title", "description", "script")
    if not isinstance(value, dict) or any(not isinstance(value.get(k), str) or not value[k].strip() for k in required):
        raise EngineError("Generated text is missing required fields")
    if len(value["title"]) >= 100 or len(value["description"]) > 260 or not 20 <= len(value["script"].split()) <= 65:
        if not fixture:
            raise EngineError("Generated text exceeded title, description or narration limits")
    if any("http" in value[k].lower() for k in required):
        raise EngineError("Generated text contains an unsolicited link")
    tags = value.get("hashtags", [])
    if not isinstance(tags, list) or any(not isinstance(t, str) or not t.startswith("#") for t in tags):
        raise EngineError("Generated hashtags are malformed")
    value["description"] = f"{DISCLOSURE}\n{value['description']}\n{AI_NOTICE}\n{' '.join(tags[:4])}"
    if len(value["description"]) > 800:
        raise EngineError("Pin description exceeds platform limit")
    return value
