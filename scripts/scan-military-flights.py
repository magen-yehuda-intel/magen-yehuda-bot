#!/usr/bin/env python3
"""
US/Israeli Military Flight Tracker for Middle East.
Uses FlightRadar24 public API (no auth needed, ~400 aircraft).
Falls back to OpenSky if FR24 fails.

Detects: tankers, bombers, AWACS, ISR, airlift, fighters by callsign + type + registration.

Usage:
    python3 scan-military-flights.py <config.json> <state_dir> [--seed]
"""

import sys
import os
import json
import time
import urllib.request
from datetime import datetime, timezone

# Middle East bounding box: N,S,W,E
ME_BOUNDS = {"n": 42, "s": 12, "w": 24, "e": 65}

# US military callsign prefixes
US_MIL_CALLSIGNS = [
    'RCH', 'REACH', 'EVAC', 'FORTE', 'JAKE', 'NCHO', 'LAGR',
    'SAM', 'AF1', 'AF2', 'EXEC', 'NAVY', 'CNV', 'TOPCT',
    'ORDER', 'GOLD', 'TITAN', 'VIPER', 'HAWK', 'STORM',
    'QID', 'DUKE', 'SNTRY', 'DOOM', 'KNIFE', 'ANGRY',
    'WRATH', 'BOLT', 'RAID', 'HAVOC', 'OMNI', 'COBRA',
    'TEAL', 'NEON', 'IRIS', 'AERO', 'ETHYL', 'SHELL',
    'BONE', 'BUFF', 'GIANT', 'SENTRY', 'TROUT', 'ATLAS',
    'GORDO', 'OLIVE', 'DRAGN', 'IRON', 'NATO',
]

IAF_CALLSIGNS = ['IAF', 'ISF']

US_MIL_TYPES = {
    'C17', 'C5M', 'C130', 'C130J', 'KC135', 'KC46', 'KC10',
    'E3TF', 'E3CF', 'E6B', 'E8C', 'RC135', 'EP3', 'P8',
    'B1B', 'B2', 'B52', 'F15', 'F16', 'F18', 'F22', 'F35',
    'V22', 'CV22', 'MV22', 'MQ9', 'RQ4', 'U2',
    'C40', 'C32', 'C37', 'C20', 'VC25', 'K35R', 'K135',
}

IAF_TYPES = {'F35', 'F15', 'F16', 'C130', 'C130J', 'G550', 'B762', 'B763', 'GLEX'}

# Role descriptions for notable callsigns/types
ROLE_MAP = {
    'FORTE': '🛰️ RQ-4 Global Hawk (ISR)',
    'HAWK': '🛰️ Global Hawk variant',
    'GORDO': '🔍 RC-135 Rivet Joint (SIGINT)',
    'OLIVE': '🔍 RC-135 Rivet Joint (SIGINT)',
    'GIANT': '📡 E-3 AWACS',
    'SNTRY': '📡 E-3 AWACS',
    'SENTRY': '📡 E-3 AWACS',
    'DOOM': '💣 B-2 Spirit',
    'BONE': '💣 B-1B Lancer',
    'BUFF': '💣 B-52 Stratofortress',
    'ETHYL': '⛽ KC-135/KC-46 Tanker',
    'SHELL': '⛽ Tanker',
    'JAKE': '⛽ Tanker',
    'TROUT': '🔍 P-8 Poseidon (ASW)',
    'DRAGN': '🛰️ U-2 Dragon Lady',
    'RCH': '✈️ C-17 Globemaster (Airlift)',
    'REACH': '✈️ Strategic Airlift',
    'ATLAS': '✈️ Strategic Airlift',
    'SAM': '🏛️ VIP Transport',
    'AF1': '🏛️ Air Force One',
    'NAVY': '⚓ US Navy',
    'CNV': '⚓ US Navy',
}

TYPE_ROLE = {
    'C17': '✈️ C-17 Globemaster III',
    'C5M': '✈️ C-5M Super Galaxy',
    'KC135': '⛽ KC-135 Stratotanker',
    'KC46': '⛽ KC-46A Pegasus',
    'KC10': '⛽ KC-10 Extender',
    'E3TF': '📡 E-3 Sentry AWACS',
    'E3CF': '📡 E-3 Sentry AWACS',
    'E6B': '📡 E-6B Mercury (TACAMO)',
    'E8C': '📡 E-8C JSTARS',
    'RC135': '🔍 RC-135 (SIGINT)',
    'P8': '🔍 P-8A Poseidon',
    'B1B': '💣 B-1B Lancer',
    'B2': '💣 B-2A Spirit',
    'B52': '💣 B-52H Stratofortress',
    'MQ9': '🛰️ MQ-9 Reaper (UAV)',
    'RQ4': '🛰️ RQ-4 Global Hawk',
    'U2': '🛰️ U-2 Dragon Lady',
    'F35': '🔥 F-35 Lightning II',
    'F22': '🔥 F-22 Raptor',
    'F15': '🔥 F-15 Eagle/Strike Eagle',
    'F16': '🔥 F-16 Fighting Falcon',
}


