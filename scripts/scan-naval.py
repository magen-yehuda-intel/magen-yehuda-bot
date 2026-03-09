#!/usr/bin/env python3
"""
Naval/Ship Tracker for Persian Gulf & Gulf of Oman.
Monitors military and strategic vessel movements.

Uses AIS data from public sources.

Usage:
    python3 scan-naval.py <config.json> <state_dir> [--seed]
"""

import sys
import os
import json
import time
import math
import urllib.request
from datetime import datetime, timezone, timedelta

# Strait of Hormuz / Persian Gulf / Gulf of Oman bounding box
ZONES = {
    "strait_of_hormuz": {"lamin": 25.5, "lomin": 55.5, "lamax": 27.0, "lomax": 57.5, "label": "Strait of Hormuz"},
    "persian_gulf": {"lamin": 24.0, "lomin": 48.0, "lamax": 30.5, "lomax": 56.0, "label": "Persian Gulf"},
    "gulf_of_oman": {"lamin": 22.0, "lomin": 56.0, "lamax": 26.0, "lomax": 62.0, "label": "Gulf of Oman"},
    "arabian_sea": {"lamin": 18.0, "lomin": 57.0, "lamax": 25.0, "lomax": 68.0, "label": "Arabian Sea"},
}

# US Navy vessel names/hull numbers to watch
US_NAVY_VESSELS = {
    "EISENHOWER": {"type": "CVN", "hull": "CVN-69", "desc": "Aircraft Carrier"},
    "LINCOLN": {"type": "CVN", "hull": "CVN-72", "desc": "Aircraft Carrier"},
    "TRUMAN": {"type": "CVN", "hull": "CVN-75", "desc": "Aircraft Carrier"},
    "FORD": {"type": "CVN", "hull": "CVN-78", "desc": "Aircraft Carrier"},
    "BATAAN": {"type": "LHD", "hull": "LHD-5", "desc": "Amphibious Assault"},
    "WASP": {"type": "LHD", "hull": "LHD-1", "desc": "Amphibious Assault"},
    "MASON": {"type": "DDG", "hull": "DDG-87", "desc": "Destroyer"},
    "LABOON": {"type": "DDG", "hull": "DDG-58", "desc": "Destroyer"},
    "COLE": {"type": "DDG", "hull": "DDG-67", "desc": "Destroyer"},
    "CARNEY": {"type": "DDG", "hull": "DDG-64", "desc": "Destroyer"},
    "GRAVELY": {"type": "DDG", "hull": "DDG-107", "desc": "Destroyer"},
    "PHILIPPINE SEA": {"type": "CG", "hull": "CG-58", "desc": "Cruiser"},
    "FLORIDA": {"type": "SSGN", "hull": "SSGN-728", "desc": "Guided Missile Sub"},
    "OHIO": {"type": "SSGN", "hull": "SSGN-726", "desc": "Guided Missile Sub"},
    "GEORGIA": {"type": "SSGN", "hull": "SSGN-729", "desc": "Guided Missile Sub"},
}

# IRGC Navy vessel types (Iranian fast attack boats)
IRGC_INDICATORS = [
    "IRGC", "IRAN NAVY", "ARTESH", "SEPAH",
    "TONDAR", "SINA", "ALVAND", "SABALAN", "SAHAND",
    "MAKRAN", "SHAHID", "JAMARAN", "DENA",
]

# Known naval bases
NAVAL_BASES = [
    {"name": "Bandar Abbas (Iran)", "lat": 27.19, "lon": 56.27, "flag": "🇮🇷"},
    {"name": "Jask (Iran)", "lat": 25.64, "lon": 57.77, "flag": "🇮🇷"},
    {"name": "Bushehr (Iran)", "lat": 28.83, "lon": 50.89, "flag": "🇮🇷"},
    {"name": "NSA Bahrain (US 5th Fleet)", "lat": 26.23, "lon": 50.63, "flag": "🇺🇸"},
    {"name": "Al Dhafra (UAE/US)", "lat": 24.25, "lon": 54.55, "flag": "🇺🇸"},
    {"name": "Duqm (Oman/US)", "lat": 19.67, "lon": 57.70, "flag": "🇺🇸"},
    {"name": "Diego Garcia", "lat": -7.32, "lon": 72.42, "flag": "🇺🇸"},
]


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def check_zone(lat, lon):
    """Determine which zone a vessel is in."""
    # Check specific zones first (Hormuz most important)
    for zone_id, zone in ZONES.items():
        if (zone["lamin"] <= lat <= zone["lamax"] and
            zone["lomin"] <= lon <= zone["lomax"]):
            return zone_id, zone["label"]
    return "other", "Open Waters"


