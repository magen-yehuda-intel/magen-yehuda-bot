#!/usr/bin/env python3
"""
Energy & Oil/Gas Impact Tracker for Magen Yehuda Dashboard.
Extracts energy-related events from intel feed, classifies them,
and outputs structured JSON for the dashboard energy panel.
Also identifies struck/damaged facilities for map markers.
"""
import json, os, re, time, sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_PATH = os.path.join(SKILL_DIR, 'docs', 'intel-feed.json')
V2_DATA = os.path.join(SKILL_DIR, 'scripts', 'v2-data.js')
OUTPUT = os.path.join(SKILL_DIR, 'docs', 'energy-feed.json')

# ─── Keywords ───
EN_KEYWORDS = [
    'gas', 'oil', 'tanker', 'lng', 'hormuz', 'pipeline', 'refinery', 'crude',
    'petroleum', 'energy', 'leviathan', 'karish', 'tamar', 'kharg', 'bushehr',
    'south pars', 'jask', 'fujairah', 'shipping', 'vessel', 'maritime', 'strait',
    'blockade', 'naval blockade', 'opec', 'barrel', 'brent', 'wti',
    'fuel', 'diesel', 'kerosene', 'lpg', 'propane', 'asaluyeh',
    'abadan', 'isfahan refin', 'bandar abbas', 'arak refin', 'port of jask',
    'neka', 'gachsaran', 'marun', 'ahvaz oil', 'forouzan', 'doroud',
    'natural gas', 'gas field', 'gas platform', 'gas production',
    'oil depot', 'oil terminal', 'oil storage', 'oil facility', 'oil price',
    'gas price', 'energy price', 'energy security', 'energy crisis',
    'suez', 'bab el-mandeb', 'persian gulf',
]
HE_KEYWORDS = [
    'גז', 'נפט', 'אנרגיה', 'הורמוז', 'מכלית', 'בית זיקוק', 'לוויתן', 'כריש',
    'תמר', 'חארג', 'דלק', 'צינור', 'מיכל', 'שדה גז', 'קידוח',
]

# ─── Event classification ───
CATEGORIES = {
    'attack': ['strike', 'struck', 'attack', 'hit', 'bomb', 'destroy', 'missile',
               'drone', 'fire', 'burning', 'ablaze', 'damage', 'explosion',
               'תקיפה', 'פגיעה', 'הפצצה', 'שריפה'],
    'shutdown': ['shut down', 'halt', 'suspend', 'close', 'closed', 'stop',
                 'offline', 'ceased', 'shutdown', 'evacuate', 'הפסקת', 'השבתה', 'סגירה'],
    'blockade': ['blockade', 'block', 'closed strait', 'closure', 'hormuz close',
                 'strait of hormuz', 'naval block', 'חסימה', 'סגירת מצר'],
    'price': ['price', 'surge', 'spike', 'jump', 'leap', 'soar', 'rally',
              'dollar', '$', '€', '£', 'barrel', 'brent', 'wti', 'מחיר'],
    'military': ['navy', 'naval', 'submarine', 'carrier', 'destroyer', 'warship',
                 'fleet', 'patrol', 'escort', 'חיל הים', 'צוללת'],
    'disruption': ['tanker', 'shipping', 'vessel', 'cargo', 'route', 'diverted',
                   'reroute', 'delay', 'stuck', 'insurance', 'transit'],
    'diplomatic': ['sanction', 'negotiate', 'pressure', 'demand', 'warn',
                   'urge', 'condemn', 'un security', 'opec', 'china', 'russia'],
}

# Known facility locations for damage markers
FACILITY_COORDS = {
    'kharg': (29.240, 50.330, 'Kharg Island Terminal'),
    'south pars': (27.5, 52.6, 'South Pars Gas Field'),
    'asaluyeh': (27.48, 52.61, 'Asaluyeh Petrochemical Zone'),
    'bushehr': (28.97, 50.84, 'Bushehr'),
    'abadan': (30.339, 48.283, 'Abadan Refinery'),
    'isfahan refin': (32.65, 51.68, 'Isfahan Refinery'),
    'bandar abbas': (27.19, 56.27, 'Bandar Abbas Refinery'),
    'jask': (25.64, 57.77, 'Jask Oil Terminal'),
    'fujairah': (25.13, 56.33, 'Fujairah Oil Terminal (UAE)'),
    'leviathan': (32.95, 34.15, 'Leviathan Gas Platform'),
    'karish': (32.78, 34.12, 'Karish Gas Platform'),
    'tamar': (32.60, 34.03, 'Tamar Gas Platform'),
    'haifa refin': (32.81, 35.01, 'Haifa Refinery'),
    'eilat ashkelon': (31.67, 34.57, 'Eilat-Ashkelon Pipeline'),
    'tehran refin': (35.69, 51.39, 'Tehran Refinery'),
    'arak': (34.09, 49.77, 'Arak Refinery'),
    'tabriz': (38.08, 46.29, 'Tabriz Refinery'),
    'neka': (36.65, 53.30, 'Neka Oil Terminal'),
    'strait of hormuz': (26.57, 56.25, 'Strait of Hormuz'),
    'hormuz': (26.57, 56.25, 'Strait of Hormuz'),
    'suez': (30.01, 32.58, 'Suez Canal'),
    'kuwait': (29.31, 47.48, 'Kuwait'),
    'qatar': (25.35, 51.18, 'Qatar'),
}


