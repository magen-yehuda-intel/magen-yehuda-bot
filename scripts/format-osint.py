#!/usr/bin/env python3
"""
Format OSINT alerts for bilingual output.
Reads JSON array of alerts from stdin, outputs JSON with text_he and text_en.

Usage:
    echo '[...]' | python3 format-osint.py
    
Output:
    {"text_he": "...", "text_en": "...", "count": N, "summary": "..."}
"""

import json
import sys
import html as h

# Source labels
SOURCE_EN = {"telegram": "📢", "twitter": "🐦", "rss": "📰", "seismic": "🌍"}
SOURCE_HE = {
    "telegram": "📢 ערוץ טלגרם",
    "twitter": "🐦 טוויטר",
    "rss": "📰 עדכון",
    "seismic": "🌍 רעידה",
}

# Source name translations (well-known channels)
CHANNEL_HE = {
    "warmonitors": "מוניטור מלחמה",
    "Times of Israel": "טיימס אוף ישראל",
    "Jerusalem Post": "ג׳רוזלם פוסט",
    "Al Jazeera": "אל ג׳זירה",
    "Haaretz": "הארץ",
    "Reuters": "רויטרס",
    "AP News": "AP",
    "BBC": "BBC",
    "Ynet": "Ynet",
    "TASS": "TASS",
}


def format_alert_en(a, emoji_map):
    """Format a single alert in English."""
    src = a.get("source", "?")
    ch = h.escape(a.get("channel", "?"))
    text = h.escape(a["text"][:150])
    link = a.get("link", "")
    link_tag = f' <a href="{link}">[↗]</a>' if link else ""
    
    if src == "twitter" and a.get("is_rt"):
        icon = "🔁"
    else:
        icon = emoji_map.get(src, "📡")
    
    return f"{icon} <b>{ch}</b>: {text}{link_tag}"


def format_alert_he(a, emoji_map):
    """Format a single alert in Hebrew."""
    src = a.get("source", "?")
    ch_raw = a.get("channel", "?")
    ch_he = CHANNEL_HE.get(ch_raw, ch_raw)
    ch = h.escape(ch_he)
    text = h.escape(a["text"][:150])
    link = a.get("link", "")
    link_tag = f' <a href="{link}">[↗]</a>' if link else ""
    
    if src == "twitter" and a.get("is_rt"):
        icon = "🔁"
    else:
        icon = SOURCE_EN.get(src, "📡")  # keep emoji icons universal
    
    return f"{icon} <b>{ch}</b>: {text}{link_tag}"


def main():
    raw = sys.stdin.read()
    all_alerts = json.loads(raw)
    alerts = [a for a in all_alerts if a.get("source") != "seismic"]
    
    if not alerts:
        print(json.dumps({"text_he": "", "text_en": "", "count": 0, "summary": ""}))
        return
    
    import re
    HE_CHARS = re.compile(r'[\u0590-\u05FF]')
    HEBREW_CHANNELS = {
        'ynet', 'מעריב', 'maariv', 'וואלה', 'walla', 'חדשות 13', '13news',
        'kann_news', 'aharonyediot', 'flash_news_il', 'idfofficial', 'idfonline',
        'AbuAliExpress', 'IDFarabic',
    }
    
    def is_hebrew_alert(a):
        ch = (a.get('channel', '') or '').lower()
        return any(hs in ch for hs in HEBREW_CHANNELS) or bool(HE_CHARS.search(a.get('text', '')))
    
    by_source = {}
    for a in alerts:
        by_source.setdefault(a.get("source", "?"), []).append(a)
    
    lines_en = []
    lines_he = []
    
    # For Hebrew: prioritize Hebrew-language alerts, then fill with English
    he_alerts = [a for a in alerts if is_hebrew_alert(a)]
    en_alerts = [a for a in alerts if not is_hebrew_alert(a)]
    
    # Hebrew channel: Hebrew first, then English to fill up to 12
    for a in he_alerts[:10]:
        lines_he.append(format_alert_he(a, SOURCE_EN))
    if len(lines_he) < 12:
        for a in en_alerts[:12 - len(lines_he)]:
            lines_he.append(format_alert_he(a, SOURCE_EN))
    
    # English channel: English first, then Hebrew to fill up to 12
    for a in en_alerts[:10]:
        lines_en.append(format_alert_en(a, SOURCE_EN))
    if len(lines_en) < 12:
        for a in he_alerts[:12 - len(lines_en)]:
            lines_en.append(format_alert_en(a, SOURCE_EN))
    
    # Cap at 12
    text_en = "\n".join(lines_en[:12])
    text_he = "\n".join(lines_he[:12])
    
    if len(alerts) > 12:
        text_en += f"\n... +{len(alerts)-12} more updates"
        text_he += f"\n... +{len(alerts)-12} עדכונים נוספים"
    
    # Summary
    summary_parts = []
    for src, items in by_source.items():
        summary_parts.append(f"{SOURCE_EN.get(src, '?')} {len(items)} {src}")
    summary = " | ".join(summary_parts)
    
    result = {
        "text_he": text_he,
        "text_en": text_en,
        "count": len(alerts),
        "summary": summary,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
