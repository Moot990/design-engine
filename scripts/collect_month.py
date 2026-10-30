"""Fetch only bounded, genuine daily image archives for the previous Egypt month."""
import io
import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.common import EngineError, request, response_json, secret


def main():
    month = (datetime.now(ZoneInfo("Africa/Cairo")).date().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    repository = os.environ["GITHUB_REPOSITORY"]
    headers = {"Authorization": "Bearer " + secret("GITHUB_TOKEN"), "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{repository}/actions/artifacts"
    selected = {}
    for page in range(1, 11):
        batch = response_json(request("GET", base, service="Monthly artifact list", retry_safe=True, headers=headers, params={"per_page": 100, "page": page}), "GitHub artifacts")["artifacts"]
        for artifact in batch:
            if artifact["expired"] or not re.fullmatch(r"image-archive-" + re.escape(month) + r"-\d{2}", artifact["name"]):
                continue
            selected.setdefault(artifact["name"], artifact)  # API returns newest first.
        if len(batch) < 100:
            break
    if not selected:
        raise EngineError("No real image archives from the previous month; generate reviewed images first")
    target = Path("output/monthly-sources").resolve()
    target.mkdir(parents=True, exist_ok=True)
    total = 0
    for artifact in selected.values():
        if artifact["size_in_bytes"] > 8_000_000:
            raise EngineError("Image archive exceeds its storage budget")
        response = request("GET", base + f"/{artifact['id']}/zip", service="Monthly archive download", retry_safe=True, headers=headers)
        if len(response.content) > 10_000_000:
            raise EngineError("Downloaded archive exceeds its size budget")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                total += info.file_size
                output = (target / artifact["name"] / info.filename).resolve()
                if not output.is_relative_to(target) or info.file_size > 8_000_000 or total > 240_000_000 or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    raise EngineError("Unsafe or oversized monthly archive member")
                if output.suffix not in {".jpg", ".json"}:
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(archive.read(info))
    print(f"Collected {len(selected)} daily source archives for {month}")


if __name__ == "__main__":
    try:
        main()
    except EngineError as error:
        print("BLOCKED: " + str(error))
        raise SystemExit(2)
    except Exception as error:
        print("FAILED: " + type(error).__name__)
        raise SystemExit(1)
