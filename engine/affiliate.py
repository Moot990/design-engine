from __future__ import annotations

import re
from datetime import date
from urllib.parse import parse_qs, urlencode, urlparse

from .common import EngineError, read_csv

DISCLOSURE = "#ad As an Amazon Associate I earn from qualifying purchases. إعلان: بصفتي شريك أمازون، أكسب من المشتريات المؤهلة."
AI_NOTICE = "AI-generated design concept; similar-item inspiration, not an exact product match. تصور تصميم مولد بالذكاء الاصطناعي؛ المنتجات المقترحة مشابهة وليست مطابقة."


def affiliate_link(idea, tag, products_file, today=None):
    if not re.fullmatch(r"[A-Za-z0-9-]+-21", tag):
        raise EngineError("AMAZON_ASSOCIATE_TAG must be a Saudi tracking tag ending in -21")
    today = today or date.today()
    rows = read_csv(products_file)
    for row in rows:
        if row["active"].lower() != "true" or row["item_id"] != idea["item"]["id"]:
            continue
        if row["style_id"] and row["style_id"] != idea["style"]["id"]:
            continue
        try:
            age = (today - date.fromisoformat(row["reviewed_on"])).days
        except ValueError:
            continue
        if not 0 <= age <= 14:
            continue
        if re.fullmatch(r"[A-Z0-9]{10}", row["asin"]):
            return f"https://www.amazon.sa/dp/{row['asin']}?{urlencode({'tag': tag})}"
        if row["search_query"]:
            return "https://www.amazon.sa/s?" + urlencode({"k": row["search_query"], "tag": tag})
    return "https://www.amazon.sa/s?" + urlencode({"k": idea["item"]["query"], "tag": tag})


def validate_affiliate_url(url):
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.hostname == "www.amazon.sa" and not parsed.username and parsed.port in (None, 443) and bool(parse_qs(parsed.query).get("tag")))
