#!/bin/bash
# Master control for Iran-Israel Alert Monitor
# Usage: bash ctl.sh [start|stop|status|check|post|teardown]

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SKILL_DIR/state/watcher.pid"
LOG_FILE="$SKILL_DIR/state/watcher.log"
LOG_DIR="$SKILL_DIR/state/logs"
CRON_NAME="Iran-Israel Alert Monitor"
MAX_LOG_SIZE=512000   # 500KB — rotate when exceeded
MAX_LOG_FILES=5       # Keep 5 rotated logs

rotate_log() {
  [ ! -f "$LOG_FILE" ] && return
  local size=$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
  if [ "$size" -gt "$MAX_LOG_SIZE" ]; then
    mkdir -p "$LOG_DIR"
    local ts=$(date +%Y%m%d-%H%M%S)
    mv "$LOG_FILE" "$LOG_DIR/watcher-${ts}.log"
    touch "$LOG_FILE"
    # Prune old logs
    ls -t "$LOG_DIR"/watcher-*.log 2>/dev/null | tail -n +$((MAX_LOG_FILES + 1)) | xargs rm -f 2>/dev/null
    echo "[$(TZ=Asia/Jerusalem date '+%Y-%m-%d %H:%M:%S %Z')] 🔄 Log rotated (was ${size} bytes)" >> "$LOG_FILE"
  fi
}

case "${1:-help}" in

  start)
    # Start the real-time watcher daemon
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "⚠️  Watcher already running (PID $(cat "$PID_FILE"))"
      exit 0
    fi
    rotate_log
    echo "🚀 Starting real-time watcher..."
    nohup bash "$SKILL_DIR/scripts/realtime-watcher.sh" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ Watcher started (PID $!). Log: $LOG_FILE"
    ;;

  start-foreground)
    # Run watcher in foreground (for Docker/container use)
    echo "🚀 Starting real-time watcher (foreground mode)..."
    exec bash "$SKILL_DIR/scripts/realtime-watcher.sh" 2>&1 | tee -a "$LOG_FILE"
    ;;

  stop)
    # Stop the real-time watcher
    # 1. Kill the tracked PID + children
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        pkill -P "$PID" 2>/dev/null || true
        kill "$PID" 2>/dev/null || true
        echo "✅ Watcher stopped (PID $PID)"
      else
        echo "⚠️  Watcher not running (stale PID $PID)"
      fi
      rm -f "$PID_FILE"
    else
      echo "⚠️  No watcher PID file found"
    fi
    # 2. Kill any orphaned watcher instances for THIS skill directory
    _orphans=""
    for _p in $(pgrep -f "realtime-watcher\\.sh" 2>/dev/null); do
      if ps -p "$_p" -o args= 2>/dev/null | grep -q "$SKILL_DIR"; then
        _orphans="$_orphans $_p"
      fi
    done
    if [ -n "$_orphans" ]; then
      # First pass: SIGTERM all orphans + their children
      for _p in $_orphans; do
        pkill -P "$_p" 2>/dev/null || true
        kill "$_p" 2>/dev/null || true
      done
      sleep 1
      # Second pass: SIGKILL any survivors
      for _p in $_orphans; do
        kill -0 "$_p" 2>/dev/null && kill -9 "$_p" 2>/dev/null || true
      done
      echo "🧹 Killed orphaned watcher(s):$_orphans"
    fi
    ;;

  status)
    echo "🔴 Iran-Israel Alert Monitor — Status"
    echo "======================================"
    # Watcher
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "📡 Real-time watcher: RUNNING (PID $(cat "$PID_FILE"))"
      echo "   Log: tail -20 $LOG_FILE"
    else
      echo "📡 Real-time watcher: STOPPED"
    fi
    # Cron
    CRON_STATUS=$(openclaw cron list 2>/dev/null | grep -i "iran-israel" || echo "")
    if [ -n "$CRON_STATUS" ]; then
      echo "⏰ Cron job: ACTIVE"
      echo "   $CRON_STATUS"
    else
      echo "⏰ Cron job: NOT FOUND"
    fi
    # Last check
    if [ -f "$SKILL_DIR/state/last-check.json" ]; then
      echo ""
      python3 -c "
