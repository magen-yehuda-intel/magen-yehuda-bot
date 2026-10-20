"""Shared publication-time and scope gates for live intelligence surfaces.

Retrieval time is not publication time. Malformed or missing source dates fail
closed for scraped news; sensor events may explicitly use their observation time.
"""
import math
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

ME_ANCHORS = re.compile(
    r"\b(?:iran(?:ian)?|israel(?:i)?|tehran|idf|irgc|hezbollah|hamas|houthi\w*|"
    r"gaza|beirut|leban(?:on|ese)|syria\w*|iraq\w*|hormuz|centcom|middle east|"
    r"persian gulf|red sea|yemen\w*|natanz|kharg|south pars)\b|"
    r"איראן|איראני|ישראל|צה[״\"]?ל|חיזבאללה|חמאס|חותי|עזה|לבנון|הורמוז|טהרן",
    re.IGNORECASE,
)


def relevant_news(text):
    return bool(ME_ANCHORS.search(text or ""))


def parse_timestamp(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        ts = float(value)
        if ts > 1e12:
            ts /= 1000
        return ts if math.isfinite(ts) and ts > 0 else None
    except (ValueError, TypeError):
        pass
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if dt.tzinfo is None:
        return None  # Ambiguous local dates must not become live news.
    try:
        return dt.timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def source_timestamp(event, fallback=None):
    # An explicitly supplied but invalid source date must not fall back to now.
    for key in ("published_at", "published", "pubDate", "time", "timestamp", "ts"):
        if event.get(key) not in (None, ""):
            return parse_timestamp(event[key])
    return parse_timestamp(fallback)


def fresh_timestamp(ts, hours=48, now=None):
    now = time.time() if now is None else now
    return ts is not None and 0 <= now - ts <= hours * 3600
