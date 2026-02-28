#!/usr/bin/env python3
"""
Generate a FlightRadar-style map of Middle East air traffic.
Shows all aircraft with heading arrows, airport disruption stats,
notable military aircraft, and top routes.

Usage:
    python3 generate-flight-map.py <config.json> <state_dir> <output.png>
"""

import sys
import os
import json
import math
import time
import urllib.request
from datetime import datetime, timezone

# Middle East bounding box
BBOX = {"lamin": 12, "lomin": 30, "lamax": 42, "lomax": 65}

# Iran rough polygon for highlighting
IRAN_BOUNDS = {"lat_min": 25, "lat_max": 40, "lon_min": 44, "lon_max": 63.5}

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Known airport sets
IRAN_AIRPORTS = {'THR','IKA','MHD','ISF','TBZ','SYZ','KER','AWZ','BND','ABD',
                 'ZAH','RAS','KIH','BUZ','GBT','LRR','OMH','SDG','AZD','XBJ',
                 'BJB','CQD','IFN','KHD','NSH','PGU','SRY','TCX','YES'}
ISRAEL_AIRPORTS = {'TLV','SDV','VDA','ETH','BEV','RPN','HFA'}
IRAQ_AIRPORTS = {'BGW','BSR','EBL','NJF','SDA'}
SYRIA_AIRPORTS = {'DAM','ALP','LTK'}
LEBANON_AIRPORTS = {'BEY'}
JORDAN_AIRPORTS = {'AMM','AQJ'}

# US military callsign prefixes
US_MIL_CALLSIGNS = {
    # USAF strategic
    'RCH', 'REACH', 'EVAC', 'FORTE', 'JAKE', 'NCHO', 'LAGR',
    'DOOM', 'TOPCT', 'BOLT', 'IRON', 'LANCE', 'ORDER',
    # USAF tankers/ISR
    'ETHYL', 'SHELL', 'TEXAS', 'ARIEL', 'HOMER', 'SNOOP',
    # Air Force One / VIP
    'SAM', 'AF1', 'AF2', 'EXEC', 'VENUS',
    # US Navy
    'NAVY', 'CNV',
    # CENTCOM / special
    'EPIC', 'GHOST', 'BANZAI', 'HOUND', 'SNTRY',
}

# Israeli Air Force callsign prefixes
IAF_CALLSIGNS = {
    'IAF', 'ISF', 'ELAL',  # El Al sometimes used for mil charters
}

# US military aircraft types (only flag if callsign also matches US/IL patterns)
US_MIL_TYPES = {
    'C17', 'C17A', 'C5', 'C5M', 'KC135', 'KC10', 'KC46',
    'E3', 'E8', 'E6', 'P3', 'P8', 'P8A', 'RC135',
    'B52', 'B1', 'B2', 'F15', 'F16', 'F18', 'F22', 'F35',
    'RQ4', 'MQ9', 'C130', 'C130J', 'C30J', 'V22',
}

# Israeli military types
IAF_TYPES = {
    'F35', 'F15', 'F16', 'B762', 'B763',  # IAF tankers are 767s
    'C130', 'C130J', 'G550', 'GLEX',  # IAF SIGINT/EW
}

