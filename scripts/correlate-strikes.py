#!/usr/bin/env python3
"""
Strike Correlation Engine.
Correlates fire + seismic events at the same location within a time window.
If fire + earthquake happen within 30km and 30min → probable strike.

Usage:
    python3 correlate-strikes.py <state_dir>
"""

import sys
import os
import json
import time
import math
from datetime import datetime, timezone, timedelta

CORRELATION_DISTANCE_KM = 50  # Max distance between fire + quake
CORRELATION_TIME_SEC = 1800   # 30 minutes
MIN_FRP_FOR_STRIKE = 20       # Minimum fire radiative power

# Known military/nuclear sites
KNOWN_SITES = [
    {"name": "Natanz (Nuclear)", "lat": 33.72, "lon": 51.72, "type": "nuclear"},
    {"name": "Fordow (Nuclear)", "lat": 34.88, "lon": 51.59, "type": "nuclear"},
    {"name": "Isfahan (Nuclear)", "lat": 32.65, "lon": 51.68, "type": "nuclear"},
    {"name": "Bushehr (Nuclear)", "lat": 28.83, "lon": 50.89, "type": "nuclear"},
    {"name": "Arak (Heavy Water)", "lat": 34.38, "lon": 49.24, "type": "nuclear"},
    {"name": "Parchin (Military)", "lat": 35.52, "lon": 51.77, "type": "military"},
    {"name": "Tehran", "lat": 35.69, "lon": 51.39, "type": "capital"},
    {"name": "Bandar Abbas", "lat": 27.19, "lon": 56.27, "type": "military"},
    {"name": "Kharg Island (Oil)", "lat": 29.23, "lon": 50.31, "type": "oil"},
    {"name": "Shahrud Missile Base", "lat": 36.42, "lon": 55.00, "type": "military"},
    {"name": "Tabriz", "lat": 38.08, "lon": 46.29, "type": "military"},
    {"name": "Shiraz Air Base", "lat": 29.54, "lon": 52.59, "type": "military"},
]


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_site(lat, lon, threshold_km=80):
    best = None
    best_dist = threshold_km + 1
    for site in KNOWN_SITES:
        d = haversine_km(lat, lon, site["lat"], site["lon"])
        if d < best_dist:
            best_dist = d
            best = site
    if best and best_dist <= threshold_km:
        return {**best, "distance_km": round(best_dist, 1)}
    return None


def load_recent_events(state_dir, hours=2):
    """Load recent fire and seismic events from intel log."""
    fires = []
    quakes = []
    cutoff = time.time() - (hours * 3600)
    
    # From intel log
    log_path = os.path.join(state_dir, "intel-log.jsonl")
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                try:
                    ev = json.loads(line.strip())
                    if ev.get("logged_at", 0) < cutoff:
                        continue
                    if ev.get("type") == "fires" and ev.get("data", {}).get("fires"):
                        for fire in ev["data"]["fires"]:
                            fire["_event_time"] = ev.get("logged_at", 0)
                            fires.append(fire)
                    if ev.get("type") == "seismic" and ev.get("data", {}).get("quakes"):
                        for quake in ev["data"]["quakes"]:
                            quake["_event_time"] = quake.get("time_epoch", ev.get("logged_at", 0))
                            quakes.append(quake)
                except:
                    continue
    
    # Also check current state files for recent data
    try:
        with open(os.path.join(state_dir, "firms-seen.json")) as f:
            seen = json.load(f).get("seen", {})
        for key, data in seen.items():
            if data.get("ts", 0) >= cutoff:
                # Key format: "lat_lon_date" — parse coords from key
                parts = key.split("_")
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                except (ValueError, IndexError):
                    continue
                if lat == 0 and lon == 0:
                    continue
                fires.append({
                    "lat": lat,
                    "lon": lon,
                    "frp": data.get("frp", 10),
                    "_event_time": data.get("ts", 0),
                    "priority": data.get("priority", "medium"),
                })
    except:
        pass
    
    try:
        with open(os.path.join(state_dir, "seismic-seen.json")) as f:
            seen = json.load(f).get("seen", {})
        for key, data in seen.items():
            if data.get("ts", 0) >= cutoff:
                quakes.append({
                    "lat": data.get("lat", 0),
                    "lon": data.get("lon", 0),
                    "mag": data.get("mag", 0),
                    "depth_km": data.get("depth_km", 0),
                    "_event_time": data.get("ts", 0),
                })
    except:
        pass
    
    return fires, quakes


