#!/usr/bin/env python3
"""
Azure Table Storage client for intel events.
Dual-auth: DefaultAzureCredential (managed identity / az login) preferred,
falls back to connection string if AZURE_TABLE_CONN env var is set.

Table: intelevents
PartitionKey: date (YYYY-MM-DD)
RowKey: hash of (src + text + ts) for dedup
"""

import os
import hashlib
import json
import math
import time

TABLE_NAME = "intelevents"
OREF_TABLE_NAME = "orefalerts"
SEISMIC_TABLE_NAME = "seismicevents"
FIRE_TABLE_NAME = "fireevents"
ACCOUNT_URL = "https://magenyehudadata.table.core.windows.net"

_client = None
_oref_client = None
_seismic_client = None
_fire_client = None

def _get_client():
    global _client
    if _client:
        return _client

    conn_str = os.environ.get("AZURE_TABLE_CONN")
    if conn_str:
        from azure.data.tables import TableClient
        _client = TableClient.from_connection_string(conn_str, table_name=TABLE_NAME)
    else:
        from azure.data.tables import TableClient
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        _client = TableClient(endpoint=ACCOUNT_URL, table_name=TABLE_NAME, credential=cred)

    return _client


def _row_key(event):
    """Deterministic hash for dedup — ignores ts so re-scraped events don't duplicate."""
    raw = f"{event.get('src','')}{(event.get('text','') or '')[:60]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _partition_key(ts):
    """Date string from unix timestamp."""
    if not ts:
        return time.strftime("%Y-%m-%d")
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def insert_event(event):
    """Insert or upsert a single event. Returns True on success."""
    try:
        # Skip empty events
        if not (event.get("text", "") or "").strip() and not (event.get("src", "") or "").strip():
            return False
        client = _get_client()
        ts = event.get("ts") or event.get("timestamp") or time.time()

        entity = {
            "PartitionKey": _partition_key(ts),
            "RowKey": _row_key(event),
            "ts": float(ts),
            "src": event.get("src", ""),
            "text": (event.get("text", "") or "")[:4000],  # Table Storage limit ~32KB per prop
            "side": event.get("side", "unknown"),
            "type": event.get("type", ""),
            "sub_event_type": event.get("sub_event_type", ""),
            "lat": float(event.get("lat", 0)),
            "lon": float(event.get("lon", 0)),
            "location": event.get("location", event.get("loc", "")),
            "breaking": event.get("breaking", False),
            "confidence": event.get("confidence", ""),
            "link": event.get("link", ""),
            "raw_json": json.dumps(event)[:8000],  # full event as backup
        }
        client.upsert_entity(entity)
        return True
    except Exception as e:
        print(f"[db] insert_event error: {e}")
        return False


def insert_events(events):
    """Bulk insert. Returns (success_count, fail_count)."""
    ok, fail = 0, 0
    for e in events:
        if insert_event(e):
            ok += 1
        else:
            fail += 1
    return ok, fail


def query_events(hours=6, side=None, event_type=None, limit=500):
    """Query recent events from Azure Table Storage."""
    try:
        client = _get_client()
        cutoff = time.time() - (hours * 3600)
        cutoff_date = time.strftime("%Y-%m-%d", time.gmtime(cutoff))

        # PartitionKey filter for relevant dates
        filter_str = f"PartitionKey ge '{cutoff_date}'"
        if side:
            filter_str += f" and side eq '{side}'"
        if event_type:
            filter_str += f" and type eq '{event_type}'"

        entities = []
        for entity in client.query_entities(
            query_filter=filter_str,
            select=["PartitionKey", "RowKey", "ts", "src", "text", "side", "type",
                    "sub_event_type", "lat", "lon", "location", "breaking", "confidence"],
        ):
            if entity.get("ts", 0) >= cutoff:
                entities.append(entity)
            if len(entities) >= limit:
                break

        # Sort by ts descending
        entities.sort(key=lambda x: x.get("ts", 0), reverse=True)
        return entities

    except Exception as e:
        print(f"[db] query_events error: {e}")
        return []


def count_events(hours=24):
    """Quick count of events in time range."""
    try:
        events = query_events(hours=hours, limit=10000)
        return len(events)
    except:
        return -1


def get_latest_ts():
    """Get timestamp of newest event."""
    try:
        events = query_events(hours=1, limit=1)
        return events[0]["ts"] if events else 0
    except:
        return 0


# ═══════════════════════════════════════════════════════════
# OREF ALERTS TABLE
# ═══════════════════════════════════════════════════════════

