#!/bin/bash
# Iran-Israel Attack Alert Monitor v3 — Structured JSON output
# Multi-source intelligence check with timestamps, state tracking & threat scoring

set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
CONFIG_FILE="$SKILL_DIR/config.json"
STATE_FILE="$SKILL_DIR/state/last-check.json"
HISTORY_DIR="$SKILL_DIR/state/history"
mkdir -p "$SKILL_DIR/state" "$HISTORY_DIR"

# Load timezone from config (default: Asia/Jerusalem)
DISPLAY_TZ=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('timezone','Asia/Jerusalem'))" 2>/dev/null || echo "Asia/Jerusalem")
TG_CHAT_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('telegram_chat_id',''))" 2>/dev/null || echo "")
TG_CHANNEL_NAME=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('telegram_channel_name','Alert Monitor'))" 2>/dev/null || echo "Alert Monitor")

NOW=$(date +%s)
NOW_FMT=$(TZ="$DISPLAY_TZ" date '+%Y-%m-%d %H:%M %Z')
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')

# Output mode: "json" for structured output, "text" for legacy human-readable
OUTPUT_MODE="${OUTPUT_MODE:-json}"

# NordVPN or custom proxy for geo-blocked Oref API
NORD_AUTH_FILE="$SKILL_DIR/secrets/nordvpn-auth.txt"
PROXY_OVERRIDE="$SKILL_DIR/secrets/proxy-override.txt"
NORD_PROXY=""

# Priority: proxy-override.txt > nordvpn-auth.txt > direct
if [ -f "$PROXY_OVERRIDE" ]; then
  CUSTOM_PROXY=$(head -1 "$PROXY_OVERRIDE" | tr -d '[:space:]')
  if [ -n "$CUSTOM_PROXY" ]; then
    NORD_PROXY="--proxy $CUSTOM_PROXY"
  fi
elif [ -f "$NORD_AUTH_FILE" ]; then
  NORD_USER=$(sed -n '1p' "$NORD_AUTH_FILE")
  NORD_PASS=$(sed -n '2p' "$NORD_AUTH_FILE")
  NORD_PROXY="--proxy https://${NORD_USER}:${NORD_PASS}@il66.nordvpn.com:89"
fi

# Temp files for collecting data
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# ============================================================
# 1. PIKUD HAOREF
# ============================================================
OREF_RAW=$(curl -sf --max-time 10 $NORD_PROXY \
  "https://www.oref.org.il/WarningMessages/alert/alerts.json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://www.oref.org.il/" 2>/dev/null || \
  curl -sf --max-time 10 "https://www.oref.org.il/WarningMessages/alert/alerts.json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://www.oref.org.il/" 2>/dev/null || echo "FAIL")

# Strip BOM
OREF_RAW=$(echo "$OREF_RAW" | tr -d '\r\n' | sed 's/^\xEF\xBB\xBF//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')

echo "$OREF_RAW" > "$TMPDIR/oref.txt"

# ============================================================
# 2. POLYMARKET
# ============================================================
curl -sf --max-time 15 "https://gamma-api.polymarket.com/markets?closed=false&limit=200&order=volume&ascending=false" > "$TMPDIR/poly1.json" 2>/dev/null || echo "[]" > "$TMPDIR/poly1.json"
curl -sf --max-time 15 "https://gamma-api.polymarket.com/markets?closed=false&limit=200&offset=200&order=volume&ascending=false" > "$TMPDIR/poly2.json" 2>/dev/null || echo "[]" > "$TMPDIR/poly2.json"

# ============================================================
# 3. RSS FEEDS (with timestamps and URLs)
# ============================================================
for feed_info in \
  "TOI|https://www.timesofisrael.com/feed/" \
  "IranIntl|https://www.iranintl.com/en/feed" \
  "Haaretz|https://www.haaretz.com/srv/haaretz-latest-headlines" \
  "NYT|https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml" \
  "BBC|https://feeds.bbci.co.uk/news/world/middle_east/rss.xml" \
  "AlArabiya|https://english.alarabiya.net/tools/rss" \
  "JPost|https://www.jpost.com/rss/rssfeedsheadlines.aspx"; do
  
  IFS='|' read -r LABEL URL <<< "$feed_info"
  curl -sf --max-time 10 "$URL" 2>/dev/null > "$TMPDIR/rss_${LABEL}.xml" || true
