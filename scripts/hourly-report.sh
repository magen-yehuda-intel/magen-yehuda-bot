#!/usr/bin/env bash
# MagenYehudaBot — Hourly status report to Telegram
# Sends via dispatch.py: 1) Intel map, 2) Hebrew summary, 3) English summary, 4) Time-lapse GIF

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$SKILL_DIR/config.json"
STATE_DIR="$SKILL_DIR/state"
DISPATCH="python3 $SKILL_DIR/scripts/dispatch.py $CONFIG_FILE"

NOW_UTC=$(date -u '+%Y-%m-%d %H:%M UTC')

# ── Generate fresh intel map ──
FIRE_JSON="$STATE_DIR/tmp-report-fires.json"
SEISMIC_JSON="$STATE_DIR/tmp-report-seismic.json"
MAP_FILE="$STATE_DIR/report-map.png"

python3 "$SKILL_DIR/scripts/scan-fires.py" "$CONFIG_FILE" "$STATE_DIR" --seed 2>/dev/null > "$FIRE_JSON" || echo '{"fires":[]}' > "$FIRE_JSON"
python3 "$SKILL_DIR/scripts/scan-seismic.py" "$CONFIG_FILE" "$STATE_DIR" --seed 2>/dev/null > "$SEISMIC_JSON" || echo '{"quakes":[]}' > "$SEISMIC_JSON"

python3 "$SKILL_DIR/scripts/generate-fire-map.py" "$FIRE_JSON" "$MAP_FILE" --seismic "$SEISMIC_JSON" 2>/dev/null

# ── Send map via dispatch ──
if [ -f "$MAP_FILE" ]; then
  echo "{\"type\":\"map\",\"severity\":\"LOW\",\"image\":\"$MAP_FILE\",\"image_importance\":\"medium\",\"image_caption\":\"🛰️ Iran Intel Map — $NOW_UTC\",\"image_caption_he\":\"\u200F🛰️ מפת מודיעין איראן — $NOW_UTC\"}" | $DISPATCH 2>/dev/null && echo "  📸 Map sent" || echo "  ⚠️ Map send failed"
fi

# ── Generate summaries ──
SUMMARY_JSON=$(python3 "$SKILL_DIR/scripts/generate-summary.py" 2>/dev/null)

if [ -z "$SUMMARY_JSON" ]; then
  echo "⚠️ Summary generation failed"
  exit 1
fi

# ── Send Hebrew summary ──
HEB_MSG=$(echo "$SUMMARY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['hebrew'])")

python3 -c "
import json, sys
msg = sys.stdin.read()
event = {'type': 'summary_he', 'severity': 'LOW', 'text_he': msg, 'text_en': ''}
print(json.dumps(event, ensure_ascii=False))
" <<< "$HEB_MSG" | $DISPATCH 2>/dev/null && echo "  🇮🇱 Hebrew summary sent" || echo "  ❌ Hebrew send failed"

sleep 2

# ── Send English summary ──
ENG_MSG=$(echo "$SUMMARY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['english'])")

python3 -c "
import json, sys
msg = sys.stdin.read()
event = {'type': 'summary_en', 'severity': 'LOW', 'text_he': '', 'text_en': msg}
print(json.dumps(event, ensure_ascii=False))
" <<< "$ENG_MSG" | $DISPATCH 2>/dev/null && echo "  🇺🇸 English summary sent" || echo "  ❌ English send failed"

# ── Generate and send flight radar map ──
FLIGHT_MAP="$STATE_DIR/flight-map.png"
FLIGHT_JSON=$(python3 "$SKILL_DIR/scripts/generate-flight-map.py" "$CONFIG_FILE" "$STATE_DIR" "$FLIGHT_MAP" 2>/dev/null || echo '{}')

if [ -f "$FLIGHT_MAP" ]; then
  FLIGHT_TOTAL=$(echo "$FLIGHT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
  FLIGHT_IRAN=$(echo "$FLIGHT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('over_iran',0))" 2>/dev/null || echo "0")
  echo "{\"type\":\"flight_map\",\"severity\":\"LOW\",\"image\":\"$FLIGHT_MAP\",\"image_importance\":\"high\",\"image_caption\":\"✈️ Air Traffic — ${FLIGHT_TOTAL} aircraft, ${FLIGHT_IRAN} over Iran — $NOW_UTC\",\"image_caption_he\":\"\u200F✈️ תנועה אווירית — ${FLIGHT_TOTAL} מטוסים, ${FLIGHT_IRAN} מעל איראן — $NOW_UTC\"}" | $DISPATCH 2>/dev/null && echo "  ✈️ Flight map sent" || echo "  ⚠️ Flight map send failed"
fi

# ── Cleanup ──
rm -f "$FIRE_JSON" "$SEISMIC_JSON"

# ── Generate and send 24h time-lapse GIF ──
TIMELAPSE_FILE="$STATE_DIR/timelapse-24h.gif"
python3 "$SKILL_DIR/scripts/generate-timelapse.py" "$CONFIG_FILE" "$STATE_DIR" "$TIMELAPSE_FILE" --hours 24 2>/dev/null

if [ -f "$TIMELAPSE_FILE" ]; then
  echo "{\"type\":\"timelapse\",\"severity\":\"LOW\",\"gif\":\"$TIMELAPSE_FILE\",\"gif_caption\":\"🎬 24h Time-Lapse — Iran Fire & Seismic Activity\"}" | $DISPATCH 2>/dev/null && echo "  🎬 Time-lapse sent" || echo "  ⚠️ Time-lapse send failed"
fi

EVENT_COUNT=$(echo "$SUMMARY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['event_count'])" 2>/dev/null || echo "0")
echo "✅ Hourly report sent at $NOW_UTC ($EVENT_COUNT events summarized)"
