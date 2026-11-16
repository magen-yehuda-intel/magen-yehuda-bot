#!/usr/bin/env python3
"""Convert classify-attack.py output to a RECENT_EVENTS-compatible live event.

Reads classification JSON from stdin, writes/appends to docs/live-events.json.
Called by realtime-watcher.sh after successful classification.

Usage: echo '{"source":"iran","weapon":"ballistic_missile",...}' | python3 write-live-event.py --oref-areas "Tel Aviv,Jerusalem"
"""

import json, sys, os, time, argparse
from datetime import datetime, timezone, timedelta

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
LIVE_EVENTS_PATH = os.path.join(DOCS_DIR, "live-events.json")
MAX_EVENTS = 20  # keep last 20 live events
IST = timezone(timedelta(hours=3))

# Source → origin coordinates (launch sites)
ORIGIN_COORDS = {
    "iran":    {"lat": 33.5,  "lon": 48.5,  "label": "Western Iran (Kermanshah/Lorestan)"},
    "yemen":   {"lat": 15.35, "lon": 44.2,  "label": "Sana'a, Yemen"},
    "lebanon": {"lat": 33.85, "lon": 35.86, "label": "Southern Lebanon"},
    "iraq":    {"lat": 33.3,  "lon": 44.4,  "label": "Baghdad area, Iraq"},
    "syria":   {"lat": 33.5,  "lon": 36.3,  "label": "Damascus area, Syria"},
    "gaza":    {"lat": 31.42, "lon": 34.35, "label": "Gaza Strip"},
}

# Direction → approximate target coordinates in Israel
TARGET_COORDS = {
    "center": {"lat": 32.085, "lon": 34.781, "label": "Tel Aviv metro"},
    "north":  {"lat": 32.794, "lon": 34.989, "label": "Haifa area"},
    "south":  {"lat": 31.252, "lon": 34.791, "label": "Beer Sheva area"},
    "east":   {"lat": 31.768, "lon": 35.214, "label": "Jerusalem area"},
    "multi":  {"lat": 32.085, "lon": 34.781, "label": "Multiple regions (Israel)"},
}

WEAPON_LABELS = {
    "ballistic_missile": "Ballistic missile",
    "cruise_missile": "Cruise missile",
    "rocket": "Rocket barrage",
    "uav_drone": "UAV/Drone attack",
    "mortar": "Mortar fire",
}


def build_event(classification, oref_areas=""):
    source = classification.get("source", "unknown")
    weapon = classification.get("weapon", "unknown")
    actor = classification.get("actor", classification.get("source", "Unknown"))
    direction = classification.get("direction", "center")
    confidence = classification.get("confidence", 0)
    reasoning = classification.get("reasoning", "")
    sub_type = classification.get("sub_type", "")

    if source == "unknown" or confidence < 0.3:
        return None

    origin = ORIGIN_COORDS.get(source)
    target = TARGET_COORDS.get(direction, TARGET_COORDS["center"])

    if not origin:
        return None

    now = datetime.now(IST)
    weapon_label = WEAPON_LABELS.get(weapon, weapon)
    desc = f"{weapon_label}"
    if sub_type:
        desc += f" ({sub_type})"
    desc += f" — {reasoning}" if reasoning else ""
    if oref_areas:
        areas_short = ", ".join(oref_areas.split(",")[:3])
        if len(oref_areas.split(",")) > 3:
            areas_short += f" +{len(oref_areas.split(',')) - 3} more"

    event = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "ts": int(time.time()),
        "lat": target["lat"],
        "lon": target["lon"],
        "type": "missile",
        "actor": actor,
        "target": oref_areas.split(",")[0] if oref_areas else target["label"],
        "desc": desc[:200],
        "severity": "critical" if confidence >= 0.7 else "high",
        "origin_lat": origin["lat"],
        "origin_lon": origin["lon"],
        "source_country": source,
        "weapon_type": weapon,
        "confidence": confidence,
        "live": True,  # flag to distinguish from static events
    }
    return event


def write_event(event):
    # Read existing
    events = []
    if os.path.exists(LIVE_EVENTS_PATH):
        try:
            with open(LIVE_EVENTS_PATH, "r") as f:
                data = json.load(f)
                events = data.get("events", [])
        except (json.JSONDecodeError, KeyError):
            events = []

    # Dedup: don't add if same source+weapon within 120s
    for e in events:
        if (e.get("source_country") == event["source_country"]
                and e.get("weapon_type") == event["weapon_type"]
                and abs(e.get("ts", 0) - event["ts"]) < 120):
            return False  # duplicate

    events.append(event)
    # Trim to max
    events = events[-MAX_EVENTS:]

    with open(LIVE_EVENTS_PATH, "w") as f:
        json.dump({"events": events, "updated": int(time.time())}, f, indent=2)

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--oref-areas", default="", help="Comma-separated Oref alert areas")
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit(1)

    try:
        classification = json.loads(raw)
    except json.JSONDecodeError:
        print("ERROR: invalid JSON input", file=sys.stderr)
        sys.exit(1)

    event = build_event(classification, args.oref_areas)
    if not event:
        print(json.dumps({"status": "skipped", "reason": "low confidence or unknown source"}))
        sys.exit(0)

    written = write_event(event)
    print(json.dumps({"status": "written" if written else "duplicate", "event": event}))