def _get_oref_client():
    global _oref_client
    if _oref_client:
        return _oref_client
    from azure.data.tables import TableClient
    conn_str = os.environ.get("AZURE_TABLE_CONN")
    if conn_str:
        _oref_client = TableClient.from_connection_string(conn_str, table_name=OREF_TABLE_NAME)
    else:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        _oref_client = TableClient(endpoint=ACCOUNT_URL, table_name=OREF_TABLE_NAME, credential=cred)
    return _oref_client


def _oref_row_key(alert):
    """Deterministic hash for oref alert dedup: title + first 5 areas + cat."""
    areas = alert.get("areas", alert.get("data", []))
    area_str = ",".join(sorted(areas[:5])) if isinstance(areas, list) else str(areas)[:100]
    raw = f"{alert.get('title','')}{alert.get('cat','')}{area_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def insert_oref_alert(alert):
    """Insert a Pikud HaOref alert. Returns True on success.

    Expected fields:
        title: str - alert type (e.g. "ירי רקטות וטילים")
        cat: int/str - alert category
        areas: list[str] - affected areas
        ts: float - unix timestamp of alert
        cleared_ts: float - when alert cleared (optional, update later)
        duration_s: int - seconds alert was active (optional)
    """
    try:
        ts = alert.get("ts") or time.time()
        areas = alert.get("areas", alert.get("data", []))
        if isinstance(areas, str):
            areas = [areas]

        entity = {
            "PartitionKey": _partition_key(ts),
            "RowKey": _oref_row_key(alert),
            "ts": float(ts),
            "title": alert.get("title", ""),
            "cat": str(alert.get("cat", "")),
            "area_count": len(areas),
            "areas": json.dumps(areas, ensure_ascii=False)[:32000],
            "cleared_ts": float(alert.get("cleared_ts", 0)),
            "duration_s": int(alert.get("duration_s", 0)),
        }
        _get_oref_client().upsert_entity(entity)
        return True
    except Exception as e:
        print(f"[db] insert_oref_alert error: {e}")
        return False


def update_oref_cleared(alert, cleared_ts=None):
    """Update an alert with cleared timestamp and duration."""
    try:
        ts = alert.get("ts") or time.time()
        cleared = cleared_ts or time.time()
        pk = _partition_key(ts)
        rk = _oref_row_key(alert)
        client = _get_oref_client()
        entity = client.get_entity(pk, rk)
        entity["cleared_ts"] = float(cleared)
        entity["duration_s"] = int(cleared - entity.get("ts", cleared))
        client.upsert_entity(entity)
        return True
    except Exception as e:
        print(f"[db] update_oref_cleared error: {e}")
        return False


def query_oref_alerts(hours=24, limit=100):
    """Query recent Oref alerts."""
    try:
        client = _get_oref_client()
        cutoff = time.time() - (hours * 3600)
        cutoff_date = time.strftime("%Y-%m-%d", time.gmtime(cutoff))

        entities = []
        for entity in client.query_entities(
            query_filter=f"PartitionKey ge '{cutoff_date}'",
            select=["PartitionKey", "RowKey", "ts", "title", "cat", "area_count",
                    "areas", "cleared_ts", "duration_s"],
        ):
            if entity.get("ts", 0) >= cutoff:
                entities.append(entity)

        entities.sort(key=lambda x: x.get("ts", 0), reverse=True)
        return entities[:limit]
    except Exception as e:
        print(f"[db] query_oref_alerts error: {e}")
        return []


def get_last_oref_alert():
    """Get the most recent Oref alert."""
    alerts = query_oref_alerts(hours=48, limit=1)
    return alerts[0] if alerts else None


# ═══════════════════════════════════════════════════════════
# SEISMIC EVENTS TABLE
# ═══════════════════════════════════════════════════════════

def _get_seismic_client():
    global _seismic_client
    if _seismic_client:
        return _seismic_client
    from azure.data.tables import TableClient
    conn_str = os.environ.get("AZURE_TABLE_CONN")
    if conn_str:
        _seismic_client = TableClient.from_connection_string(conn_str, table_name=SEISMIC_TABLE_NAME)
    else:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        _seismic_client = TableClient(endpoint=ACCOUNT_URL, table_name=SEISMIC_TABLE_NAME, credential=cred)
    return _seismic_client


