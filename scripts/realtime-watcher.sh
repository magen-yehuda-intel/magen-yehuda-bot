#!/bin/bash
# Real-time watcher daemon for Pikud HaOref sirens + Polymarket spikes + Twitter OSINT
# Features adaptive threat-level system: polling frequency scales with danger.
# Designed to run as a background process. Use ctl.sh start/stop to manage.

SKILL_DIR="${SKILL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
CONFIG_FILE="$SKILL_DIR/config.json"
STATE_DIR="$SKILL_DIR/state"
mkdir -p "$STATE_DIR"

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

DISPLAY_TZ=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('timezone','Asia/Jerusalem'))" 2>/dev/null || echo "Asia/Jerusalem")
BOT_TOKEN=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('telegram_bot_token',''))" 2>/dev/null || echo "")
CHAT_ID=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('telegram_chat_id',''))" 2>/dev/null || echo "")
CHANNEL_NAME=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('telegram_channel_name','Alert Monitor'))" 2>/dev/null || echo "Alert Monitor")

# Proxy for Oref (priority: override > nordvpn > direct)
NORD_AUTH_FILE="$SKILL_DIR/secrets/nordvpn-auth.txt"
PROXY_OVERRIDE="$SKILL_DIR/secrets/proxy-override.txt"
NORD_PROXY=""
if [ -f "$PROXY_OVERRIDE" ]; then
  CUSTOM_PROXY=$(head -1 "$PROXY_OVERRIDE" | tr -d '[:space:]')
  [ -n "$CUSTOM_PROXY" ] && NORD_PROXY="--proxy $CUSTOM_PROXY"
elif [ -f "$NORD_AUTH_FILE" ]; then
  NORD_USER=$(sed -n '1p' "$NORD_AUTH_FILE")
  NORD_PASS=$(sed -n '2p' "$NORD_AUTH_FILE")
  NORD_PROXY="--proxy https://${NORD_USER}:${NORD_PASS}@il66.nordvpn.com:89"
fi

# Base intervals from config (used at GREEN level)
OREF_INTERVAL=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('oref_poll_interval',30))" 2>/dev/null || echo "30")
POLY_INTERVAL_BASE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('polymarket_poll_interval',300))" 2>/dev/null || echo "300")
POLY_SPIKE_THRESHOLD=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('polymarket_spike_threshold',5))" 2>/dev/null || echo "5")
OSINT_INTERVAL_BASE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('twitter_poll_interval',300))" 2>/dev/null || echo "300")

# OSINT scanner script path
OSINT_SCANNER="$SKILL_DIR/scripts/scan-osint.py"

# ══════════════════════════════════════════════════════════════
# THREAT LEVEL SYSTEM
# ══════════════════════════════════════════════════════════════
#
# Level    │ Trigger                          │ Oref  │ Twitter │ Poly   │ Cooldown
# ─────────┼──────────────────────────────────┼───────┼─────────┼────────┼─────────
# 🟢 GREEN │ No recent sirens (>30min)        │ 30s   │ 5min    │ 5min   │ —
# 🟡 ELEV  │ Sirens in last 30min (not live)  │ 15s   │ 2min    │ 2min   │ 30min→GREEN
# 🔴 HIGH  │ Active sirens NOW                │ 10s   │ 60s     │ 60s    │ 10min→ELEV
# ⚫ CRIT  │ Major cities under fire          │ 10s   │ 30s     │ 60s    │ 10min→HIGH
#
# Oref always polls fast (it's cheap). Twitter/Poly scale with threat.

THREAT_LEVEL="GREEN"     # Current level
THREAT_FILE="$STATE_DIR/watcher-threat-level.txt"
LAST_SIREN_TIME=0        # epoch of most recent siren
LAST_SIREN_CRITICAL=0    # epoch of most recent CRITICAL-trigger siren
ESCALATION_COOLDOWN=600  # 10min before stepping down from HIGH/CRIT
ELEVATED_COOLDOWN=1800   # 30min before stepping down from ELEVATED to GREEN

# Major population centers that trigger CRITICAL
CRITICAL_CITIES="תל אביב|ירושלים|חיפה|באר שבע|פתח תקווה|ראשון לציון|רמת גן|בני ברק|חולון|בת ים|הרצליה|נתניה|אשדוד|אשקלון|רחובות|מודיעין|גבעתיים"

get_threat_intervals() {
  # Sets EFFECTIVE_OREF, EFFECTIVE_OSINT, EFFECTIVE_POLY based on current THREAT_LEVEL
  # OSINT = unified scan (Telegram channels + Twitter + RSS + seismic)
  case "$THREAT_LEVEL" in
    GREEN)
      EFFECTIVE_OREF=$OREF_INTERVAL
      EFFECTIVE_OSINT=$OSINT_INTERVAL_BASE
      EFFECTIVE_POLY=$POLY_INTERVAL_BASE
      EFFECTIVE_FIRES=900     # 15min
      EFFECTIVE_INTEL=1800    # 30min (blackout + flights + naval)
      ;;
    ELEVATED)
      EFFECTIVE_OREF=15
      EFFECTIVE_OSINT=120
      EFFECTIVE_POLY=120
      EFFECTIVE_FIRES=600     # 10min
      EFFECTIVE_INTEL=900     # 15min
      ;;
    HIGH)
      EFFECTIVE_OREF=10
      EFFECTIVE_OSINT=60
      EFFECTIVE_POLY=60
      EFFECTIVE_FIRES=300     # 5min
      EFFECTIVE_INTEL=600     # 10min
      ;;
    CRITICAL)
      EFFECTIVE_OREF=10
      EFFECTIVE_OSINT=30
      EFFECTIVE_POLY=60
      EFFECTIVE_FIRES=180     # 3min
      EFFECTIVE_INTEL=300     # 5min
      ;;
  esac
}

threat_emoji() {
  case "$1" in
    GREEN)    echo "🟢" ;;
    ELEVATED) echo "🟡" ;;
    HIGH)     echo "🔴" ;;
    CRITICAL) echo "⚫" ;;
  esac
}

