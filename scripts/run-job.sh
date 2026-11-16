#!/usr/bin/env bash
# Portable entrypoint for every scheduled Magen job (Mac cron or Linux systemd timer).
# Resolves python3 from the repo .venv if present, else PATH — no /opt/homebrew hardcoding.
# Usage: scripts/run-job.sh <hourly-report|export-feed|fr24|enrich-intel|generate-brief|sitrep|rotate-logs|watcher>
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export SKILL_DIR
cd "$SKILL_DIR"
for d in "$SKILL_DIR/.venv/bin" /opt/homebrew/bin /usr/local/bin; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH";; esac
done
export PATH
mkdir -p state
job="${1:-}"; shift || true
case "$job" in
  hourly-report)  exec >>state/hourly-report.log 2>&1; bash scripts/hourly-report.sh "$@" ;;
  export-feed)    exec >>state/feed-export.log 2>&1; python3 scripts/export-feed.py "$@" ;;
  fr24)
    exec >>state/fr24.log 2>&1
    bash scripts/fetch-fr24.sh || exit 0
    git diff --quiet -- docs/fr24-cache.json && exit 0
    # Pathspec commit: never sweep up unrelated staged changes.
    git commit -q -m "auto: fr24 cache update" -- docs/fr24-cache.json || exit 0
    git pull -q --rebase --autostash origin main && git push -q origin HEAD:main ;;
  enrich-intel)   exec >>state/enrich-intel.log 2>&1; python3 scripts/enrich-intel.py --hours 2 --limit 100 "$@" ;;
  generate-brief) exec >>state/brief-gen.log 2>&1; python3 scripts/generate-brief.py "$@" ;;
  sitrep)         exec >>state/sitrep-cron.log 2>&1; bash scripts/post-telegram.sh --force "$@" ;;
  rotate-logs)    exec >>state/rotate-logs.log 2>&1; bash scripts/rotate-logs.sh "$@" ;;
  watcher)        exec bash scripts/realtime-watcher.sh "$@" ;;
  *) echo "unknown job: $job" >&2; exit 2 ;;
esac