def nearest_base(lat, lon, threshold_km=100):
    best = None
    best_dist = threshold_km + 1
    for base in NAVAL_BASES:
        d = haversine_km(lat, lon, base["lat"], base["lon"])
        if d < best_dist:
            best_dist = d
            best = base
    if best and best_dist <= threshold_km:
        return {**best, "distance_km": round(best_dist, 1)}
    return None


def fetch_marine_traffic_data():
    """
    Fetch vessel data. Uses MarineTraffic public density API
    and supplementary open AIS sources.
    """
    vessels = []
    
    # Method 1: VesselFinder free API (ship positions)
    try:
        # Persian Gulf area
        url = "https://www.vesselfinder.com/api/pub/vesselsonmap?bbox=48.00,24.00,62.00,30.50&zoom=6&mmsi=0&ref=0&reqtype=R"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.vesselfinder.com/",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            # VesselFinder returns a custom format, not standard JSON
            # Try to parse it
            if raw.startswith("[") or raw.startswith("{"):
                data = json.loads(raw)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            vessels.append(item)
                elif isinstance(data, dict):
                    for v in data.get("vessels", data.get("data", [])):
                        vessels.append(v)
            print(f"  VesselFinder: {len(vessels)} vessels", file=sys.stderr)
    except Exception as e:
        print(f"  VesselFinder: {e}", file=sys.stderr)
    
    # Method 2: AISHub public data (if available)
    try:
        url = "https://data.aishub.net/ws.php?username=AH_3918_F93D7E&format=1&output=json&compress=0&latmin=24&latmax=30.5&lonmin=48&lonmax=62"
        req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ais_data = json.loads(resp.read().decode("utf-8"))
            if isinstance(ais_data, list) and len(ais_data) > 1:
                for record in ais_data[1:]:  # First element is metadata
                    vessels.append({
                        "mmsi": record.get("MMSI"),
                        "name": record.get("NAME", "").strip(),
                        "lat": record.get("LATITUDE"),
                        "lon": record.get("LONGITUDE"),
                        "speed": record.get("SOG"),
                        "course": record.get("COG"),
                        "type": record.get("TYPE"),
                    })
                print(f"  AISHub: {len(ais_data)-1} vessels", file=sys.stderr)
    except Exception as e:
        print(f"  AISHub: {e}", file=sys.stderr)
    
    return vessels


def analyze_vessels(vessels, state_dir):
    """Analyze vessels for military significance."""
    military_vessels = []
    strategic = []
    
    for v in vessels:
        name = (v.get("name") or v.get("SHIPNAME") or "").upper().strip()
        mmsi = str(v.get("mmsi") or v.get("MMSI") or "")
        lat = v.get("lat") or v.get("LAT")
        lon = v.get("lon") or v.get("LON")
        
        if lat is None or lon is None:
            continue
        
        try:
            lat = float(lat)
            lon = float(lon)
        except:
            continue
        
        # Check for US Navy vessels
        for vessel_name, info in US_NAVY_VESSELS.items():
            if vessel_name in name:
                zone_id, zone_label = check_zone(lat, lon)
                base = nearest_base(lat, lon)
                military_vessels.append({
                    "name": name,
                    "mmsi": mmsi,
                    "lat": lat,
                    "lon": lon,
                    "type": info["type"],
                    "hull": info["hull"],
                    "desc": info["desc"],
                    "zone": zone_label,
                    "flag": "🇺🇸",
                    "near_base": base,
                })
                break
        
        # Check for Iranian military
        for indicator in IRGC_INDICATORS:
            if indicator in name:
                zone_id, zone_label = check_zone(lat, lon)
                military_vessels.append({
                    "name": name,
                    "mmsi": mmsi,
                    "lat": lat,
                    "lon": lon,
                    "type": "IRGCN",
                    "hull": "",
                    "desc": "Iranian Navy/IRGC",
                    "zone": zone_label,
                    "flag": "🇮🇷",
                })
                break
        
        # Check for military MMSI ranges (US Navy: 338-339, 369)
        if mmsi.startswith("338") or mmsi.startswith("339") or mmsi.startswith("369"):
            if name and name not in [mv["name"] for mv in military_vessels]:
                zone_id, zone_label = check_zone(lat, lon)
                military_vessels.append({
                    "name": name or f"MMSI:{mmsi}",
                    "mmsi": mmsi,
                    "lat": lat,
                    "lon": lon,
                    "type": "USN",
                    "hull": "",
                    "desc": "US Navy (MMSI)",
                    "zone": zone_label,
                    "flag": "🇺🇸",
                })
    
    return military_vessels


