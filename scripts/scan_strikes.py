#!/usr/bin/env python3
"""
scan_strikes.py — Strikes Map Data Aggregator

Collects geolocated strike events from multiple sources:
  1. ACLED API (Armed Conflict Location & Event Data Project) — structured conflict events
  2. Existing FIRMS fire detections near known military sites
  3. Existing USGS seismic events
  4. Strike correlation engine outputs
  5. OSINT intel log (location extraction from text)

Outputs: state/strikes-data.json — unified strike database for map generation

Usage:
    python3 scan_strikes.py <config.json> <state_dir> [--backfill]

Config fields (in config.json):
    strikes:
        acled_email: "user@example.com"
        acled_password: "password"        # OR use secrets/acled-creds.txt
        countries: ["Iran", "Israel", "Lebanon", "Syria", "Iraq", "Yemen"]
        event_types: ["Explosions/Remote violence", "Battles"]
        sub_event_types: ["Air/drone strike", "Shelling/artillery/missile attack", ...]
        start_date: "2023-10-07"          # War start date (default)
        window_days: null                  # If set, overrides start_date with rolling window
        max_events: 50000                  # API row limit per query
        poll_interval_hours: 6            # How often to fetch new ACLED data
        include_firms: true               # Overlay FIRMS fire data
        include_seismic: true             # Overlay USGS seismic data
        include_correlations: true        # Overlay strike correlations
        include_osint: true               # Extract locations from intel log
        min_fatalities: 0                 # Minimum fatalities filter (0 = all)
        actor_filter: []                  # Empty = all actors; or ["Israel", "Iran", ...]
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

# ═══════════════════════════════════════════════════════════
# CONFIGURATION DEFAULTS
# ═══════════════════════════════════════════════════════════

DEFAULTS = {
    "countries": [
        "Iran", "Israel", "Lebanon", "Syria", "Iraq", "Yemen",
        "Palestine", "Saudi Arabia", "Jordan", "Bahrain",
    ],
    "event_types": [
        "Explosions/Remote violence",
        "Battles",
        "Violence against civilians",
        "Strategic developments",
    ],
    "sub_event_types": [
        "Air/drone strike",
        "Shelling/artillery/missile attack",
        "Suicide bomb",
        "Remote explosive/landmine/IED",
        "Grenade",
        "Chemical weapon",
        "Armed clash",
        "Attack",
    ],
    "start_date": "2023-10-07",  # October 7 — war start
    "window_days": None,
    "max_events": 50000,
    "poll_interval_hours": 6,
    "include_firms": True,
    "include_seismic": True,
    "include_correlations": True,
    "include_osint": True,
    "min_fatalities": 0,
    "actor_filter": [],
}

# Known locations for geocoding OSINT text
KNOWN_LOCATIONS = {
    # Iran — nuclear/military sites
    "natanz": (33.72, 51.73), "isfahan": (32.65, 51.68), "esfahan": (32.65, 51.68),
    "bushehr": (28.97, 50.84), "parchin": (35.52, 51.77), "fordow": (34.88, 51.58),
    "arak": (34.09, 49.70), "bandar abbas": (27.19, 56.28), "chabahar": (25.29, 60.64),
    "tehran": (35.69, 51.39), "tabriz": (38.08, 46.29), "shiraz": (29.59, 52.58),
    "mashhad": (36.31, 59.60), "ahvaz": (31.32, 48.68), "abadan": (30.34, 48.30),
    "kharg island": (29.24, 50.33), "kish island": (26.53, 54.02),
    "qom": (34.64, 50.88), "semnan": (35.57, 53.39), "dezful": (32.38, 48.40),
    # Israel
    "tel aviv": (32.08, 34.78), "jerusalem": (31.77, 35.23), "haifa": (32.79, 34.99),
    "beer sheva": (31.25, 34.79), "be'er sheva": (31.25, 34.79), "eilat": (29.56, 34.95),
    "ashkelon": (31.67, 34.57), "ashdod": (31.80, 34.65), "rishon lezion": (31.96, 34.80),
    "netanya": (32.33, 34.86), "dimona": (31.07, 35.03), "negev": (30.85, 34.78),
    "golan heights": (33.00, 35.75), "nevatim": (31.21, 34.94),
    # Lebanon
    "beirut": (33.89, 35.50), "dahiyeh": (33.85, 35.49), "tyre": (33.27, 35.20),
    "sidon": (33.56, 35.37), "baalbek": (34.01, 36.21), "nabatieh": (33.38, 35.48),
    "south lebanon": (33.30, 35.30), "litani": (33.35, 35.30),
    # Syria
    "damascus": (33.51, 36.28), "aleppo": (36.20, 37.15), "homs": (34.73, 36.72),
    "latakia": (35.52, 35.78), "deir ez-zor": (35.34, 40.14), "raqqa": (35.95, 39.01),
    "tartus": (34.89, 35.89), "palmyra": (34.55, 38.28), "idlib": (35.93, 36.63),
    "daraa": (32.63, 36.10), "quneitra": (33.13, 35.82),
    # Iraq
    "baghdad": (33.31, 44.37), "erbil": (36.19, 44.01), "basra": (30.51, 47.78),
    "mosul": (36.34, 43.12), "kirkuk": (35.47, 44.39), "karbala": (32.62, 44.02),
    "al-asad": (33.78, 42.44), "ain al-asad": (33.78, 42.44),
    # Yemen
    "sanaa": (15.35, 44.21), "aden": (12.80, 45.02), "hodeidah": (14.80, 42.95),
    "marib": (15.46, 45.32), "taiz": (13.58, 44.02), "saada": (16.94, 43.76),
    # Red Sea / Gulf
    "strait of hormuz": (26.56, 56.25), "bab el-mandeb": (12.58, 43.33),
    "red sea": (20.00, 38.00), "gulf of oman": (24.50, 58.50),
    "persian gulf": (26.50, 52.00),
    # Gaza / West Bank
    "gaza": (31.50, 34.47), "gaza city": (31.52, 34.44), "rafah": (31.30, 34.25),
    "khan younis": (31.35, 34.30), "jabalia": (31.53, 34.48),
    "nablus": (32.22, 35.26), "jenin": (32.46, 35.30), "ramallah": (31.90, 35.20),
    "hebron": (31.53, 35.10), "tulkarm": (32.31, 35.03), "bethlehem": (31.70, 35.21),
}

# Actor normalization — map ACLED actor strings to display names
ACTOR_SIDES = {
    "Military Forces of Israel": {"name": "Israel (IDF)", "side": "israel", "emoji": "🇮🇱"},
    "Military Forces of Iran": {"name": "Iran (IRGC)", "side": "iran", "emoji": "🇮🇷"},
    "Hezbollah": {"name": "Hezbollah", "side": "iran_proxy", "emoji": "🟡"},
    "Hamas": {"name": "Hamas", "side": "iran_proxy", "emoji": "🟢"},
    "Houthis": {"name": "Houthis (Ansar Allah)", "side": "iran_proxy", "emoji": "🔴"},
    "Islamic Jihad": {"name": "Palestinian Islamic Jihad", "side": "iran_proxy", "emoji": "🟢"},
    "Military Forces of the United States": {"name": "USA (CENTCOM)", "side": "us", "emoji": "🇺🇸"},
    "Military Forces of Syria": {"name": "Syria (SAA)", "side": "syria", "emoji": "🇸🇾"},
    "Iraqi Resistance": {"name": "Iraqi Resistance", "side": "iran_proxy", "emoji": "🇮🇶"},
    "Kata'ib Hezbollah": {"name": "Kata'ib Hezbollah", "side": "iran_proxy", "emoji": "🇮🇶"},
    "Military Forces of Saudi Arabia": {"name": "Saudi Arabia", "side": "gulf", "emoji": "🇸🇦"},
    "Military Forces of Jordan": {"name": "Jordan", "side": "gulf", "emoji": "🇯🇴"},
}


# ═══════════════════════════════════════════════════════════
# ACLED API CLIENT
# ═══════════════════════════════════════════════════════════

class ACLEDClient:
    """ACLED API client with OAuth token management."""

    TOKEN_URL = "https://acleddata.com/oauth/token"
    API_BASE = "https://acleddata.com/api/acled/read"
    CLIENT_ID = "acled"

    def __init__(self, email, password, state_dir):
        self.email = email
        self.password = password
        self.state_dir = state_dir
        self.token_file = os.path.join(state_dir, "acled-token.json")
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
        self._load_token()

    def _load_token(self):
        """Load cached OAuth token if still valid."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file) as f:
                    data = json.load(f)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_expires = data.get("expires_at", 0)
            except Exception:
                pass

    def _save_token(self, token_data):
        """Save OAuth token to disk."""
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        self.token_expires = time.time() + token_data.get("expires_in", 86400) - 300  # 5min buffer
        with open(self.token_file, "w") as f:
            json.dump({
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.token_expires,
            }, f)

    def _request_token(self):
        """Get new OAuth token using credentials."""
        data = urllib.parse.urlencode({
            "username": self.email,
            "password": self.password,
            "grant_type": "password",
            "client_id": self.CLIENT_ID,
        }).encode()
        req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                token_data = json.loads(resp.read())
                self._save_token(token_data)
                print(f"  [ACLED] New token obtained, expires in {token_data.get('expires_in', '?')}s", file=sys.stderr)
                return True
        except Exception as e:
            print(f"  [ACLED] Token request failed: {e}", file=sys.stderr)
            return False

    def _refresh_access_token(self):
        """Refresh expired token."""
        if not self.refresh_token:
            return self._request_token()
        data = urllib.parse.urlencode({
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
        }).encode()
        req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                token_data = json.loads(resp.read())
                self._save_token(token_data)
                print(f"  [ACLED] Token refreshed", file=sys.stderr)
                return True
        except Exception:
            # Refresh failed, try full auth
            return self._request_token()

    def _ensure_token(self):
        """Ensure we have a valid token."""
        if self.access_token and time.time() < self.token_expires:
            return True
        if self.refresh_token:
            return self._refresh_access_token()
        return self._request_token()

    def fetch_events(self, countries, event_types, start_date, end_date=None,
                     max_events=50000, min_fatalities=0):
        """
        Fetch ACLED events for given countries and date range.
        Returns list of event dicts.
        """
        if not self._ensure_token():
            print("  [ACLED] Cannot authenticate — check credentials", file=sys.stderr)
            return []

        # Build query params
        country_str = "|".join(countries)
        event_type_str = "|".join(event_types)

        params = {
            "country": country_str,
            "event_type": event_type_str,
            "event_date": f"{start_date}|{end_date or datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "event_date_where": "BETWEEN",
            "limit": str(max_events),
        }

        if min_fatalities > 0:
            params["fatalities"] = str(min_fatalities)
            params["fatalities_where"] = ">"

        url = f"{self.API_BASE}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.access_token}")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                events = data.get("data", [])
                count = data.get("count", len(events))
                print(f"  [ACLED] Fetched {len(events)} events (total: {count})", file=sys.stderr)
                return events
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Token expired during request — retry once
                if self._request_token():
                    req.remove_header("Authorization")
                    req.add_header("Authorization", f"Bearer {self.access_token}")
                    try:
                        with urllib.request.urlopen(req, timeout=120) as resp:
                            data = json.loads(resp.read())
                            return data.get("data", [])
                    except Exception as e2:
                        print(f"  [ACLED] Retry failed: {e2}", file=sys.stderr)
            else:
                print(f"  [ACLED] API error {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"  [ACLED] Fetch error: {e}", file=sys.stderr)
            return []


# ═══════════════════════════════════════════════════════════
# STRIKE EVENT NORMALIZATION
# ═══════════════════════════════════════════════════════════

def normalize_acled_event(event):
    """Convert ACLED API event to our unified strike format."""
    lat = event.get("latitude")
    lon = event.get("longitude")
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None

    actor1 = event.get("actor1", "Unknown")
    actor2 = event.get("actor2", "")
    sub_event = event.get("sub_event_type", "")
    fatalities = int(event.get("fatalities", 0) or 0)

    # Classify actor sides
    actor1_info = None
    actor2_info = None
    for key, info in ACTOR_SIDES.items():
        if key.lower() in actor1.lower():
            actor1_info = info
        if actor2 and key.lower() in actor2.lower():
            actor2_info = info

    return {
        "source": "acled",
        "event_id": event.get("event_id_cnty", ""),
        "date": event.get("event_date", ""),
        "timestamp": event.get("timestamp", ""),
        "lat": lat,
        "lon": lon,
        "country": event.get("country", ""),
        "admin1": event.get("admin1", ""),
        "admin2": event.get("admin2", ""),
        "location": event.get("location", ""),
        "event_type": event.get("event_type", ""),
        "sub_event_type": sub_event,
        "actor1": actor1,
        "actor1_side": actor1_info["side"] if actor1_info else "unknown",
        "actor1_display": actor1_info["name"] if actor1_info else actor1[:40],
        "actor1_emoji": actor1_info["emoji"] if actor1_info else "⚪",
        "actor2": actor2,
        "actor2_side": actor2_info["side"] if actor2_info else "unknown",
        "actor2_display": actor2_info["name"] if actor2_info else (actor2[:40] if actor2 else ""),
        "fatalities": fatalities,
        "notes": event.get("notes", "")[:300],
        "sources": event.get("source", ""),
        "geo_precision": int(event.get("geo_precision", 3) or 3),
        "confidence": "high" if int(event.get("geo_precision", 3) or 3) <= 2 else "medium",
    }


def normalize_firms_event(fire):
    """Convert a FIRMS fire entry to strike format."""
    return {
        "source": "firms",
        "event_id": f"firms-{fire.get('latitude','')}-{fire.get('longitude','')}-{fire.get('acq_date','')}",
        "date": fire.get("acq_date", ""),
        "timestamp": "",
        "lat": float(fire.get("latitude", 0)),
        "lon": float(fire.get("longitude", 0)),
        "country": fire.get("country", ""),
        "admin1": "",
        "admin2": "",
        "location": fire.get("nearest_site", fire.get("location", "")),
        "event_type": "Thermal Anomaly",
        "sub_event_type": f"Satellite detection ({fire.get('satellite', 'FIRMS')})",
        "actor1": "Unknown",
        "actor1_side": "unknown",
        "actor1_display": "Satellite Detection",
        "actor1_emoji": "🛰️",
        "actor2": "",
        "actor2_side": "unknown",
        "actor2_display": fire.get("nearest_site", ""),
        "fatalities": 0,
        "notes": f"FRP: {fire.get('frp', '?')} MW, Confidence: {fire.get('confidence', '?')}",
        "sources": "NASA FIRMS",
        "geo_precision": 1,
        "confidence": "high" if float(fire.get("frp", 0) or 0) > 20 else "medium",
    }


def normalize_seismic_event(quake):
    """Convert a USGS seismic entry to strike format."""
    props = quake.get("properties", {})
    coords = quake.get("geometry", {}).get("coordinates", [0, 0, 0])
    return {
        "source": "usgs",
        "event_id": quake.get("id", f"usgs-{coords[1]}-{coords[0]}"),
        "date": datetime.fromtimestamp(props.get("time", 0) / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": str(props.get("time", "")),
        "lat": coords[1],
        "lon": coords[0],
        "country": "",
        "admin1": "",
        "admin2": "",
        "location": props.get("place", ""),
        "event_type": "Seismic Event",
        "sub_event_type": f"M{props.get('mag', '?')} Earthquake",
        "actor1": "Natural/Unknown",
        "actor1_side": "unknown",
        "actor1_display": "Seismic Event",
        "actor1_emoji": "🌍",
        "actor2": "",
        "actor2_side": "unknown",
        "actor2_display": "",
        "fatalities": 0,
        "notes": f"Magnitude {props.get('mag', '?')}, Depth {coords[2]}km",
        "sources": "USGS",
        "geo_precision": 2,
        "confidence": "medium",
    }


def normalize_correlation(corr):
    """Convert a strike correlation entry to strike format."""
    return {
        "source": "correlation",
        "event_id": f"corr-{corr.get('fire_lat','')}-{corr.get('fire_lon','')}-{corr.get('fire_time','')}",
        "date": corr.get("fire_time", "")[:10] if corr.get("fire_time") else "",
        "timestamp": "",
        "lat": float(corr.get("fire_lat", 0)),
        "lon": float(corr.get("fire_lon", 0)),
        "country": corr.get("country", ""),
        "admin1": "",
        "admin2": "",
        "location": corr.get("nearest_site", "Unknown"),
        "event_type": "Strike Correlation",
        "sub_event_type": f"Fire+Seismic ({corr.get('distance_km', '?')}km, {corr.get('time_diff_min', '?')}min)",
        "actor1": "Unknown",
        "actor1_side": "unknown",
        "actor1_display": "Correlated Strike",
        "actor1_emoji": "🎯",
        "actor2": "",
        "actor2_side": "unknown",
        "actor2_display": corr.get("nearest_site", ""),
        "fatalities": 0,
        "notes": f"Fire FRP {corr.get('frp', '?')}MW + M{corr.get('magnitude', '?')} seismic, {corr.get('distance_km', '?')}km apart, {corr.get('time_diff_min', '?')}min window",
        "sources": "FIRMS+USGS correlation",
        "geo_precision": 1,
        "confidence": "high",
    }


def extract_osint_locations(intel_log_path, start_date):
    """Extract geolocated events from intel-log.jsonl based on known location mentions."""
    events = []
    if not os.path.exists(intel_log_path):
        return events

    start_ts = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()

    with open(intel_log_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue

            logged_at = entry.get("logged_at", 0)
            if logged_at < start_ts:
                continue

            # Check alerts array
            alerts_list = entry.get("alerts", [])
            if isinstance(alerts_list, list):
                for alert in alerts_list:
                    text = (alert.get("text", "") or "").lower()
                    source = alert.get("channel", alert.get("source", "osint"))
                    link = alert.get("link", "")

                    for loc_name, (lat, lon) in KNOWN_LOCATIONS.items():
                        if loc_name in text:
                            # Check for strike-related keywords
                            strike_words = [
                                "strike", "attack", "bomb", "missile", "rocket",
                                "hit", "target", "blast", "explosion", "intercept",
                                "תקיפה", "טיל", "פגיעה", "הפצצה", "ירי", "פיצוץ",
                            ]
                            if any(w in text for w in strike_words):
                                events.append({
                                    "source": "osint",
                                    "event_id": f"osint-{loc_name}-{int(logged_at)}",
                                    "date": datetime.fromtimestamp(logged_at, tz=timezone.utc).strftime("%Y-%m-%d"),
                                    "timestamp": str(int(logged_at)),
                                    "lat": lat,
                                    "lon": lon,
                                    "country": "",
                                    "admin1": "",
                                    "admin2": "",
                                    "location": loc_name.title(),
                                    "event_type": "OSINT Report",
                                    "sub_event_type": "Location mention in OSINT",
                                    "actor1": "Unknown",
                                    "actor1_side": "unknown",
                                    "actor1_display": source,
                                    "actor1_emoji": "📡",
                                    "actor2": "",
                                    "actor2_side": "unknown",
                                    "actor2_display": "",
                                    "fatalities": 0,
                                    "notes": text[:200],
                                    "sources": source,
                                    "geo_precision": 3,
                                    "confidence": "low",
                                })
                                break  # One location per alert
    return events


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config.json> <state_dir> [--backfill]", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    backfill = "--backfill" in sys.argv

    with open(config_path) as f:
        config = json.load(f)

    strikes_cfg = config.get("strikes", {})
    cfg = {**DEFAULTS, **strikes_cfg}

    output_file = os.path.join(state_dir, "strikes-data.json")
    last_fetch_file = os.path.join(state_dir, "strikes-last-fetch.json")

    # Check poll interval
    if not backfill and os.path.exists(last_fetch_file):
        try:
            with open(last_fetch_file) as f:
                last = json.load(f)
            elapsed_hours = (time.time() - last.get("ts", 0)) / 3600
            if elapsed_hours < cfg["poll_interval_hours"]:
                print(f"  [strikes] Last fetch {elapsed_hours:.1f}h ago (interval: {cfg['poll_interval_hours']}h) — skipping", file=sys.stderr)
                sys.exit(0)
        except Exception:
            pass

    # Determine date range
    if cfg["window_days"]:
        start_date = (datetime.now(timezone.utc) - timedelta(days=cfg["window_days"])).strftime("%Y-%m-%d")
    else:
        start_date = cfg["start_date"]
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"  [strikes] Collecting events {start_date} → {end_date}", file=sys.stderr)

    all_events = []

    # ── Source 1: ACLED API ──
    acled_email = strikes_cfg.get("acled_email", "")
    acled_password = strikes_cfg.get("acled_password", "")

    # Try secrets file fallback
    if not acled_email or not acled_password:
        creds_file = os.path.join(os.path.dirname(config_path), "secrets", "acled-creds.txt")
        if os.path.exists(creds_file):
            with open(creds_file) as f:
                lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
                if len(lines) >= 2:
                    acled_email = lines[0]
                    acled_password = lines[1]

    if acled_email and acled_password:
        client = ACLEDClient(acled_email, acled_password, state_dir)
        raw_events = client.fetch_events(
            countries=cfg["countries"],
            event_types=cfg["event_types"],
            start_date=start_date,
            end_date=end_date,
            max_events=cfg["max_events"],
            min_fatalities=cfg["min_fatalities"],
        )
        for ev in raw_events:
            # Filter by sub_event_type if configured
            sub_type = ev.get("sub_event_type", "")
            if cfg["sub_event_types"] and sub_type not in cfg["sub_event_types"]:
                # Be more lenient — check if any configured sub_type is contained
                if not any(st.lower() in sub_type.lower() for st in cfg["sub_event_types"]):
                    continue

            # Filter by actor if configured
            if cfg["actor_filter"]:
                actor1 = ev.get("actor1", "").lower()
                actor2 = ev.get("actor2", "").lower()
                if not any(a.lower() in actor1 or a.lower() in actor2 for a in cfg["actor_filter"]):
                    continue

            normalized = normalize_acled_event(ev)
            if normalized:
                all_events.append(normalized)
        print(f"  [strikes] ACLED: {len([e for e in all_events if e['source'] == 'acled'])} events", file=sys.stderr)
    else:
        print("  [strikes] ACLED: skipped (no credentials configured)", file=sys.stderr)

    # ── Source 2: FIRMS fires ──
    if cfg["include_firms"]:
        firms_file = os.path.join(state_dir, "firms-seen.json")
        if os.path.exists(firms_file):
            try:
                with open(firms_file) as f:
                    firms_data = json.load(f)
                # firms-seen.json is {key: fire_data}
                for key, fire in firms_data.items():
                    if isinstance(fire, dict):
                        ev = normalize_firms_event(fire)
                        if ev and ev["date"] >= start_date:
                            all_events.append(ev)
                print(f"  [strikes] FIRMS: {len([e for e in all_events if e['source'] == 'firms'])} fires", file=sys.stderr)
            except Exception as e:
                print(f"  [strikes] FIRMS load error: {e}", file=sys.stderr)

    # ── Source 3: USGS seismic ──
    if cfg["include_seismic"]:
        seismic_file = os.path.join(state_dir, "seismic-seen.json")
        if os.path.exists(seismic_file):
            try:
                with open(seismic_file) as f:
                    seismic_data = json.load(f)
                for key, quake in seismic_data.items():
                    if isinstance(quake, dict):
                        ev = normalize_seismic_event(quake)
                        if ev and ev["date"] >= start_date:
                            all_events.append(ev)
                print(f"  [strikes] Seismic: {len([e for e in all_events if e['source'] == 'usgs'])} events", file=sys.stderr)
            except Exception as e:
                print(f"  [strikes] Seismic load error: {e}", file=sys.stderr)

    # ── Source 4: Strike correlations ──
    if cfg["include_correlations"]:
        corr_file = os.path.join(state_dir, "strike-correlations.json")
        if os.path.exists(corr_file):
            try:
                with open(corr_file) as f:
                    corr_data = json.load(f)
                if isinstance(corr_data, list):
                    for corr in corr_data:
                        ev = normalize_correlation(corr)
                        if ev:
                            all_events.append(ev)
                print(f"  [strikes] Correlations: {len([e for e in all_events if e['source'] == 'correlation'])} events", file=sys.stderr)
            except Exception as e:
                print(f"  [strikes] Correlations load error: {e}", file=sys.stderr)

    # ── Source 5: OSINT text extraction ──
    if cfg["include_osint"]:
        intel_log = os.path.join(state_dir, "intel-log.jsonl")
        osint_events = extract_osint_locations(intel_log, start_date)
        all_events.extend(osint_events)
        print(f"  [strikes] OSINT extraction: {len(osint_events)} geolocated mentions", file=sys.stderr)

    # Deduplicate by event_id
    seen_ids = set()
    unique_events = []
    for ev in all_events:
        eid = ev.get("event_id", "")
        if eid and eid not in seen_ids:
            seen_ids.add(eid)
            unique_events.append(ev)
        elif not eid:
            unique_events.append(ev)

    # Sort by date descending
    unique_events.sort(key=lambda e: e.get("date", ""), reverse=True)

    # Build summary stats
    stats = {
        "total": len(unique_events),
        "by_source": {},
        "by_country": {},
        "by_actor_side": {},
        "date_range": {"start": start_date, "end": end_date},
        "total_fatalities": sum(e.get("fatalities", 0) for e in unique_events),
    }
    for ev in unique_events:
        src = ev["source"]
        stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
        country = ev.get("country", "Unknown")
        stats["by_country"][country] = stats["by_country"].get(country, 0) + 1
        side = ev.get("actor1_side", "unknown")
        stats["by_actor_side"][side] = stats["by_actor_side"].get(side, 0) + 1

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "start_date": start_date,
            "end_date": end_date,
            "countries": cfg["countries"],
            "event_types": cfg["event_types"],
        },
        "stats": stats,
        "events": unique_events,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    # Update last fetch timestamp
    with open(last_fetch_file, "w") as f:
        json.dump({"ts": time.time(), "count": len(unique_events)}, f)

    print(f"  [strikes] Saved {len(unique_events)} events to {output_file}", file=sys.stderr)
    print(f"  [strikes] Stats: {json.dumps(stats, ensure_ascii=False)}", file=sys.stderr)

    # Output summary to stdout for watcher integration
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
