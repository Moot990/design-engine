from __future__ import annotations

import base64
import os
import re
from functools import lru_cache
from pathlib import Path

from .affiliate import validate_affiliate_url
from .common import EngineError, request, response_json, secret


def save_refresh_secret(name, value):
    """Encrypt directly for GitHub Secrets; never serialize a token to disk."""
    from nacl import public
    from nacl.encoding import Base64Encoder

    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise EngineError("Repository context missing for safe token rotation")
    headers = {"Authorization": "Bearer " + secret("REPO_SECRETS_TOKEN"), "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{repository}/actions/secrets"
    key = response_json(request("GET", base + "/public-key", service="GitHub secret public key", retry_safe=True, headers=headers), "GitHub secret key")
    encrypted = public.SealedBox(public.PublicKey(key["key"], Base64Encoder)).encrypt(value.encode())
    request("PUT", base + "/" + name, service="GitHub refresh-secret rotation", retry_safe=True, headers=headers, json={"encrypted_value": base64.b64encode(encrypted).decode(), "key_id": key["key_id"]})
    os.environ[name] = value


@lru_cache(maxsize=1)
def pinterest_bearer():
    refresh = os.environ.get("PINTEREST_REFRESH_TOKEN", "")
    if not refresh:
        return secret("PINTEREST_ACCESS_TOKEN")
    basic = base64.b64encode((secret("PINTEREST_CLIENT_ID") + ":" + secret("PINTEREST_CLIENT_SECRET")).encode()).decode()
    value = response_json(request("POST", "https://api.pinterest.com/v5/oauth/token", service="Pinterest OAuth refresh", headers={"Authorization": "Basic " + basic}, data={"grant_type": "refresh_token", "refresh_token": refresh}), "Pinterest OAuth refresh")
    if not value.get("access_token"):
        raise EngineError("Pinterest OAuth returned no access token")
    if value.get("refresh_token") and value["refresh_token"] != refresh:
        # Persist rotation before proceeding so the next cloud run has the new token.
        save_refresh_secret("PINTEREST_REFRESH_TOKEN", value["refresh_token"])
    return value["access_token"]


def pinterest(image, title, description, link, board_id, program=None):
    if len(title) >= 100 or len(description) > 800 or not validate_affiliate_url(link, program):
        raise EngineError("Pinterest payload validation failed")
    if not re.fullmatch(r"\d+", board_id):
        raise EngineError("Pinterest board ID must be numeric")
    data = {"board_id": board_id, "title": title, "description": description, "link": link,
            "alt_text": "AI-generated residential interior design concept",
            "media_source": {"source_type": "image_base64", "content_type": "image/jpeg", "data": base64.b64encode(Path(image).read_bytes()).decode()}}
    response = request("POST", "https://api.pinterest.com/v5/pins", service="Pinterest publish", headers={"Authorization": "Bearer " + pinterest_bearer()}, json=data)
    value = response_json(response, "Pinterest")
    if not value.get("id"):
        raise EngineError("Pinterest response missing Pin ID; reconcile before retrying")
    return str(value["id"])


def youtube(video, title, description, privacy="private", language="en"):
    token = response_json(request("POST", "https://oauth2.googleapis.com/token", service="YouTube OAuth", retry_safe=True, data={"client_id": secret("YOUTUBE_CLIENT_ID"), "client_secret": secret("YOUTUBE_CLIENT_SECRET"), "refresh_token": secret("YOUTUBE_REFRESH_TOKEN"), "grant_type": "refresh_token"}), "YouTube OAuth")
    if not token.get("access_token"):
        raise EngineError("YouTube OAuth did not return an access token")
    headers = {"Authorization": "Bearer " + token["access_token"]}
    video = Path(video)
    body = {"snippet": {"title": title[:99], "description": description[:4900], "categoryId": "26", "defaultLanguage": language, "tags": ["interior design", "Shorts"]},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
    start = request("POST", "https://www.googleapis.com/upload/youtube/v3/videos", service="YouTube upload session", params={"uploadType": "resumable", "part": "snippet,status"}, headers={**headers, "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(video.stat().st_size)}, json=body)
    location = start.headers.get("Location", "")
    from urllib.parse import urlparse
    if urlparse(location).scheme != "https" or urlparse(location).hostname not in {"www.googleapis.com", "upload.youtube.com"}:
        raise EngineError("Invalid YouTube upload-session destination")
    with video.open("rb") as handle:
        response = request("PUT", location, service="YouTube video upload", headers={**headers, "Content-Type": "video/mp4", "Content-Length": str(video.stat().st_size)}, data=handle)
    value = response_json(response, "YouTube")
    if not value.get("id"):
        raise EngineError("YouTube response missing video ID; reconcile before retrying")
    return str(value["id"]), value.get("status", {}).get("privacyStatus", privacy)
