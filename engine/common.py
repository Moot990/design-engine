from __future__ import annotations

import csv
import json
import os
import random
import subprocess
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]


class EngineError(RuntimeError):
    """Safe to display: contains no request bodies, URLs or credentials."""


def config():
    value = yaml.safe_load((ROOT / "config/engine.yaml").read_text(encoding="utf-8"))
    if not 3 <= int(value["pins_per_day"]) <= 10:
        raise EngineError("pins_per_day must be between 3 and 10")
    if not 15 <= int(value["short_seconds"]) <= 30:
        raise EngineError("short_seconds must be between 15 and 30")
    if value["youtube_privacy"] not in {"private", "unlisted", "public"}:
        raise EngineError("Invalid YouTube privacy configuration")
    return value


def secret(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise EngineError(f"Missing GitHub Secret: {name}")
    return value


def request(method, url, *, service, retry_safe=False, **kwargs):
    """Retry reads/idempotent operations only. Never log server bodies or URLs."""
    attempts = 3 if retry_safe else 1
    for attempt in range(attempts):
        response = None
        try:
            response = requests.request(method, url, timeout=(15, 150), **kwargs)
            if 200 <= response.status_code < 300:
                return response
            transient = response.status_code in {408, 429, 500, 502, 503, 504}
            if not transient or attempt == attempts - 1:
                raise EngineError(f"{service}: HTTP {response.status_code}; check access, quota and workflow readiness")
        except requests.RequestException:
            if attempt == attempts - 1:
                raise EngineError(f"{service}: network failure; remote result may be unknown") from None
        delay = min(30, 2 ** (attempt + 1) + random.random())
        if response is not None:
            try:
                delay = max(delay, min(30, float(response.headers.get("Retry-After", 0))))
            except ValueError:
                pass
            response.close()
        time.sleep(delay)
    raise EngineError(f"{service}: retries exhausted")


def response_json(response, service):
    try:
        return response.json()
    except (ValueError, TypeError):
        raise EngineError(f"{service}: invalid JSON response") from None


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Exports may be opened in Excel. Neutralize formula injection.
            writer.writerow({k: "'" + str(v) if str(v).startswith(("=", "+", "-", "@", "\t", "\r")) else v for k, v in row.items()})


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def checkpoint(message):
    """Persist dedup/outbox state BEFORE any irreversible platform request."""
    if os.environ.get("ENGINE_CHECKPOINT_PUSH") != "true":
        return
    for args in (["git", "add", "state", "reports"], ["git", "diff", "--cached", "--quiet"]):
        result = subprocess.run(args, cwd=ROOT, capture_output=True)
        if args[1] == "add" and result.returncode:
            raise EngineError("Could not stage engine state")
    if result.returncode == 0:
        return
    for args in (["git", "commit", "-m", message + " [skip ci]"], ["git", "push", "origin", "HEAD:main"]):
        if subprocess.run(args, cwd=ROOT, capture_output=True).returncode:
            raise EngineError("State checkpoint could not reach main; publishing stopped")
