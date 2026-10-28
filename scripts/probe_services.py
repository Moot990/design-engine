"""Non-secret cloud probes. This does NOT claim publishing or real generation works."""
import asyncio
import json
from pathlib import Path

from engine.common import EngineError, request, response_json, save_json
from engine.media import _voice, probe

results = {"pollinations_no_key": "not tested", "edge_tts": "not tested", "gemini": "not tested: requires your free-tier key", "pinterest": "not tested: requires your approved app/token", "youtube": "not tested: requires your channel OAuth", "amazon_attribution": "not tested: requires your Associates account"}
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
except EngineError as error:
    results["edge_tts"] = str(error)
save_json("output/service-probes.json", results)
print(json.dumps(results, indent=2))
