"""Magen Yehuda Intel API — Lightweight Flask backend
Polls Oref + FIRMS on background threads, serves cached data via HTTP.

Data sources:
  - Pikud HaOref alerts (via GitHub Pages export or direct API)
  - NASA FIRMS fire hotspots (direct API)

Deployment: Azure Container Apps (see deploy.sh)
"""

from flask import Flask, jsonify, request
import json, os, time, threading, logging, requests as rq
from datetime import datetime, timezone

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ═══════ IN-MEMORY CACHE ═══════
cache = {
    "oref": {"alerts": [], "alert_count": 0, "ts": 0},
    "fires": {"fires": [], "ts": 0},
    "intel": {"events": [], "ts": 0},
}

def cors_response(data, status=200):
    resp = jsonify(data)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
    resp.headers["Cache-Control"] = "no-cache"
    resp.status_code = status
    return resp

# ═══════ GET ENDPOINTS ═══════
@app.route("/api/oref", methods=["GET", "OPTIONS"])
def oref_get():
    if request.method == "OPTIONS":
        return cors_response({})
    c = cache["oref"]
    return cors_response({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "pikud-haoref",
        "cache_age_seconds": int(time.time() - c["ts"]) if c["ts"] > 0 else None,
        "alert_count": c["alert_count"],
        "alerts": c["alerts"],
    })

@app.route("/api/oref/history", methods=["GET", "OPTIONS"])
def oref_history():
    if request.method == "OPTIONS":
        return cors_response({})
    try:
        from db import query_oref_alerts, get_last_oref_alert
        hours = int(request.args.get("hours", 24))
        limit = min(int(request.args.get("limit", 50)), 500)
        alerts = query_oref_alerts(hours=hours, limit=limit)
        # Normalize for JSON
        for a in alerts:
            a.pop("PartitionKey", None)
            a.pop("RowKey", None)
            if "areas" in a and isinstance(a["areas"], str):
                try:
                    a["areas"] = __import__("json").loads(a["areas"])
                except:
                    pass
        return cors_response({"alerts": alerts, "count": len(alerts)})
    except Exception as e:
        return cors_response({"error": str(e), "alerts": []}, 500)

@app.route("/api/oref/last", methods=["GET", "OPTIONS"])
def oref_last():
    if request.method == "OPTIONS":
        return cors_response({})
    try:
        from db import get_last_oref_alert
        alert = get_last_oref_alert()
        if alert:
            alert.pop("PartitionKey", None)
            alert.pop("RowKey", None)
            if "areas" in alert and isinstance(alert["areas"], str):
                try:
                    alert["areas"] = __import__("json").loads(alert["areas"])
                except:
                    pass
        return cors_response({"alert": alert})
    except Exception as e:
        return cors_response({"error": str(e), "alert": None}, 500)

@app.route("/api/fires", methods=["GET", "OPTIONS"])
def fires_get():
    if request.method == "OPTIONS":
        return cors_response({})
    c = cache["fires"]
    return cors_response({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "nasa-firms",
        "cache_age_seconds": int(time.time() - c["ts"]) if c["ts"] > 0 else None,
        "fire_count": len(c["fires"]),
        "fires": c["fires"],
    })