done

# ============================================================
# 4. OIL & COMMODITIES
# ============================================================
curl -sf --max-time 10 "https://api.oilpriceapi.com/v1/demo/prices" > "$TMPDIR/oil.json" 2>/dev/null || echo "{}" > "$TMPDIR/oil.json"

# ============================================================
# 5. AVIATION
# ============================================================
curl -sf --max-time 10 "https://opensky-network.org/api/states/all?lamin=27&lomin=34&lamax=38&lomax=55" > "$TMPDIR/flights.json" 2>/dev/null || echo "{}" > "$TMPDIR/flights.json"

# ============================================================
# 6. ASSEMBLE — Python does all the heavy lifting
# ============================================================
TMPDIR_INNER="$TMPDIR" NOW="$NOW" NOW_FMT="$NOW_FMT" TIMESTAMP="$TIMESTAMP" SKILL_DIR="$SKILL_DIR" DISPLAY_TZ="$DISPLAY_TZ" TG_CHAT_ID="$TG_CHAT_ID" TG_CHANNEL_NAME="$TG_CHANNEL_NAME" python3 << 'PYEOF'
import json, os, sys, re, html
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

TMPDIR = os.environ["TMPDIR_INNER"]
SKILL_DIR = os.environ.get("SKILL_DIR", ".")
state_dir = os.path.join(SKILL_DIR, "state")

result = {
    "timestamp": int(os.environ.get("NOW", 0)),
    "timestamp_fmt": os.environ.get("NOW_FMT", ""),
    "timezone": os.environ.get("DISPLAY_TZ", "Asia/Jerusalem"),
    "telegram_chat_id": os.environ.get("TG_CHAT_ID", ""),
    "telegram_channel_name": os.environ.get("TG_CHANNEL_NAME", "Alert Monitor"),
    "oref": {},
    "headlines": [],
    "polymarket": [],
    "commodities": [],
    "aviation": {},
    "threat_score": 0,
    "threat_level": "GREEN",
    "signals": [],
}

score = 0
signals = []

def add_signal(pts, reason):
    global score
    score += pts
    signals.append(f"(+{pts}) {reason}")

# ──── OREF ────
oref_raw = open(os.path.join(TMPDIR, "oref.txt")).read().strip()
if oref_raw == "FAIL":
    result["oref"] = {"status": "error", "note": "API unreachable"}
elif not oref_raw or oref_raw == "[]":
    result["oref"] = {"status": "clear"}
else:
    try:
        alerts_data = json.loads(oref_raw)
        cat_map = {
            1: "🚀 Rockets & Missiles", 2: "✈️ UAV Intrusion", 3: "🌍 Earthquake",
            4: "🌊 Tsunami", 5: "☢️ Radiological", 6: "✈️ Hostile Aircraft",
            7: "💣 Terrorist Infiltration", 8: "⚠️ Chemical Hazard",
            9: "🔥 Non-Conventional", 10: "⚠️ Imminent Threat",
            11: "📢 Drill", 12: "⚠️ General Alert", 13: "🔊 Siren Test"
        }
        # Key cities to highlight (rest get counted)
        key_cities = {"תל אביב", "ירושלים", "חיפה", "באר שבע", "אשדוד", "אשקלון",
                       "נתניה", "פתח תקווה", "ראשון לציון", "רחובות", "הרצליה",
                       "קריית שמונה", "נהריה", "עכו", "טבריה", "צפת", "אילת",
                       "מודיעין", "רמת גן", "בני ברק", "חולון", "בת ים",
                       "מטולה", "שדרות", "עפולה", "חדרה", "כפר סבא"}
        parsed = []
        for a in (alerts_data if isinstance(alerts_data, list) else [alerts_data]):
            data_field = a.get("data", [])
            if isinstance(data_field, list):
                locations = [str(d) for d in data_field]
            else:
                locations = [str(data_field)]

            cat_val = a.get("cat", "?")
            try:
                cat_int = int(cat_val)
            except:
                cat_int = 0
            alert_type = cat_map.get(cat_int, a.get("title", "Alert"))

            # Deduplicate: "חיפה - X" → "חיפה"
            seen = set()
            display = []
            for loc in locations:
                for city in key_cities:
                    if city in loc and city not in seen:
                        seen.add(city)
                        display.append(city)
                        break

            if not display:
                display = locations[:3]

            if len(locations) <= 3:
                location_str = ", ".join(locations)
            else:
                shown = ", ".join(display[:5])
                remaining = len(locations) - len(display[:5])
                location_str = f"{shown} (+{remaining} more)" if remaining > 0 else shown

            desc = a.get("desc", "").replace("\n", " ").strip()
            entry = {"location": location_str, "type": alert_type, "total_areas": len(locations)}
            if desc:
                entry["desc"] = desc
            parsed.append(entry)
        result["oref"] = {"status": "active", "alerts": parsed}
        add_signal(30, "Active Pikud HaOref sirens")
    except:
        result["oref"] = {"status": "active", "raw": oref_raw}
        add_signal(30, "Active Pikud HaOref sirens (unparsed)")