def format_telegram(military_vessels, total_vessels):
    """Format military vessel report for Telegram."""
    if not military_vessels:
        return None
    
    lines = [
        "🚢🚢🚢 <b>NAVAL ACTIVITY — PERSIAN GULF</b> 🚢🚢🚢",
        "",
        f"<i>{datetime.now(timezone.utc).strftime('%H:%M UTC')} | {total_vessels} vessels tracked</i>",
        "",
        f"⚓ <b>{len(military_vessels)} military vessel(s) detected</b>",
        "",
    ]
    
    # Group by flag
    by_flag = {}
    for v in military_vessels:
        flag = v.get("flag", "🏴")
        by_flag.setdefault(flag, []).append(v)
    
    for flag, vlist in sorted(by_flag.items()):
        lines.append(f"{flag} <b>{'US Navy' if flag == '🇺🇸' else 'Iranian Navy' if flag == '🇮🇷' else 'Military'}:</b>")
        for v in vlist[:8]:
            type_emoji = {"CVN": "🛳️", "DDG": "⚓", "CG": "⚓", "LHD": "🚢",
                         "SSGN": "🦈", "IRGCN": "🚤"}.get(v["type"], "🚢")
            desc = f"{v['hull']} " if v["hull"] else ""
            lines.append(f"  {type_emoji} <b>{v['name']}</b> {desc}")
            lines.append(f"     📍 {v['zone']} ({v['lat']:.2f}, {v['lon']:.2f})")
            if v.get("near_base"):
                b = v["near_base"]
                lines.append(f"     {b['flag']} Near {b['name']} ({b['distance_km']}km)")
        lines.append("")
    
    lines.append("<i>⚓ Vessel tracking via AIS — some military vessels may disable transponders</i>")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scan-naval.py <config.json> <state_dir> [--seed]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    seed_mode = "--seed" in sys.argv
    
    os.makedirs(state_dir, exist_ok=True)
    
    print("  Scanning naval activity...", file=sys.stderr)
    vessels = fetch_marine_traffic_data()
    print(f"  Total vessels in zone: {len(vessels)}", file=sys.stderr)
    
    military = analyze_vessels(vessels, state_dir)
    print(f"  Military vessels: {len(military)}", file=sys.stderr)
    
    # Change detection
    state_file = os.path.join(state_dir, "naval-state.json")
    prev_names = set()
    try:
        with open(state_file) as f:
            prev = json.load(f)
            prev_names = set(v["name"] for v in prev.get("military_vessels", []))
    except:
        pass
    
    new_vessels = [v for v in military if v["name"] not in prev_names]
    
    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_vessels": len(vessels),
        "military_count": len(military),
        "new_count": len(new_vessels),
        "military_vessels": military,
        "new_vessels": [] if seed_mode else new_vessels,
        "seed_mode": seed_mode,
    }
    
    # Save state
    with open(state_file, "w") as f:
        json.dump(result, f, indent=2)
    
    msg = format_telegram(military, len(vessels))
    if msg:
        result["telegram_message"] = msg
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