@app.route("/api/intel-feed", methods=["GET", "OPTIONS"])
def intel_feed():
    if request.method == "OPTIONS":
        return cors_response({})

    hours = request.args.get("hours", 6, type=float)
    side = request.args.get("side", None)
    limit = request.args.get("limit", 500, type=int)

    # Primary: Azure Table Storage
    events = []
    source = "unknown"
    try:
        from db import query_events
        events = query_events(hours=hours, side=side, limit=limit)
        source = "azure-table"
        app.logger.info(f"DB query: {len(events)} events (hours={hours})")
    except Exception as e:
        app.logger.warning(f"DB query failed: {e}", exc_info=True)

    # Fallback: in-memory cache (Oref + FIRMS + pushed events)
    if not events:
        source = "cache-fallback"
        for a in cache["oref"]["alerts"]:
            events.append({
                "type": "siren", "source": "oref", "src": "oref",
                "text": a.get("data", a.get("title", "")),
                "location": a.get("data", ""), "ts": time.time(),
            })
        for f in cache["fires"]["fires"][:200]:
            events.append({
                "type": "fire", "source": "nasa-firms", "src": "nasa-firms",
                "lat": f.get("lat"), "lon": f.get("lon"),
                "confidence": f.get("confidence", ""), "ts": time.time(),
            })
        for e in cache["intel"].get("events", []):
            events.append(e)

    # Normalize field names for dashboard compatibility
    normalized = []
    for e in events:
        evt = dict(e)
        # Map DB field names → dashboard field names
        if "src" in evt and "source" not in evt:
            evt["source"] = evt["src"]
        if "ts" in evt and "timestamp" not in evt:
            evt["timestamp"] = evt["ts"]
        # Strip Azure Table internal fields
        evt.pop("PartitionKey", None)
        evt.pop("RowKey", None)
        normalized.append(evt)

    return cors_response({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_count": len(normalized), "events": normalized,
        "source": source,
    })

@app.route("/api/health", methods=["GET"])
def health():
    now = time.time()
    pollers = {}
    for name in ["oref", "fires", "seismic", "aircraft"]:
        ts = cache.get(name, {}).get("ts", 0)
        pollers[name] = {
            "age_s": int(now - ts) if ts > 0 else None,
            "healthy": ts > 0 and (now - ts) < 600,  # stale if >10min
        }
    # Watcher heartbeat (last push timestamp)
    watcher_ts = cache.get("_watcher_heartbeat", 0)
    watcher_age = int(now - watcher_ts) if watcher_ts > 0 else None
    return cors_response({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pollers": pollers,
        "watcher": {
            "last_push_age_s": watcher_age,
            "healthy": watcher_ts > 0 and (now - watcher_ts) < 600,
        },
        "caches": {
            "oref": {
                "age_s": pollers["oref"]["age_s"],
                "alerts": cache["oref"]["alert_count"],
            },
            "fires": {
                "age_s": pollers["fires"]["age_s"],
                "count": len(cache["fires"]["fires"]),
            },
        }
    })

@app.route("/")
def root():
    return cors_response({"service": "magen-yehuda-intel-api", "version": "2.0", "docs": "/api/health"})

# ═══════ PUSH ENDPOINTS (optional, for external pollers) ═══════
def check_push_auth():
    """Validate X-API-Key header against PUSH_API_KEY env var."""
    expected = os.environ.get("PUSH_API_KEY", "")
    if not expected:
        logging.warning("PUSH_API_KEY not configured — denying push request")
        return False
    if request.headers.get("X-API-Key", "") != expected:
        return False
    return True

@app.route("/api/push/oref", methods=["POST", "OPTIONS"])
def oref_push():
    if request.method == "OPTIONS":
        return cors_response({})
    if not check_push_auth():
        return cors_response({"error": "unauthorized"}, 403)
    cache["_watcher_heartbeat"] = time.time()
    try:
        data = request.get_json(force=True)
        alerts = data if isinstance(data, list) else data.get("alerts", data.get("data", []))
        ttl = data.get("ttl", 120) if isinstance(data, dict) else 120
        cache["oref"] = {"alerts": alerts, "alert_count": len(alerts), "ts": time.time(), "push_until": time.time() + ttl}
        if alerts:
            _persist_oref_alerts(alerts)
        return cors_response({"ok": True, "alert_count": len(alerts), "ttl": ttl})
    except Exception as ex:
        return cors_response({"error": str(ex)}, 400)