# ──── RSS HEADLINES (with timestamps) ────
display_tz = ZoneInfo(os.environ.get("DISPLAY_TZ", "Asia/Jerusalem"))
# Get the current timezone abbreviation (e.g. IST, IDT, EST, EDT)
tz_abbr = datetime.now(display_tz).strftime("%Z")

for fname in sorted(os.listdir(TMPDIR)):
    if not fname.startswith("rss_") or not fname.endswith(".xml"):
        continue
    label = fname.replace("rss_", "").replace(".xml", "")
    
    try:
        content = open(os.path.join(TMPDIR, fname)).read()
    except:
        continue
    
    # Parse items with regex (lightweight, no lxml needed)
    items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
    
    keywords = re.compile(r"iran|israel|idf|irgc|hezbollah|houthi|strike|attack|missile|military|war\b|escalat|nuclear|bomb|tehran|siren|hamas|gaza", re.I)
    
    for item in items:
        title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", item)
        link_m = re.search(r"<link>(.*?)</link>", item)
        date_m = re.search(r"<pubDate>(.*?)</pubDate>", item)
        
        if not title_m:
            continue
        
        title = title_m.group(1).strip()
        title = html.unescape(title)
        
        # Skip feed-level titles
        if title in [label, f"{label} International", "The Times of Israel"] or "Search Results" in title:
            continue
        
        if not keywords.search(title):
            continue
        
        url = link_m.group(1).strip() if link_m else ""
        
        # Parse timestamp
        time_str = ""
        time_epoch = 0
        if date_m:
            try:
                dt = parsedate_to_datetime(date_m.group(1).strip())
                dt_local = dt.astimezone(display_tz)
                now_local = datetime.now(display_tz)
                time_epoch = int(dt.timestamp())
                if dt_local.date() == now_local.date():
                    time_str = dt_local.strftime("%H:%M") + f" {tz_abbr}"
                elif dt_local.date() == (now_local - timedelta(days=1)).date():
                    time_str = "Yest " + dt_local.strftime("%H:%M")
                else:
                    time_str = dt_local.strftime("%d/%m %H:%M")
            except:
                time_str = ""
        
        result["headlines"].append({
            "source": label,
            "title": title,
            "url": url,
            "time": time_str,
            "epoch": time_epoch,
        })

# Sort headlines by time (newest first), blanks last
result["headlines"].sort(key=lambda h: h.get("epoch", 0), reverse=True)

# Score headlines
headline_count = len(result["headlines"])
if headline_count > 8:
    add_signal(8, f"Heavy news cycle: {headline_count} conflict headlines")
elif headline_count > 4:
    add_signal(5, f"Active news: {headline_count} conflict headlines")
elif headline_count > 0:
    add_signal(2, f"{headline_count} conflict headline(s)")

# ──── POLYMARKET ────
keywords = ['iran', 'israel', 'idf', 'hezbollah', 'houthi', 'irgc', 'middle east', 'gaza', 'tehran', 'netanyahu']
exclude = ['thailand', 'cambodia', 'china x india', 'gta', 'taylor', 'bitcoin', 'crypto', 'microstrategy', 'annex']

all_markets = []
for f in ["poly1.json", "poly2.json"]:
    try:
        all_markets.extend(json.load(open(os.path.join(TMPDIR, f))))
    except:
        pass

prev_poly_file = os.path.join(state_dir, "poly_previous.json")
prev_poly = {}
if os.path.exists(os.path.join(state_dir, "poly_current.json")):
    try:
        prev_poly = json.load(open(os.path.join(state_dir, "poly_current.json")))
    except:
        pass

