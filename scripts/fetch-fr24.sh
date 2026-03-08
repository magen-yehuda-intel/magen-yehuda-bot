#!/bin/bash
# Fetch FlightRadar24 data and write static JSON cache for CENTCOM dashboard
# Run via cron every 30s-60s
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCS_DIR="$SCRIPT_DIR/../docs"
OUT="$DOCS_DIR/fr24-cache.json"

DATA=$(curl -s --max-time 10 \
  "https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds=42,12,24,62&faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=0&estimated=1&maxage=14400&gliders=0&stats=0")

if [ -z "$DATA" ]; then
  exit 1
fi

python3 -c "
import json,sys
d=json.loads('''$DATA''') if False else json.load(sys.stdin)
aircraft=[]
for k,v in d.items():
    if not isinstance(v,list) or len(v)<13: continue
    aircraft.append({
        'id':k,'lat':v[1],'lon':v[2],'heading':v[3],'alt':v[4],'speed':v[5],
        'actype':v[8] or '','reg':v[9] or '','origin':v[11] or '','dest':v[12] or '',
        'callsign':(v[16] or '').strip()
    })
json.dump({'ts':$(date +%s),'count':len(aircraft),'aircraft':aircraft},sys.stdout)
" <<< "$DATA" > "$OUT.tmp" 2>/dev/null && mv "$OUT.tmp" "$OUT"
