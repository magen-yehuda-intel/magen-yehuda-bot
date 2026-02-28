#!/usr/bin/env bash
# MagenYehudaBot — Hourly status report to Telegram
# Sends: 1) Intel map, 2) Hebrew summary, 3) English summary

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$SKILL_DIR/config.json"
STATE_DIR="$SKILL_DIR/state"

BOT_TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['telegram_bot_token'])")
CHAT_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['telegram_chat_id'])")

NOW_UTC=$(date -u '+%Y-%m-%d %H:%M UTC')

# ── Generate fresh intel map ──
FIRE_JSON="$STATE_DIR/tmp-report-fires.json"
SEISMIC_JSON="$STATE_DIR/tmp-report-seismic.json"
MAP_FILE="$STATE_DIR/report-map.png"

python3 "$SKILL_DIR/scripts/scan-fires.py" "$CONFIG_FILE" "$STATE_DIR" --seed 2>/dev/null > "$FIRE_JSON" || echo '{"fires":[]}' > "$FIRE_JSON"
python3 "$SKILL_DIR/scripts/scan-seismic.py" "$CONFIG_FILE" "$STATE_DIR" --seed 2>/dev/null > "$SEISMIC_JSON" || echo '{"quakes":[]}' > "$SEISMIC_JSON"

python3 "$SKILL_DIR/scripts/generate-fire-map.py" "$FIRE_JSON" "$MAP_FILE" --seismic "$SEISMIC_JSON" 2>/dev/null

# ── Send map ──
if [ -f "$MAP_FILE" ]; then
  python3 -c "
import json, urllib.request, io, uuid

with open('$MAP_FILE', 'rb') as f:
    img_data = f.read()

boundary = uuid.uuid4().hex
body = io.BytesIO()
body.write(f'--{boundary}\r\n'.encode())
body.write(f'Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n$CHAT_ID\r\n'.encode())
body.write(f'--{boundary}\r\n'.encode())
body.write(f'Content-Disposition: form-data; name=\"caption\"\r\n\r\n🛰️ Iran Intel Map — $NOW_UTC\r\n'.encode())
body.write(f'--{boundary}\r\n'.encode())
body.write(b'Content-Disposition: form-data; name=\"photo\"; filename=\"intel-map.png\"\r\n')
body.write(b'Content-Type: image/png\r\n\r\n')
body.write(img_data)
body.write(b'\r\n')
body.write(f'--{boundary}--\r\n'.encode())

req = urllib.request.Request(
    f'https://api.telegram.org/bot$BOT_TOKEN/sendPhoto',
    data=body.getvalue(),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
urllib.request.urlopen(req, timeout=30)
" 2>/dev/null && echo "  📸 Map sent" || echo "  ⚠️ Map send failed"
fi

# ── Generate summaries ──
SUMMARY_JSON=$(python3 "$SKILL_DIR/scripts/generate-summary.py" 2>/dev/null)

if [ -z "$SUMMARY_JSON" ]; then
  echo "⚠️ Summary generation failed"
  exit 1
fi

# ── Send Hebrew summary ──
HEB_MSG=$(echo "$SUMMARY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['hebrew'])")

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d chat_id="$CHAT_ID" \
  -d parse_mode="HTML" \
  -d disable_web_page_preview="true" \
  --data-urlencode "text=${HEB_MSG}" >/dev/null && echo "  🇮🇱 Hebrew summary sent" || echo "  ❌ Hebrew send failed"

# Small delay between messages
sleep 2

# ── Send English summary ──
ENG_MSG=$(echo "$SUMMARY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['english'])")

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d chat_id="$CHAT_ID" \
  -d parse_mode="HTML" \
  -d disable_web_page_preview="true" \
  --data-urlencode "text=${ENG_MSG}" >/dev/null && echo "  🇺🇸 English summary sent" || echo "  ❌ English send failed"

# ── Cleanup ──
rm -f "$FIRE_JSON" "$SEISMIC_JSON"

# ── Generate and send 24h time-lapse GIF ──
TIMELAPSE_FILE="$STATE_DIR/timelapse-24h.gif"
python3 "$SKILL_DIR/scripts/generate-timelapse.py" "$CONFIG_FILE" "$STATE_DIR" "$TIMELAPSE_FILE" --hours 24 2>/dev/null

if [ -f "$TIMELAPSE_FILE" ]; then
  python3 -c "
import json, urllib.request, io, uuid

with open('$TIMELAPSE_FILE', 'rb') as f:
    gif_data = f.read()

boundary = uuid.uuid4().hex
body = io.BytesIO()
body.write(f'--{boundary}\r\n'.encode())
body.write(f'Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n$CHAT_ID\r\n'.encode())
body.write(f'--{boundary}\r\n'.encode())
body.write(f'Content-Disposition: form-data; name=\"caption\"\r\n\r\n🎬 24h Time-Lapse — Iran Fire & Seismic Activity\r\n'.encode())
body.write(f'--{boundary}\r\n'.encode())
body.write(b'Content-Disposition: form-data; name=\"animation\"; filename=\"timelapse.gif\"\r\n')
body.write(b'Content-Type: image/gif\r\n\r\n')
body.write(gif_data)
body.write(b'\r\n')
body.write(f'--{boundary}--\r\n'.encode())

req = urllib.request.Request(
    f'https://api.telegram.org/bot$BOT_TOKEN/sendAnimation',
    data=body.getvalue(),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
urllib.request.urlopen(req, timeout=60)
" 2>/dev/null && echo "  🎬 Time-lapse sent" || echo "  ⚠️ Time-lapse send failed"
fi

EVENT_COUNT=$(echo "$SUMMARY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['event_count'])" 2>/dev/null || echo "0")
echo "✅ Hourly report sent at $NOW_UTC ($EVENT_COUNT events summarized)"