current_poly = {}
for m in all_markets:
    q = m.get("question", "?")
    q_lower = q.lower()
    if not any(kw in q_lower for kw in keywords):
        continue
    if any(ex in q_lower for ex in exclude):
        continue
    
    slug = m.get("slug", "")
    prices = m.get("outcomePrices", "[]")
    p = json.loads(prices) if isinstance(prices, str) else prices
    yes = float(p[0]) if isinstance(p, list) and len(p) > 0 else 0
    vol = float(m.get("volume", 0))
    vol24 = float(m.get("volume24hr", 0))
    
    entry = {"q": q, "yes": yes, "vol": vol, "vol24": vol24, "slug": slug}
    current_poly[slug] = {"yes": yes, "q": q}
    
    # Check spike
    if slug in prev_poly:
        delta = (yes - prev_poly[slug]["yes"]) * 100
        if abs(delta) >= 5:
            entry["delta"] = delta
            add_signal(15, f"Polymarket spike: {q} moved {delta:+.1f}pp")
    
    result["polymarket"].append(entry)

# Sort by volume
result["polymarket"].sort(key=lambda m: m.get("vol", 0), reverse=True)

# Save current poly state
try:
    with open(os.path.join(state_dir, "poly_current.json"), "w") as f:
        json.dump(current_poly, f)
except:
    pass

# ──── COMMODITIES ────
try:
    oil = json.load(open(os.path.join(TMPDIR, "oil.json")))
    for p in oil.get("data", {}).get("prices", []):
        code = p["code"]
        if code in ("WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD", "GOLD_USD"):
            chg = p.get("change_24h") or 0
            result["commodities"].append({
                "name": p["name"],
                "price": p["price"],
                "change": chg,
            })
            if code in ("WTI_USD", "BRENT_CRUDE_USD"):
                if abs(chg) > 10:
                    add_signal(25, f"Major oil spike: {p['name']} {chg:+.1f}%")
                elif abs(chg) > 5:
                    add_signal(15, f"High oil move: {p['name']} {chg:+.1f}%")
                elif abs(chg) > 3:
                    add_signal(8, f"Elevated oil: {p['name']} {chg:+.1f}%")
except:
    pass

# ──── AVIATION ────
try:
    flights = json.load(open(os.path.join(TMPDIR, "flights.json")))
    states = flights.get("states", [])
    mil_callsigns = ["IAF", "USAF", "RCH", "FORTE", "DUKE", "LAGR", "HOMER", "NCHO", "JAKE", "EVAC"]
    mil_found = []
    for s in states:
        cs = (s[1] or "").strip()
        if any(x in cs.upper() for x in mil_callsigns):
            mil_found.append({"callsign": cs, "alt": s[7] or 0})
    result["aviation"] = {"total": len(states), "military": mil_found}
except:
    result["aviation"] = {"total": 0, "military": []}

# ──── THREAT LEVEL ────
result["threat_score"] = score
result["signals"] = signals

if score >= 40:
    result["threat_level"] = "CRITICAL"
elif score >= 20:
    result["threat_level"] = "HIGH"
elif score >= 8:
    result["threat_level"] = "ELEVATED"
else:
    result["threat_level"] = "LOW"

# ──── SAVE STATE ────
state = {
    "timestamp": result["timestamp"],
    "timestamp_fmt": result["timestamp_fmt"],
    "threat_score": score,
    "threat_level": result["threat_level"],
    "oref_hash": hash(str(result["oref"])),
}
try:
    with open(os.path.join(state_dir, "last-check.json"), "w") as f:
        json.dump(state, f, indent=2)
    
    # History
    hist_dir = os.path.join(state_dir, "history")
    os.makedirs(hist_dir, exist_ok=True)
    ts = os.environ.get("TIMESTAMP", "unknown")
    with open(os.path.join(hist_dir, f"check-{ts}.json"), "w") as f:
        json.dump(state, f)
    
    # Cleanup old history
    files = sorted(os.listdir(hist_dir), reverse=True)
    for old in files[100:]:
        os.remove(os.path.join(hist_dir, old))
except:
    pass

# Output
print(json.dumps(result, ensure_ascii=False))

PYEOF

