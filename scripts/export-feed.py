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
    # Specific cities/ports FIRST (before country-level fallbacks)
    'bandar abbas': ('Bandar Abbas', 27.18, 56.27), 'bandar anzali': ('Bandar Anzali', 37.47, 49.46),
    'chabahar': ('Chabahar', 25.29, 60.64), 'kharg island': ('Kharg Island', 29.24, 50.31),
    'south pars': ('South Pars', 27.50, 52.20), 'assaluyeh': ('Assaluyeh', 27.47, 52.60),
    'abadan': ('Abadan', 30.34, 48.30), 'bandar imam': ('Bandar Imam Khomeini', 30.43, 49.08),
    'pardis': ('Pardis/South Pars', 27.52, 52.53), 'kangan': ('Kangan', 27.84, 52.06),
    'lavan': ('Lavan Island', 26.80, 53.36), 'sirri': ('Sirri Island', 25.91, 54.54),
    'qeshm': ('Qeshm Island', 26.95, 56.27), 'hormuz': ('Strait of Hormuz', 26.60, 56.30),
    'tehran': ('Tehran', 35.69, 51.39), 'isfahan': ('Isfahan', 32.65, 51.68),
    'bushehr': ('Bushehr', 28.97, 50.84), 'natanz': ('Natanz', 33.51, 51.92),
    'qom': ('Qom', 34.64, 50.88), 'shiraz': ('Shiraz', 29.59, 52.58),
    'tabriz': ('Tabriz', 38.08, 46.29), 'mashhad': ('Mashhad', 36.31, 59.60),
    'ahvaz': ('Ahvaz', 31.32, 48.67), 'dezful': ('Dezful', 32.38, 48.40),
    'kermanshah': ('Kermanshah', 34.31, 47.06), 'arak': ('Arak', 34.09, 49.69),
    'parchin': ('Parchin', 35.52, 51.77), 'fordow': ('Fordow', 34.88, 51.58),
    'kerman': ('Kerman', 30.28, 57.08), 'bandar lengeh': ('Bandar Lengeh', 26.56, 54.88),
    'jask': ('Jask', 25.64, 57.77), 'konarak': ('Konarak', 25.35, 60.38),
    'haifa': ('Haifa', 32.79, 34.99), 'tel aviv': ('Tel Aviv', 32.07, 34.77),
    'gaza': ('Gaza', 31.50, 34.47), 'beirut': ('Beirut', 33.89, 35.50),
    'erbil': ('Erbil', 36.19, 44.01), 'damascus': ('Damascus', 33.51, 36.29),
    'sanaa': ("Sana'a", 15.37, 44.19), 'jerusalem': ('Jerusalem', 31.77, 35.23),
    'yanbu': ('Yanbu', 24.09, 38.06), 'jeddah': ('Jeddah', 21.49, 39.19),
    'riyadh': ('Riyadh', 24.71, 46.68), 'abqaiq': ('Abqaiq', 25.94, 49.68),
    'jubail': ('Jubail', 27.01, 49.66), 'dammam': ('Dammam', 26.43, 50.10),
    'ras tanura': ('Ras Tanura', 26.64, 50.05), 'dhahran': ('Dhahran', 26.27, 50.21),
    'fujairah': ('Fujairah', 25.13, 56.33), 'jebel ali': ('Jebel Ali', 25.00, 55.03),
    'ras laffan': ('Ras Laffan', 25.91, 51.53), 'doha': ('Doha', 25.29, 51.53),
    'caspian': ('Caspian Sea/Iran', 37.50, 49.90), 'gilan': ('Gilan', 37.28, 49.60),
    # Country-level fallbacks LAST
    'iran': ('Iran', 32.43, 53.69), 'israel': ('Israel', 31.77, 35.23),
    'lebanon': ('Lebanon', 33.85, 35.86), 'yemen': ('Yemen', 15.55, 48.52),
    'iraq': ('Iraq', 33.22, 43.68), 'syria': ('Syria', 34.80, 38.99),
    'saudi': ('Saudi Arabia', 24.71, 46.68),
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

    # Sync recent events to Azure Table Storage (best-effort, 30s timeout)
    try:
        import signal
        def _db_timeout(signum, frame): raise TimeoutError("DB sync timed out")
        signal.signal(signal.SIGALRM, _db_timeout)
        signal.alarm(30)
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
    finally:
        signal.alarm(0)  # cancel alarm

    # Export siren history from dispatch-log.jsonl
    try:
        dispatch_log = os.path.join(STATE_DIR, 'dispatch-log.jsonl')
        siren_history = []
        if os.path.exists(dispatch_log):
            with open(dispatch_log, 'rb') as f:
                # Read last 64KB for recent events
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 65536))
                tail = f.read().decode('utf-8', errors='replace')
            for line in tail.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') in ('siren', 'siren_clear', 'siren_standdown'):
                        siren_history.append({
                            'ts': entry.get('ts'),
                            'utc': entry.get('utc'),
                            'type': entry.get('type'),
                            'severity': entry.get('severity', ''),
                        })
                except:
                    pass
        # Keep last 20 siren events, newest first
        siren_history.sort(key=lambda x: x.get('ts', 0), reverse=True)
        siren_history = siren_history[:20]
        # Also pull area info from oref-alert-tmp.json if available
        oref_tmp = os.path.join(STATE_DIR, 'oref-alert-tmp.json')
        last_areas = []
        last_title = ''
        if os.path.exists(oref_tmp):
            try:
                with open(oref_tmp) as f:
                    tmp = json.load(f)
                if isinstance(tmp, list) and tmp:
                    last_title = tmp[0].get('title', '')
                    last_areas = [a.get('data', a.get('area', '')) for a in tmp if isinstance(a, dict)]
                elif isinstance(tmp, dict):
                    last_title = tmp.get('title', '')
                    last_areas = tmp.get('data', tmp.get('areas', []))
            except:
                pass
        history_out = os.path.join(DOCS_DIR, 'oref-history.json')
        with open(history_out, 'w') as f:
            json.dump({
                'alerts': siren_history,
                'last_title': last_title,
                'last_areas': last_areas[:10] if isinstance(last_areas, list) else [],
                'exported': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'count': len(siren_history)
            }, f, ensure_ascii=False, indent=2)
        print(f"Siren history: {len(siren_history)} events exported")
    except Exception as ex:
        print(f"Siren history export error: {ex}")

    # Git commit + push
    try:
        subprocess.run(['git', 'add', 'docs/intel-feed.json', 'docs/oref-alerts.json', 'docs/oref-history.json'], cwd=SKILL_DIR, check=True,
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

    # Run energy RSS scanner to pull dedicated energy sources
    try:
        energy_rss = os.path.join(SKILL_DIR, 'scripts', 'scan-energy-rss.py')
        if os.path.exists(energy_rss):
            subprocess.run([sys.executable, energy_rss], cwd=SKILL_DIR,
                           capture_output=True, timeout=120)
            print("Energy RSS scan complete")
    except Exception as ex:
        print(f"Energy RSS error: {ex}")

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
