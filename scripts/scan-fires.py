#!/usr/bin/env python3
"""
NASA FIRMS Satellite Fire Detection for Iran/Persian Gulf/Gulf of Oman.
Fetches active fire hotspots, filters to Iran region, reverse geocodes to nearest city,
tracks state for new-only alerts, and outputs JSON for Telegram integration.

Usage:
    python3 scan-fires.py <config.json> <state_dir> [--seed]
    
    --seed: First run; saves current fires as baseline without alerting.
"""

import sys
import os
import json
import csv
import io
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2

# Iran approximate polygon (simplified) - points roughly tracing the border
# We use a bounding box for API fetch, then filter with point-in-polygon for Iran proper
# Plus Persian Gulf and Gulf of Oman water areas
IRAN_BBOX = {"west": 44, "south": 25, "east": 63.5, "north": 40}

# Simplified Iran border polygon (lon, lat pairs) - rough but functional
# Includes mainland Iran. Water areas (Persian Gulf, Gulf of Oman) handled separately.
IRAN_POLYGON = [
    (44.0, 39.4), (44.4, 38.4), (44.8, 39.6), (45.5, 38.9), (46.2, 39.0),
    (47.0, 39.1), (48.0, 38.9), (48.4, 38.5), (48.9, 38.4), (48.6, 37.8),
    (49.1, 37.6), (50.0, 37.4), (50.5, 37.2), (51.1, 36.7), (52.0, 36.8),
    (53.0, 37.0), (53.9, 37.3), (54.7, 37.0), (55.4, 37.2), (56.0, 37.4),
    (57.2, 37.6), (58.4, 37.6), (59.3, 37.5), (60.1, 36.6), (61.0, 36.6),
    (61.1, 35.3), (61.2, 34.0), (61.0, 33.2), (60.5, 33.0), (60.6, 31.5),
    (61.8, 31.0), (61.8, 30.0), (61.6, 29.4), (60.9, 29.0), (60.6, 28.5),
    (60.0, 27.8), (59.0, 27.0), (58.5, 26.5), (57.8, 26.0), (57.0, 25.5),
    (56.5, 26.0), (56.3, 26.5), (55.6, 26.5), (54.8, 26.6), (54.0, 26.8),
    (53.5, 26.5), (52.5, 27.0), (51.5, 27.5), (50.8, 27.9), (50.2, 28.5),
    (49.5, 29.0), (49.0, 29.5), (48.5, 30.0), (48.0, 30.5), (48.0, 31.0),
    (47.5, 31.5), (47.0, 32.0), (46.5, 32.5), (46.0, 33.0), (45.5, 33.5),
    (45.5, 34.0), (45.5, 34.5), (45.0, 35.0), (44.5, 35.5), (44.2, 36.5),
    (44.0, 37.0), (44.3, 37.5), (44.0, 38.0), (44.0, 39.4),
]

# Persian Gulf + Gulf of Oman water zone (fires here = offshore/island military targets)
WATER_ZONE = {
    "persian_gulf": {"west": 48, "south": 24, "east": 56.5, "north": 30.5},
    "gulf_of_oman": {"west": 56.5, "south": 24, "east": 61.5, "north": 26.5},
}

