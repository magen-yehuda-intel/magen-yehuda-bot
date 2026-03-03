#!/usr/bin/env python3
"""
Energy/Oil/Gas RSS scanner — dedicated feeds for Hormuz Crisis Dashboard.
Fetches energy-specific RSS sources and appends to intel feed for energy-tracker.py to process.
"""
import json, os, re, sys, time, hashlib, subprocess
from xml.etree import ElementTree
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, 'state')
STATE_FILE = os.path.join(STATE_DIR, 'energy-rss-state.json')
INTEL_LOG = os.path.join(SKILL_DIR, 'state', 'log-intel.jsonl')

# Energy-specific RSS feeds
FEEDS = [
    # Oil/gas industry via Google News proxy (direct feeds blocked by Cloudflare)
    ('oilprice', 'https://news.google.com/rss/search?q=site:oilprice.com+oil+gas+energy+hormuz&hl=en-US&gl=US&ceid=US:en'),
    ('reuters_energy', 'https://news.google.com/rss/search?q=site:reuters.com+oil+gas+hormuz+energy+tanker+strait&hl=en-US&gl=US&ceid=US:en'),
    ('bloomberg_energy', 'https://news.google.com/rss/search?q=site:bloomberg.com+oil+gas+hormuz+energy+iran+crude&hl=en-US&gl=US&ceid=US:en'),
    ('gcaptain', 'https://news.google.com/rss/search?q=site:gcaptain.com+hormuz+tanker+oil+shipping+iran&hl=en-US&gl=US&ceid=US:en'),
    ('sp_global', 'https://news.google.com/rss/search?q=site:spglobal.com+oil+gas+hormuz+crude+LNG+iran&hl=en-US&gl=US&ceid=US:en'),
    ('tradewinds', 'https://news.google.com/rss/search?q=tanker+shipping+hormuz+oil+strait+iran+blockade&hl=en-US&gl=US&ceid=US:en'),
    ('iran_energy_he', 'https://news.google.com/rss/search?q=%D7%A0%D7%A4%D7%98+%D7%92%D7%96+%D7%90%D7%99%D7%A8%D7%9F+%D7%94%D7%95%D7%A8%D7%9E%D7%95%D7%96+%D7%90%D7%A0%D7%A8%D7%92%D7%99%D7%94&hl=iw&gl=IL&ceid=IL:he'),
]

PROXY = os.environ.get('HTTPS_PROXY', '')


def fetch_rss(url: str) -> str:
    """Fetch RSS via curl (handles HTTPS proxy)."""
    cmd = ['curl', '-sL', '--connect-timeout', '10', '-m', '20', '-A',
           'Mozilla/5.0 (compatible; MagenYehudaBot/1.0)', url]
    if PROXY:
        cmd = ['curl', '-sL', '--proxy', PROXY, '--connect-timeout', '10', '-m', '20', '-A',
               'Mozilla/5.0 (compatible; MagenYehudaBot/1.0)', url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout
    except Exception as e:
        print(f'  fetch error: {e}', file=sys.stderr)
        return ''


def parse_rss(xml_text: str, source: str) -> list:
    """Parse RSS XML into events."""
    events = []
    try:
        root = ElementTree.fromstring(xml_text)
    except Exception:
        return events
    
    for item in root.iter('item'):
        title = (item.findtext('title') or '').strip()
        desc = (item.findtext('description') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = (item.findtext('pubDate') or '').strip()
        
        # Get actual source from Google News
        src_el = item.find('source')
        actual_source = src_el.text if src_el is not None and src_el.text else source
        
        if not title:
            continue
        
        # Parse date
        ts = time.time()
        if pub:
            # Strip CDATA wrapper if present
            pub = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', pub).strip()
            try:
                dt = parsedate_to_datetime(pub)
                ts = dt.timestamp()
                # Reject future timestamps
                if ts > time.time() + 600:
                    ts = time.time()
            except Exception:
                pass
        
        # Skip old items (>72h)
        if time.time() - ts > 72 * 3600:
            continue
        
        # Dedup key
        text = f'{title}'
        if desc and len(desc) < 300:
            text = f'{title}. {desc}'
        
        events.append({
            'ts': ts,
            'src': actual_source,
            'text': text[:400],
            'link': link,
            'type': 'energy_rss',
        })
    
    return events


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {'seen': {}}


def save_state(state: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def event_hash(e: dict) -> str:
    """Dedup hash from title text."""
    # Normalize: lowercase, strip numbers/punctuation for fuzzy dedup
    t = re.sub(r'[^a-z\u0590-\u05ff ]+', '', e['text'].lower())
    t = re.sub(r'\s+', ' ', t).strip()[:100]
    return hashlib.md5(t.encode()).hexdigest()[:12]


def log_event(e: dict):
    """Append to intel JSONL log for dispatch pipeline."""
    entry = {
        'ts': e['ts'],
        'date': datetime.fromtimestamp(e['ts'], tz=timezone.utc).strftime('%Y-%m-%d'),
        'time': datetime.fromtimestamp(e['ts'], tz=timezone.utc).strftime('%H:%M'),
        'src': e['src'],
        'loc': 'Middle East',
        'lat': 30.0,
        'lon': 52.0,
        'side': 'unknown',
        'text': e['text'],
        'breaking': False,
        'type': 'energy_rss',
    }
    os.makedirs(os.path.dirname(INTEL_LOG), exist_ok=True)
    with open(INTEL_LOG, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def main():
    state = load_state()
    seen = state.get('seen', {})
    total_new = 0
    
    for name, url in FEEDS:
        print(f'Scanning {name}...', end=' ')
        xml = fetch_rss(url)
        if not xml or '<' not in xml:
            print('empty/error')
            continue
        
        events = parse_rss(xml, name)
        new = 0
        for e in events:
            h = event_hash(e)
            if h in seen:
                continue
            seen[h] = int(time.time())
            log_event(e)
            new += 1
            total_new += 1
        
        print(f'{len(events)} items, {new} new')
    
    # Prune old seen entries (>7 days)
    cutoff = int(time.time()) - 7 * 86400
    seen = {k: v for k, v in seen.items() if v > cutoff}
    state['seen'] = seen
    state['last_run'] = int(time.time())
    save_state(state)
    
    print(f'\nTotal new energy events: {total_new}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