@app.route("/api/push/intel", methods=["POST", "OPTIONS"])
def intel_push():
    if request.method == "OPTIONS":
        return cors_response({})
    if not check_push_auth():
        return cors_response({"error": "unauthorized"}, 403)
    cache["_watcher_heartbeat"] = time.time()
    try:
        data = request.get_json(force=True)
        events = data.get("events", data if isinstance(data, list) else [])
        cache["intel"] = {"events": events, "ts": time.time()}
        return cors_response({"ok": True, "event_count": len(events)})
    except Exception as ex:
        return cors_response({"error": str(ex)}, 400)

@app.route("/api/push/threat", methods=["POST", "OPTIONS"])
def threat_push():
    """Push threat level from watcher. Persists in memory cache."""
    if request.method == "OPTIONS":
        return cors_response({})
    if not check_push_auth():
        return cors_response({"error": "unauthorized"}, 403)
    cache["_watcher_heartbeat"] = time.time()
    try:
        data = request.get_json(force=True)
        cache["threat"] = {
            "level": data.get("level", "GREEN"),
            "score": data.get("score", 0),
            "reason": data.get("reason", ""),
            "attack_class": data.get("attack_class", None),
            "ts": time.time(),
        }
        return cors_response({"ok": True, "level": cache["threat"]["level"]})
    except Exception as ex:
        return cors_response({"error": str(ex)}, 400)

@app.route("/api/threat", methods=["GET", "OPTIONS"])
def get_threat():
    """Get current threat level."""
    if request.method == "OPTIONS":
        return cors_response({})
    t = cache.get("threat", {"level": "UNKNOWN", "score": 0, "reason": "", "ts": 0})
    return cors_response(t)

# ═══════ BACKGROUND POLLERS ═══════

# Dedup: track last persisted alert ID to avoid re-inserting on every poll cycle
_last_persisted_oref_id = None

def _persist_oref_alerts(alerts):
    """Write Oref alerts to Azure Table Storage (best-effort, deduped by alert ID)."""
    global _last_persisted_oref_id
    try:
        # Dedup: skip if same alert batch (same first alert ID)
        first_id = alerts[0].get("id", "") if alerts else ""
        if first_id and first_id == _last_persisted_oref_id:
            return
        _last_persisted_oref_id = first_id

        from db import insert_oref_alert
        import time as _time
        for a in alerts:
            insert_oref_alert({
                "title": a.get("title", ""),
                "cat": a.get("cat", ""),
                "areas": a.get("data", []),
                "ts": _time.time(),
                "alert_id": a.get("id", ""),
            })
        logging.info(f"[db] Persisted {len(alerts)} Oref alerts to Azure Table")
    except Exception as e:
        logging.error(f"[db] Failed to persist Oref alerts: {e}")

