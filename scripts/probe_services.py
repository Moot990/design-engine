"""Non-secret cloud probes. This does NOT claim publishing or real generation works."""
import asyncio
import json
from pathlib import Path

from engine.common import EngineError, config, request, response_json, save_json
from engine.media import _voice, probe, render_short

results = {"pollinations_no_key": "not tested", "edge_tts": "not tested", "gemini": "not tested: requires your free-tier key", "pinterest": "not tested: requires your approved app/token", "youtube": "not tested: requires your channel OAuth", "amazon_attribution": "not tested: requires your Associates account"}
try:
    models = response_json(request("GET", "https://gen.pollinations.ai/image/models", service="Pollinations public catalog", retry_safe=True), "Pollinations public catalog")
    model = next((m for m in models if m.get("name") == config()["image_model"] or config()["image_model"] in m.get("aliases", [])), {})
    results["image_model_catalog"] = {key: model.get(key) for key in ("name", "paid_only", "flat_rate", "pricing")}
except EngineError as error:
    results["image_model_catalog"] = str(error)
try:
    request("GET", "https://gen.pollinations.ai/image/a%20minimal%20living%20room", service="Pollinations no-key probe", params={"width": 1000, "height": 1500})
    results["pollinations_no_key"] = "returned a response; terms still require a key; engine does not rely on no-key access"
except EngineError as error:
    results["pollinations_no_key"] = str(error)
try:
    target = Path("output/qa/tts-probe.mp3")
    target.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_voice("Compare texture and light before choosing furniture.", "en-US-AriaNeural", target))
    results["edge_tts"] = {"status": "live synthesis succeeded", "seconds": float(probe(target)["format"]["duration"])}
    sources = sorted(Path("output/smoke/image-archive").glob("*.jpg"))[:4]
    copy = {"hook": "TEST - Four details to check", "captions": ["Check the room proportions.", "Balance smooth and woven textures.", "Layer soft light.", "Leave a clear walking route."], "script": "Check the room proportions before choosing a sofa. Balance smooth and woven textures. Layer soft light instead of relying on one ceiling light. Finally, leave a clear walking route around the main seating area."}
    video, warnings = render_short(sources, copy, config(), "en", "output/voiced-test", fixture=False)
    results["narrated_fixture_short"] = {"has_audio": any(s["codec_type"] == "audio" for s in probe(video)["streams"]), "warnings": warnings}
    arabic = Path("output/qa/tts-probe-ar.mp3")
    asyncio.run(_voice("اختبر توازن الخامات والإضاءة قبل اختيار أثاث غرفة المعيشة.", "ar-EG-SalmaNeural", arabic))
    results["arabic_edge_tts"] = {"status": "live synthesis succeeded", "seconds": float(probe(arabic)["format"]["duration"])}
    arabic_copy = json.loads(Path("output/smoke/short-copy.json").read_text(encoding="utf-8"))
    video_ar, warnings_ar = render_short(sources, arabic_copy, config(), "ar", "output/voiced-ar-test", fixture=False)
    results["arabic_narrated_fixture_short"] = {"has_audio": any(s["codec_type"] == "audio" for s in probe(video_ar)["streams"]), "warnings": warnings_ar, "voice": config()["voices"]["ar"][0]}

except EngineError as error:
    results["edge_tts"] = str(error)
save_json("output/service-probes.json", results)
print(json.dumps(results, indent=2))
