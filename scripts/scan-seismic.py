#!/usr/bin/env python3
"""
USGS Earthquake/Seismic scanner for Iran region.
Fetches recent earthquakes, filters to Iran, tracks state for new-only alerts.
Outputs JSON compatible with the fire map generator.

Usage:
    python3 scan-seismic.py <config.json> <state_dir> [--seed] [--days 2] [--min-mag 2.5]
"""

import sys
import os
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

IRAN_BBOX = {"west": 44, "south": 25, "east": 63.5, "north": 40}

# Known sites for proximity flagging (same as fires)
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
]


def haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def check_proximity(lat, lon, threshold_km=30):
    nearby = []
    for site in KNOWN_SITES:
        dist = haversine_km(lat, lon, site["lat"], site["lon"])
        if dist <= threshold_km:
            nearby.append({**site, "distance_km": round(dist, 1)})
    nearby.sort(key=lambda x: x["distance_km"])
    return nearby


def classify_quake(mag, depth, event_type, nearby):
    """Classify quake priority."""
    priority = "low"
    suspicious = False
    
    # Shallow + high magnitude near known sites = very suspicious
    if mag >= 5.0:
        priority = "high"
    elif mag >= 4.0:
        priority = "medium"
    elif mag >= 3.0:
        priority = "low"
    
    # Explosion type = always critical
    if event_type and event_type.lower() in ("explosion", "nuclear explosion", "mining explosion"):
        priority = "critical"
        suspicious = True
    
    # Shallow + moderate near nuclear = suspicious (could be underground test/strike)
    if depth < 10 and mag >= 3.5:
        suspicious = True
        if nearby:
            for site in nearby:
                if site["type"] == "nuclear" and site["distance_km"] < 50:
                    priority = "critical"
                    break
    
    # Near nuclear site bumps priority
    if nearby and priority in ("low", "medium"):
        for site in nearby:
            if site["type"] == "nuclear":
                priority = "high"
                break
    
    return priority, suspicious


def fetch_usgs(config, days=2, min_mag=2.5):
    """Fetch earthquakes from USGS."""
    seismic_cfg = config.get("usgs_seismic", {})
    if not seismic_cfg.get("enabled", True):
        return []
    
    min_lat = seismic_cfg.get("min_latitude", IRAN_BBOX["south"])
    max_lat = seismic_cfg.get("max_latitude", IRAN_BBOX["north"])
    min_lon = seismic_cfg.get("min_longitude", IRAN_BBOX["west"])
    max_lon = seismic_cfg.get("max_longitude", IRAN_BBOX["east"])
    min_mag = seismic_cfg.get("min_magnitude", min_mag)
    
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    
    url = (f"https://earthquake.usgs.gov/fdsnws/event/1/query?"
           f"format=geojson&minlatitude={min_lat}&maxlatitude={max_lat}"
           f"&minlongitude={min_lon}&maxlongitude={max_lon}"
           f"&minmagnitude={min_mag}&starttime={start}&orderby=time&limit=50")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IranSeismicMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("features", [])
    except Exception as e:
        print(f"  ⚠️  USGS fetch error: {e}", file=sys.stderr)
        return []


def load_state(state_dir):
    path = os.path.join(state_dir, "seismic-seen.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"seen": {}, "last_scan": None}


def save_state(state_dir, state):
    path = os.path.join(state_dir, "seismic-seen.json")
    # Prune entries older than 7 days
    cutoff = time.time() - (7 * 86400)
    state["seen"] = {k: v for k, v in state["seen"].items() if v.get("ts", 0) > cutoff}
    state["last_scan"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scan-seismic.py <config.json> <state_dir> [--seed] [--days N] [--min-mag N]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    seed_mode = "--seed" in sys.argv
    
    days = 2
    min_mag = 2.5
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
        if arg == "--min-mag" and i + 1 < len(sys.argv):
            min_mag = float(sys.argv[i + 1])
    
    with open(config_path) as f:
        config = json.load(f)
    
    os.makedirs(state_dir, exist_ok=True)
    state = load_state(state_dir)
    
    features = fetch_usgs(config, days, min_mag)
    print(f"  USGS: {len(features)} quakes (M{min_mag}+, {days}d)", file=sys.stderr)
    
    new_quakes = []
    for f in features:
        qid = f["id"]
        if qid in state["seen"]:
            continue
        
        props = f["properties"]
        coords = f["geometry"]["coordinates"]  # [lon, lat, depth]
        lon, lat, depth = coords[0], coords[1], coords[2]
        mag = props.get("mag", 0) or 0
        place = props.get("place", "Unknown")
        event_type = props.get("type", "earthquake")
        event_time = props.get("time", 0)  # epoch ms
        
        nearby = check_proximity(lat, lon)
        priority, suspicious = classify_quake(mag, depth, event_type, nearby)
        
        quake = {
            "id": qid,
            "lat": lat,
            "lon": lon,
            "depth_km": depth,
            "mag": mag,
            "place": place,
            "type": event_type,
            "time_epoch": event_time / 1000 if event_time else 0,
            "time_str": datetime.fromtimestamp(event_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if event_time else "",
            "priority": priority,
            "suspicious": suspicious,
            "nearby_sites": nearby,
            "google_maps": f"https://maps.google.com/maps?q={lat},{lon}&z=10",
            "usgs_url": props.get("url", ""),
        }
        new_quakes.append(quake)
        state["seen"][qid] = {"ts": time.time(), "mag": mag, "priority": priority}
    
    print(f"  New quakes: {len(new_quakes)}", file=sys.stderr)
    
    save_state(state_dir, state)
    
    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_quakes": len(features),
        "new_quakes": len(new_quakes),
        "seed_mode": seed_mode,
        "quakes": [] if seed_mode else new_quakes,
        "summary": {
            "critical": len([q for q in new_quakes if q["priority"] == "critical"]),
            "high": len([q for q in new_quakes if q["priority"] == "high"]),
            "medium": len([q for q in new_quakes if q["priority"] == "medium"]),
            "low": len([q for q in new_quakes if q["priority"] == "low"]),
            "suspicious": len([q for q in new_quakes if q["suspicious"]]),
        }
    }
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
