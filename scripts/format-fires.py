#!/usr/bin/env python3
"""
Format NASA FIRMS fire detection data as Telegram HTML message.
Reads JSON from scan-fires.py output and produces HTML for Telegram.
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

REGION_EMOJI = {
    "iran": "🇮🇷",
    "persian_gulf": "🌊",
    "gulf_of_oman": "🌊",
}

SITE_TYPE_EMOJI = {
    "nuclear": "☢️",
    "military": "🎯",
    "capital": "🏛️",
    "oil": "🛢️",
}


def format_fire_message(data):
    """Format fire data as Telegram HTML."""
    fires = data.get("fires", [])
    if not fires:
        return None  # Nothing to report
    
    now = datetime.now(timezone.utc)
    
    # Header
    lines = [
        "<b>🔥🛰️ SATELLITE FIRE DETECTION — IRAN</b>",
        f"<i>{now.strftime('%H:%M UTC')} | NASA FIRMS (VIIRS+MODIS)</i>",
        "",
    ]
    
    # Summary bar
    s = data["summary"]
    total = data["new_fires"]
    summary_parts = []
    if s["critical"]:
        summary_parts.append(f"🚨 {s['critical']} CRITICAL")
    if s["high"]:
        summary_parts.append(f"🔴 {s['high']} HIGH")
    if s["medium"]:
        summary_parts.append(f"🟡 {s['medium']} MED")
    if s["low"]:
        summary_parts.append(f"⚪ {s['low']} LOW")
    
    lines.append(f"<b>{total} new thermal anomalies</b> | {' · '.join(summary_parts)}")
    lines.append("")
    
    # Critical and high priority fires first, then medium
    # Skip low unless near known sites
    shown = 0
    max_show = 12
    
    for fire in fires:
        if shown >= max_show:
            remaining = len(fires) - shown
            if remaining > 0:
                lines.append(f"\n<i>+ {remaining} more detections</i>")
            break
        
        # Skip low priority unless near a known site
        if fire["priority"] == "low" and not fire["nearby_sites"]:
            continue
        
        emoji = PRIORITY_EMOJI.get(fire["priority"], "")
        region_emoji = REGION_EMOJI.get(fire["region"], "")
        
        # Location string
        city = fire["city"] or "Unknown"
        province = fire["province"]
        loc = f"{city}, {province}" if province else city
        
        frp_str = f"FRP:{fire['frp']}" if fire["frp"] else ""
        time_str = ""
        if fire.get("acq_time"):
            t = str(fire["acq_time"]).zfill(4)
            time_str = f"{t[:2]}:{t[2:]}z"
        
        dn = "🌙" if fire.get("daynight") == "N" else "☀️"
        
        line = f"{emoji} {region_emoji} <b>{loc}</b>"
        meta = " · ".join(filter(None, [frp_str, time_str, dn]))
        if meta:
            line += f" <i>({meta})</i>"
        
        lines.append(line)
        
        # Show nearby known sites
        for site in fire.get("nearby_sites", []):
            site_emoji = SITE_TYPE_EMOJI.get(site["type"], "📍")
            lines.append(f"  {site_emoji} <b>Near {site['name']}</b> ({site['distance_km']}km)")
        
        # Google Maps link
        lines.append(f'  📍 <a href="{fire["google_maps"]}">View on Map</a>')
        lines.append("")
        shown += 1
    
    # Footer
    lines.append(f"<i>Scanning {data['total_detections']} global detections → {data['iran_region_fires']} in region</i>")
    lines.append(f'🗺️ <a href="https://firms.modaps.eosdis.nasa.gov/map/#d:24hrs;c:53.0,32.0;z:6">FIRMS Live Map</a>')
    
    return "\n".join(lines)


def main():
    data = json.load(sys.stdin)
    
    if data.get("seed_mode"):
        print("SEED_MODE: No message generated (baseline established)", file=sys.stderr)
        sys.exit(0)
    
    msg = format_fire_message(data)
    if msg:
        print(msg)
    else:
        print("NO_NEW_FIRES", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