set_threat_level() {
  local new_level="$1"
  local reason="$2"
  if [ "$new_level" != "$THREAT_LEVEL" ]; then
    local old_level="$THREAT_LEVEL"
    THREAT_LEVEL="$new_level"
    echo "$THREAT_LEVEL" > "$THREAT_FILE"
    get_threat_intervals

    local old_emoji=$(threat_emoji "$old_level")
    local new_emoji=$(threat_emoji "$new_level")

    log "⚡ THREAT LEVEL: $old_emoji $old_level → $new_emoji $new_level ($reason)"
    log "   Intervals: Oref=${EFFECTIVE_OREF}s OSINT=${EFFECTIVE_OSINT}s Poly=${EFFECTIVE_POLY}s"

    # Post threat level change to Telegram
    send_telegram "$new_emoji <b>THREAT LEVEL: $new_level</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z')
$old_emoji $old_level → $new_emoji $new_level

📋 <i>$reason</i>

⚡ Monitoring frequency adjusted:
• Oref: every ${EFFECTIVE_OREF}s
• OSINT (TG+X+RSS): every ${EFFECTIVE_OSINT}s
• Polymarket: every ${EFFECTIVE_POLY}s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    
    # Log intel
    log_intel "{\"type\":\"threat_change\",\"from\":\"$old_level\",\"to\":\"$new_level\",\"reason\":$(echo "$reason" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '""')}"
  fi
}

evaluate_threat_level() {
  local NOW=$(date +%s)
  local time_since_siren=$((NOW - LAST_SIREN_TIME))
  local time_since_critical=$((NOW - LAST_SIREN_CRITICAL))

  # Read current Oref state
  local oref_state=$(cat "$OREF_LAST" 2>/dev/null || echo "")
  local sirens_active=false
  if [ -n "$oref_state" ] && [ "$oref_state" != "" ] && [ "$oref_state" != "[]" ]; then
    sirens_active=true
  fi

  if [ "$sirens_active" = true ]; then
    # Active sirens — check if major cities (Python for reliable Hebrew)
    local is_crit
    is_crit=$(python3 -c "
import sys
raw = sys.stdin.read()
critical = ['תל אביב', 'ירושלים', 'חיפה', 'באר שבע', 'פתח תקווה', 'ראשון לציון',
            'רמת גן', 'בני ברק', 'חולון', 'בת ים', 'הרצליה', 'נתניה',
            'אשדוד', 'אשקלון', 'רחובות', 'מודיעין', 'גבעתיים']
print('1' if any(c in raw for c in critical) else '0')
" <<< "$oref_state" 2>/dev/null)
    if [ "$is_crit" = "1" ]; then
      set_threat_level "CRITICAL" "Active sirens in major population centers"
    else
      # Active sirens but peripheral areas only
      if [ "$THREAT_LEVEL" = "CRITICAL" ]; then
        : # Don't downgrade from CRITICAL while sirens are still active
      else
        set_threat_level "HIGH" "Active sirens — Pikud HaOref broadcasting"
      fi
    fi
  else
    # No active sirens — check cooldown timers for de-escalation
    case "$THREAT_LEVEL" in
      CRITICAL)
        if [ $time_since_critical -ge $ESCALATION_COOLDOWN ]; then
          set_threat_level "HIGH" "No major-city sirens for ${ESCALATION_COOLDOWN}s — stepping down"
        fi
        ;;
      HIGH)
        if [ $time_since_siren -ge $ESCALATION_COOLDOWN ]; then
          set_threat_level "ELEVATED" "Sirens cleared for ${ESCALATION_COOLDOWN}s — stepping down"
        fi
        ;;
      ELEVATED)
        if [ $time_since_siren -ge $ELEVATED_COOLDOWN ]; then
          set_threat_level "GREEN" "No sirens for ${ELEVATED_COOLDOWN}s — returning to baseline"
        fi
        ;;
    esac
  fi
}

# ══════════════════════════════════════════════════════════════
# STATE FILES
# ══════════════════════════════════════════════════════════════

OREF_LAST="$STATE_DIR/watcher-oref-last.txt"
POLY_LAST="$STATE_DIR/watcher-poly-last.json"
ALERT_LOG="$STATE_DIR/watcher-alerts.log"

touch "$OREF_LAST" "$ALERT_LOG"
echo "{}" > "$POLY_LAST" 2>/dev/null || true

# ══════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════

log() {
  echo "[$(TZ="$DISPLAY_TZ" date '+%Y-%m-%d %H:%M:%S %Z')] $*"
}

log_intel() {
  # Log a structured intel event to JSONL for hourly summaries
  local event_json="$1"
  echo "$event_json" | python3 "$SKILL_DIR/scripts/log-intel.py" "$STATE_DIR" 2>/dev/null
}

send_telegram() {
  local msg="$1"
  curl -sf --max-time 10 "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    -d "parse_mode=HTML" \
    -d "disable_web_page_preview=true" \
    --data-urlencode "text=${msg}" >/dev/null 2>&1 || log "⚠️  Telegram send failed"
}

# ══════════════════════════════════════════════════════════════
# OREF CHECK
# ══════════════════════════════════════════════════════════════

