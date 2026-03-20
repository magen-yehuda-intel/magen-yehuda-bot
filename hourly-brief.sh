#!/bin/bash
# Hourly story-style brief — runs 6 times then self-destructs
set -euo pipefail
cd "$(dirname "$0")"

STATE_FILE="state/hourly-brief-count.txt"
MAX_RUNS=6

# Track run count
if [ -f "$STATE_FILE" ]; then
  COUNT=$(cat "$STATE_FILE")
else
  COUNT=0
fi

COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

# Gather fresh intel
INTEL=$(bash ctl.sh check 2>/dev/null)

# Generate and send brief
python3 << 'PYEOF'
import json, sys, os, urllib.request
from datetime import datetime, timezone, timedelta

token = None
with open('config.json') as f:
    config = json.load(f)
    token = config.get('telegram_bot_token')

# Load intel from ctl.sh check
import subprocess
result = subprocess.run(['bash', 'ctl.sh', 'check'], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)) or '.')
try:
    intel = json.loads(result.stdout)
except:
    intel = {}

count = int(open('state/hourly-brief-count.txt').read().strip())
et = datetime.now(timezone(timedelta(hours=-4)))
ist = datetime.now(timezone(timedelta(hours=2)))
et_str = et.strftime('%I:%M %p ET')
ist_str = ist.strftime('%I:%M %p IST')

headlines = intel.get('headlines', [])
threat_level = intel.get('threat_level', 'UNKNOWN')
threat_score = intel.get('threat_score', 0)
commodities = {c['name']: c for c in intel.get('commodities', [])}
polymarket = {p['q'][:30]: p for p in intel.get('polymarket', [])}
oref = intel.get('oref', {}).get('status', 'unknown')

# Build story from headlines — group by theme
themes = {
    'strikes': [], 'diplomacy': [], 'gulf': [], 'iran_internal': [],
    'lebanon': [], 'humanitarian': [], 'us': [], 'other': []
}
import html as html_mod
for h in headlines[:40]:  # Recent ones
    t = h.get('title', '')
    url = h.get('url', '')
    time_str = h.get('time', '')
    tl = t.lower()
    entry = {'title': t, 'url': url, 'time': time_str}
    if any(w in tl for w in ['strike', 'bomb', 'kill', 'attack', 'missile', 'intercept', 'drone']):
        themes['strikes'].append(entry)
    elif any(w in tl for w in ['diplomac', 'ceasefire', 'talk', 'negotiat', 'deal']):
        themes['diplomacy'].append(entry)
    elif any(w in tl for w in ['hormuz', 'gulf', 'oil', 'tanker', 'crude', 'shipping', 'strait']):
        themes['gulf'].append(entry)
    elif any(w in tl for w in ['iran', 'tehran', 'khamenei', 'irgc', 'larijani']):
        themes['iran_internal'].append(entry)
    elif any(w in tl for w in ['lebanon', 'hezbollah', 'beirut']):
        themes['lebanon'].append(entry)
    elif any(w in tl for w in ['trump', 'pentagon', 'congress', 'us ', 'american', 'nato']):
        themes['us'].append(entry)
    elif any(w in tl for w in ['humanitarian', 'civilian', 'refugee', 'hunger', 'child']):
        themes['humanitarian'].append(entry)
    else:
        themes['other'].append(entry)

def fmt_headline(entry):
    """Format headline as clickable HTML link with timestamp"""
    t = html_mod.escape(entry['title'])
    ts = entry.get('time', '')
    url = entry.get('url', '')
    ts_prefix = f"[{ts}] " if ts else ""
    if url:
        return f'  • {ts_prefix}<a href="{url}">{t}</a>'
    return f'  • {ts_prefix}{t}'

# Compose story-style brief
emoji_map = {
    'strikes': '💥', 'diplomacy': '🕊️', 'gulf': '🛢️', 'iran_internal': '🇮🇷',
    'lebanon': '🇱🇧', 'humanitarian': '🏥', 'us': '🇺🇸', 'other': '📰'
}
label_map = {
    'strikes': 'Battlefield', 'diplomacy': 'Diplomacy', 'gulf': 'Energy & Hormuz',
    'iran_internal': 'Inside Iran', 'lebanon': 'Lebanon Front',
    'humanitarian': 'Humanitarian', 'us': 'Washington', 'other': 'Also Happening'
}

# Build English brief
lines = [f"📡 HOURLY BRIEF #{count}/6 — {et_str} / {ist_str}"]
lines.append(f"Threat: {threat_level} (Score {threat_score}) | Oref: {oref.upper()}\n")

# Story intro
hour = et.hour
if hour < 5:
    time_feel = "The Middle East doesn't sleep tonight."
elif hour < 9:
    time_feel = "Dawn breaks across a region still at war."