# Known Iranian military/nuclear sites for proximity flagging
KNOWN_SITES = [
    {"name": "Natanz (Nuclear)", "lat": 33.72, "lon": 51.72, "type": "nuclear"},
    {"name": "Fordow (Nuclear)", "lat": 34.88, "lon": 51.59, "type": "nuclear"},
    {"name": "Isfahan (Nuclear/Military)", "lat": 32.65, "lon": 51.68, "type": "nuclear"},
    {"name": "Bushehr (Nuclear Plant)", "lat": 28.83, "lon": 50.89, "type": "nuclear"},
    {"name": "Arak (Heavy Water)", "lat": 34.38, "lon": 49.24, "type": "nuclear"},
    {"name": "Parchin (Military)", "lat": 35.52, "lon": 51.77, "type": "military"},
    {"name": "Tehran (Capital)", "lat": 35.69, "lon": 51.39, "type": "capital"},
    {"name": "Bandar Abbas (Naval)", "lat": 27.19, "lon": 56.27, "type": "military"},
    {"name": "Chabahar (Naval)", "lat": 25.29, "lon": 60.64, "type": "military"},
    {"name": "Kharg Island (Oil Terminal)", "lat": 29.23, "lon": 50.31, "type": "oil"},
    {"name": "Abadan (Refinery)", "lat": 30.34, "lon": 48.30, "type": "oil"},
    {"name": "Isfahan Refinery", "lat": 32.58, "lon": 51.72, "type": "oil"},
    {"name": "Tabriz (Military)", "lat": 38.08, "lon": 46.29, "type": "military"},
    {"name": "Shiraz (Air Base)", "lat": 29.54, "lon": 52.59, "type": "military"},
    {"name": "Esfahan Air Base", "lat": 32.75, "lon": 51.86, "type": "military"},
    {"name": "Mehrabad (Tehran Airport)", "lat": 35.69, "lon": 51.31, "type": "military"},
    {"name": "Khatami Air Base (Isfahan)", "lat": 32.57, "lon": 51.69, "type": "military"},
    {"name": "Dezful Air Base", "lat": 32.43, "lon": 48.38, "type": "military"},
    {"name": "Hamadan Air Base", "lat": 35.21, "lon": 48.65, "type": "military"},
    {"name": "Konarak (Naval)", "lat": 25.35, "lon": 60.38, "type": "military"},
    {"name": "Jask (Naval)", "lat": 25.64, "lon": 57.77, "type": "military"},
    {"name": "Imam Khomeini Space Center", "lat": 35.23, "lon": 53.95, "type": "military"},
    {"name": "Shahrud Missile Base", "lat": 36.42, "lon": 55.00, "type": "military"},
    # Saudi oil/refinery infrastructure
    {"name": "Ras Tanura Refinery (Saudi Aramco)", "lat": 26.63, "lon": 50.16, "type": "oil"},
    {"name": "Jubail Refinery (Saudi)", "lat": 27.01, "lon": 49.66, "type": "oil"},
    {"name": "Abqaiq Oil Processing (Saudi Aramco)", "lat": 25.94, "lon": 49.68, "type": "oil"},
    {"name": "Yanbu Refinery (Saudi)", "lat": 24.09, "lon": 38.06, "type": "oil"},
    {"name": "Dhahran (Aramco HQ)", "lat": 26.27, "lon": 50.21, "type": "oil"},
    # Qatar LNG
    {"name": "Ras Laffan LNG Terminal (Qatar)", "lat": 25.93, "lon": 51.53, "type": "oil"},
    {"name": "Mesaieed Industrial/LNG (Qatar)", "lat": 24.99, "lon": 51.55, "type": "oil"},
    # Iraq oil
    {"name": "Basrah Oil Terminal (Iraq)", "lat": 30.51, "lon": 47.78, "type": "oil"},
    {"name": "Kirkuk Oil Fields (Iraq)", "lat": 35.47, "lon": 44.39, "type": "oil"},
    # UAE
    {"name": "Ruwais Refinery (ADNOC, UAE)", "lat": 24.11, "lon": 52.73, "type": "oil"},
    {"name": "Jebel Dhanna Terminal (UAE)", "lat": 24.19, "lon": 52.58, "type": "oil"},
    {"name": "Das Island Oil/Gas (UAE)", "lat": 25.15, "lon": 52.87, "type": "oil"},
    {"name": "Fujairah Oil Terminal (UAE)", "lat": 25.13, "lon": 56.33, "type": "oil"},
    # Iran additional
    {"name": "Tehran Refinery", "lat": 35.69, "lon": 51.39, "type": "oil"},
    {"name": "Bandar Imam Khomeini Petrochemical", "lat": 30.43, "lon": 49.08, "type": "oil"},
    {"name": "Lavan Island Oil Terminal", "lat": 26.81, "lon": 53.36, "type": "oil"},
    {"name": "Kermanshah Refinery", "lat": 34.33, "lon": 47.08, "type": "oil"},
    {"name": "Asaluyeh Petrochemical Zone", "lat": 27.48, "lon": 52.61, "type": "oil"},
    # Israel
    {"name": "Haifa Refinery (Israel)", "lat": 32.81, "lon": 35.01, "type": "oil"},
    {"name": "Ashdod Oil Terminal (Israel)", "lat": 31.80, "lon": 34.65, "type": "oil"},
]