# Aircraft role descriptions (1-5 words)
AIRCRAFT_ROLES = {
    # Fighters / strike
    'F35':   'Stealth strike fighter',
    'F22':   'Air superiority stealth',
    'F15':   'Air superiority / strike',
    'F16':   'Multirole fighter',
    'F18':   'Carrier strike fighter',
    # Bombers
    'B52':   'Strategic bomber',
    'B1':    'Supersonic bomber',
    'B2':    'Stealth bomber',
    # Transport
    'C17':   'Strategic airlift',
    'C17A':  'Strategic airlift',
    'C5':    'Heavy airlift',
    'C5M':   'Heavy airlift',
    'C130':  'Tactical airlift',
    'C130J': 'Tactical airlift',
    'C30J':  'Tactical airlift',
    'V22':   'Tiltrotor transport',
    'IL76':  'Heavy cargo transport',
    'A400':  'Military transport',
    'C295':  'Light transport / patrol',
    # Tankers
    'KC135': 'Aerial refueling tanker',
    'KC10':  'Refueling / cargo tanker',
    'KC46':  'Aerial refueling tanker',
    'KC30':  'Aerial refueling tanker',
    # ISR / SIGINT / EW
    'E3':    'AWACS airborne radar',
    'E8':    'Ground surveillance JSTARS',
    'E6':    'Nuclear command relay',
    'RC135': 'SIGINT reconnaissance',
    'P3':    'Maritime patrol / ASW',
    'P8':    'Maritime patrol / ASW',
    'P8A':   'Maritime patrol / ASW',
    'RQ4':   'High-alt surveillance drone',
    'MQ9':   'Armed recon drone',
    'G550':  'SIGINT / early warning',
    'GLEX':  'SIGINT / EW platform',
    'GLF5':  'VIP / SIGINT platform',
    'GLF6':  'VIP / SIGINT platform',
    # VIP
    'B742':  'Air Force One / VIP',
    'B747':  'Air Force One / VIP',
    'VC25':  'Air Force One',
    'C32':   'VIP executive transport',
    'C40':   'VIP / logistics',
    # Israeli specific
    'B762':  'IAF aerial refueling',
    'B763':  'IAF aerial refueling',
}


def fetch_opensky():
    """Fetch all aircraft in Middle East from OpenSky (fallback)."""
    try:
        url = (f"https://opensky-network.org/api/states/all?"
               f"lamin={BBOX['lamin']}&lomin={BBOX['lomin']}"
               f"&lamax={BBOX['lamax']}&lomax={BBOX['lomax']}")
        req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaBot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("states", []) or [], "opensky_raw"
    except Exception as e:
        print(f"  ⚠️ OpenSky error: {e}", file=sys.stderr)
        return [], "error"


def fetch_fr24():
    """Fetch aircraft from FlightRadar24 public feed."""
    try:
        url = (f"https://data-cloud.flightradar24.com/zones/fcgi/feed.js?"
               f"faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1"
               f"&vehicles=0&estimated=0&maxage=14400&gliders=0&stats=0"
               f"&bounds={BBOX['lamax']},{BBOX['lamin']},{BBOX['lomin']},{BBOX['lomax']}")
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        aircraft = []
        for key, val in data.items():
            if not isinstance(val, list) or len(val) < 5:
                continue
            aircraft.append({
                "lat": val[1], "lon": val[2], "heading": val[3],
                "altitude": val[4], "speed": val[5],
                "type": (val[8] or "") if len(val) > 8 else "",
                "reg": (val[9] or "") if len(val) > 9 else "",
                "origin": (val[11] or "") if len(val) > 11 else "",
                "dest": (val[12] or "") if len(val) > 12 else "",
                "callsign": (val[16] or "") if len(val) > 16 else "",
                "airline": (val[18] or "") if len(val) > 18 else "",
            })
        return aircraft, "fr24"
    except Exception as e:
        print(f"  ⚠️ FR24 error: {e}", file=sys.stderr)
        return [], "error"


def fetch_aircraft():
    """Try FR24 first, fall back to OpenSky."""
    aircraft, src = fetch_fr24()
    if aircraft:
        print(f"  ✈️  Source: FlightRadar24 ({len(aircraft)} aircraft)", file=sys.stderr)
        return aircraft, src
    
    raw, _ = fetch_opensky()
    aircraft = []
    for s in raw:
        if not s or len(s) < 12 or s[5] is None or s[6] is None:
            continue
        aircraft.append({
            "lat": s[6], "lon": s[5], "heading": s[10],
            "altitude": s[7], "speed": s[9],
            "type": "", "reg": "", "origin": "", "dest": "",
            "callsign": (s[1] or "").strip(), "airline": "",
        })
    print(f"  ✈️  Source: OpenSky fallback ({len(aircraft)} aircraft)", file=sys.stderr)
    return aircraft, "opensky"


