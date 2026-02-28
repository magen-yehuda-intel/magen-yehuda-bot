#!/usr/bin/env python3
"""
US Military Flight Tracker for Persian Gulf / Middle East.
Uses OpenSky Network API to detect military aircraft.

Tracks: tankers (KC-135, KC-46), bombers (B-2, B-52, B-1B), 
AWACS (E-3), surveillance (RQ-4, RC-135, E-8, P-8), 
fighters (F-15E, F-35, F-22)

Usage:
    python3 scan-military-flights.py <config.json> <state_dir> [--seed]
"""

import sys
import os
import json
import time
import urllib.request
from datetime import datetime, timezone

# Middle East / Persian Gulf bounding box
ME_BBOX = {
    "lamin": 20, "lomin": 40, "lamax": 42, "lomax": 65,
}

# Military aircraft identifiers
# ICAO type designators for known military platforms
MILITARY_TYPES = {
    # Tankers
    "K35R": "KC-135R Stratotanker",
    "K135": "KC-135 Stratotanker",
    "KC46": "KC-46A Pegasus",
    "KC10": "KC-10 Extender",
    # Bombers
    "B2": "B-2A Spirit",
    "B52": "B-52H Stratofortress",
    "B1": "B-1B Lancer",
    # AWACS / C2
    "E3CF": "E-3 Sentry AWACS",
    "E3TF": "E-3 Sentry AWACS",
    "E6B": "E-6B Mercury (C2)",
    "E8": "E-8C JSTARS",
    # ISR
    "GLHK": "RQ-4 Global Hawk",
    "RQ4": "RQ-4 Global Hawk",
    "RC35": "RC-135 Rivet Joint",
    "P8": "P-8A Poseidon",
    "EP3": "EP-3E Aries",
    "U2": "U-2 Dragon Lady",
    "MQ9": "MQ-9 Reaper",
    # Fighters (less likely on ADS-B)
    "F15": "F-15 Eagle/Strike Eagle",
    "F16": "F-16 Fighting Falcon",
    "F35": "F-35 Lightning II",
    "F22": "F-22 Raptor",
    "FA18": "F/A-18 Hornet/Super Hornet",
}

# Military callsign prefixes (US + coalition)
MILITARY_CALLSIGNS = [
    "RCH",    # AMC strategic airlift
    "REACH",
    "JAKE",   # Tankers
    "ETHYL",  # Tankers
    "SHELL",  # Tankers
    "DOOM",   # B-2
    "BONE",   # B-1B
    "BUFF",   # B-52
    "FURY",   # Strike fighters
    "VIPER",  # F-16
    "RAPER",  # MQ-9
    "HAWK",   # Global Hawk variants
    "FORTE",  # RQ-4 Global Hawk (famous callsign)
    "GORDO",  # RC-135
    "OLIVE",  # RC-135
    "GIANT",  # AWACS
    "DRAGN",  # Dragon Lady
    "NUKE",   # Nuclear-capable
    "NAVY",   # US Navy
    "TOPCT",  # USAF special ops
    "IRON",   # Various
    "COBRA",  # Various
    "ATLAS",  # C-17
    "SNTRY",  # E-3
    "SENTRY",
    "TROUT",  # P-8
    "RED",    # Red Flag exercises
    "SIAP",   # Various USAF
    "CAIRO",  # CENTCOM airlift
    "QUID",   # RAF tankers
    "NATO",
    "IAF",    # Israeli Air Force
]

# Military hex registration ranges (ICAO 24-bit addresses)
# US military: AE0000-AE0FFF (and others)
US_MIL_HEX_PREFIXES = ["AE", "AF", "A0"]


def is_military(callsign, icao24, category=None):
    """Determine if an aircraft is likely military."""
    callsign = (callsign or "").strip().upper()
    icao24 = (icao24 or "").strip().upper()
    
    # Check callsign prefixes
    for prefix in MILITARY_CALLSIGNS:
        if callsign.startswith(prefix):
            return True, f"Callsign: {callsign} ({prefix}*)"
    
    # Check ICAO hex prefix (US military)
    for prefix in US_MIL_HEX_PREFIXES:
        if icao24.startswith(prefix):
            return True, f"ICAO24: {icao24} (US MIL range)"
    
    # No commercial-sounding callsigns
    commercial_prefixes = ["UAL", "AAL", "DAL", "SWA", "ETH", "THY", "SVA", "UAE", "QTR", "IRA", "KLM", "BAW", "AFR", "DLH", "ELY"]
    for cp in commercial_prefixes:
        if callsign.startswith(cp):
            return False, None
    
    # Check if no callsign + military hex = suspicious
    if not callsign and icao24.startswith("AE"):
        return True, f"Dark target (no callsign, military hex {icao24})"
    
    return False, None


