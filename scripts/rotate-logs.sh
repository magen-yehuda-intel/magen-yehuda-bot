#!/usr/bin/env bash
# Size-based rotation for Magen state logs. Keeps the last 3 gzip archives per file.
# Usage: scripts/rotate-logs.sh [max_bytes]   (default 5 MB)
# intel-log.jsonl is copy-truncated (writers hold it open / append); archives in state/logs/.
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$SKILL_DIR/state"; ARCH="$STATE/logs"; KEEP=3
MAX="${1:-5242880}"
mkdir -p "$ARCH"
fsize() { stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null || echo 0; }
for f in feed-export.log hourly-report.log enrich-intel.log brief-gen.log sitrep-cron.log fr24.log \
         watcher.log watcher-alerts.log watcher-launchd.log intel-log.jsonl; do
  p="$STATE/$f"; [ -f "$p" ] || continue
  s=$(fsize "$p"); [ "$s" -gt "$MAX" ] || continue
  ts=$(date +%Y%m%d-%H%M%S)
  if [ "$f" = "intel-log.jsonl" ]; then
    # archive, then keep only the last 48h in place (hourly report/brief/export read it)
    cp "$p" "$ARCH/$f.$ts"
    python3 - "$p" <<'PY'
import json, sys, time
p = sys.argv[1]; cut = time.time() - 48 * 3600; keep = []
for line in open(p, encoding="utf-8", errors="replace"):
    try:
        if float(json.loads(line).get("logged_at", 0)) >= cut: keep.append(line)
    except Exception: pass
with open(p, "r+", encoding="utf-8") as f:   # in-place rewrite keeps the inode for open appenders
    f.seek(0); f.writelines(keep); f.truncate()
PY
  else
    cp "$p" "$ARCH/$f.$ts" && : > "$p"
  fi
  gzip -f "$ARCH/$f.$ts"
  ls -1t "$ARCH/$f".*.gz 2>/dev/null | tail -n +$((KEEP+1)) | xargs rm -f 2>/dev/null
  echo "$(date -u +%FT%TZ) rotated $f ($s bytes)"
done
