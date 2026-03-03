#!/usr/bin/env python3
"""Export recent OSINT events from intel-log.jsonl → docs/intel-feed.json
Runs every 5 min via cron. Only commits+pushes if file changed."""

import json, os, re, subprocess, sys, time, hashlib
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, 'state')
DOCS_DIR = os.path.join(SKILL_DIR, 'docs')
INTEL_LOG = os.path.join(STATE_DIR, 'intel-log.jsonl')
FEED_FILE = os.path.join(DOCS_DIR, 'intel-feed.json')

HOURS = 48  # export last 48h
ME_KEYWORDS = re.compile(
    r'iran|israel|idf|irgc|hamas|hezbollah|houthi|gaza|lebanon|tehran|isfahan|bushehr|'
    r'haifa|tel.?aviv|missile|strike|attack|bomb|nuclear|siren|intercept|drone|ballistic|'
    r'centcom|natanz|qom|erbil|yemen|syria|khamenei|netanyahu|trump|pentagon|iaea|'
    r'roaring.lion|iron.dome|arrow|david.sling', re.I)

LOC_MAP = {
    'tehran': ('Tehran', 35.69, 51.39), 'isfahan': ('Isfahan', 32.65, 51.68),
    'bushehr': ('Bushehr', 28.97, 50.84), 'natanz': ('Natanz', 33.51, 51.92),
    'qom': ('Qom', 34.64, 50.88), 'shiraz': ('Shiraz', 29.59, 52.58),
    'tabriz': ('Tabriz', 38.08, 46.29), 'mashhad': ('Mashhad', 36.31, 59.60),
    'haifa': ('Haifa', 32.79, 34.99), 'tel aviv': ('Tel Aviv', 32.07, 34.77),
    'gaza': ('Gaza', 31.50, 34.47), 'beirut': ('Beirut', 33.89, 35.50),
    'erbil': ('Erbil', 36.19, 44.01), 'damascus': ('Damascus', 33.51, 36.29),
    'sanaa': ("Sana'a", 15.37, 44.19), 'jerusalem': ('Jerusalem', 31.77, 35.23),
    'iran': ('Iran', 32.43, 53.69), 'israel': ('Israel', 31.77, 35.23),
    'lebanon': ('Lebanon', 33.85, 35.86), 'yemen': ('Yemen', 15.55, 48.52),
}

def detect_side(text):
    t = text.lower()
    if any(w in t for w in ['idf', 'israel strike', 'iaf', 'israeli']): return 'israel'
    if any(w in t for w in ['irgc', 'iran launch', 'iranian']): return 'iran'
    if any(w in t for w in ['hamas', 'hezbollah', 'houthi']): return 'iran_proxy'
    if any(w in t for w in ['centcom', 'us strike', 'american', 'pentagon', 'usaf']): return 'us'
    return 'unknown'

def detect_location(text):
    t = text.lower()
    for kw, (name, lat, lon) in LOC_MAP.items():
        if kw in t:
            return name, lat, lon
    return '', 32.0, 50.0