def classify_event(text: str) -> list:
    """Return list of matching categories."""
    t = text.lower()
    cats = []
    for cat, kws in CATEGORIES.items():
        if any(kw in t for kw in kws):
            cats.append(cat)
    return cats or ['info']


def extract_facilities_hit(text: str) -> list:
    """Identify facilities mentioned in attack/damage context."""
    t = text.lower()
    attack_words = ['strike', 'struck', 'attack', 'hit', 'bomb', 'destroy',
                    'fire', 'burning', 'damage', 'תקיפה', 'פגיעה', 'שריפה']
    has_attack = any(w in t for w in attack_words)
    shutdown_words = ['shut', 'halt', 'suspend', 'close', 'offline', 'ceased', 'השבתה']
    has_shutdown = any(w in t for w in shutdown_words)

    hits = []
    seen_names = set()
    for key, (lat, lon, name) in FACILITY_COORDS.items():
        if key in t and (has_attack or has_shutdown) and name not in seen_names:
            status = 'struck' if has_attack else 'shutdown'
            hits.append({'key': name.lower().replace(' ', '_'), 'lat': lat, 'lon': lon, 'name': name, 'status': status})
            seen_names.add(name)
    return hits


def severity_score(cats: list, text: str) -> int:
    """0-100 severity for sorting."""
    s = 0
    if 'attack' in cats: s += 50
    if 'blockade' in cats: s += 40
    if 'shutdown' in cats: s += 35
    if 'military' in cats: s += 25
    if 'price' in cats: s += 20
    if 'disruption' in cats: s += 15
    # Boost for key terms
    t = text.lower()
    if 'hormuz' in t: s += 20
    if 'nuclear' in t: s += 15
    if any(x in t for x in ['leviathan', 'karish', 'tamar']): s += 15
    if any(x in t for x in ['kharg', 'south pars']): s += 15
    return min(s, 100)


def cat_emoji(cat: str) -> str:
    return {
        'attack': '💥', 'shutdown': '🚫', 'blockade': '⛔',
        'price': '📈', 'military': '⚓', 'disruption': '🚢',
        'diplomatic': '🏛️', 'info': 'ℹ️',
    }.get(cat, 'ℹ️')


def main():
    # Load feed
    with open(FEED_PATH) as f:
        raw = json.load(f)
    events = raw if isinstance(raw, list) else raw.get('events', [])

    now = time.time()
    energy_events = []
    facilities_affected = {}  # key -> {status, name, lat, lon, last_event_ts, events}

    for e in events:
        text = e.get('text', '') or ''
        ts = float(e.get('timestamp', e.get('ts', 0)))
        age_h = (now - ts) / 3600
        if age_h > 72:
            continue

        t_lower = text.lower()
        if not (any(k in t_lower for k in EN_KEYWORDS) or any(k in text for k in HE_KEYWORDS)):
            continue

        cats = classify_event(text)
        sev = severity_score(cats, text)
        source = e.get('source', '') or 'unknown'

        entry = {
            'ts': ts,
            'age_h': round(age_h, 1),
            'text': text[:300],
            'source': source,
            'categories': cats,
            'severity': sev,
            'emoji': cat_emoji(cats[0]),
        }
        energy_events.append(entry)

        # Track facility damage
        for fac in extract_facilities_hit(text):
            key = fac['key']
            if key not in facilities_affected or facilities_affected[key]['last_ts'] < ts:
                facilities_affected[key] = {
                    'name': fac['name'],
                    'lat': fac['lat'],
                    'lon': fac['lon'],
                    'status': fac['status'],
                    'last_ts': ts,
                    'event_count': facilities_affected.get(key, {}).get('event_count', 0) + 1,
                }
            else:
                facilities_affected[key]['event_count'] += 1

    # Sort by severity then recency
    energy_events.sort(key=lambda x: (-x['severity'], -x['ts']))

    # Build summary stats
    cats_count = {}
    for ev in energy_events:
        for c in ev['categories']:
            cats_count[c] = cats_count.get(c, 0) + 1

    output = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'total_events': len(energy_events),
        'window_hours': 72,
        'summary': {
            'categories': cats_count,
            'facilities_affected': len(facilities_affected),
            'top_severity': energy_events[0]['severity'] if energy_events else 0,
        },
        'facilities': [
            {**v, 'last_ts': v['last_ts']}
            for v in sorted(facilities_affected.values(), key=lambda x: -x['last_ts'])
        ],
        'events': energy_events[:100],  # top 100
    }

    with open(OUTPUT, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=None)

    print(f"Energy tracker: {len(energy_events)} events, {len(facilities_affected)} facilities affected")
    for fac in output['facilities']:
        print(f"  {'💥' if fac['status']=='struck' else '🚫'} {fac['name']} — {fac['status']} ({fac['event_count']} reports)")

    return output


if __name__ == '__main__':
    main()
