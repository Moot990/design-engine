"""Optional local FreeVideo agent API. Never starts a server or downloads models."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests

from .common import ROOT, EngineError, save_json

PREFIX = "/freevideo/agent/v1"
PROMPT = (
    "integrated_multimodal_description: [Shot 1] Realistic residential interior. "
    "The supplied image is the first frame. Preserve its furniture, architecture, "
    "materials and lighting. A small, slow camera push forward, no cuts. "
    "No moving furniture, people, new objects, subtitles or on-screen text.\n\n"
    "overall_soundscape: Silence, no speech.\n\nnon_diegetic_music: None."
)


def options(settings):
    value = {"quality": "light", "width": 544, "height": 960, "clip_seconds": 5,
             "max_ai_clips_per_week": 2, "max_minutes_per_run": 12,
             "cooldown_seconds": 30, "max_gpu_temperature_c": 82,
             "publication_cleared": False, **settings.get("freevideo", {})}
    if value["quality"] not in {"light", "medium"} or value["clip_seconds"] != 5:
        raise EngineError("FreeVideo supports Light/Medium and five-second clips in this project")
    for field in ("width", "height"):
        if type(value[field]) is not int or not 256 <= value[field] <= 1344 or value[field] % 32:
            raise EngineError("FreeVideo dimensions must be 256-1344 and multiples of 32")
    for field, low, high in (("max_ai_clips_per_week", 0, 10), ("max_minutes_per_run", 1, 60), ("cooldown_seconds", 0, 600), ("max_gpu_temperature_c", 60, 87)):
        if type(value[field]) is not int or not low <= value[field] <= high:
            raise EngineError("Invalid FreeVideo safety limit: " + field)
    return value


class Client:
    def __init__(self, deadline):
        self.deadline = deadline
        self.origin = os.environ.get("FREEVIDEO_URL", "http://127.0.0.1:8188").rstrip("/")
        parsed = urlsplit(self.origin)
        try:
            local = parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback
        except (ValueError, TypeError):
            local = False
        if not local or parsed.scheme != "http" or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            raise EngineError("FreeVideo must use a loopback HTTP origin; do not expose a laptop agent on the internet")
        token = os.environ.get("FREEVIDEO_AGENT_TOKEN", "").strip()
        if not token:
            home = Path(os.environ.get("FREEVIDEO_HOME", str(Path.home() / "FreeVideo" / "FreeVideo-engine")))
            try:
                token = (home / "agent" / "token").read_text(encoding="ascii").strip()
            except OSError:
                raise EngineError("FreeVideo local agent token unavailable; start the installed app") from None
        if not token:
            raise EngineError("FreeVideo local agent token is empty")
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"Authorization": "Bearer " + token, "X-FreeVideo-Client": "design-engine"})

    def call(self, method, path, body=None, *, binary=False, cleanup=False):
        if not path.startswith(PREFIX + "/") and path != PREFIX:
            raise EngineError("Unexpected FreeVideo API path")
        if ".." in path or "\\" in path:
            raise EngineError("Invalid FreeVideo API path")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 and not cleanup:
            raise EngineError("FreeVideo time budget exhausted")
        timeout = max(.1, min(10, remaining)) if not cleanup else 5
        # Idempotent reads can retry within the same deadline. Job submissions use
        # a durable ref, but ambiguous submissions still stop instead of duplicating.
        for attempt in range(2 if method == "GET" else 1):
            try:
                response = self.session.request(method, self.origin + path, json=body, timeout=timeout, allow_redirects=False)
                if not 200 <= response.status_code < 300:
                    raise EngineError(f"FreeVideo HTTP {response.status_code}; use ffmpeg fallback")
                if binary:
                    if len(response.content) > 80_000_000:
                        raise EngineError("FreeVideo output exceeds download budget")
                    return response.content
                return response.json()
            except (requests.RequestException, ValueError):
                if attempt == 0 and method == "GET" and time.monotonic() + 1 < self.deadline:
                    time.sleep(.5)
                    continue
                raise EngineError("FreeVideo connection/response failed; remote job may need reconciliation") from None

    def cancel(self, job_id):
        try:
            self.call("POST", PREFIX + "/jobs/" + job_id + "/cancel", {}, cleanup=True)
            return True
        except EngineError:
            return False


def gpu_sample():
    executable = shutil.which("nvidia-smi")
    if not executable and os.name == "nt":
        candidate = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/nvidia-smi.exe"
        executable = str(candidate) if candidate.is_file() else None
    if not executable:
        return None
    try:
        value = subprocess.run([executable, "--query-gpu=temperature.gpu,power.draw,clocks_event_reasons.hw_thermal_slowdown,clocks_event_reasons.sw_thermal_slowdown", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4)
        row = value.stdout.strip().splitlines()[0].split(",")
        return {"temperature_c": float(row[0]), "power_w": float(row[1]), "hardware_thermal_slowdown": row[2].strip(), "software_thermal_slowdown": row[3].strip()}
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return None


@contextmanager
def budget_lock(path):
    lock = path.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise EngineError("Another FreeVideo run or unreconciled lock exists; using ffmpeg") from None
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def animate_selected(images, settings, directory, *, publishing=False, budget_path=None):
    """Return {image_index: clip_path}, warnings. Any AI failure falls back as a batch."""
    warnings, clips = [], {}
    if settings.get("video_backend", "ffmpeg") != "freevideo":
        return clips, warnings
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    report = {"backend": "freevideo", "status": "fallback", "attempts": [], "warnings": warnings}
    started, client, job_id = time.monotonic(), None, None
    state_path = Path(budget_path) if budget_path else ROOT / ".local/freevideo-budget.json"
    try:
        limits = options(settings)
        report.update(quality=limits["quality"], publication_cleared=limits["publication_cleared"] is True)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise EngineError("Local FreeVideo is unavailable to standard GitHub-hosted runners")
        if publishing and limits["publication_cleared"] is not True:
            raise EngineError("Worldwide FreeVideo output rights are not cleared; publishing uses ffmpeg")
        deadline = started + limits["max_minutes_per_run"] * 60
        client = Client(deadline)
        status = client.call("GET", PREFIX)
        if not status.get("ready") or not status.get("features", {}).get("generate.first_frame"):
            raise EngineError("Installed FreeVideo is not ready for image-to-video")
        queue = status.get("queue", {})
        if any(queue.get(key, 0) for key in ("running", "pending", "agent_active")):
            raise EngineError("FreeVideo queue is busy; using ffmpeg without interrupting another job")
        with budget_lock(state_path):
            history = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"weeks": {}, "attempts": []}
            calendar = datetime.now(ZoneInfo(settings.get("timezone", "Africa/Cairo"))).isocalendar()
            week = f"{calendar.year}-W{calendar.week:02}"
            available = max(0, limits["max_ai_clips_per_week"] - history["weeks"].get(week, 0))
            if not available:
                raise EngineError("FreeVideo weekly AI clip allowance exhausted")
            for index, image in enumerate(images[:available]):
                if index:
                    pause = limits["cooldown_seconds"]
                    if time.monotonic() + pause + 1 >= deadline:
                        raise EngineError("FreeVideo run budget cannot fit the cooldown")
                    time.sleep(pause)
                sample = gpu_sample()
                if sample and sample["temperature_c"] >= limits["max_gpu_temperature_c"]:
                    raise EngineError("FreeVideo GPU temperature limit reached")
                data = Path(image).read_bytes()
                if len(data) > 15_000_000:
                    raise EngineError("FreeVideo first-frame image is too large")
                ref = "design-" + hashlib.sha256(data + json.dumps(limits, sort_keys=True).encode() + PROMPT.encode()).hexdigest()[:40]
                if any(a.get("ref") == ref for a in history["attempts"]):
                    raise EngineError("Image already attempted in FreeVideo; no duplicate AI generation")
                attempt = {"ref": ref, "week": week, "status": "reserved", "samples": []}
                history["weeks"][week] = history["weeks"].get(week, 0) + 1
                history["attempts"].append(attempt)
                save_json(state_path, history)  # Charge attempts, including failures, before submitting.
                report["attempts"].append(attempt)
                upload = client.call("POST", PREFIX + "/media", {"name": "first-frame.jpg", "data_base64": base64.b64encode(data).decode()})
                spec = {"prompt": PROMPT, "media": {"first": {"file": upload["file"]}}, "width": limits["width"], "height": limits["height"], "seconds": 5, "quality": limits["quality"], "seed": int(ref[-8:], 16), "ref": ref}
                client.call("POST", PREFIX + "/plan", spec)
                job = client.call("POST", PREFIX + "/jobs", spec)["job"]
                job_id = job["id"]
                attempt.update(job_id=job_id, status="submitted")
                save_json(state_path, history)
                while True:
                    if time.monotonic() >= deadline:
                        raise EngineError("FreeVideo run time limit reached; cancellation requested")
                    sample = gpu_sample()
                    if sample:
                        attempt["samples"].append({"elapsed_seconds": round(time.monotonic() - started, 1), **sample})
                        if sample["temperature_c"] >= limits["max_gpu_temperature_c"]:
                            raise EngineError("FreeVideo GPU temperature limit reached; cancellation requested")
                    job = client.call("GET", PREFIX + "/jobs/" + job_id)
                    if job["status"] in {"failed", "cancelled", "interrupted"}:
                        raise EngineError("FreeVideo generation did not complete")
                    if job["status"] == "succeeded":
                        output = directory / f"ai-{index}.mp4"
                        output.write_bytes(client.call("GET", job["result"]["video"]["url"], binary=True))
                        from .media import probe
                        info = probe(output)
                        if float(info["format"]["duration"]) < 4.9:
                            raise EngineError("FreeVideo returned a clip shorter than five seconds")
                        clips[index] = output
                        attempt["status"] = "succeeded"
                        save_json(state_path, history)
                        job_id = None
                        break
                    time.sleep(min(2, max(.01, deadline - time.monotonic())))
            report["status"] = "complete"
    except Exception as error:
        if client and job_id:
            report["cancellation_requested"] = client.cancel(job_id) is True
        warnings.append(str(error) if isinstance(error, EngineError) else "FreeVideo failed: " + type(error).__name__)
        clips = {}  # Keep failed/partial AI assets local but assemble a full ffmpeg fallback.
    finally:
        if client:
            client.session.close()
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        report["used_ai_clips"] = len(clips)
        save_json(directory / "freevideo-result.json", report)
    return clips, warnings
