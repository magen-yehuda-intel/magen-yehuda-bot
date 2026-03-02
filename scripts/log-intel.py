#!/usr/bin/env python3
"""
Intel logger — appends structured intel events to a JSONL file.
Each line = one event. Used by the watcher to save ALL intel for hourly summaries.

Usage:
    echo '{"type":"siren","data":{...}}' | python3 log-intel.py <state_dir>
    python3 log-intel.py <state_dir> --read [--since <hours>] [--type <type>]
"""

import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta

def get_log_path(state_dir):
    return os.path.join(state_dir, "intel-log.jsonl")

def append_event(state_dir, event):
    """Append a structured event to the intel log + Azure Table Storage."""
    path = get_log_path(state_dir)
    event["logged_at"] = time.time()
    event["logged_utc"] = datetime.now(timezone.utc).isoformat()
    # File backup (always)
    with open(path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    # DB write (best-effort, never blocks)
    try:
        from db import insert_event as db_insert
        # Batch events (osint/rss/telegram) contain alerts[] — extract individual events
        alerts = event.get("alerts", [])
        if alerts:
            for alert in alerts:
                db_event = {
                    "src": alert.get("channel", alert.get("source", "")),
                    "text": alert.get("text", ""),
                    "ts": _parse_alert_ts(alert),
                    "type": event.get("type", "osint"),
                    "side": alert.get("side", "unknown"),
                    "breaking": alert.get("breaking", False),
                    "breaking_topic": alert.get("breaking_topic", ""),
                    "lat": alert.get("lat", 0),
                    "lon": alert.get("lon", 0),
                    "location": alert.get("location", ""),
                    "link": alert.get("link", ""),
                }
                db_insert(db_event)
        else:
            # Single event (siren, threat_change, etc.)
            db_insert(event)
    except Exception:
        pass  # DB is optional; file is the backup


def _parse_alert_ts(alert):
    """Extract timestamp from an OSINT alert, fallback to now."""
    t = alert.get("ts") or alert.get("timestamp")
    if t:
        return float(t) if isinstance(t, (int, float)) else time.time()
    # Try parsing RSS-style time string
    time_str = alert.get("time", "")
    if time_str:
        # Strip CDATA wrappers from RSS feeds (e.g. Ynet: <![CDATA[Mon, 02 Mar 2026 02:23:15 +0200]]>)
        import re
        time_str = re.sub(r'<!\[CDATA\[|\]\]>', '', time_str).strip()
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(time_str)
            ts = dt.timestamp()
            # Sanity: reject timestamps more than 10 min in the future
            if ts > time.time() + 600:
                return time.time()
            return ts
        except Exception:
            pass
    return time.time()

def read_events(state_dir, since_hours=1, event_type=None):
    """Read events from the log, filtered by time and type."""
    path = get_log_path(state_dir)
    if not os.path.exists(path):
        return []
    
    cutoff = time.time() - (since_hours * 3600)
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("logged_at", 0) >= cutoff:
                    if event_type is None or event.get("type") == event_type:
                        events.append(event)
            except json.JSONDecodeError:
                continue
    return events

def rotate_log(state_dir, max_hours=48):
    """Remove entries older than max_hours."""
    path = get_log_path(state_dir)
    if not os.path.exists(path):
        return
    cutoff = time.time() - (max_hours * 3600)
    kept = []
    with open(path) as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if event.get("logged_at", 0) >= cutoff:
                    kept.append(line.strip())
            except:
                continue
    with open(path, "w") as f:
        for line in kept:
            f.write(line + "\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 log-intel.py <state_dir> [--read] [--since N] [--type TYPE]", file=sys.stderr)
        sys.exit(1)
    
    state_dir = sys.argv[1]
    os.makedirs(state_dir, exist_ok=True)
    
    if "--read" in sys.argv:
        since = 1
        etype = None
        for i, arg in enumerate(sys.argv):
            if arg == "--since" and i+1 < len(sys.argv):
                since = float(sys.argv[i+1])
            if arg == "--type" and i+1 < len(sys.argv):
                etype = sys.argv[i+1]
        events = read_events(state_dir, since, etype)
        print(json.dumps(events, ensure_ascii=False, indent=2))
    elif "--rotate" in sys.argv:
        rotate_log(state_dir)
        print("Rotated", file=sys.stderr)
    else:
        # Read event from stdin
        data = sys.stdin.read().strip()
        if data:
            try:
                event = json.loads(data)
                append_event(state_dir, event)
            except json.JSONDecodeError:
                # Plain text — wrap it
                append_event(state_dir, {"type": "raw", "text": data})

if __name__ == "__main__":
    main()
