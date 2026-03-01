#!/usr/bin/env bash
# Push Oref alerts from local watcher state to the Azure API backend.
# Called after each Oref poll cycle. Reads config.json for API URL/key.
# Falls back to env vars MAGEN_API_URL and MAGEN_API_KEY.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$SKILL_DIR/state"
CONFIG="$SKILL_DIR/config.json"

# Read API config
API_URL="${MAGEN_API_URL:-}"
API_KEY="${MAGEN_API_KEY:-}"

if [ -z "$API_URL" ] && [ -f "$CONFIG" ]; then
  API_URL=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('dashboard',{}).get('api_url',''))" 2>/dev/null || true)
  API_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('dashboard',{}).get('api_key',''))" 2>/dev/null || true)
fi

[ -z "$API_URL" ] && exit 0  # No API configured

# Read Oref state
OREF_FILE="$STATE_DIR/oref-last-alert.json"
[ -f "$OREF_FILE" ] || echo '{"alerts":[]}' > "$OREF_FILE"

# Push
curl -s -m 5 -X POST "${API_URL}/api/push/oref" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d @"$OREF_FILE" >/dev/null 2>&1 || true