def analyze_traffic(aircraft):
    """Extract intel from aircraft data."""
    stats = {
        "total": 0, "over_iran": 0,
        "iran_flights": 0, "israel_flights": 0,
        "notable": [],  # military / interesting
        "top_origins": {}, "top_dests": {},
        "disrupted_airports": [],
        "airport_counts": {},
    }
    
    for a in aircraft:
        lat, lon = a["lat"], a["lon"]
        if lat is None or lon is None:
            continue
        stats["total"] += 1
        
        over_iran = (IRAN_BOUNDS["lat_min"] <= lat <= IRAN_BOUNDS["lat_max"] and
                     IRAN_BOUNDS["lon_min"] <= lon <= IRAN_BOUNDS["lon_max"])
        if over_iran:
            stats["over_iran"] += 1
        
        orig = a.get("origin", "").upper()
        dest = a.get("dest", "").upper()
        atype = a.get("type", "").upper()
        callsign = a.get("callsign", "").upper()
        
        if orig:
            stats["top_origins"][orig] = stats["top_origins"].get(orig, 0) + 1
        if dest:
            stats["top_dests"][dest] = stats["top_dests"].get(dest, 0) + 1
        
        # Count airport activity
        for apt in [orig, dest]:
            if apt:
                stats["airport_counts"][apt] = stats["airport_counts"].get(apt, 0) + 1
        
        # Iran/Israel flights
        if orig in IRAN_AIRPORTS or dest in IRAN_AIRPORTS:
            stats["iran_flights"] += 1
        if orig in ISRAEL_AIRPORTS or dest in ISRAEL_AIRPORTS:
            stats["israel_flights"] += 1
        
        # Notable aircraft — US or Israeli military only
        is_us_mil = (any(callsign.startswith(p) for p in US_MIL_CALLSIGNS) or
                     (atype in US_MIL_TYPES and callsign and
                      any(callsign.startswith(p) for p in US_MIL_CALLSIGNS)))
        is_iaf = any(callsign.startswith(p) for p in IAF_CALLSIGNS)
        
        # Also catch: US mil type with no airline (likely military)
        if not is_us_mil and atype in US_MIL_TYPES:
            airline = a.get("airline", "").upper()
            # No commercial airline = likely military
            if not airline or airline in ('', 'N/A'):
                # Check registration for US (N-prefix) or Israel (4X-prefix)
                reg = a.get("reg", "").upper()
                if reg.startswith("N") or not reg:
                    is_us_mil = True
                elif reg.startswith("4X"):
                    is_iaf = True
        
        if is_us_mil or is_iaf:
            tag = "US" if is_us_mil else "IL"
            role = AIRCRAFT_ROLES.get(atype, "Military")
            stats["notable"].append({
                "callsign": a.get("callsign", "?"),
                "type": a.get("type", "?"),
                "origin": orig, "dest": dest,
                "lat": lat, "lon": lon,
                "alt": a.get("altitude", 0),
                "tag": tag,
                "role": role,
            })
    
    # Check disrupted airports
    watched = {
        "Iran": IRAN_AIRPORTS, "Israel": ISRAEL_AIRPORTS,
        "Iraq": IRAQ_AIRPORTS, "Syria": SYRIA_AIRPORTS,
        "Lebanon": LEBANON_AIRPORTS, "Jordan": JORDAN_AIRPORTS,
    }
    for country, airports in watched.items():
        count = sum(stats["airport_counts"].get(a, 0) for a in airports)
        status = "CLOSED" if count == 0 else f"{count} flights"
        stats["disrupted_airports"].append((country, count, status))
    
    stats["disrupted_airports"].sort(key=lambda x: x[1])
    return stats