def main():
    if not os.path.exists(INTEL_LOG):
        print("No intel-log.jsonl found")
        return

    cutoff = time.time() - HOURS * 3600
    seen_texts = set()
    events = []

    with open(INTEL_LOG) as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                ts = e.get('logged_at', 0)
                if ts < cutoff: continue
                if e.get('type') not in ('osint', 'breaking_news'): continue

                for a in e.get('alerts', []):
                    text = a.get('text', '')
                    if not text or len(text) < 20: continue
                    if not ME_KEYWORDS.search(text): continue

                    text_key = text[:80].lower().strip()
                    if text_key in seen_texts: continue
                    seen_texts.add(text_key)

                    source = a.get('channel', a.get('source', ''))
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    location, lat, lon = detect_location(text)
                    side = detect_side(text)

                    events.append({
                        'ts': int(ts),
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M'),
                        'src': source[:30],
                        'loc': location,
                        'lat': round(lat, 2),
                        'lon': round(lon, 2),
                        'side': side,
                        'text': text[:200],
                        'breaking': a.get('breaking', False),
                    })
            except:
                pass

    # Sort newest first
    events.sort(key=lambda e: e['ts'], reverse=True)

    feed = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'count': len(events),
        'events': events,
    }

    feed_json = json.dumps(feed, ensure_ascii=False, separators=(',', ':'))

    # Check if changed
    old_hash = ''
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'rb') as f:
            old_hash = hashlib.md5(f.read()).hexdigest()

    new_hash = hashlib.md5(feed_json.encode()).hexdigest()
    if old_hash == new_hash:
        print(f"Feed unchanged ({len(events)} events)")
        return

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(FEED_FILE, 'w') as f:
        f.write(feed_json)

    # Also export Oref alerts from state
    oref_state = os.path.join(STATE_DIR, 'oref-last-alert.json')
    oref_out = os.path.join(DOCS_DIR, 'oref-alerts.json')
    try:
        if os.path.exists(oref_state):
            with open(oref_state) as f:
                oref_data = json.load(f)
        else:
            oref_data = {"alerts": []}
        oref_export = {
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "source": "pikud-haoref",
            "poll_interval": "5m",
            "alert_count": len(oref_data.get("alerts", [])),
            "alerts": oref_data.get("alerts", [])
        }
        # Add last siren info from watcher log
        try:
            log_path = os.path.join(STATE_DIR, 'watcher.log')
            if os.path.exists(log_path):
                with open(log_path, 'rb') as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 32768))
                    tail = f.read().decode('utf-8', errors='replace')
                for line in reversed(tail.splitlines()):
                    if 'NEW SIRENS' in line and line.startswith('['):
                        ts_str = line[1:line.index(']')]
                        oref_export['last_siren_ts'] = ts_str
                        break
            # Get siren title from oref-alert-tmp.json
            tmp_path = os.path.join(STATE_DIR, 'oref-alert-tmp.json')
            if os.path.exists(tmp_path):
                with open(tmp_path) as f:
                    raw = f.read().strip()
                if raw and raw != '{"alerts":[]}':
                    import re
                    m = re.search(r'"title"\s*:\s*"([^"]+)"', raw)
                    if m:
                        oref_export['last_siren_title'] = m.group(1)
        except:
            pass
        with open(oref_out, 'w') as f:
            json.dump(oref_export, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"Oref export error: {ex}")

    size_kb = len(feed_json) / 1024
    print(f"Exported {len(events)} events ({size_kb:.0f}KB) → {FEED_FILE}")

    # Sync recent events to Azure Table Storage (best-effort)
    try:
        from db import insert_events, query_events
        # Get what's already in DB for last 48h
        db_events = query_events(hours=48, limit=10000)
        db_keys = set(f"{e.get('src','')}{e.get('text','')[:40]}{e.get('ts',0)}" for e in db_events)
        # Find events in export that are missing from DB
        missing = [e for e in events if f"{e.get('src','')}{e.get('text','')[:40]}{e.get('ts',0)}" not in db_keys]
        if missing:
            ok, fail = insert_events(missing)
            print(f"DB sync: {ok} new, {fail} failed (was missing {len(missing)} of {len(events)})")
        else:
            print(f"DB sync: up to date ({len(db_events)} in DB)")
    except Exception as ex:
        print(f"DB sync error: {ex}")

    # Git commit + push
    try:
        subprocess.run(['git', 'add', 'docs/intel-feed.json', 'docs/oref-alerts.json'], cwd=SKILL_DIR, check=True,
                       capture_output=True, timeout=10)
        subprocess.run(['git', 'commit', '-m', f'feed: {len(events)} events ({datetime.now(timezone.utc).strftime("%H:%M UTC")})'],
                       cwd=SKILL_DIR, check=True, capture_output=True, timeout=10)
        result = subprocess.run(['git', 'push', 'origin', 'main'], cwd=SKILL_DIR,
                                capture_output=True, timeout=30)
        if result.returncode == 0:
            print("Pushed to GitHub")
        else:
            print(f"Push failed: {result.stderr.decode()[:200]}")
    except Exception as ex:
        print(f"Git error: {ex}")

    # Run energy tracker to update energy-feed.json
    try:
        import importlib.util
        energy_script = os.path.join(SKILL_DIR, 'scripts', 'energy-tracker.py')
        if os.path.exists(energy_script):
            spec = importlib.util.spec_from_file_location("energy_tracker", energy_script)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.main()
            # Commit energy feed too
            subprocess.run(['git', 'add', 'docs/energy-feed.json'], cwd=SKILL_DIR,
                           capture_output=True, timeout=10)
            subprocess.run(['git', 'commit', '-m', 'energy: update feed'],
                           cwd=SKILL_DIR, capture_output=True, timeout=10)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=SKILL_DIR,
                           capture_output=True, timeout=30)
    except Exception as ex:
        print(f"Energy tracker error: {ex}")

if __name__ == '__main__':
    main()