def insert_seismic(quake):
    """Insert a seismic event. Dedup by USGS event ID or lat+lon+mag+time."""
    try:
        ts = quake.get("time") or time.time()
        event_id = quake.get("id", "")
        if event_id:
            rk = hashlib.sha256(event_id.encode()).hexdigest()[:32]
        else:
            raw = f"{quake.get('lat',0):.3f}{quake.get('lon',0):.3f}{quake.get('mag',0):.1f}{int(ts)}"
            rk = hashlib.sha256(raw.encode()).hexdigest()[:32]

        entity = {
            "PartitionKey": _partition_key(ts),
            "RowKey": rk,
            "ts": float(ts),
            "lat": float(quake.get("lat", 0)),
            "lon": float(quake.get("lon", 0)),
            "depth": float(quake.get("depth", 0)),
            "mag": float(quake.get("mag", 0)),
            "place": quake.get("place", "")[:500],
            "type": quake.get("type", "earthquake"),
            "url": quake.get("url", ""),
            "near_nuclear": quake.get("near_nuclear", ""),
            "near_nuclear_dist_km": float(quake.get("near_nuclear_dist_km", 0)),
        }
        _get_seismic_client().upsert_entity(entity)
        return True
    except Exception as e:
        print(f"[db] insert_seismic error: {e}")
        return False


def insert_seismic_batch(quakes):
    ok, fail = 0, 0
    for q in quakes:
        if insert_seismic(q):
            ok += 1
        else:
            fail += 1
    return ok, fail


