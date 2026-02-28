#!/bin/bash
# Post Iran-Israel alert check results to Telegram channel
# Usage: bash scripts/post-telegram.sh [--force]

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$SKILL_DIR/config.json"
BOT_TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('telegram_bot_token',''))" 2>/dev/null)
CHAT_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('telegram_chat_id',''))" 2>/dev/null)

# Run the check — outputs structured JSON
JSON_OUTPUT=$(SKILL_DIR="$SKILL_DIR" bash "$SKILL_DIR/scripts/check-alerts.sh" 2>/dev/null || true)

if [ -z "$JSON_OUTPUT" ]; then
  echo "❌ Check script produced no output"
  exit 1
fi

# Extract threat score
SCORE=$(echo "$JSON_OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('threat_score',0))" 2>/dev/null || echo "0")

# Post on ELEVATED (8+) or above, or if --force flag
FORCE=false
[[ "${1:-}" == "--force" ]] && FORCE=true

if [ "$SCORE" -lt 8 ] && [ "$FORCE" = false ]; then
  echo "Threat level LOW (score: $SCORE). Skipping post. Use --force to override."
  exit 0
fi

# Format for Telegram
MESSAGE=$(echo "$JSON_OUTPUT" | python3 "$SKILL_DIR/scripts/format-telegram.py" 2>/dev/null)

if [ -z "$MESSAGE" ]; then
  echo "❌ Formatter produced no output"
  exit 1
fi

# Truncate if > 4096 chars (Telegram limit)
if [ ${#MESSAGE} -gt 4000 ]; then
  MESSAGE="${MESSAGE:0:3950}

<i>... (truncated)</i>"
fi

# Send to Telegram
RESULT=$(curl -sf "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "parse_mode=HTML" \
  -d "disable_web_page_preview=true" \
  --data-urlencode "text=${MESSAGE}" 2>&1)

if echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['ok']" 2>/dev/null; then
  echo "✅ Posted to $CHAT_ID (score: $SCORE)"
else
  echo "❌ Failed to post: $RESULT"
  exit 1
fi
