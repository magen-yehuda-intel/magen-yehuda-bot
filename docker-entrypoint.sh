#!/bin/bash
set -e

# Bootstrap config from env vars if config.json doesn't exist
if [ ! -f /app/config.json ]; then
  python3 /app/scripts/env-config.py
fi

exec "$@"