def query_seismic(hours=168, min_mag=2.5, limit=200):
    """Query recent seismic events. Default 7 days."""
    try:
        client = _get_seismic_client()
        cutoff = time.time() - (hours * 3600)
        cutoff_date = time.strftime("%Y-%m-%d", time.gmtime(cutoff))
        entities = []
        for entity in client.query_entities(
            query_filter=f"PartitionKey ge '{cutoff_date}'",
            select=["ts", "lat", "lon", "depth", "mag", "place", "type", "url", "near_nuclear", "near_nuclear_dist_km"],
        ):
            if entity.get("ts", 0) >= cutoff and entity.get("mag", 0) >= min_mag:
                entities.append(entity)
        entities.sort(key=lambda x: x.get("ts", 0), reverse=True)
        return entities[:limit]
    except Exception as e:
        print(f"[db] query_seismic error: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# FIRE EVENTS TABLE
# ═══════════════════════════════════════════════════════════

def _get_fire_client():
    global _fire_client
    if _fire_client:
        return _fire_client
    from azure.data.tables import TableClient
    conn_str = os.environ.get("AZURE_TABLE_CONN")
    if conn_str:
        _fire_client = TableClient.from_connection_string(conn_str, table_name=FIRE_TABLE_NAME)
    else:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        _fire_client = TableClient(endpoint=ACCOUNT_URL, table_name=FIRE_TABLE_NAME, credential=cred)
    return _fire_client


def insert_fire(fire):
    """Insert a FIRMS fire hotspot. Dedup by lat+lon+acq_time+satellite."""
    try:
        ts = fire.get("ts") or fire.get("time") or time.time()
        raw = f"{fire.get('lat',0):.4f}{fire.get('lon',0):.4f}{fire.get('satellite','')}{int(ts)}"
        rk = hashlib.sha256(raw.encode()).hexdigest()[:32]

        entity = {
            "PartitionKey": _partition_key(ts),
            "RowKey": rk,
            "ts": float(ts),
            "lat": float(fire.get("lat", 0)),
            "lon": float(fire.get("lon", 0)),
            "frp": float(fire.get("frp", 0)),
            "confidence": str(fire.get("confidence", "")),
            "satellite": fire.get("satellite", ""),
            "country": fire.get("country", ""),
            "acq_time": fire.get("acq_time", ""),
            "bright": float(fire.get("bright", fire.get("brightness", 0))),
        }
        _get_fire_client().upsert_entity(entity)
        return True
    except Exception as e:
        print(f"[db] insert_fire error: {e}")
        return False


def insert_fires_batch(fires):
    ok, fail = 0, 0
    for f in fires:
        if insert_fire(f):
            ok += 1
        else:
            fail += 1
    return ok, fail


def query_fires(hours=24, min_frp=10, limit=2000):
    """Query recent fire hotspots."""
    try:
        client = _get_fire_client()
        cutoff = time.time() - (hours * 3600)
        cutoff_date = time.strftime("%Y-%m-%d", time.gmtime(cutoff))
        entities = []
        for entity in client.query_entities(
            query_filter=f"PartitionKey ge '{cutoff_date}'",
            select=["ts", "lat", "lon", "frp", "confidence", "satellite", "country", "acq_time", "bright"],
        ):
            if entity.get("ts", 0) >= cutoff and entity.get("frp", 0) >= min_frp:
                entities.append(entity)
        entities.sort(key=lambda x: x.get("ts", 0), reverse=True)
        return entities[:limit]
    except Exception as e:
        print(f"[db] query_fires error: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# STRIKE CORRELATION ENGINE
# Detects potential strikes by correlating seismic + fire + OSINT
# ═══════════════════════════════════════════════════════════

def correlate_strike_indicators(hours=1, radius_km=50):
    """Find seismic events near fire hotspots (potential strike indicators).

    Logic: If a seismic event (M2.0+) occurs within radius_km of a fire
    hotspot (FRP>10MW) within the same time window, flag as potential strike.
    Also checks proximity to nuclear/military sites.

    Returns list of correlation objects.
    """
    try:

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        # Known targets of interest
        TARGETS = {
            "Natanz": (33.724, 51.727), "Isfahan": (32.654, 51.676),
            "Fordow": (34.883, 51.984), "Bushehr": (28.831, 50.886),
            "Arak": (34.382, 49.244), "Parchin": (35.517, 51.771),
            "Isfahan Missile Fac": (32.600, 51.750),
            "Kharg Island": (29.234, 50.329), "Bandar Abbas": (27.179, 56.272),
            "Tehran": (35.689, 51.389), "Shiraz Air Base": (29.539, 52.589),
        }

        quakes = query_seismic(hours=hours, min_mag=2.0, limit=100)
        fires = query_fires(hours=hours, min_frp=10, limit=2000)

        if not quakes and not fires:
            return []

        correlations = []
        for q in quakes:
            q_lat, q_lon = q.get("lat", 0), q.get("lon", 0)
            nearby_fires = []
            for f in fires:
                dist = haversine(q_lat, q_lon, f.get("lat", 0), f.get("lon", 0))
                if dist <= radius_km:
                    nearby_fires.append({"fire": f, "distance_km": round(dist, 1)})

            nearest_target = None
            nearest_dist = 999999
            for name, (tlat, tlon) in TARGETS.items():
                d = haversine(q_lat, q_lon, tlat, tlon)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_target = name

            if nearby_fires or nearest_dist <= 80:
                correlations.append({
                    "type": "strike_indicator",
                    "quake": {
                        "mag": q.get("mag", 0), "place": q.get("place", ""),
                        "lat": q_lat, "lon": q_lon, "depth": q.get("depth", 0),
                        "time": q.get("ts", 0),
                    },
                    "nearby_fires": len(nearby_fires),
                    "fire_details": nearby_fires[:5],
                    "nearest_target": nearest_target,
                    "target_distance_km": round(nearest_dist, 1),
                    "confidence": "HIGH" if nearby_fires and nearest_dist <= 50 else
                                  "MEDIUM" if nearby_fires or nearest_dist <= 30 else "LOW",
                    "ts": q.get("ts", 0),
                })

        correlations.sort(key=lambda x: x.get("ts", 0), reverse=True)
        return correlations
    except Exception as e:
        print(f"[db] correlate_strike_indicators error: {e}")
        return []


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing Azure Table Storage connection...")
        test_event = {
            "ts": time.time(),
            "src": "test",
            "text": "Connection test event",
            "side": "unknown",
            "type": "test",
            "lat": 0, "lon": 0,
        }
        ok = insert_event(test_event)
        print(f"Insert: {'OK' if ok else 'FAIL'}")

        events = query_events(hours=1)
        print(f"Query (1h): {len(events)} events")
        for e in events[:3]:
            print(f"  {e['src']}: {e['text'][:60]}")

    elif len(sys.argv) > 1 and sys.argv[1] == "backfill":
        # Backfill from existing intel-log.jsonl
        log_path = os.path.join(os.path.dirname(__file__), "..", "state", "intel-log.jsonl")
        if not os.path.exists(log_path):
            print(f"No log file: {log_path}")
            sys.exit(1)

        events = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    if e.get("ts") and e.get("text"):
                        events.append(e)
                except:
                    pass

        print(f"Backfilling {len(events)} events...")
        ok, fail = insert_events(events)
        print(f"Done: {ok} inserted, {fail} failed")

    else:
        print("Usage: python3 db.py [test|backfill]")
        events = query_events(hours=6)
        print(f"Last 6h: {len(events)} events")
