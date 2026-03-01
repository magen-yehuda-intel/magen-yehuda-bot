#!/usr/bin/env python3
"""Build standalone dashboard HTML with compacted inline data."""
import json, os, sys, hashlib
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(SKILL_DIR, "scripts/strikes-dashboard.html")
STRIKES  = os.path.join(SKILL_DIR, "state/strikes-data.json")
OUTPUT   = os.path.join(SKILL_DIR, "scripts/strikes-dashboard-standalone.html")
DOCS_OUT = os.path.join(SKILL_DIR, "docs/index.html")

with open(STRIKES) as f:
    data = json.load(f)

events = data["events"]
base_date = datetime(2023, 10, 7)

# Build lookup tables
countries = sorted(set(e.get("country","") for e in events))
sides = sorted(set(e.get("actor1_side","unknown") for e in events))
subtypes = sorted(set(e.get("sub_event_type","") for e in events))
locations = sorted(set(e.get("location","") for e in events))
country_idx = {c:i for i,c in enumerate(countries)}
side_idx = {s:i for i,s in enumerate(sides)}
subtype_idx = {s:i for i,s in enumerate(subtypes)}
loc_idx = {l:i for i,l in enumerate(locations)}

# Compact rows: [day, lat*1000, lon*1000, country_i, side_i, fatalities, subtype_i, loc_i, actor1, actor2, confidence, notes, timestamp]
cutoff_90d = (datetime.utcnow() - base_date).days - 90
rows = []
for e in events:
    d = e.get("date","2023-10-07")
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        day = (dt - base_date).days
    except:
        day = 0
    lat = int(round(e.get("lat",0)*1000))
    lon = int(round(e.get("lon",0)*1000))
    ci = country_idx.get(e.get("country",""), 0)
    si = side_idx.get(e.get("actor1_side","unknown"), 0)
    fat = e.get("fatalities", 0) or 0
    sti = subtype_idx.get(e.get("sub_event_type",""), 0)
    li = loc_idx.get(e.get("location",""), -1)
    a1 = e.get("actor1_display","") or e.get("actor1","") or ""
    a2 = e.get("actor2_display","") or e.get("actor2","") or ""
    # Confidence: h=high, m=medium, l=low
    conf = "h"
    src = e.get("source","")
    if src == "firms": conf = "m"
    elif "osint" in src.lower(): conf = "m"
    # Notes: only for recent events or events with fatalities
    notes = ""
    if day >= cutoff_90d or fat > 0:
        n = e.get("notes","") or ""
        if n: notes = n[:150]
    # Timestamp (real event time, 0 for ACLED)
    ts = 0
    raw_ts = e.get("timestamp","") or ""
    if raw_ts:
        try:
            ts_val = int(raw_ts)
            # ACLED timestamps are import artifacts (all similar epoch)
            # Only keep if > 2024-01-01 and looks like real event time
            if ts_val > 1704067200 and src != "acled":
                ts = ts_val
        except:
            pass
    rows.append([day, lat, lon, ci, si, fat, sti, li, a1, a2, conf, notes, ts])

compact = {
    "base": "2023-10-07",
    "countries": countries,
    "sides": sides,
    "subtypes": subtypes,
    "locations": locations,
    "rows": rows
}

compact_json = json.dumps(compact, ensure_ascii=False, separators=(',',':'))

with open(TEMPLATE) as f:
    template = f.read()

standalone = template.replace("const C = COMPACT_DATA;", f"const C = {compact_json};")

with open(OUTPUT, "w") as f:
    f.write(standalone)
os.makedirs(os.path.dirname(DOCS_OUT), exist_ok=True)
with open(DOCS_OUT, "w") as f:
    f.write(standalone)

size_mb = os.path.getsize(OUTPUT) / 1048576
n_events = len(rows)
print(f"Built standalone: {size_mb:.1f}MB, {n_events} events")
print(f"  → {OUTPUT}")
print(f"  → {DOCS_OUT}")