def load_borders():
    path = os.path.join(SKILL_DIR, "references", "borders.geojson")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def generate_map(aircraft, stats, borders_geo, output_path):
    """Generate flight map with side intel panel."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patheffects as pe
        from matplotlib.gridspec import GridSpec
    except ImportError:
        print("ERROR: matplotlib not installed", file=sys.stderr)
        sys.exit(1)

    fig = plt.figure(figsize=(16, 9), dpi=150)
    fig.patch.set_facecolor("#0d1117")
    
    gs = GridSpec(1, 2, width_ratios=[3, 1], wspace=0.02)
    ax_map = fig.add_subplot(gs[0])
    ax_info = fig.add_subplot(gs[1])
    
    # ── MAP PANEL ──
    ax_map.set_facecolor("#16213e")
    ax_map.set_xlim(BBOX["lomin"], BBOX["lomax"])
    ax_map.set_ylim(BBOX["lamin"], BBOX["lamax"])
    ax_map.set_aspect("equal")
    
    # Draw borders
    if borders_geo:
        for feature in borders_geo.get("features", []):
            geom = feature.get("geometry", {})
            name = feature.get("properties", {}).get("ADMIN", "")
            is_iran = name.lower() == "iran"
            
            def draw_poly(coords, is_ir=is_iran):
                for ring in coords:
                    xs = [p[0] for p in ring]
                    ys = [p[1] for p in ring]
                    if is_ir:
                        ax_map.fill(xs, ys, color="#2d1b1b", alpha=0.6, zorder=1)
                        ax_map.plot(xs, ys, color="#ff4444", lw=0.8, alpha=0.7, zorder=2)
                    else:
                        ax_map.fill(xs, ys, color="#1e2d45", alpha=0.4, zorder=1)
                        ax_map.plot(xs, ys, color="#4a6fa5", lw=0.4, alpha=0.5, zorder=2)
            
            if geom["type"] == "Polygon":
                draw_poly(geom["coordinates"])
            elif geom["type"] == "MultiPolygon":
                for poly in geom["coordinates"]:
                    draw_poly(poly)
    
    # Country labels
    labels = {
        "Iran": (53, 33), "Iraq": (43.5, 33), "Syria": (38.5, 35),
        "Saudi\nArabia": (45, 24), "Turkey": (35, 39.5),
        "Yemen": (47, 15.5), "Oman": (57, 21),
        "UAE": (54, 24), "Pakistan": (63, 28),
    }
    for name, (lon, lat) in labels.items():
        ax_map.text(lon, lat, name, fontsize=7, color="#667788",
                    ha="center", va="center", alpha=0.5, zorder=3)
    
    # Country highlight labels
    ax_map.text(53, 32, "IRAN", fontsize=11, ha="center", va="center", zorder=15,
                color="#ff4444", fontweight="bold", alpha=0.7,
                path_effects=[pe.withStroke(linewidth=2, foreground="#1a1a2e")])
    ax_map.text(35.2, 31.5, "ISRAEL", fontsize=8, ha="center", va="center", zorder=15,
                color="#4488ff", fontweight="bold", alpha=0.7,
                path_effects=[pe.withStroke(linewidth=2, foreground="#1a1a2e")])
    
    # Plot aircraft
    for a in aircraft:
        lat, lon = a["lat"], a["lon"]
        if lat is None or lon is None:
            continue
        heading = a["heading"]
        atype = a.get("type", "").upper()
        callsign = a.get("callsign", "").upper()
        
        over_iran = (IRAN_BOUNDS["lat_min"] <= lat <= IRAN_BOUNDS["lat_max"] and
                     IRAN_BOUNDS["lon_min"] <= lon <= IRAN_BOUNDS["lon_max"])
        
        # Check if US/IL military (match same logic as analyze_traffic)
        is_tracked = any(cs for cs in stats["notable"]
                         if abs(cs["lat"] - lat) < 0.01 and abs(cs["lon"] - lon) < 0.01)
        
        if is_tracked:
            color = "#00ff88"
            lw = 1.2
        elif over_iran:
            color = "#ff6644"
            lw = 0.9
        else:
            color = "#ffdd44"
            lw = 0.6
        
        if heading is not None:
            rad = math.radians(heading)
            dx = math.sin(rad) * 0.25
            dy = math.cos(rad) * 0.25
            ax_map.annotate("", xy=(lon + dx, lat + dy), xytext=(lon - dx, lat - dy),
                            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw),
                            zorder=10)
        else:
            ax_map.plot(lon, lat, ".", color=color, markersize=2, zorder=10)
    
    ax_map.tick_params(colors="#4a6fa5", labelsize=5)
    for spine in ax_map.spines.values():
        spine.set_color("#30363d")
    
    # ── INFO PANEL ──
    ax_info.set_facecolor("#0d1117")
    ax_info.set_xlim(0, 1)
    ax_info.set_ylim(0, 1)
    ax_info.axis("off")
    
    now = datetime.now(timezone.utc)
    y = 0.96
    gap = 0.028
    
    def txt(text, ypos, size=8, color="#c9d1d9", weight="normal", alpha=1.0):
        ax_info.text(0.05, ypos, text, fontsize=size, color=color,
                     fontweight=weight, alpha=alpha, va="top",
                     fontfamily="monospace", transform=ax_info.transAxes)
    
    # Header
    txt("FLIGHT INTEL", y, size=11, color="#ffffff", weight="bold"); y -= gap * 1.5
    txt(now.strftime("%Y-%m-%d %H:%M UTC"), y, size=7, color="#8b949e"); y -= gap * 1.8
    
    # Divider
    ax_info.axhline(y=y+0.005, xmin=0.05, xmax=0.95, color="#30363d", lw=0.5)
    y -= gap * 0.8
    
    # Traffic stats
    txt("TRAFFIC", y, size=9, color="#58a6ff", weight="bold"); y -= gap * 1.3
    txt(f"Total:     {stats['total']}", y, color="#c9d1d9"); y -= gap
    txt(f"Over Iran: {stats['over_iran']}", y, color="#ff6644"); y -= gap * 1.5
    
    # Airport disruption
    ax_info.axhline(y=y+0.005, xmin=0.05, xmax=0.95, color="#30363d", lw=0.5)
    y -= gap * 0.8
    txt("AIRPORT STATUS", y, size=9, color="#58a6ff", weight="bold"); y -= gap * 1.3
    
    for country, count, status in stats["disrupted_airports"]:
        if count == 0:
            icon = "[X]"
            col = "#ff4444"
        elif count < 5:
            icon = "[!]"
            col = "#d29922"
        else:
            icon = "[+]"
            col = "#3fb950"
        txt(f"{icon} {country}: {status}", y, color=col); y -= gap
    y -= gap * 0.5
    
    # Notable aircraft
    ax_info.axhline(y=y+0.005, xmin=0.05, xmax=0.95, color="#30363d", lw=0.5)
    y -= gap * 0.8
    txt("US / ISRAELI MILITARY", y, size=9, color="#58a6ff", weight="bold"); y -= gap * 1.3
    
    if stats["notable"]:
        for n in stats["notable"][:8]:
            cs = n["callsign"] or "?"
            at = n["type"] or "?"
            tag = n.get("tag", "?")
            role = n.get("role", "")
            route = ""
            if n["origin"] or n["dest"]:
                route = f" {n['origin']}->{n['dest']}"
            txt(f"[{tag}] {cs} ({at}){route}", y, size=7, color="#00ff88"); y -= gap
            if role:
                txt(f"     {role}", y, size=6, color="#8b949e"); y -= gap
    else:
        txt("No US/IL military detected", y, size=7, color="#8b949e"); y -= gap
    y -= gap * 0.5
    
    # Top routes
    ax_info.axhline(y=y+0.005, xmin=0.05, xmax=0.95, color="#30363d", lw=0.5)
    y -= gap * 0.8
    txt("TOP ORIGINS", y, size=9, color="#58a6ff", weight="bold"); y -= gap * 1.3
    
    top_orig = sorted(stats["top_origins"].items(), key=lambda x: -x[1])[:6]
    for apt, count in top_orig:
        txt(f"  {apt}: {count}", y, size=7, color="#8b949e"); y -= gap
    
    # Legend at bottom
    txt("Yellow=Civil  Red=Iran  Green=US/IL Military", 0.02, size=6, color="#8b949e", alpha=0.7)
    
    # Title
    fig.suptitle("MIDDLE EAST AIR TRAFFIC", fontsize=14, fontweight="bold",
                 color="#ffffff", fontfamily="monospace", y=0.98)
    fig.text(0.98, 0.98, "MagenYehudaBot", fontsize=7, color="#4a6fa5",
             ha="right", va="top", alpha=0.5, fontfamily="monospace")
    
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    print(f"  ✈️  Flight map: {stats['total']} aircraft, "
          f"{stats['over_iran']} over Iran, "
          f"{len(stats['notable'])} military", file=sys.stderr)
    return stats


def log_flight_snapshot(state_dir, stats, source):
    """Log structured flight data for historical stats and trends."""
    now = datetime.now(timezone.utc)
    ts = now.timestamp()
    
    # ── 1. Dedicated flight history log (state/flight-history.jsonl) ──
    flight_log = os.path.join(state_dir, "flight-history.jsonl")
    snapshot = {
        "ts": ts,
        "utc": now.isoformat(),
        "source": source,
        "total": stats["total"],
        "over_iran": stats["over_iran"],
        "iran_flights": stats["iran_flights"],
        "israel_flights": stats["israel_flights"],
        "airports": {
            country: {"count": count, "status": status}
            for country, count, status in stats["disrupted_airports"]
        },
        "military": [
            {
                "callsign": n["callsign"],
                "type": n["type"],
                "tag": n.get("tag", "?"),
                "role": n.get("role", ""),
                "origin": n["origin"],
                "dest": n["dest"],
                "lat": round(n["lat"], 2),
                "lon": round(n["lon"], 2),
                "alt": n.get("alt", 0),
            }
            for n in stats["notable"]
        ],
        "top_origins": dict(sorted(stats["top_origins"].items(),
                                   key=lambda x: -x[1])[:10]),
        "top_dests": dict(sorted(stats["top_dests"].items(),
                                 key=lambda x: -x[1])[:10]),
    }
    with open(flight_log, "a") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    
    # ── 2. Append to main intel log (state/intel-log.jsonl) ──
    intel_log = os.path.join(state_dir, "intel-log.jsonl")
    intel_event = {
        "type": "flight_scan",
        "logged_at": ts,
        "logged_utc": now.isoformat(),
        "data": {
            "total": stats["total"],
            "over_iran": stats["over_iran"],
            "iran_flights": stats["iran_flights"],
            "israel_flights": stats["israel_flights"],
            "military_count": len(stats["notable"]),
            "military_callsigns": [n["callsign"] for n in stats["notable"]],
            "airports_closed": [c for c, cnt, _ in stats["disrupted_airports"] if cnt == 0],
            "airports_limited": [f"{c}:{cnt}" for c, cnt, _ in stats["disrupted_airports"] if 0 < cnt < 5],
            "source": source,
        }
    }
    with open(intel_log, "a") as f:
        f.write(json.dumps(intel_event, ensure_ascii=False) + "\n")
    
    # ── 3. Rotate flight history (keep 7 days) ──
    rotate_flight_log(flight_log, max_days=7)
    
    print(f"  ✈️  Logged flight snapshot to {flight_log}", file=sys.stderr)


def rotate_flight_log(path, max_days=7):
    """Keep only entries from the last N days."""
    if not os.path.exists(path):
        return
    cutoff = time.time() - (max_days * 86400)
    kept = []
    with open(path) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("ts", 0) >= cutoff:
                    kept.append(line.strip())
            except (json.JSONDecodeError, KeyError):
                continue
    with open(path, "w") as f:
        for line in kept:
            f.write(line + "\n")


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 generate-flight-map.py <config.json> <state_dir> <output.png>",
              file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    output_path = sys.argv[3]
    
    print("  ✈️  Fetching air traffic data...", file=sys.stderr)
    aircraft, source = fetch_aircraft()
    print(f"  ✈️  Got {len(aircraft)} aircraft from {source}", file=sys.stderr)
    
    stats = analyze_traffic(aircraft)
    borders = load_borders()
    generate_map(aircraft, stats, borders, output_path)
    
    # Log structured data for historical trends
    log_flight_snapshot(state_dir, stats, source)
    
    result = {
        "total": stats["total"],
        "over_iran": stats["over_iran"],
        "iran_flights": stats["iran_flights"],
        "israel_flights": stats["israel_flights"],
        "military": len(stats["notable"]),
        "path": output_path,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