def correlate(fires, quakes):
    """Find fire-quake pairs that might be strikes."""
    correlations = []
    used_fires = set()
    used_quakes = set()
    
    for qi, quake in enumerate(quakes):
        qlat = quake.get("lat", 0)
        qlon = quake.get("lon", 0)
        qtime = quake.get("_event_time", 0)
        qmag = quake.get("mag", 0)
        
        for fi, fire in enumerate(fires):
            flat = fire.get("lat", 0)
            flon = fire.get("lon", 0)
            ftime = fire.get("_event_time", 0)
            frp = fire.get("frp", 0)
            
            # Distance check
            dist = haversine_km(qlat, qlon, flat, flon)
            if dist > CORRELATION_DISTANCE_KM:
                continue
            
            # Time check
            time_diff = abs(qtime - ftime)
            if time_diff > CORRELATION_TIME_SEC:
                continue
            
            # Found correlation!
            confidence = 0.5  # Base
            
            # Closer = higher confidence
            if dist < 10:
                confidence += 0.2
            elif dist < 25:
                confidence += 0.1
            
            # Higher FRP = more likely bombing
            if frp >= 50:
                confidence += 0.15
            elif frp >= 20:
                confidence += 0.1
            
            # Shallow quake = more likely explosion
            depth = quake.get("depth_km", 99)
            if depth < 5:
                confidence += 0.15
            elif depth < 10:
                confidence += 0.1
            
            # Near known site = more significant
            site = nearest_site((qlat + flat) / 2, (qlon + flon) / 2)
            if site:
                confidence += 0.1
                if site["type"] == "nuclear":
                    confidence += 0.1
            
            confidence = min(confidence, 0.99)
            
            # Midpoint
            mid_lat = (qlat + flat) / 2
            mid_lon = (qlon + flon) / 2
            
            correlations.append({
                "confidence": round(confidence, 2),
                "distance_km": round(dist, 1),
                "time_diff_sec": int(time_diff),
                "time_diff_min": round(time_diff / 60, 1),
                "location": {"lat": mid_lat, "lon": mid_lon},
                "fire": {
                    "lat": flat, "lon": flon,
                    "frp": frp,
                    "priority": fire.get("priority", "?"),
                },
                "quake": {
                    "lat": qlat, "lon": qlon,
                    "mag": qmag,
                    "depth_km": depth,
                },
                "nearest_site": site,
                "google_maps": f"https://maps.google.com/maps?q={mid_lat},{mid_lon}&z=10",
            })
    
    # Sort by confidence descending
    correlations.sort(key=lambda c: c["confidence"], reverse=True)
    return correlations


def format_telegram(correlations):
    """Format correlations as Telegram HTML alert."""
    if not correlations:
        return None
    
    lines = [
        "🎯🎯🎯 <b>STRIKE CORRELATION DETECTED</b> 🎯🎯🎯",
        "",
        f"<i>Fire + Seismic events correlated — possible military strike</i>",
        "",
    ]
    
    for i, c in enumerate(correlations[:5]):
        conf_bar = "█" * int(c["confidence"] * 10) + "░" * (10 - int(c["confidence"] * 10))
        conf_pct = int(c["confidence"] * 100)
        
        lines.append(f"🎯 <b>Correlation #{i+1}</b> — {conf_pct}% confidence")
        lines.append(f"  <code>[{conf_bar}]</code>")
        lines.append(f"  🔥 Fire: FRP {c['fire']['frp']} MW ({c['fire']['priority']})")
        lines.append(f"  🌍 Quake: M{c['quake']['mag']} depth {c['quake']['depth_km']}km")
        lines.append(f"  📏 Distance: {c['distance_km']}km apart | ⏱️ {c['time_diff_min']}min apart")
        
        if c.get("nearest_site"):
            site = c["nearest_site"]
            type_emoji = {"nuclear": "☢️", "military": "🎯", "capital": "🏛️", "oil": "🛢️"}.get(site["type"], "📍")
            lines.append(f"  {type_emoji} <b>Near {site['name']}</b> ({site['distance_km']}km)")
        
        lines.append(f'  📍 <a href="{c["google_maps"]}">View on Map</a>')
        lines.append("")
    
    lines.append("⚠️ <i>Combined fire + seismic signature suggests kinetic strike. Natural coincidence is possible but rare at close range.</i>")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 correlate-strikes.py <state_dir>", file=sys.stderr)
        sys.exit(1)
    
    state_dir = sys.argv[1]
    
    fires, quakes = load_recent_events(state_dir)
    print(f"  Strike correlator: {len(fires)} fires, {len(quakes)} quakes in window", file=sys.stderr)
    
    correlations = correlate(fires, quakes)
    
    # Save state
    state_file = os.path.join(state_dir, "strike-correlations.json")
    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "fires_checked": len(fires),
        "quakes_checked": len(quakes),
        "correlations": correlations,
        "count": len(correlations),
    }
    with open(state_file, "w") as f:
        json.dump(result, f, indent=2)
    
    if correlations:
        print(f"  🎯 {len(correlations)} STRIKE CORRELATION(S) FOUND", file=sys.stderr)
        msg = format_telegram(correlations)
        if msg:
            result["telegram_message"] = msg
    else:
        print(f"  ✓ No strike correlations", file=sys.stderr)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