FIRMS_SOURCES = [
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT",
    "MODIS_NRT",
]


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance in km between two points."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def point_in_polygon(lat, lon, polygon):
    """Ray casting algorithm for point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]  # lon, lat
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def in_water_zone(lat, lon):
    """Check if point is in Persian Gulf or Gulf of Oman."""
    for name, zone in WATER_ZONE.items():
        if zone["south"] <= lat <= zone["north"] and zone["west"] <= lon <= zone["east"]:
            return name
    return None


def in_iran_region(lat, lon):
    """Check if fire is in Iran (land) or Persian Gulf/Gulf of Oman."""
    if point_in_polygon(lat, lon, IRAN_POLYGON):
        return "iran"
    water = in_water_zone(lat, lon)
    if water:
        return water
    return None


def fetch_firms_data(map_key, source, bbox, days=1):
    """Fetch fire data from NASA FIRMS API."""
    url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}"
           f"/{source}/{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}/{days}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IranFireMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            if "Invalid MAP_KEY" in data:
                print(f"  ⚠️  Invalid MAP_KEY for {source}", file=sys.stderr)
                return []
            reader = csv.DictReader(io.StringIO(data))
            rows = list(reader)
            return rows
    except Exception as e:
        print(f"  ⚠️  FIRMS fetch error ({source}): {e}", file=sys.stderr)
        return []


def reverse_geocode(lat, lon):
    """Reverse geocode using Nominatim (free, no key needed)."""
    url = (f"https://nominatim.openstreetmap.org/reverse?"
           f"lat={lat}&lon={lon}&format=json&zoom=10&accept-language=en")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IranFireMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            addr = data.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county", "")
            province = addr.get("state", addr.get("province", ""))
            country = addr.get("country", "")
            display = data.get("display_name", "")
            return {
                "city": city,
                "province": province,
                "country": country,
                "display": display,
            }
    except Exception as e:
        return {"city": "Unknown", "province": "", "country": "", "display": str(e)}


def check_proximity_to_sites(lat, lon, threshold_km=15):
    """Check if fire is near a known military/nuclear site."""
    nearby = []
    for site in KNOWN_SITES:
        dist = haversine_km(lat, lon, site["lat"], site["lon"])
        if dist <= threshold_km:
            nearby.append({**site, "distance_km": round(dist, 1)})
    nearby.sort(key=lambda x: x["distance_km"])
    return nearby


def fire_key(row):
    """Generate unique key for a fire detection to avoid duplicate alerts."""
    # Round to ~1km grid to deduplicate overlapping satellite passes
    lat = round(float(row["latitude"]), 2)
    lon = round(float(row["longitude"]), 2)
    date = row["acq_date"]
    return f"{lat}_{lon}_{date}"


def classify_fire(row, nearby_sites):
    """Classify fire severity/interest level."""
    frp = float(row.get("frp", 0) or 0)
    confidence = row.get("confidence", "")
    
    # High FRP = large/intense fire
    priority = "low"
    if frp >= 50:
        priority = "high"
    elif frp >= 15:
        priority = "medium"
    
    # Near military/nuclear site = always high
    if nearby_sites:
        for site in nearby_sites:
            if site["type"] in ("nuclear", "capital"):
                priority = "critical"
                break
            elif site["type"] in ("military", "oil"):
                priority = max(priority, "high", key=["low", "medium", "high", "critical"].index)
    
    # High confidence from satellite
    if confidence in ("high", "h") or (confidence.isdigit() and int(confidence) >= 80):
        if priority == "low":
            priority = "medium"
    
    return priority


def load_state(state_dir):
    """Load seen fires state."""
    path = os.path.join(state_dir, "firms-seen.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"seen": {}, "last_scan": None}


def save_state(state_dir, state):
    """Save seen fires state."""
    path = os.path.join(state_dir, "firms-seen.json")
    # Prune entries older than 3 days
    cutoff = (datetime.now(timezone.utc).timestamp()) - (3 * 86400)
    pruned = {k: v for k, v in state["seen"].items() if v.get("ts", 0) > cutoff}
    state["seen"] = pruned
    state["last_scan"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scan-fires.py <config.json> <state_dir> [--seed]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    seed_mode = "--seed" in sys.argv
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Get MAP_KEY from config or secrets file
    map_key = config.get("firms_map_key", "")
    if not map_key:
        key_path = os.path.join(os.path.dirname(config_path), "secrets", "firms-map-key.txt")
        if os.path.exists(key_path):
            with open(key_path) as f:
                map_key = f.read().strip()
    
    if not map_key:
        print(json.dumps({"error": "No FIRMS MAP_KEY found", "fires": []}))
        sys.exit(1)
    
    os.makedirs(state_dir, exist_ok=True)
    state = load_state(state_dir)
    
    # Fetch from all FIRMS sources
    all_fires = []
    for source in FIRMS_SOURCES:
        rows = fetch_firms_data(map_key, source, IRAN_BBOX, days=1)
        print(f"  {source}: {len(rows)} detections", file=sys.stderr)
        for row in rows:
            row["_source"] = source
        all_fires.extend(rows)
    
    print(f"  Total raw detections: {len(all_fires)}", file=sys.stderr)
    
    # Filter to Iran + water zones and deduplicate
    iran_fires = []
    seen_keys = set()
    for row in all_fires:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        region = in_iran_region(lat, lon)
        if not region:
            continue
        
        key = fire_key(row)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        row["_region"] = region
        row["_key"] = key
        iran_fires.append(row)
    
    print(f"  Iran region fires (deduped): {len(iran_fires)}", file=sys.stderr)
    
    # Find NEW fires (not in state)
    new_fires = []
    for row in iran_fires:
        if row["_key"] not in state["seen"]:
            new_fires.append(row)
    
    print(f"  New fires: {len(new_fires)}", file=sys.stderr)
    
    # Process new fires: geocode + proximity check + classify
    # Rate limit Nominatim: 1 req/sec. Only geocode up to 20 fires per scan.
    # Group fires by ~10km grid to reduce geocoding calls
    geocode_cache = {}
    processed = []
    
    # Sort by FRP descending (highest intensity first)
    new_fires.sort(key=lambda r: float(r.get("frp", 0) or 0), reverse=True)
    
    geocode_count = 0
    for row in new_fires:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        frp = float(row.get("frp", 0) or 0)
        
        # Check proximity to known sites
        nearby = check_proximity_to_sites(lat, lon)
        priority = classify_fire(row, nearby)
        
        # Geocode grid key (round to ~10km)
        geo_key = f"{round(lat, 1)}_{round(lon, 1)}"
        
        if geo_key not in geocode_cache and geocode_count < 20:
            geocode_cache[geo_key] = reverse_geocode(lat, lon)
            geocode_count += 1
            if geocode_count < 20:
                time.sleep(1.1)  # Nominatim rate limit
        
        location = geocode_cache.get(geo_key, {"city": "Unknown", "province": "", "country": ""})
        
        fire_info = {
            "lat": lat,
            "lon": lon,
            "frp": frp,
            "confidence": row.get("confidence", ""),
            "acq_date": row.get("acq_date", ""),
            "acq_time": row.get("acq_time", ""),
            "satellite": row.get("satellite", ""),
            "daynight": row.get("daynight", ""),
            "region": row["_region"],
            "key": row["_key"],
            "source": row["_source"],
            "priority": priority,
            "city": location.get("city", "Unknown"),
            "province": location.get("province", ""),
            "country": location.get("country", ""),
            "nearby_sites": nearby,
            "google_maps": f"https://maps.google.com/maps?q={lat},{lon}&z=12",
        }
        processed.append(fire_info)
        
        # Add to seen state
        state["seen"][row["_key"]] = {"ts": time.time(), "priority": priority}
    
    # Save state
    save_state(state_dir, state)
    
    # Output
    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_detections": len(all_fires),
        "iran_region_fires": len(iran_fires),
        "new_fires": len(processed),
        "seed_mode": seed_mode,
        "fires": [] if seed_mode else processed,
        "summary": {
            "critical": len([f for f in processed if f["priority"] == "critical"]),
            "high": len([f for f in processed if f["priority"] == "high"]),
            "medium": len([f for f in processed if f["priority"] == "medium"]),
            "low": len([f for f in processed if f["priority"] == "low"]),
        }
    }
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