elif hour < 13:
    time_feel = "Morning brings fresh headlines, no fresh hope."
elif hour < 17:
    time_feel = "The afternoon news cycle churns on."
elif hour < 21:
    time_feel = "Evening falls — the war continues."
else:
    time_feel = "Night descends, but the conflict doesn't pause."

lines.append(time_feel + "\n")

for key in ['strikes', 'iran_internal', 'lebanon', 'gulf', 'us', 'diplomacy', 'humanitarian', 'other']:
    items = themes[key]
    if items:
        lines.append(f"{emoji_map[key]} {label_map[key]}:")
        for entry in items[:3]:
            lines.append(fmt_headline(entry))
        if len(items) > 3:
            lines.append(f"  ...and {len(items)-3} more")
        lines.append("")

# Markets
wti = commodities.get('WTI Crude Oil', {})
brent = commodities.get('Brent Crude Oil', {})
gold = commodities.get('Gold', {})
if wti:
    lines.append(f"📊 WTI ${wti.get('price',0)} ({wti.get('change',0):+.1f}%) | Brent ${brent.get('price',0)} ({brent.get('change',0):+.1f}%) | Gold ${gold.get('price',0)}")

lines.append(f"\n{'━'*30}")
if count < 6:
    lines.append(f"Next brief in ~1 hour. Stay safe. 🛡️")
else:
    lines.append(f"This was the final hourly brief. Stay safe. 🛡️")

en_msg = '\n'.join(lines)

# Build Hebrew brief
he_lines = [f"📡 תקציר שעתי #{count}/6 — {ist_str}"]
he_lines.append(f"איום: {threat_level} (ציון {threat_score}) | פיקוד העורף: {oref.upper()}\n")

time_feel_he = {
    'The Middle East doesn\'t sleep tonight.': 'המזרח התיכון לא ישן הלילה.',
    'Dawn breaks across a region still at war.': 'השחר עולה על אזור שעדיין במלחמה.',
    'Morning brings fresh headlines, no fresh hope.': 'הבוקר מביא כותרות חדשות, לא תקווה חדשה.',
    'The afternoon news cycle churns on.': 'מחזור החדשות של אחר הצהריים ממשיך.',
    'Evening falls — the war continues.': 'הערב יורד — המלחמה נמשכת.',
    'Night descends, but the conflict doesn\'t pause.': 'הלילה יורד, אבל הסכסוך לא עוצר.'
}.get(time_feel, 'המצב ממשיך.')

he_lines.append(time_feel_he + "\n")

he_label = {
    'strikes': '💥 שדה הקרב', 'diplomacy': '🕊️ דיפלומטיה', 'gulf': '🛢️ אנרגיה והורמוז',
    'iran_internal': '🇮🇷 בתוך איראן', 'lebanon': '🇱🇧 חזית לבנון',
    'humanitarian': '🏥 הומניטרי', 'us': '🇺🇸 וושינגטון', 'other': '📰 גם קורה'
}

for key in ['strikes', 'iran_internal', 'lebanon', 'gulf', 'us', 'diplomacy', 'humanitarian', 'other']:
    items = themes[key]
    if items:
        he_lines.append(f"{he_label[key]}:")
        for entry in items[:3]:
            he_lines.append(fmt_headline(entry))
        if len(items) > 3:
            he_lines.append(f"  ...ועוד {len(items)-3}")
        he_lines.append("")

if wti:
    he_lines.append(f"📊 WTI ${wti.get('price',0)} ({wti.get('change',0):+.1f}%) | ברנט ${brent.get('price',0)} ({brent.get('change',0):+.1f}%) | זהב ${gold.get('price',0)}")

he_lines.append(f"\n{'━'*30}")
if count < 6:
    he_lines.append(f"תקציר הבא בעוד ~שעה. שמרו על עצמכם 🛡️")
else:
    he_lines.append(f"זה היה התקציר השעתי האחרון. שמרו על עצמכם 🛡️")

he_msg = '\n'.join(he_lines)

# Send to both channels
for chat_id, text in [('@magenyehudaupdates', en_msg), ('@opssheagathaariupdates', he_msg)]:
    data = json.dumps({'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode()
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=data, headers={'Content-Type': 'application/json'}
    )
    try:
        r = urllib.request.urlopen(req)
        result = json.loads(r.read())
        print(f'{chat_id}: ok={result["ok"]}, msg={result["result"]["message_id"]}')
    except Exception as e:
        print(f'{chat_id}: ERROR {e}')

PYEOF

# Self-destruct after 6 runs
if [ "$COUNT" -ge "$MAX_RUNS" ]; then
  echo "Final brief sent. Removing cron job."
  crontab -l 2>/dev/null | grep -v 'hourly-brief.sh' | crontab -
  rm -f "$STATE_FILE"
fi