check_oref() {
  local alerts
  alerts=$(curl -sf --max-time 10 $NORD_PROXY \
    "https://www.oref.org.il/WarningMessages/alert/alerts.json" \
    -H "X-Requested-With: XMLHttpRequest" \
    -H "Referer: https://www.oref.org.il/" 2>/dev/null || echo "")

  # Strip BOM and whitespace
  alerts=$(echo "$alerts" | tr -d '\r\n' | sed 's/^\xEF\xBB\xBF//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')

  local prev
  prev=$(cat "$OREF_LAST" 2>/dev/null || echo "")

  # No alerts = quiet
  if [ -z "$alerts" ] || [ "$alerts" = "[]" ]; then
    if [ -n "$prev" ] && [ "$prev" != "" ] && [ "$prev" != "[]" ]; then
      log "ℹ️ No new alerts broadcasting"
      send_telegram "ℹ️ <b>NO NEW ALERTS BROADCASTING</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z')

Pikud HaOref is no longer broadcasting new alerts.
⚠️ <b>Stay in shelter until instructed otherwise by Pikud HaOref.</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    fi
    echo "" > "$OREF_LAST"
    return
  fi

  # We have a non-empty response — but is it an ACTIVE THREAT or an INFORMATIONAL message?
  # Pikud HaOref sends stand-down messages ("ניתן לצאת מהמרחב המוגן") through the same API.
  # These should NOT escalate threat level.
  
  local alert_type
  alert_type=$(python3 -c "
import json, sys

STAND_DOWN_PHRASES = [
    'ניתן לצאת',         # You can leave (the shelter)
    'ניתן לחזור',        # You can return (to routine)
    'הותר',              # Allowed / permitted
    'שגרה',              # Routine
    'אין צורך',          # No need
    'הסתיים',            # Ended
    'בוטל',              # Cancelled
    'תרגיל',             # Drill / exercise
]

# Pre-alert warnings — not threats, not standdowns
PRE_ALERT_PHRASES = [
    'צפויות להתקבל',     # Expected to receive (alerts)
    'בדקות הקרובות',     # In the coming minutes
    'היערכות',            # Preparation
]

# Categories that are real threats vs informational
THREAT_CATS = {1, 2, 3, 4, 5, 6, 7}  # missiles, earthquake, tsunami, aircraft, hazmat, unconventional

try:
    raw = sys.stdin.read().strip()
    if raw.startswith('\ufeff'):
        raw = raw[1:]
    alerts = json.loads(raw)
    if not isinstance(alerts, list):
        alerts = [alerts]
    
    has_threat = False
    has_standdown = False
    
    for a in alerts:
        cat = int(a.get('cat', 0))
        title = a.get('title', '')
        desc = a.get('desc', '')
        combined = f'{title} {desc}'
        
        # Check if this is a stand-down message by content
        is_standdown = any(phrase in combined for phrase in STAND_DOWN_PHRASES)
        is_prealert = any(phrase in combined for phrase in PRE_ALERT_PHRASES)
        
        if is_standdown:
            has_standdown = True
        elif is_prealert:
            has_standdown = True  # Pre-alerts are informational, not threats
            has_standdown = True
        elif cat in THREAT_CATS:
            has_threat = True
        elif cat == 0:
            # Unknown category — check content for threat keywords
            threat_words = ['אזעקה', 'ירי', 'טילים', 'רקטות', 'חדירה', 'כלי טיס', 'רעידת אדמה']
            if any(w in combined for w in threat_words):
                has_threat = True
            else:
                has_standdown = True  # Unknown + no threat words = likely informational
        else:
            has_standdown = True  # Non-standard category = informational
    
    if has_threat:
        print('THREAT')
    elif has_standdown:
        print('STANDDOWN')
    else:
        print('UNKNOWN')
except:
    print('UNKNOWN')
" <<< "$alerts" 2>/dev/null)

  log "  Oref alert type: $alert_type"

  if [ "$alert_type" = "STANDDOWN" ]; then
    # This is an informational/stand-down message — do NOT escalate
    # Throttle: max 1 standdown message per 5 minutes to avoid spam
    local now_sd=$(date +%s)
    local last_sd=$(cat "$STATE_DIR/last-standdown-ts.txt" 2>/dev/null || echo "0")
    local sd_elapsed=$((now_sd - last_sd))
    
    if [ "$alerts" != "$prev" ] && [ $sd_elapsed -ge 300 ]; then
      log "ℹ️ Pikud HaOref stand-down / informational message"
      echo "$now_sd" > "$STATE_DIR/last-standdown-ts.txt"
      
      local details
      details=$(python3 -c "
import json, html, sys
try:
    raw = sys.stdin.read().strip()
    if raw.startswith('\ufeff'):
        raw = raw[1:]
    alerts = json.loads(raw)
    if not isinstance(alerts, list):
        alerts = [alerts]
    for a in alerts:
        title = html.escape(a.get('title', ''))
        desc = html.escape(a.get('desc', '').replace(chr(10), ' ').strip())
        data_field = a.get('data', [])
        locs = [str(d) for d in data_field] if isinstance(data_field, list) else [str(data_field)]
        loc_str = html.escape(', '.join(locs[:5]))
        if len(locs) > 5:
            loc_str += f' (+{len(locs)-5} more)'
        print(f'  🟢 <b>{title}</b>')
        print(f'     📍 {loc_str}')
        if desc:
            print(f'     <i>{desc[:200]}</i>')
except:
    print('  ℹ️ Stand-down message received')
" <<< "$alerts" 2>/dev/null)

      send_telegram "✅ <b>PIKUD HAOREF — STAND DOWN</b> ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z') | $(threat_emoji "$THREAT_LEVEL") $THREAT_LEVEL

${details}

🔗 https://www.oref.org.il/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"

      log_intel "{\"type\":\"siren_standdown\",\"details\":$(echo "$details" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '\"\"')}"
    fi
    # Clear OREF_LAST so evaluate_threat_level doesn't think sirens are active
    echo "" > "$OREF_LAST"
    return
  fi

  # ─── ACTIVE THREAT: update siren timestamps and escalate ───
  LAST_SIREN_TIME=$(date +%s)

  # Check if critical cities are in the alert (Python for reliable Hebrew matching)
  local is_critical
  is_critical=$(python3 -c "
import sys
raw = sys.stdin.read()
critical = ['תל אביב', 'ירושלים', 'חיפה', 'באר שבע', 'פתח תקווה', 'ראשון לציון',
            'רמת גן', 'בני ברק', 'חולון', 'בת ים', 'הרצליה', 'נתניה',
            'אשדוד', 'אשקלון', 'רחובות', 'מודיעין', 'גבעתיים']
print('1' if any(c in raw for c in critical) else '0')
" <<< "$alerts" 2>/dev/null)
  if [ "$is_critical" = "1" ]; then
    LAST_SIREN_CRITICAL=$(date +%s)
  fi

  # Evaluate threat level NOW (before sending Telegram) so the message shows the correct level
  evaluate_threat_level

  # Check if they're new (different from previous)
  if [ "$alerts" != "$prev" ]; then
    log "🚨 NEW SIRENS detected"
    echo "$alerts" >> "$ALERT_LOG"

    # Parse alert details via temp file
    local alert_tmp="$STATE_DIR/oref-alert-tmp.json"
    printf '%s' "$alerts" > "$alert_tmp"
    local details
    details=$(python3 -c "
import json, html

key_cities = {'תל אביב', 'ירושלים', 'חיפה', 'באר שבע', 'אשדוד', 'אשקלון',
              'נתניה', 'פתח תקווה', 'ראשון לציון', 'רחובות', 'הרצליה',
              'קריית שמונה', 'נהריה', 'עכו', 'טבריה', 'צפת', 'אילת',
              'מודיעין', 'רמת גן', 'בני ברק', 'חולון', 'בת ים',
              'מטולה', 'שדרות', 'עפולה', 'חדרה', 'כפר סבא'}
try:
    with open('$alert_tmp', 'r') as f:
        raw = f.read().strip()
    if raw.startswith('\ufeff'):
        raw = raw[1:]
    alerts = json.loads(raw)
    if not isinstance(alerts, list):
        alerts = [alerts]
    for a in alerts:
        title = html.escape(a.get('title', 'התרעה'))
        desc = html.escape(a.get('desc', '').replace(chr(10), ' ').strip())
        data_field = a.get('data', [])
        locs = [str(d) for d in data_field] if isinstance(data_field, list) else [str(data_field)]

        seen = set()
        display = []
        for loc in locs:
            for city in key_cities:
                if city in loc and city not in seen:
                    seen.add(city)
                    display.append(city)
                    break
        if not display:
            display = locs[:3]
        if len(locs) <= 3:
            loc_str = html.escape(', '.join(locs))
        else:
            shown = html.escape(', '.join(display[:5]))
            rest = len(locs) - len(display[:5])
            loc_str = f'{shown} (+{rest} more)' if rest > 0 else shown

        total = f' ({len(locs)} areas)' if len(locs) > 5 else ''
        print(f'  🔴 <b>{title}</b>{total}')
        print(f'     📍 {loc_str}')
        if desc:
            if len(desc) > 200:
                desc = desc[:197] + '...'
            print(f'     <i>{desc}</i>')
except Exception as e:
    print(f'  ⚠️ Alert received (parse error: {e})')
" 2>/dev/null)
    if [ -z "$details" ]; then
      details="  ⚠️ Alert received — check https://www.oref.org.il/"
    fi

    local level_emoji=$(threat_emoji "$THREAT_LEVEL")

    send_telegram "🚨🚨🚨 <b>ACTIVE SIRENS — PIKUD HAOREF</b> 🚨🚨🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z') | $level_emoji $THREAT_LEVEL

${details}

⚡ Real-time alert from Pikud HaOref
🔗 https://www.oref.org.il/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    
    # Log intel
    log_intel "{\"type\":\"siren\",\"threat_level\":\"$THREAT_LEVEL\",\"details\":$(echo "$details" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '""'),\"raw\":$(echo "$alerts" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '""')}"
  fi

  echo "$alerts" > "$OREF_LAST"
}

# ══════════════════════════════════════════════════════════════
# POLYMARKET CHECK
# ══════════════════════════════════════════════════════════════

check_polymarket() {
  local data
  data=$(curl -sf --max-time 15 "https://gamma-api.polymarket.com/markets?closed=false&limit=200&order=volume&ascending=false" 2>/dev/null || echo "[]")

  python3 -c "
import json, sys, os

STATE_DIR = os.environ.get('STATE_DIR', '.')
prev_file = os.path.join(STATE_DIR, 'watcher-poly-last.json')
alert_file = os.path.join(STATE_DIR, 'watcher-poly-alerts.txt')

keywords = ['iran', 'israel', 'idf', 'hezbollah', 'houthi', 'irgc', 'middle east', 'gaza', 'tehran', 'netanyahu']
exclude = ['thailand', 'cambodia', 'china x india', 'gta', 'taylor', 'bitcoin', 'crypto', 'microstrategy', 'annex']

try:
    markets = json.load(sys.stdin)
    prev = {}
    if os.path.exists(prev_file):
        prev = json.load(open(prev_file))

    current = {}
    alerts = []

    for m in markets:
        q = m.get('question', '?')
        q_lower = q.lower()
        if not any(kw in q_lower for kw in keywords):
            continue
        if any(ex in q_lower for ex in exclude):
            continue

        slug = m.get('slug', '')
        prices = m.get('outcomePrices', '[]')
        p = json.loads(prices) if isinstance(prices, str) else prices
        yes = float(p[0]) if isinstance(p, list) and len(p) > 0 else 0
        current[slug] = {'yes': yes, 'q': q}

        if slug in prev:
            delta = (yes - prev[slug]['yes']) * 100
            if abs(delta) >= $POLY_SPIKE_THRESHOLD:
                direction = '📈' if delta > 0 else '📉'
                alerts.append(f'{direction} <b>{q}</b>\n   {prev[slug][\"yes\"]:.0%} → {yes:.0%} ({delta:+.1f}pp)')

    with open(prev_file, 'w') as f:
        json.dump(current, f)

    if alerts:
        with open(alert_file, 'w') as f:
            f.write('\n\n'.join(alerts))
    else:
        open(alert_file, 'w').close()

except Exception as ex:
    print(f'Polymarket error: {ex}', file=sys.stderr)
" <<< "$data" 2>/dev/null

  local alert_file="$STATE_DIR/watcher-poly-alerts.txt"
  if [ -f "$alert_file" ] && [ -s "$alert_file" ]; then
    local alert_text
    alert_text=$(cat "$alert_file")
    local level_emoji=$(threat_emoji "$THREAT_LEVEL")
    log "📊 Polymarket spike detected"
    send_telegram "📊 <b>MARKET MOVEMENT DETECTED</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z') | $level_emoji $THREAT_LEVEL

${alert_text}

🔗 https://polymarket.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    
    # Log intel
    log_intel "{\"type\":\"polymarket\",\"threat_level\":\"$THREAT_LEVEL\",\"text\":$(echo "$alert_text" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '""')}"
    > "$alert_file"
  fi
}

# ══════════════════════════════════════════════════════════════
# UNIFIED OSINT CHECK (Telegram channels + Twitter + RSS + Seismic)
# ══════════════════════════════════════════════════════════════

check_osint() {
  # Guard: skip if previous scan is still running
  if [ -f "$STATE_DIR/osint-scan.lock" ]; then
    local lock_age=$(( $(date +%s) - $(stat -f%m "$STATE_DIR/osint-scan.lock" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -lt 120 ]; then
      log "⏳ OSINT scan still running (${lock_age}s), skipping"
      return
    fi
    log "⚠️ Stale OSINT lock (${lock_age}s), breaking it"
    rm -f "$STATE_DIR/osint-scan.lock"
  fi
  touch "$STATE_DIR/osint-scan.lock"

  # Run the Python OSINT scanner — returns JSON array of alerts
  local raw_json
  raw_json=$(python3 "$OSINT_SCANNER" "$CONFIG_FILE" "$STATE_DIR" --source all 2>/dev/null)

  rm -f "$STATE_DIR/osint-scan.lock"

  if [ -z "$raw_json" ] || [ "$raw_json" = "[]" ]; then
    return
  fi

  # Send seismic events as separate prominent alerts (like sirens)
  local seismic_alerts
  seismic_alerts=$(python3 -c "
import json, sys, html as h
alerts = json.loads(sys.stdin.read())
seismic = [a for a in alerts if a.get('source') == 'seismic']
for a in seismic:
    text = h.escape(a['text'])
    link = a.get('link', '')
    suspicious = '⚠️ SUSPICIOUS' in a.get('text', '')
    link_tag = f'🔗 <a href=\"{link}\">USGS Details</a>' if link else ''
    print(f'{text}')
    if link_tag:
        print(link_tag)
    print()
print(len(seismic), file=sys.stderr)
" <<< "$raw_json" 2>"$STATE_DIR/watcher-seismic-count.txt")
  local seismic_count
  seismic_count=$(cat "$STATE_DIR/watcher-seismic-count.txt" 2>/dev/null | tr -d '[:space:]')
  if [ -n "$seismic_count" ] && [ "$seismic_count" -gt 0 ] 2>/dev/null; then
    local level_emoji=$(threat_emoji "$THREAT_LEVEL")
    send_telegram "🌍🌍🌍 <b>SEISMIC ACTIVITY — IRAN REGION</b> 🌍🌍🌍
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z') | $level_emoji $THREAT_LEVEL

${seismic_alerts}
⚠️ Shallow high-magnitude events or 'explosion' type may indicate underground nuclear tests or large conventional strikes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    log "🌍 SEISMIC: $seismic_count events in Iran region"
    
    # Log intel
    log_intel "{\"type\":\"seismic_osint\",\"count\":$seismic_count,\"text\":$(echo "$seismic_alerts" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '""')}"
  fi

  # Format non-seismic alerts for Telegram
  local alert_file="$STATE_DIR/watcher-osint-alerts.txt"
  python3 -c "
import json, sys, html as h

alerts = [a for a in json.loads(sys.stdin.read()) if a.get('source') != 'seismic']
if not alerts:
    sys.exit(0)

# Source emoji mapping
emoji = {
    'telegram': '📢',
    'twitter': '🐦',
    'rss': '📰',
    'seismic': '🌍',
}

lines = []
by_source = {}
for a in alerts:
    src = a.get('source', '?')
    by_source.setdefault(src, []).append(a)

# Telegram channels
for a in by_source.get('telegram', [])[:6]:
    ch = h.escape(a.get('channel', '?'))
    text = h.escape(a['text'][:150])
    link = a.get('link', '')
    link_tag = f' <a href=\"{link}\">[↗]</a>' if link else ''
    lines.append(f'{emoji[\"telegram\"]} <b>{ch}</b>: {text}{link_tag}')

# Twitter
for a in by_source.get('twitter', [])[:4]:
    ch = h.escape(a.get('channel', '?'))
    text = h.escape(a['text'][:150])
    link = a.get('link', '')
    rt = '🔁' if a.get('is_rt') else emoji['twitter']
    link_tag = f' <a href=\"{link}\">[↗]</a>' if link else ''
    lines.append(f'{rt} <b>{ch}</b>: {text}{link_tag}')

# RSS
for a in by_source.get('rss', [])[:3]:
    ch = h.escape(a.get('channel', '?'))
    text = h.escape(a['text'][:120])
    link = a.get('link', '')
    link_tag = f' <a href=\"{link}\">[↗]</a>' if link else ''
    lines.append(f'{emoji[\"rss\"]} <b>{ch}</b>: {text}{link_tag}')

# Cap total at 12 items to stay under 4096 chars
output = chr(10).join(lines[:12])
if len(alerts) > 12:
    output += f'{chr(10)}... +{len(alerts)-12} more updates'

# Write summary counts for logging
summary_parts = []
for src, items in by_source.items():
    summary_parts.append(f'{emoji.get(src,\"?\")} {len(items)} {src}')
summary = ' | '.join(summary_parts)
print(f'SUMMARY:{summary}', file=sys.stderr)

print(output)
" <<< "$raw_json" > "$alert_file" 2>"$STATE_DIR/watcher-osint-summary.txt"

  if [ -f "$alert_file" ] && [ -s "$alert_file" ]; then
    local alert_text
    alert_text=$(cat "$alert_file")
    local summary
    summary=$(grep '^SUMMARY:' "$STATE_DIR/watcher-osint-summary.txt" 2>/dev/null | sed 's/^SUMMARY://')
    local alert_count
    alert_count=$(python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())))" <<< "$raw_json" 2>/dev/null || echo "?")
    local level_emoji=$(threat_emoji "$THREAT_LEVEL")

    log "📡 OSINT: $alert_count updates ($summary)"
    send_telegram "📡 <b>OSINT INTEL UPDATE</b> ($alert_count new)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z') | $level_emoji $THREAT_LEVEL

${alert_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    
    # Log intel — save raw JSON of all alerts
    log_intel "{\"type\":\"osint\",\"count\":$alert_count,\"summary\":$(echo "$summary" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || echo '""'),\"alerts\":$raw_json}"
    > "$alert_file"  # Clear after sending
  fi
}

# ══════════════════════════════════════════════════════════════
# SATELLITE FIRE DETECTION (NASA FIRMS)
# ══════════════════════════════════════════════════════════════

check_fires_seismic() {
  log "🛰️  Checking satellite fires + seismic activity..."
  
  # ── Fire scan ──
  local fire_json
  fire_json=$(python3 "$SKILL_DIR/scripts/scan-fires.py" "$CONFIG_FILE" "$STATE_DIR" 2>>"$SKILL_DIR/state/watcher.log")
  local fire_ok=$?
  local new_fires=0
  if [ $fire_ok -eq 0 ]; then
    new_fires=$(echo "$fire_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_fires',0))" 2>/dev/null)
  fi
  
  # ── Seismic scan ──
  local seismic_json
  seismic_json=$(python3 "$SKILL_DIR/scripts/scan-seismic.py" "$CONFIG_FILE" "$STATE_DIR" 2>>"$SKILL_DIR/state/watcher.log")
  local seismic_ok=$?
  local new_quakes=0
  if [ $seismic_ok -eq 0 ]; then
    new_quakes=$(echo "$seismic_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_quakes',0))" 2>/dev/null)
  fi
  
  log "  Fires: ${new_fires:-0} new | Quakes: ${new_quakes:-0} new"
  
  # Nothing new? Done.
  if [ "${new_fires:-0}" = "0" ] && [ "${new_quakes:-0}" = "0" ]; then
    log "  ✓ No new fires or quakes in Iran region"
    return
  fi
  
  # ── Generate combined map ──
  local map_file="$STATE_DIR/intel-map-latest.png"
  local fire_tmp="$STATE_DIR/tmp-fires.json"
  local seismic_tmp="$STATE_DIR/tmp-seismic.json"
  
  echo "$fire_json" > "$fire_tmp"
  echo "$seismic_json" > "$seismic_tmp"
  
  python3 "$SKILL_DIR/scripts/generate-fire-map.py" "$fire_tmp" "$map_file" --seismic "$seismic_tmp" 2>>"$SKILL_DIR/state/watcher.log"
  local map_ok=$?
  
  rm -f "$fire_tmp" "$seismic_tmp"
  
  # ── Send map image ──
  if [ $map_ok -eq 0 ] && [ -f "$map_file" ]; then
    local caption="🛰️ Iran Intel Map"
    [ "${new_fires:-0}" != "0" ] && caption="$caption — ${new_fires} fires"
    [ "${new_quakes:-0}" != "0" ] && caption="$caption — ${new_quakes} quakes"
    
    local photo_ok
    photo_ok=$(python3 -c "
import json, urllib.request, io, uuid

config = json.load(open('$CONFIG_FILE'))
bot_token = config['telegram_bot_token']
chat_id = config['telegram_chat_id']

with open('$map_file', 'rb') as f:
    img_data = f.read()

boundary = uuid.uuid4().hex
body = io.BytesIO()
body.write(f'--{boundary}\r\n'.encode())
body.write(f'Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n'.encode())
body.write(f'--{boundary}\r\n'.encode())
body.write(f'Content-Disposition: form-data; name=\"caption\"\r\n\r\n$caption\r\n'.encode())
body.write(f'--{boundary}\r\n'.encode())
body.write(b'Content-Disposition: form-data; name=\"photo\"; filename=\"intel-map.png\"\r\n')
body.write(b'Content-Type: image/png\r\n\r\n')
body.write(img_data)
body.write(b'\r\n')
body.write(f'--{boundary}--\r\n'.encode())

req = urllib.request.Request(
    f'https://api.telegram.org/bot{bot_token}/sendPhoto',
    data=body.getvalue(),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print('ok' if result.get('ok') else 'fail')
except Exception as e:
    print(f'fail: {e}')
" 2>/dev/null)
    if [ "$photo_ok" = "ok" ]; then
      log "  📸 Intel map sent to Telegram"
    else
      log "  ⚠️  Map send failed: $photo_ok"
    fi
  fi
  
  # ── Send fire text alert ──
  if [ "${new_fires:-0}" != "0" ]; then
    local fire_msg
    fire_msg=$(echo "$fire_json" | python3 "$SKILL_DIR/scripts/format-fires.py" 2>/dev/null)
    if [ -n "$fire_msg" ]; then
      local resp
      resp=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="$CHAT_ID" -d parse_mode="HTML" -d disable_web_page_preview="true" \
        --data-urlencode "text=${fire_msg}")
      local ok=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',''))" 2>/dev/null)
      [ "$ok" = "True" ] && log "  ✅ Fire alert sent ($new_fires fires)" || log "  ❌ Fire alert failed"
    fi
    # Log intel
    log_intel "{\"type\":\"fires\",\"count\":${new_fires},\"data\":$fire_json}"
  fi
  
  # ── Send seismic text alert ──
  if [ "${new_quakes:-0}" != "0" ]; then
    local quake_msg
    quake_msg=$(echo "$seismic_json" | python3 "$SKILL_DIR/scripts/format-seismic.py" 2>/dev/null)
    if [ -n "$quake_msg" ]; then
      local resp
      resp=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="$CHAT_ID" -d parse_mode="HTML" -d disable_web_page_preview="true" \
        --data-urlencode "text=${quake_msg}")
      local ok=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',''))" 2>/dev/null)
      [ "$ok" = "True" ] && log "  ✅ Seismic alert sent ($new_quakes quakes)" || log "  ❌ Seismic alert failed"
    fi
    # Log intel
    log_intel "{\"type\":\"seismic\",\"count\":${new_quakes},\"data\":$seismic_json}"
  fi
}

# ══════════════════════════════════════════════════════════════
# EXTENDED INTEL: Blackout + Military Flights + Naval + Strike Correlation
# ══════════════════════════════════════════════════════════════

check_blackout() {
  log "🌐 Checking Iran internet status..."
  local result
  result=$(python3 "$SKILL_DIR/scripts/scan-blackout.py" "$CONFIG_FILE" "$STATE_DIR" 2>>"$SKILL_DIR/state/watcher.log")
  local exit_code=$?
  
  if [ $exit_code -ne 0 ]; then
    log "  ⚠️  Blackout check failed"
    return
  fi
  
  local level changed last_alert_ts
  level=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['assessment']['level'])" 2>/dev/null)
  changed=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['assessment']['changed'])" 2>/dev/null)
  last_alert_ts=$(echo "$result" | python3 -c "import sys,json; print(int(json.load(sys.stdin)['assessment'].get('last_alert_ts',0)))" 2>/dev/null || echo "0")
  
  log "  🌐 Iran internet: $level"
  
  # Only alert on REAL changes — and throttle to max once per hour
  local now_ts=$(date +%s)
  local since_last=$((now_ts - ${last_alert_ts:-0}))
  local min_interval=3600  # 1 hour minimum between alerts
  
  # For BLACKOUT level, alert faster (every 15 min)
  if [ "$level" = "BLACKOUT" ]; then
    min_interval=900
  fi
  
  # Send alert if: level changed AND enough time passed since last alert
  # OR: level is BLACKOUT/DEGRADED (always send every interval even without change)
  local should_alert=false
  if [ "$changed" = "True" ] && [ "$level" != "NORMAL" ] && [ "$since_last" -ge "$min_interval" ]; then
    should_alert=true
  elif [ "$level" = "BLACKOUT" ] && [ "$since_last" -ge "$min_interval" ]; then
    should_alert=true
  fi
  
  if [ "$should_alert" = "true" ]; then
    # Generate visual Telegram message with bar graph
    local msg
    msg=$(echo "$result" | python3 -c "
import sys, json
from datetime import datetime, timezone

d = json.load(sys.stdin)
a = d['assessment']
level = a['level']
score = a['score']
emoji = a['emoji']
prev = a.get('prev_level', 'NORMAL')
history = a.get('history', [])
ioda_details = a.get('ioda_details', [])
probes = d.get('probes', {})

# Level descriptions for humans
level_desc = {
    'NORMAL': 'Internet operating normally',
    'MINOR_ISSUES': 'Some connectivity fluctuations detected',
    'DEGRADED': 'Significant disruptions — possible throttling',
    'BLACKOUT': 'Major outage — internet appears cut off',
}

# Visual threat meter
meter_fill = min(score, 100) // 5  # 0-20 blocks
meter = '█' * meter_fill + '░' * (20 - meter_fill)

# Bar graph from history (last 12 readings = ~6 hours at 30min intervals)
graph_data = history[-12:] if history else []
graph_lines = []
if len(graph_data) >= 3:
    max_score = max(h['score'] for h in graph_data) if graph_data else 1
    max_score = max(max_score, 10)  # floor so bars aren't all full on low scores
    for h in graph_data:
        s = h['score']
        bar_len = int((s / max_score) * 8) if max_score > 0 else 0
        bar = '▓' * bar_len + '░' * (8 - bar_len)
        ts = datetime.fromtimestamp(h['ts'], tz=timezone.utc).strftime('%H:%M')
        lvl_dot = {'NORMAL': '🟢', 'MINOR_ISSUES': '🟠', 'DEGRADED': '🟡', 'BLACKOUT': '⚫'}.get(h['level'], '⚪')
        graph_lines.append(f'  {ts} {lvl_dot} <code>{bar}</code> {s}')

# Probe status
probe_parts = []
for p in probes.get('probes', []):
    url = p.get('url', '').replace('https://', '').split('/')[0]
    lat = p.get('latency_ms', '?')
    ok = '✅' if p.get('reachable') else '❌'
    probe_parts.append(f'  {ok} {url} ({lat}ms)')

# Build message
lines = []
if level == 'BLACKOUT':
    lines.append('🚨🚨🚨 <b>IRAN INTERNET BLACKOUT</b> 🚨🚨🚨')
elif level == 'DEGRADED':
    lines.append('⚠️⚠️⚠️ <b>IRAN INTERNET DEGRADED</b> ⚠️⚠️⚠️')
else:
    lines.append('🌐 <b>IRAN INTERNET STATUS</b> 🌐')
lines.append('━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
lines.append('')

# Big status
lines.append(f'{emoji} <b>{level_desc.get(level, level)}</b>')
if prev != level:
    prev_emoji = {'NORMAL': '🟢', 'MINOR_ISSUES': '🟠', 'DEGRADED': '🟡', 'BLACKOUT': '⚫'}.get(prev, '⚪')
    lines.append(f'   {prev_emoji} {prev} → {emoji} {level}')
lines.append('')

# Threat meter
lines.append(f'<code>{meter}</code> {score}/100')
lines.append('')

# Activity graph
if graph_lines:
    lines.append('📊 <b>Recent Activity</b>')
    for gl in graph_lines:
        lines.append(gl)
    lines.append('')

# Probe results
if probe_parts:
    lines.append('🔍 <b>Iranian Websites</b>')
    for pp in probe_parts:
        lines.append(pp)
    lines.append('')

# Context
if level in ('BLACKOUT', 'DEGRADED'):
    lines.append('⚠️ <b>Iran has historically cut internet</b>')
    lines.append('<b>before and during military operations.</b>')
    lines.append('')
elif level == 'MINOR_ISSUES':
    lines.append('ℹ️ <i>Minor fluctuations are common and may</i>')
    lines.append('<i>not indicate military activity.</i>')
    lines.append('')

lines.append('━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
lines.append('📡 <b>@magenyehudaupdates</b> | Magen Yehuda')

print('\n'.join(lines))
" 2>/dev/null)
    
    if [ -n "$msg" ]; then
      send_telegram "$msg"
      log_intel "{\"type\":\"blackout\",\"level\":\"$level\",\"changed\":true,\"score\":$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['assessment']['score'])" 2>/dev/null || echo 0)}"
      
      # Update last_alert_ts in state file
      python3 -c "
import json, time
sf = '$STATE_DIR/blackout-state.json'
with open(sf) as f:
    s = json.load(f)
s['last_alert_ts'] = int(time.time())
with open(sf, 'w') as f:
    json.dump(s, f, indent=2)
" 2>/dev/null
    fi
  fi
}

check_military_flights() {
  log "✈️  Scanning military aircraft..."
  local result
  result=$(python3 "$SKILL_DIR/scripts/scan-military-flights.py" "$CONFIG_FILE" "$STATE_DIR" 2>>"$SKILL_DIR/state/watcher.log")
  local exit_code=$?
  
  if [ $exit_code -ne 0 ]; then
    log "  ⚠️  Military flight scan failed"
    return
  fi
  
  local mil_count new_count
  mil_count=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('military_count',0))" 2>/dev/null)
  new_count=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_count',0))" 2>/dev/null)
  
  log "  ✈️  Military aircraft: $mil_count total, $new_count new"
  
  if [ "${new_count:-0}" != "0" ] && [ "${new_count:-0}" -gt 0 ]; then
    local details
    details=$(echo "$result" | python3 -c "
import sys,json
d = json.load(sys.stdin)
for ac in d.get('new_aircraft', [])[:8]:
    cs = ac.get('callsign', '?')
    desc = ac.get('description', '?')
    alt = ac.get('altitude_ft', '?')
    vel = ac.get('velocity_kts', '?')
    cat = ac.get('category', '?')
    print(f'{desc}')
    print(f'  Callsign: {cs} | Alt: {alt}ft | Speed: {vel}kts')
print(f'')
cats = d.get('by_category', {})
for c, n in sorted(cats.items()):
    print(f'  {c}: {n}')
" 2>/dev/null)
    
    send_telegram "✈️✈️✈️ <b>MILITARY AIRCRAFT — PERSIAN GULF</b> ✈️✈️✈️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ $(TZ="$DISPLAY_TZ" date '+%H:%M:%S %Z') | $mil_count aircraft tracked

${details}

<i>⚠️ Heavy tanker/bomber activity may indicate imminent strike sortie</i>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 <b>${CHAT_ID}</b> | ${CHANNEL_NAME}"
    
    log_intel "{\"type\":\"military_flights\",\"total\":$mil_count,\"new\":$new_count}"
  fi
}

check_strike_correlation() {
  # Run after fire+seismic check — correlates recent events
  local result
  result=$(python3 "$SKILL_DIR/scripts/correlate-strikes.py" "$STATE_DIR" 2>>"$SKILL_DIR/state/watcher.log")
  local count
  count=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null)
  
  if [ "${count:-0}" != "0" ] && [ "${count:-0}" -gt 0 ]; then
    local msg
    msg=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('telegram_message',''))" 2>/dev/null)
    
    if [ -n "$msg" ]; then
      log "  🎯 STRIKE CORRELATION: $count hit(s)!"
      
      local resp
      resp=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="$CHAT_ID" -d parse_mode="HTML" -d disable_web_page_preview="true" \
        --data-urlencode "text=${msg}")
      local ok=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',''))" 2>/dev/null)
      [ "$ok" = "True" ] && log "  ✅ Strike correlation alert sent" || log "  ❌ Strike alert failed"
      
      log_intel "{\"type\":\"strike_correlation\",\"count\":$count}"
    fi
  fi
}

# ══════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════

# Initialize intervals
get_threat_intervals
echo "$THREAT_LEVEL" > "$THREAT_FILE"

# Count sources
OSINT_SOURCES=$(python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
tg = len(c.get('telegram_osint_channels', []))
tw = len(c.get('twitter_accounts', []))
rss = len(c.get('rss_feeds', []))
sei = 1 if c.get('usgs_seismic', {}).get('enabled') else 0
print(f'{tg} TG channels + {tw} X accounts + {rss} RSS feeds + {sei} seismic')
" 2>/dev/null || echo "?")

log "🚀 Real-time watcher started (adaptive threat-level system)"
log "   Threat level: 🟢 GREEN (baseline)"
log "   Oref: ${EFFECTIVE_OREF}s | OSINT: ${EFFECTIVE_OSINT}s | Poly: ${EFFECTIVE_POLY}s | Fires: ${EFFECTIVE_FIRES}s"
log "   Sources: $OSINT_SOURCES"
log "   Telegram: $CHAT_ID"
log "   Proxy: ${NORD_PROXY:+Israel 🇮🇱}"
log "   Escalation: GREEN→ELEVATED→HIGH→CRITICAL (auto-scales on sirens)"

LAST_POLY_CHECK=0
LAST_OSINT_CHECK=0
LAST_FIRES_CHECK=0
LAST_INTEL_CHECK=0
LAST_LOG_ROTATE=0
LAST_PINNED_UPDATE=0
PINNED_UPDATE_INTERVAL=60  # Update pinned status every 60 seconds
MAX_LOG_SIZE=512000   # 500KB

while true; do
  # Rotate log periodically (check every 5 min)
  NOW_ROT=$(date +%s)
  if [ $((NOW_ROT - LAST_LOG_ROTATE)) -ge 300 ]; then
    LOG_SIZE=$(stat -f%z "$SKILL_DIR/state/watcher.log" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -gt "$MAX_LOG_SIZE" ]; then
      mkdir -p "$SKILL_DIR/state/logs"
      mv "$SKILL_DIR/state/watcher.log" "$SKILL_DIR/state/logs/watcher-$(date +%Y%m%d-%H%M%S).log"
      touch "$SKILL_DIR/state/watcher.log"
      ls -t "$SKILL_DIR/state/logs"/watcher-*.log 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
      log "🔄 Log rotated (was ${LOG_SIZE} bytes)"
    fi
    LAST_LOG_ROTATE=$NOW_ROT
  fi

  # Always check Oref (fastest loop)
  check_oref

  # Evaluate threat level after every Oref check
  evaluate_threat_level

  NOW=$(date +%s)

  # Check Polymarket on threat-adjusted interval
  if [ $((NOW - LAST_POLY_CHECK)) -ge $EFFECTIVE_POLY ]; then
    check_polymarket
    LAST_POLY_CHECK=$NOW
  fi

  # Unified OSINT scan on threat-adjusted interval
  if [ $((NOW - LAST_OSINT_CHECK)) -ge $EFFECTIVE_OSINT ]; then
    check_osint
    LAST_OSINT_CHECK=$NOW
  fi

  # Satellite fire + seismic detection on threat-adjusted interval
  if [ $((NOW - LAST_FIRES_CHECK)) -ge $EFFECTIVE_FIRES ]; then
    check_fires_seismic
    check_strike_correlation  # Run correlation after fire/seismic data refreshes
    LAST_FIRES_CHECK=$NOW
  fi

  # Extended intel: blackout + military flights (less frequent)
  if [ $((NOW - LAST_INTEL_CHECK)) -ge $EFFECTIVE_INTEL ]; then
    check_blackout
    check_military_flights
    LAST_INTEL_CHECK=$NOW
  fi

  # Update pinned live status message
  if [ $((NOW - LAST_PINNED_UPDATE)) -ge $PINNED_UPDATE_INTERVAL ]; then
    python3 "$SKILL_DIR/scripts/pinned-status.py" "$CONFIG_FILE" "$STATE_DIR" 2>/dev/null
    LAST_PINNED_UPDATE=$NOW
  fi

  sleep "$EFFECTIVE_OREF"
done