def classify(callsign, atype, reg):
    """Returns (side, category, description) or None."""
    cs = (callsign or '').strip().upper()
    at = (atype or '').strip().upper()
    rg = (reg or '').strip().upper()

    side = None
    # US military
    for p in US_MIL_CALLSIGNS:
        if cs.startswith(p):
            side = 'us'
            # Find role from callsign prefix
            for rp, desc in ROLE_MAP.items():
                if cs.startswith(rp):
                    return side, desc
            return side, TYPE_ROLE.get(at, '✈️ US Military')

    # Israeli
    for p in IAF_CALLSIGNS:
        if cs.startswith(p):
            return 'il', TYPE_ROLE.get(at, '🇮🇱 Israeli Air Force')
    if rg.startswith('4X-') and at in IAF_TYPES:
        return 'il', TYPE_ROLE.get(at, '🇮🇱 IAF')

    # US type + US-ish reg without callsign
    if at in US_MIL_TYPES and rg.startswith('N') and not cs:
        return 'us', TYPE_ROLE.get(at, '✈️ US Military (dark)')

    return None, None


def fetch_fr24(proxy=None):
    """Fetch aircraft from FR24 public feed."""
    b = ME_BOUNDS
    url = (f"https://data-cloud.flightradar24.com/zones/fcgi/feed.js?"
           f"faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1"
           f"&vehicles=0&estimated=0&maxage=14400&gliders=0&stats=0"
           f"&bounds={b['n']},{b['s']},{b['w']},{b['e']}")
    headers = {"User-Agent": "Mozilla/5.0"}
    if proxy:
        handler = urllib.request.ProxyHandler({"https": proxy, "http": proxy})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    aircraft = []
    for k, v in data.items():
        if not isinstance(v, list) or len(v) < 14:
            continue
        aircraft.append({
            "lat": v[1], "lon": v[2], "heading": v[3],
            "alt": v[4], "speed": v[5], "type": v[8] or "",
            "reg": v[9] or "", "callsign": (v[16] if len(v) > 16 else "") or "",
            "from": v[11] or "", "to": v[12] or "",
        })
    return aircraft


def fetch_opensky():
    """Fallback: OpenSky Network."""
    b = ME_BOUNDS
    url = (f"https://opensky-network.org/api/states/all?"
           f"lamin={b['s']}&lomin={b['w']}&lamax={b['n']}&lomax={b['e']}")
    req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaBot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    aircraft = []
    for s in (data.get("states") or []):
        if not s or len(s) < 8 or s[8]:  # skip ground
            continue
        if s[6] is None or s[5] is None:
            continue
        aircraft.append({
            "lat": s[6], "lon": s[5], "heading": s[10] or 0,
            "alt": int((s[7] or s[13] or 0) * 3.281),
            "speed": int((s[9] or 0) * 1.944),
            "type": "", "reg": "",
            "callsign": (s[1] or "").strip(),
            "from": "", "to": "", "icao24": s[0],
        })
    return aircraft


def main():
    if len(sys.argv) < 3:
        print("Usage: scan-military-flights.py <config.json> <state_dir> [--seed]", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    seed_mode = "--seed" in sys.argv
    os.makedirs(state_dir, exist_ok=True)

    # Fetch aircraft: FR24 primary, OpenSky fallback
    source = "fr24"
    try:
        all_ac = fetch_fr24()
        print(f"  FR24: {len(all_ac)} aircraft in Middle East", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️ FR24 error: {e}", file=sys.stderr)
        source = "opensky"
        try:
            all_ac = fetch_opensky()
            print(f"  OpenSky: {len(all_ac)} aircraft in Middle East", file=sys.stderr)
        except Exception as e2:
            print(f"  ⚠️ OpenSky error: {e2}", file=sys.stderr)
            all_ac = []

    # Classify military
    military = []
    for ac in all_ac:
        side, desc = classify(ac["callsign"], ac["type"], ac["reg"])
        if side:
            ac["side"] = side
            ac["description"] = desc
            military.append(ac)

    print(f"  Military aircraft: {len(military)}", file=sys.stderr)

    # Load previous state
    state_file = os.path.join(state_dir, "military-flights.json")
    prev_keys = set()
    try:
        with open(state_file) as f:
            prev = json.load(f)
            prev_keys = set(
                a.get("icao24") or f'{a["callsign"]}_{a["type"]}'
                for a in prev.get("aircraft", [])
            )
    except:
        pass

    new_aircraft = []
    for ac in military:
        key = ac.get("icao24") or f'{ac["callsign"]}_{ac["type"]}'
        if key not in prev_keys:
            new_aircraft.append(ac)

    # Categorize
    by_cat = {}
    for ac in military:
        cat = ac["description"].split("(")[0].strip() if ac.get("description") else "Unknown"
        by_cat[cat] = by_cat.get(cat, 0) + 1

    result = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "total_in_zone": len(all_ac),
        "military_count": len(military),
        "new_count": 0 if seed_mode else len(new_aircraft),
        "aircraft": military,
        "new_aircraft": [] if seed_mode else new_aircraft,
        "seed_mode": seed_mode,
        "by_category": by_cat,
    }

    with open(state_file, "w") as f:
        json.dump(result, f, indent=2)

    for cat, count in sorted(by_cat.items()):
        print(f"    {cat}: {count}", file=sys.stderr)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