def classify_aircraft(callsign, icao24):
    """Classify military aircraft type from callsign/icao."""
    callsign = (callsign or "").strip().upper()
    
    if "FORTE" in callsign or "HAWK" in callsign:
        return "ISR", "🛰️ RQ-4 Global Hawk"
    if "GORDO" in callsign or "OLIVE" in callsign:
        return "ISR", "🔍 RC-135 Rivet Joint"
    if "GIANT" in callsign or "SNTRY" in callsign or "SENTRY" in callsign:
        return "C2", "📡 E-3 AWACS"
    if "DOOM" in callsign:
        return "BOMBER", "💣 B-2 Spirit"
    if "BONE" in callsign:
        return "BOMBER", "💣 B-1B Lancer"
    if "BUFF" in callsign:
        return "BOMBER", "💣 B-52 Stratofortress"
    if "ETHYL" in callsign or "SHELL" in callsign or "JAKE" in callsign:
        return "TANKER", "⛽ KC-135/KC-46 Tanker"
    if "TROUT" in callsign:
        return "ISR", "🔍 P-8 Poseidon"
    if "RAPER" in callsign or "REAP" in callsign:
        return "ISR", "🛰️ MQ-9 Reaper"
    if "RCH" in callsign or "REACH" in callsign or "ATLAS" in callsign:
        return "AIRLIFT", "✈️ Strategic Airlift"
    if "NUKE" in callsign:
        return "NUCLEAR", "☢️ Nuclear-capable"
    
    return "UNKNOWN", "✈️ Military Aircraft"


def fetch_opensky():
    """Fetch aircraft from OpenSky Network."""
    try:
        bbox = ME_BBOX
        url = (f"https://opensky-network.org/api/states/all?"
               f"lamin={bbox['lamin']}&lomin={bbox['lomin']}"
               f"&lamax={bbox['lamax']}&lomax={bbox['lomax']}")
        
        req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaBot/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        states = data.get("states", [])
        return states or []
    except Exception as e:
        print(f"  ⚠️ OpenSky error: {e}", file=sys.stderr)
        return []


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scan-military-flights.py <config.json> <state_dir> [--seed]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    seed_mode = "--seed" in sys.argv
    
    os.makedirs(state_dir, exist_ok=True)
    
    states = fetch_opensky()
    print(f"  OpenSky: {len(states)} aircraft in Middle East", file=sys.stderr)
    
    military = []
    for s in states:
        if not s or len(s) < 8:
            continue
        icao24 = s[0] or ""
        callsign = s[1] or ""
        lon = s[5]
        lat = s[6]
        alt = s[7] or s[13]  # baro or geo altitude
        velocity = s[9]
        on_ground = s[8]
        
        if on_ground:
            continue
        if lat is None or lon is None:
            continue
        
        is_mil, reason = is_military(callsign, icao24)
        if not is_mil:
            continue
        
        category, description = classify_aircraft(callsign, icao24)
        
        aircraft = {
            "icao24": icao24,
            "callsign": callsign.strip(),
            "lat": lat,
            "lon": lon,
            "altitude_m": alt,
            "altitude_ft": int(alt * 3.281) if alt else None,
            "velocity_kts": int(velocity * 1.944) if velocity else None,
            "category": category,
            "description": description,
            "reason": reason,
        }
        military.append(aircraft)
    
    # Deduplicate by icao24
    seen_icao = set()
    unique = []
    for ac in military:
        if ac["icao24"] not in seen_icao:
            seen_icao.add(ac["icao24"])
            unique.append(ac)
    military = unique
    
    print(f"  Military aircraft: {len(military)}", file=sys.stderr)
    
    # Load previous state for change detection
    state_file = os.path.join(state_dir, "military-flights.json")
    prev_icaos = set()
    try:
        with open(state_file) as f:
            prev = json.load(f)
            prev_icaos = set(a["icao24"] for a in prev.get("aircraft", []))
    except:
        pass
    
    new_aircraft = [a for a in military if a["icao24"] not in prev_icaos]
    
    # Save state
    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_in_zone": len(states),
        "military_count": len(military),
        "new_count": len(new_aircraft),
        "aircraft": military,
        "new_aircraft": [] if seed_mode else new_aircraft,
        "seed_mode": seed_mode,
        "by_category": {},
    }
    
    for ac in military:
        cat = ac["category"]
        result["by_category"][cat] = result["by_category"].get(cat, 0) + 1
    
    with open(state_file, "w") as f:
        json.dump(result, f, indent=2)
    
    # Summary
    for cat, count in sorted(result["by_category"].items()):
        print(f"    {cat}: {count}", file=sys.stderr)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
