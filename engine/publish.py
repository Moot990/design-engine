from __future__ import annotations

import base64
import re
from pathlib import Path

from .affiliate import validate_affiliate_url
from .common import EngineError, request, response_json, secret


def pinterest(image, title, description, link, board_id):
    if len(title) >= 100 or len(description) > 800 or not validate_affiliate_url(link):
        raise EngineError("Pinterest payload validation failed")
    if not re.fullmatch(r"\d+", board_id):
        raise EngineError("Pinterest board ID must be numeric")
    data = {"board_id": board_id, "title": title, "description": description, "link": link,
            "alt_text": "AI-generated residential interior design concept",
            "media_source": {"source_type": "image_base64", "content_type": "image/jpeg", "data": base64.b64encode(Path(image).read_bytes()).decode()}}
    response = request("POST", "https://api.pinterest.com/v5/pins", service="Pinterest publish", headers={"Authorization": "Bearer " + secret("PINTEREST_ACCESS_TOKEN")}, json=data)
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
