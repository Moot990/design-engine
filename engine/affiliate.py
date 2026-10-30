from __future__ import annotations

import os
import re
from datetime import date
from urllib.parse import parse_qs, urlencode, urlparse

from .common import EngineError, read_csv

DISCLOSURE = "إعلان #ad: قد أكسب عمولة من الروابط. بصفتي شريك أمازون، أكسب من المشتريات المؤهلة. As an Amazon Associate I earn from qualifying purchases."
AI_NOTICE = "صور وفيديو بالذكاء الاصطناعي لتوضيح أفكار التصميم؛ المنتجات المقترحة مشابهة وليست مطابقة. AI-generated design imagery/video; similar items, not exact matches."

# Explicit markets only: never accept an arbitrary hostname from configuration.
PROGRAMS = {"amazon.eg", "amazon.com", "amazon.ae"}


def affiliate_program(program=None):
    value = (os.environ.get("AFFILIATE_PROGRAM", "").strip() or program or "amazon.eg").lower()
    if value not in PROGRAMS:
        raise EngineError("Unsupported AFFILIATE_PROGRAM; use amazon.eg, amazon.com or amazon.ae")
    return value


def _amazon_url(url, program):
    try:
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname in {program, "www." + program} and not parsed.username and not parsed.password and parsed.port in (None, 443):
            return parsed
    except ValueError:
        pass
    return None


def affiliate_link(idea, tag, products_file, today=None, program=None):
    program = affiliate_program(program)
    base = "https://www." + program
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}", tag):
        raise EngineError("AMAZON_ASSOCIATE_TAG must be the tracking ID from your selected Associates account")
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
        product_url = row.get("product_url", "").strip()
        if product_url:
            parsed = _amazon_url(product_url, program)
            match = re.fullmatch(r"/(?:dp|gp/product)/([A-Z0-9]{10})/?", parsed.path) if parsed else None
            if not match:
                raise EngineError("Active product_url must be a canonical HTTPS product link for AFFILIATE_PROGRAM")
            return f"{base}/dp/{match[1]}?{urlencode({'tag': tag})}"
        if re.fullmatch(r"[A-Z0-9]{10}", row.get("asin", "")):
            return f"{base}/dp/{row['asin']}?{urlencode({'tag': tag})}"
        if row.get("search_query"):
            return base + "/s?" + urlencode({"k": row["search_query"], "tag": tag})
    return base + "/s?" + urlencode({"k": idea["item"]["query"], "tag": tag})


def validate_affiliate_url(url, program=None):
    parsed = _amazon_url(url, affiliate_program(program))
    if not parsed:
        return False
    query = parse_qs(parsed.query)
    tags = query.get("tag", [])
    path_ok = bool(re.fullmatch(r"/dp/[A-Z0-9]{10}", parsed.path)) or (parsed.path == "/s" and bool(query.get("k")))
    return path_ok and len(tags) == 1 and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}", tags[0]))
