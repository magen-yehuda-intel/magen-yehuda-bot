#!/usr/bin/env bash
# Install Magen systemd --user units (Linux). Does NOT enable/start anything unless --enable.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; dst="$HOME/.config/systemd/user"
mkdir -p "$dst"; cp "$here"/magen-*.service "$here"/magen-*.timer "$dst"/
systemctl --user daemon-reload
if [ "${1:-}" = "--enable" ]; then
  systemctl --user enable --now magen-watcher.service
  for t in "$here"/magen-*.timer; do systemctl --user enable --now "$(basename "$t")"; done
fi
systemctl --user list-unit-files 'magen-*' --no-legend