def poll_oref():
    """Poll Oref alerts. Priority:
    1. Direct Oref API (works from some cloud regions, geo-blocked from others)
    2. GitHub Pages export (reliable fallback, ~30s latency)
    3. Push endpoint fills the gap if both fail
    """
    pages_url = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.oref.org.il/",
        "User-Agent": "Mozilla/5.0 (compatible; MagenYehudaIntel/2.0)",
    }
    consecutive_failures = 0

    while True:
        # If push endpoint is feeding fresh data, skip polling
        push_until = cache["oref"].get("push_until", 0)
        if push_until and time.time() < push_until:
            time.sleep(10)
            continue

        success = False

        # Strategy 1: Direct Oref API
        try:
            resp = rq.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                text = resp.text.lstrip('\ufeff').strip()
                alerts = []
                if text:
                    import json as _json
                    raw = _json.loads(text)
                    alerts = raw if isinstance(raw, list) else raw.get("data", [])
                cache["oref"] = {"alerts": alerts, "alert_count": len(alerts), "ts": time.time()}
                consecutive_failures = 0
                success = True
                if alerts:
                    logging.warning(f"🚨 OREF: {len(alerts)} active alerts!")
                    _persist_oref_alerts(alerts)
        except Exception:
            pass

        # Strategy 2: GitHub Pages export
        if not success and pages_url:
            try:
                resp = rq.get(f"{pages_url}/oref-alerts.json", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    alerts = data.get("alerts", [])
                    cache["oref"] = {"alerts": alerts, "alert_count": len(alerts), "ts": time.time()}
                    consecutive_failures = 0
                    success = True
                    if alerts:
                        logging.warning(f"🚨 OREF (pages): {len(alerts)} active alerts!")
                        _persist_oref_alerts(alerts)
            except Exception:
                pass

        if not success:
            consecutive_failures += 1
            if consecutive_failures <= 3:
                logging.error(f"Oref poll failed (attempt {consecutive_failures})")

        time.sleep(10 if success else min(60, 10 * consecutive_failures))

def poll_firms():
    """Poll NASA FIRMS for fire hotspots in the Middle East region (4 satellites, 2-day window)."""
    api_key = os.environ.get("FIRMS_MAP_KEY", "")
    satellites = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT", "MODIS_NRT"]
    bbox = "24,12,65,42"  # FIRMS format: W,S,E,N — full ME theater
    while True:
        if not api_key:
            time.sleep(300)
            continue
        try:
            all_fires = []
            seen = set()
            for sat in satellites:
                try:
                    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/{sat}/{bbox}/2"
                    resp = rq.get(url, timeout=20)
                    if resp.status_code == 200:
                        lines = resp.text.strip().split("\n")
                        if len(lines) >= 2:
                            hdr = lines[0].split(",")
                            lat_i = hdr.index("latitude") if "latitude" in hdr else 0
                            lon_i = hdr.index("longitude") if "longitude" in hdr else 1
                            conf_i = hdr.index("confidence") if "confidence" in hdr else -1
                            frp_i = hdr.index("frp") if "frp" in hdr else -1
                            time_i = hdr.index("acq_time") if "acq_time" in hdr else -1
                            date_i = hdr.index("acq_date") if "acq_date" in hdr else -1
                            for line in lines[1:]:
                                cols = line.split(",")
                                try:
                                    lat = round(float(cols[lat_i]), 3)
                                    lon = round(float(cols[lon_i]), 3)
                                    key = f"{lat},{lon}"
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    f = {"lat": lat, "lon": lon, "sat": sat.split("_")[1]}
                                    if conf_i >= 0: f["confidence"] = cols[conf_i]
                                    if frp_i >= 0:
                                        try: f["frp"] = float(cols[frp_i])
                                        except: pass
                                    if date_i >= 0 and time_i >= 0:
                                        f["acq"] = f"{cols[date_i]} {cols[time_i]}"
                                    all_fires.append(f)
                                except:
                                    pass
                except Exception as sx:
                    logging.warning(f"FIRMS {sat}: {sx}")
            cache["fires"] = {"fires": all_fires, "ts": time.time()}
            logging.info(f"FIRMS: {len(all_fires)} hotspots from {len(satellites)} satellites")
            # Persist significant fires to Azure Table (FRP>10, best-effort)
            try:
                from db import insert_fires_batch
                sig_fires = [f for f in all_fires if f.get("frp", 0) >= 10]
                if sig_fires:
                    ok, fail = insert_fires_batch(sig_fires)
                    if ok > 0: logging.info(f"FIRMS DB: {ok} stored, {fail} failed")
            except Exception as dbe:
                logging.error(f"FIRMS DB: {dbe}")
        except Exception as ex:
            logging.error(f"FIRMS: {ex}")
        time.sleep(300)

# ═══════ USGS SEISMIC POLLER ═══════
def poll_seismic():
    """Poll USGS for earthquakes in Middle East region (M2.5+)."""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=20&maxlatitude=42&minlongitude=24&maxlongitude=65&minmagnitude=2.5&orderby=time&limit=50"
    while True:
        try:
            resp = rq.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                quakes = []
                for f in data.get("features", []):
                    p = f.get("properties", {})
                    c = f.get("geometry", {}).get("coordinates", [0, 0, 0])
                    quakes.append({
                        "lat": c[1], "lon": c[0], "depth": c[2],
                        "mag": p.get("mag", 0), "place": p.get("place", ""),
                        "time": p.get("time", 0) / 1000,  # ms to s
                        "type": p.get("type", "earthquake"),
                        "url": p.get("url", ""),
                    })
                cache["seismic"] = {"quakes": quakes, "ts": time.time(), "count": len(quakes)}
                logging.info(f"USGS: {len(quakes)} earthquakes")
                # Persist to Azure Table (best-effort)
                try:
                    from db import insert_seismic_batch
                    ok, fail = insert_seismic_batch(quakes)
                    if ok > 0: logging.info(f"USGS DB: {ok} stored, {fail} failed")
                except Exception as dbe:
                    logging.error(f"USGS DB: {dbe}")
        except Exception as ex:
            logging.error(f"USGS: {ex}")
        time.sleep(120)  # every 2min

@app.route("/api/seismic", methods=["GET", "OPTIONS"])
def get_seismic():
    if request.method == "OPTIONS":
        return cors_response({})
    data = cache.get("seismic", {})
    return cors_response({
        "quakes": data.get("quakes", []),
        "count": data.get("count", 0),
        "ts": data.get("ts", 0),
    })

@app.route("/api/correlate", methods=["GET", "OPTIONS"])
def get_correlations():
    """Detect potential strikes by correlating seismic + fire + proximity to targets."""
    if request.method == "OPTIONS":
        return cors_response({})
    try:
        from db import correlate_strike_indicators
        hours = int(request.args.get("hours", 1))
        radius = int(request.args.get("radius_km", 50))
        results = correlate_strike_indicators(hours=hours, radius_km=radius)
        return cors_response({
            "correlations": results,
            "count": len(results),
            "params": {"hours": hours, "radius_km": radius},
        })
    except Exception as e:
        return cors_response({"error": str(e), "correlations": []}, 500)

@app.route("/api/seismic/history", methods=["GET", "OPTIONS"])
def seismic_history():
    if request.method == "OPTIONS":
        return cors_response({})
    try:
        from db import query_seismic
        hours = int(request.args.get("hours", 168))
        min_mag = float(request.args.get("min_mag", 2.5))
        limit = min(int(request.args.get("limit", 200)), 1000)
        quakes = query_seismic(hours=hours, min_mag=min_mag, limit=limit)
        for q in quakes:
            q.pop("PartitionKey", None); q.pop("RowKey", None)
        return cors_response({"quakes": quakes, "count": len(quakes)})
    except Exception as e:
        return cors_response({"error": str(e), "quakes": []}, 500)

@app.route("/api/fires/history", methods=["GET", "OPTIONS"])
def fires_history():
    if request.method == "OPTIONS":
        return cors_response({})
    try:
        from db import query_fires
        hours = int(request.args.get("hours", 24))
        min_frp = float(request.args.get("min_frp", 10))
        limit = min(int(request.args.get("limit", 2000)), 5000)
        fires = query_fires(hours=hours, min_frp=min_frp, limit=limit)
        for f in fires:
            f.pop("PartitionKey", None); f.pop("RowKey", None)
        return cors_response({"fires": fires, "count": len(fires)})
    except Exception as e:
        return cors_response({"error": str(e), "fires": []}, 500)

# Start pollers lazily (after first request, not on import)
_pollers_started = False

# ═══════ US/IL MILITARY DETECTION ═══════
US_MIL_CALLSIGNS = [
    'RCH', 'REACH', 'EVAC', 'FORTE', 'JAKE', 'NCHO', 'LAGR',
    'SAM', 'AF1', 'AF2', 'EXEC', 'NAVY', 'CNV', 'TOPCT',
    'ORDER', 'GOLD', 'TITAN', 'VIPER', 'HAWK', 'STORM',
    'QID', 'DUKE', 'SNTRY', 'DOOM', 'KNIFE', 'ANGRY',
    'WRATH', 'BOLT', 'RAID', 'HAVOC', 'OMNI', 'COBRA',
    'TEAL', 'NEON', 'IRIS', 'AERO',
]
IAF_CALLSIGNS = ['IAF', 'ISF']
US_MIL_TYPES = {
    'C17', 'C5M', 'C130', 'C130J', 'KC135', 'KC46', 'KC10',
    'E3TF', 'E3CF', 'E6B', 'E8C', 'RC135', 'EP3', 'P8',
    'B1B', 'B2', 'B52', 'F15', 'F16', 'F18', 'F22', 'F35',
    'V22', 'CV22', 'MV22', 'MQ9', 'RQ4', 'U2',
    'C40', 'C32', 'C37', 'C20', 'VC25',
}

def classify_aircraft(callsign, atype, reg):
    """Classify aircraft as military/civilian. Returns ('us_mil', 'il_mil', or None)."""
    cs = (callsign or '').upper().strip()
    at = (atype or '').upper().strip()
    rg = (reg or '').upper().strip()
    if any(cs.startswith(p) for p in US_MIL_CALLSIGNS):
        return 'us_mil'
    if any(cs.startswith(p) for p in IAF_CALLSIGNS):
        return 'il_mil'
    if rg.startswith('4X-') and at in {'F35', 'F15', 'F16', 'C130', 'C130J', 'G550', 'B762', 'B763'}:
        return 'il_mil'
    if at in US_MIL_TYPES and rg.startswith('N') and not cs:
        return 'us_mil'
    return None

def poll_aircraft():
    """Poll FR24 for aircraft in Middle East region."""
    bounds = "42,12,24,65"  # N,S,W,E covering ME theater
    url = f"https://data-cloud.flightradar24.com/zones/fcgi/feed.js?faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=0&estimated=0&maxage=14400&gliders=0&stats=0&bounds={bounds}"
    while True:
        try:
            resp = rq.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                aircraft = []
                military = []
                for k, v in data.items():
                    if not isinstance(v, list) or len(v) < 14:
                        continue
                    callsign = (v[16] if len(v) > 16 else "") or ""
                    atype = v[8] or ""
                    reg = v[9] or ""
                    ac = {
                        "lat": v[1], "lon": v[2], "heading": v[3],
                        "alt": v[4], "speed": v[5], "type": atype,
                        "reg": reg, "callsign": callsign.strip(),
                        "from": v[11] or "", "to": v[12] or "",
                    }
                    mil = classify_aircraft(callsign, atype, reg)
                    if mil:
                        ac["mil"] = mil
                        military.append(ac)
                    aircraft.append(ac)
                cache["aircraft"] = {
                    "all": aircraft, "military": military,
                    "ts": time.time(), "total": len(aircraft),
                    "mil_count": len(military),
                }
                logging.info(f"FR24: {len(aircraft)} aircraft, {len(military)} military")
        except Exception as ex:
            logging.error(f"FR24: {ex}")
        time.sleep(60)

@app.route("/api/aircraft", methods=["GET", "OPTIONS"])
def get_aircraft():
    """Get live aircraft. ?filter=military for military only."""
    if request.method == "OPTIONS":
        return cors_response({})
    ac = cache.get("aircraft", {})
    filt = request.args.get("filter", "")
    if filt == "military":
        return cors_response({
            "aircraft": ac.get("military", []),
            "count": ac.get("mil_count", 0),
            "total": ac.get("total", 0),
            "ts": ac.get("ts", 0),
            "source": "fr24",
        })
    return cors_response({
        "aircraft": ac.get("all", []),
        "count": ac.get("total", 0),
        "mil_count": ac.get("mil_count", 0),
        "ts": ac.get("ts", 0),
        "source": "fr24",
    })

@app.before_request
def start_pollers():
    global _pollers_started
    if not _pollers_started:
        _pollers_started = True
        threading.Thread(target=poll_oref, daemon=True).start()
        threading.Thread(target=poll_firms, daemon=True).start()
        threading.Thread(target=poll_aircraft, daemon=True).start()
        threading.Thread(target=poll_seismic, daemon=True).start()
        logging.info("Background pollers started")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