import json
d = json.load(open('$SKILL_DIR/state/last-check.json'))
print(f'Last check: {d.get(\"timestamp_fmt\", \"unknown\")}')
print(f'Threat: {d.get(\"threat_level\", \"unknown\")} (score: {d.get(\"threat_score\", 0)})')
" 2>/dev/null
    fi
    echo ""
    echo "Files: $SKILL_DIR"
    ;;

  check)
    # Run a one-time full check (prints to stdout)
    SKILL_DIR="$SKILL_DIR" bash "$SKILL_DIR/scripts/check-alerts.sh"
    ;;

  post)
    # Run check and post to Telegram
    bash "$SKILL_DIR/scripts/post-telegram.sh" "${2:---force}"
    ;;

  log)
    # Show watcher log
    rotate_log
    tail -${2:-50} "$LOG_FILE" 2>/dev/null || echo "No log file yet"
    ;;

  rotate)
    # Force log rotation
    rotate_log
    echo "✅ Log rotation checked"
    echo "   Current: $(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0) bytes"
    echo "   Archived: $(ls "$LOG_DIR"/watcher-*.log 2>/dev/null | wc -l | tr -d ' ') files"
    ls -lh "$LOG_DIR"/watcher-*.log 2>/dev/null | awk '{print "     "$NF" ("$5")"}'
    ;;

  dashboard|dash|ps)
    # Show all running processes with timestamps and duration
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           🔴 IRAN-ISRAEL ALERT MONITOR — DASHBOARD         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    NOW=$(date +%s)

    # --- Watcher daemon ---
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ 📡 WATCHER DAEMON                                          │"
    echo "├─────────────────────────────────────────────────────────────┤"
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      PID=$(cat "$PID_FILE")
      STARTED=$(ps -p "$PID" -o lstart= 2>/dev/null | xargs)
      START_EPOCH=$(date -j -f "%a %b %d %T %Y" "$STARTED" +%s 2>/dev/null || echo "$NOW")
      UPTIME=$(( NOW - START_EPOCH ))
      HOURS=$((UPTIME / 3600))
      MINS=$(( (UPTIME % 3600) / 60 ))
      SECS=$((UPTIME % 60))
      CPU=$(ps -p "$PID" -o %cpu= 2>/dev/null | xargs)
      MEM=$(ps -p "$PID" -o rss= 2>/dev/null | awk '{printf "%.1f", $1/1024}')
      THREAT=$(cat "$SKILL_DIR/state/watcher-threat-level.txt" 2>/dev/null || echo "?")
      LOGSIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
      LOGSIZE_H=$(echo "$LOGSIZE" | awk '{if($1>1048576) printf "%.1fMB",$1/1048576; else printf "%.0fKB",$1/1024}')
      echo "│  Status:    ✅ RUNNING"
      echo "│  PID:       $PID"
      echo "│  Started:   $STARTED"
      echo "│  Uptime:    ${HOURS}h ${MINS}m ${SECS}s"
      echo "│  CPU:       ${CPU}%"
      echo "│  Memory:    ${MEM}MB"
      echo "│  Threat:    $THREAT"
      echo "│  Log:       $LOGSIZE_H (rotates at 500KB, keeps 5)"
    else
      echo "│  Status:    ❌ STOPPED"
    fi
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""

    # --- Child processes (scan-osint, curl, python) ---
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ 🔧 CHILD PROCESSES                                         │"
    echo "├─────────────────────────────────────────────────────────────┤"
    CHILDREN=$(ps -eo pid,ppid,etime,pcpu,rss,comm 2>/dev/null | awk -v ppid="$(cat "$PID_FILE" 2>/dev/null || echo 0)" '$2 == ppid {printf "│  PID %-7s %-12s CPU %-5s Mem %-6s %s\n", $1, $3, $4"%", int($5/1024)"MB", $6}')
    if [ -n "$CHILDREN" ]; then
      echo "$CHILDREN"
    else
      echo "│  (none — watcher is idle between scans)"
    fi
    # Also check for any orphaned scan processes
    ORPHANS=$(pgrep -laf 'scan-osint' 2>/dev/null | grep -v "$$" | grep -v grep || true)
    if [ -n "$ORPHANS" ]; then
      echo "│"
      echo "│  ⚠️  ORPHANED SCANNERS:"
      echo "$ORPHANS" | while read -r line; do echo "│  $line"; done
    fi
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""

    # --- Cron job ---
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ ⏰ CRON (2h SITREP)                                        │"
    echo "├─────────────────────────────────────────────────────────────┤"
    CRON_LINE=$(openclaw cron list 2>/dev/null | grep -i "iran-israel" || echo "")
    if [ -n "$CRON_LINE" ]; then
      echo "│  $CRON_LINE"
    else
      echo "│  ❌ NOT CONFIGURED"
    fi
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""

    # --- State files ---
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ 📁 STATE FILES                                              │"
    echo "├─────────────────────────────────────────────────────────────┤"
    for f in "$SKILL_DIR/state"/*.json "$SKILL_DIR/state"/*.txt "$SKILL_DIR/state"/*.pid; do
      [ -f "$f" ] || continue
      FNAME=$(basename "$f")
      FSIZE=$(stat -f%z "$f" 2>/dev/null || echo "?")
      FMOD=$(stat -f%Sm -t "%m/%d %H:%M" "$f" 2>/dev/null || echo "?")
      printf "│  %-35s %6s bytes  %s\n" "$FNAME" "$FSIZE" "$FMOD"
    done
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""

    # --- Archived logs ---
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ 📜 ARCHIVED LOGS                                            │"
    echo "├─────────────────────────────────────────────────────────────┤"
    ARCHIVED=$(ls -lh "$LOG_DIR"/watcher-*.log 2>/dev/null | awk '{printf "│  %-35s %s\n", $NF, $5}' || true)
    if [ -n "$ARCHIVED" ]; then
      echo "$ARCHIVED"
    else
      echo "│  (none yet — rotates at 500KB)"
    fi
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""

    # --- Lock status ---
    if [ -f "$SKILL_DIR/state/osint-scan.lock" ]; then
      LOCK_AGE=$(( NOW - $(stat -f%m "$SKILL_DIR/state/osint-scan.lock" 2>/dev/null || echo "$NOW") ))
      echo "⚠️  OSINT scan lock active (${LOCK_AGE}s old)"
      echo ""
    fi

    # --- Last watcher events ---
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ 📋 LAST 10 EVENTS                                          │"
    echo "├─────────────────────────────────────────────────────────────┤"
    tail -10 "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
      echo "│  $line"
    done
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""
    ;;

  teardown)
    echo "🛑 Tearing down Iran-Israel Alert Monitor..."
    echo ""

    # 1. Stop watcher
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      pkill -P "$PID" 2>/dev/null || true
      kill "$PID" 2>/dev/null || true
      rm -f "$PID_FILE"
      echo "✅ Watcher stopped"
    else
      echo "✅ Watcher already stopped"
    fi

    # 2. Remove cron job
    CRON_ID=$(openclaw cron list --json 2>/dev/null | python3 -c "
import json, sys
jobs = json.load(sys.stdin)
for j in jobs:
    if 'iran' in j.get('name','').lower() or 'israel' in j.get('name','').lower():
        print(j['id'])
" 2>/dev/null || echo "")
    if [ -n "$CRON_ID" ]; then
      openclaw cron remove "$CRON_ID" 2>/dev/null && echo "✅ Cron job removed ($CRON_ID)" || echo "⚠️  Failed to remove cron"
    else
      echo "✅ No cron job found"
    fi

    # 3. Remove launchd service if exists
    PLIST="$HOME/Library/LaunchAgents/com.openclaw.iran-israel-watcher.plist"
    if [ -f "$PLIST" ]; then
      launchctl unload "$PLIST" 2>/dev/null || true
      rm -f "$PLIST"
      echo "✅ LaunchAgent removed"
    else
      echo "✅ No LaunchAgent found"
    fi

    # 4. Clean state
    rm -rf "$SKILL_DIR/state"
    echo "✅ State cleared"

    echo ""
    echo "🏁 Teardown complete. Skill files preserved at: $SKILL_DIR"
    echo "   To fully remove: rm -rf $SKILL_DIR"
    ;;

  install-launchd)
    # Install launchd service so watcher survives reboots
    PLIST="$HOME/Library/LaunchAgents/com.openclaw.iran-israel-watcher.plist"
    cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.iran-israel-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SKILL_DIR}/scripts/realtime-watcher.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>SKILL_DIR</key>
        <string>${SKILL_DIR}</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${SKILL_DIR}/state/watcher.log</string>
    <key>StandardErrorPath</key>
    <string>${SKILL_DIR}/state/watcher.log</string>
</dict>
</plist>
EOF
    launchctl load "$PLIST"
    echo "✅ LaunchAgent installed — watcher will auto-start on boot"
    echo "   Stop: bash ctl.sh teardown (or launchctl unload $PLIST)"
    ;;

  help|*)
    echo "Iran-Israel Alert Monitor Control"
    echo "================================="
    echo ""
    echo "Usage: bash ctl.sh <command>"
    echo ""
    echo "Commands:"
    echo "  start            Start real-time watcher (background)"
    echo "  stop             Stop real-time watcher"
    echo "  status           Show everything: watcher, cron, last check"
    echo "  dashboard        📊 Full dashboard: processes, state, logs, resources"
    echo "  check            Run one-time full check (stdout)"
    echo "  post             Run check and post to Telegram"
    echo "  log [N]          Show last N lines of watcher log (default 50)"
    echo "  rotate           Force log rotation"
    echo "  install-launchd  Survive reboots (macOS LaunchAgent)"
    echo "  teardown         🛑 STOP EVERYTHING: watcher, cron, launchd, state"
    echo ""
    echo "Aliases: dash, ps → dashboard"
    echo ""
    echo "Skill dir: $SKILL_DIR"
    ;;
esac
