#!/usr/bin/env python3
"""
Format USGS seismic data as Telegram HTML message.
Reads JSON from scan-seismic.py output.
"""

import sys
import json
from datetime import datetime, timezone

PRIORITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟡",
    "low": "⚪",
}

SITE_TYPE_EMOJI = {
    "nuclear": "☢️",
    "military": "🎯",
    "capital": "🏛️",
    "oil": "🛢️",
}


def format_seismic_message(data):
    quakes = data.get("quakes", [])
    if not quakes:
        return None

    now = datetime.now(timezone.utc)
    lines = [
        "<b>🌍🌍🌍 SEISMIC ACTIVITY — IRAN</b>",
        f"<i>{now.strftime('%H:%M UTC')} | USGS Earthquake Data</i>",
        "",
    ]

    s = data["summary"]
    total = data["new_quakes"]
    parts = []
    if s["critical"]: parts.append(f"🚨 {s['critical']} CRITICAL")
    if s["high"]: parts.append(f"🔴 {s['high']} HIGH")
    if s["medium"]: parts.append(f"🟡 {s['medium']} MED")
    if s["suspicious"]: parts.append(f"⚠️ {s['suspicious']} SUSPICIOUS")

    lines.append(f"<b>{total} new earthquake(s)</b> | {' · '.join(parts)}")
    lines.append("")

    for quake in quakes[:10]:
        emoji = PRIORITY_EMOJI.get(quake["priority"], "")
        mag = quake["mag"]
        depth = quake["depth_km"]
        place = quake["place"]
        time_str = quake.get("time_str", "")
        suspicious = quake.get("suspicious", False)

        line = f"{emoji} <b>M{mag:.1f}</b> — {place}"
        meta = f"Depth: {depth:.0f}km · {time_str}"
        lines.append(line)
        lines.append(f"  <i>{meta}</i>")

        if suspicious:
            lines.append("  ⚠️ <b>SUSPICIOUS:</b> Shallow event — possible explosion/strike")

        for site in quake.get("nearby_sites", []):
            se = SITE_TYPE_EMOJI.get(site["type"], "📍")
            lines.append(f"  {se} <b>Near {site['name']}</b> ({site['distance_km']}km)")

        lines.append(f'  📍 <a href="{quake["google_maps"]}">Map</a>')
        if quake.get("usgs_url"):
            lines.append(f'  📊 <a href="{quake["usgs_url"]}">USGS Details</a>')
        lines.append("")

    lines.append("<i>⚠️ Shallow events (depth &lt;10km) near nuclear sites may indicate underground tests or strikes</i>")

    return "\n".join(lines)


def main():
    data = json.load(sys.stdin)
    if data.get("seed_mode"):
        print("SEED_MODE", file=sys.stderr)
        sys.exit(0)
    msg = format_seismic_message(data)
    if msg:
        print(msg)
    else:
        print("NO_NEW_QUAKES", file=sys.stderr)


if __name__ == "__main__":
    main()
