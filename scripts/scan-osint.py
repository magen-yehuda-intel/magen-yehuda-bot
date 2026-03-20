#!/usr/bin/env python3
"""
Multi-source OSINT scanner for iran-israel-alerts.
Checks: Telegram public channels, Twitter syndication, RSS feeds, USGS seismic.
Outputs JSON array of alerts to stdout. Called by the watcher daemon.

Usage: python3 scan-osint.py <config.json> <state_dir> [--source all|telegram|twitter|rss|seismic]
"""

import json, re, sys, os, time, html as h
import urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

def load_config(path):
    with open(path) as f:
        return json.load(f)

def load_state(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_state(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False)

def build_proxy_url(config):
    """Build proxy URL string from NordVPN or proxy-override config."""
    skill_dir = config.get('_skill_dir', '')
    
    override_path = os.path.join(skill_dir, 'secrets', 'proxy-override.txt')
    nord_path = os.path.join(skill_dir, 'secrets', 'nordvpn-auth.txt')
    
    if os.path.isfile(override_path):
        with open(override_path) as f:
            return f.read().strip()
    elif os.path.isfile(nord_path):
        with open(nord_path) as f:
            lines = f.read().strip().split('\n')
        if len(lines) >= 2:
            user, passwd = lines[0].strip(), lines[1].strip()
            return f'https://{user}:{passwd}@il66.nordvpn.com:89'
    return None

def fetch(url, timeout=10, proxy_handler=None):
    """Fetch URL. If proxy_url is set, use curl subprocess (urllib can't do HTTPS-over-HTTPS proxy)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

def fetch_via_proxy(url, proxy_url, timeout=15):
    """Fetch URL via HTTPS proxy using curl (handles HTTPS-over-HTTPS correctly)."""
    import subprocess
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', str(timeout),
             '--proxy', proxy_url,
             '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
             url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except Exception:
        return None

RSS_EXCLUDE_PHRASES = [
    'ukraine', 'ukrainian', 'kiev', 'kyiv', 'zelensky', 'zelenskyy',
    'donbas', 'donetsk', 'luhansk', 'kherson', 'zaporizhzhia',
    'crimea', 'crimean', 'belgorod', 'kursk region',
    'nato expansion', 'north korea', 'pyongyang',
]

def matches_keywords(text, keywords):
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def is_irrelevant_rss(title):
    """Filter out Russia-Ukraine and other non-ME noise from RSS feeds."""
    t = title.lower()
    # Must NOT match any exclude phrase (unless it also mentions Iran/Israel/ME)
    me_anchors = ['iran', 'israel', 'tehran', 'idf', 'irgc', 'hezbollah',
                  'houthi', 'gaza', 'beirut', 'syria', 'iraq', 'hormuz',
                  'gulf', 'centcom', 'middle east']
    has_exclude = any(phrase in t for phrase in RSS_EXCLUDE_PHRASES)
    has_me = any(anchor in t for anchor in me_anchors)
    return has_exclude and not has_me


# ── Breaking news detection ──
# High-value intelligence phrases that should trigger CRITICAL breaking alerts.
# Must match BOTH a topic trigger AND a credibility signal.

BREAKING_TOPICS = [
    # Khamenei death/health — various phrasings
    'khamenei dead', 'khamenei died', 'khamenei killed', 'khamenei death',
    'khamenei passed', 'khamenei assassinated', 'khamenei eliminated',
    'khamenei confirmed dead', 'khamenei is dead', 'khamenei has died',
    'khamenei has been killed', 'khamenei reportedly dead',
    'killing of khamenei', 'death of khamenei',
    'חמינאי מת', 'חמינאי נהרג', 'חמינאי חוסל', 'מות חמינאי',
    'supreme leader dead', 'supreme leader killed', 'supreme leader dies',
    'supreme leader confirmed dead', 'supreme leader has died',
    'המנהיג העליון מת', 'המנהיג העליון נהרג',
    # Energy infrastructure strikes — market-moving events
    'south pars', 'kharg island', 'gas field struck', 'gas field hit',
    'oil terminal struck', 'oil terminal hit', 'refinery struck', 'refinery hit',
    'lng facility', 'pipeline attack', 'pipeline struck', 'pipeline hit',
    'oil field struck', 'oil field hit', 'energy infrastructure',
    'strait of hormuz blocked', 'hormuz closed', 'hormuz shut',
    'שדה גז', 'מתקן אנרגיה', 'בית זיקוק', 'אי חארג',
    # Nuclear strike / detonation
    'nuclear detonation', 'nuclear strike on', 'nuclear bomb',
    'פיצוץ גרעיני', 'פצצה גרעינית', 'תקיפה גרעינית',
    # Major leader assassination
    'nasrallah dead', 'nasrallah killed', 'נסראללה חוסל', 'נסראללה נהרג',
    'sinwar dead', 'sinwar killed', 'סינוואר חוסל', 'סינוואר נהרג',
]

# Compound breaking checks — if ALL words appear in text (any order)
BREAKING_COMPOUND = [
    {'words': ['khamenei', 'dead'], 'topic': 'khamenei dead'},
    {'words': ['khamenei', 'killed'], 'topic': 'khamenei killed'},
    {'words': ['khamenei', 'killing'], 'topic': 'khamenei killed'},
    {'words': ['khamenei', 'died'], 'topic': 'khamenei died'},
    {'words': ['khamenei', 'death'], 'topic': 'khamenei death'},
    {'words': ['khamenei', 'eliminated'], 'topic': 'khamenei eliminated'},
    {'words': ['khamenei', 'assassinated'], 'topic': 'khamenei assassinated'},
    {'words': ['חמינאי', 'מת'], 'topic': 'חמינאי מת'},
    {'words': ['חמינאי', 'נהרג'], 'topic': 'חמינאי נהרג'},
    {'words': ['חמינאי', 'חוסל'], 'topic': 'חמינאי חוסל'},
    {'words': ['supreme leader', 'dead'], 'topic': 'supreme leader dead'},
    {'words': ['supreme leader', 'killed'], 'topic': 'supreme leader killed'},
    {'words': ['nuclear', 'detonation'], 'topic': 'nuclear detonation'},
    {'words': ['nuclear', 'strike', 'iran'], 'topic': 'nuclear strike iran'},
    # Energy infrastructure
    {'words': ['south', 'pars', 'strike'], 'topic': 'south pars struck'},
    {'words': ['south', 'pars', 'hit'], 'topic': 'south pars struck'},
    {'words': ['south', 'pars', 'attack'], 'topic': 'south pars struck'},
    {'words': ['kharg', 'island', 'strike'], 'topic': 'kharg island struck'},
    {'words': ['kharg', 'island', 'hit'], 'topic': 'kharg island struck'},
    {'words': ['gas', 'field', 'strike'], 'topic': 'gas field struck'},
    {'words': ['gas', 'field', 'hit'], 'topic': 'gas field struck'},
    {'words': ['gas', 'field', 'attack'], 'topic': 'gas field struck'},
    {'words': ['refinery', 'struck'], 'topic': 'refinery struck'},
    {'words': ['refinery', 'hit'], 'topic': 'refinery struck'},
    {'words': ['oil', 'terminal', 'struck'], 'topic': 'oil terminal struck'},
    {'words': ['oil', 'terminal', 'hit'], 'topic': 'oil terminal struck'},
    {'words': ['lng', 'facility', 'struck'], 'topic': 'lng facility struck'},
    {'words': ['lng', 'facility', 'hit'], 'topic': 'lng facility struck'},
    {'words': ['lng', 'facility', 'attack'], 'topic': 'lng facility struck'},
    {'words': ['pipeline', 'attack'], 'topic': 'pipeline struck'},
    {'words': ['pipeline', 'struck'], 'topic': 'pipeline struck'},
    {'words': ['hormuz', 'blocked'], 'topic': 'hormuz blocked'},
    {'words': ['hormuz', 'closed'], 'topic': 'hormuz blocked'},
    {'words': ['hormuz', 'shut'], 'topic': 'hormuz blocked'},
]

# Normalize topic variants to a single canonical key for corroboration.
# All language variants and phrasings that refer to the same event must map
# to the same key so corroboration counts across Hebrew/English/Farsi sources.
TOPIC_CANONICAL = {
    # Khamenei — everything maps to one key
    'khamenei dead': 'khamenei_killed',
    'khamenei died': 'khamenei_killed',
    'khamenei killed': 'khamenei_killed',
    'khamenei killing': 'khamenei_killed',
    'khamenei death': 'khamenei_killed',
    'khamenei passed': 'khamenei_killed',
    'khamenei assassinated': 'khamenei_killed',
    'khamenei eliminated': 'khamenei_killed',
    'khamenei confirmed dead': 'khamenei_killed',
    'khamenei is dead': 'khamenei_killed',
    'khamenei has died': 'khamenei_killed',
    'khamenei has been killed': 'khamenei_killed',
    'khamenei reportedly dead': 'khamenei_killed',
    'killing of khamenei': 'khamenei_killed',
    'death of khamenei': 'khamenei_killed',
    'חמינאי מת': 'khamenei_killed',
    'חמינאי נהרג': 'khamenei_killed',
    'חמינאי חוסל': 'khamenei_killed',
    'מות חמינאי': 'khamenei_killed',
    'supreme leader dead': 'khamenei_killed',
    'supreme leader killed': 'khamenei_killed',
    'supreme leader dies': 'khamenei_killed',
    'supreme leader confirmed dead': 'khamenei_killed',
    'supreme leader has died': 'khamenei_killed',
    'המנהיג העליון מת': 'khamenei_killed',
    'המנהיג העליון נהרג': 'khamenei_killed',
    # Nuclear
    'nuclear detonation': 'nuclear_event',
    'nuclear strike on': 'nuclear_event',
    'nuclear bomb': 'nuclear_event',
    'nuclear strike iran': 'nuclear_event',
    'פיצוץ גרעיני': 'nuclear_event',
    'פצצה גרעינית': 'nuclear_event',
    'תקיפה גרעינית': 'nuclear_event',
    # Nasrallah
    'nasrallah dead': 'nasrallah_killed',
    'nasrallah killed': 'nasrallah_killed',
    'נסראללה חוסל': 'nasrallah_killed',
    'נסראללה נהרג': 'nasrallah_killed',
    # Sinwar
    'sinwar dead': 'sinwar_killed',
    'sinwar killed': 'sinwar_killed',
    'סינוואר חוסל': 'sinwar_killed',
    'סינוואר נהרג': 'sinwar_killed',
    # Energy infrastructure
    'south pars': 'energy_infrastructure_struck',
    'south pars struck': 'energy_infrastructure_struck',
    'kharg island': 'energy_infrastructure_struck',
    'kharg island struck': 'energy_infrastructure_struck',
    'gas field struck': 'energy_infrastructure_struck',
    'gas field hit': 'energy_infrastructure_struck',
    'oil terminal struck': 'energy_infrastructure_struck',
    'oil terminal hit': 'energy_infrastructure_struck',
    'refinery struck': 'energy_infrastructure_struck',
    'refinery hit': 'energy_infrastructure_struck',
    'lng facility': 'energy_infrastructure_struck',
    'lng facility struck': 'energy_infrastructure_struck',
    'pipeline attack': 'energy_infrastructure_struck',
    'pipeline struck': 'energy_infrastructure_struck',
    'pipeline hit': 'energy_infrastructure_struck',
    'oil field struck': 'energy_infrastructure_struck',
    'oil field hit': 'energy_infrastructure_struck',
    'energy infrastructure': 'energy_infrastructure_struck',
    'שדה גז': 'energy_infrastructure_struck',
    'מתקן אנרגיה': 'energy_infrastructure_struck',
    'בית זיקוק': 'energy_infrastructure_struck',
    'אי חארג': 'energy_infrastructure_struck',
    'strait of hormuz blocked': 'hormuz_blocked',
    'hormuz closed': 'hormuz_blocked',
    'hormuz shut': 'hormuz_blocked',
    'hormuz blocked': 'hormuz_blocked',
}

def normalize_breaking_topic(raw_topic):
    """Map any topic variant to its canonical key for corroboration."""
    return TOPIC_CANONICAL.get(raw_topic, raw_topic)

# Credible sources — channel names and keywords that indicate reliability
CREDIBLE_SOURCES = {
    # Telegram channels (high reliability)
    'idfonline', 'kann_news', 'flash_news_il', 'aharonyediot',
    'iranintl_en', 'BBCPersian',
    # Twitter accounts
    'beholdisrael', 'sentdefender', 'IsraelRadar_',
    # RSS feeds / wire services
    'timesofisrael', 'times of israel', 'jpost', 'jerusalem post', 'ynet', 'ynetnews',
    'reuters', 'ap news', 'apnews', 'associated press',
    'tass', 'al jazeera', 'aljazeera',
    'haaretz', 'bbc', 'cnn', 'sky news', 'france24',
    'fox news', 'nbc', 'abc news', 'nytimes', 'new york times',
    'washington post', 'wall street journal',
}

CREDIBLE_ATTRIBUTION = [
    # Specific people / orgs whose statements carry weight
    'netanyahu', 'נתניהו', 'biden', 'ביידן', 'trump', 'טראמפ',
    'idf confirms', 'צה"ל מאשר', 'idf spokesperson', 'דובר צה"ל',
    'pentagon confirms', 'white house confirms',
    'reuters', 'associated press', ' ap ', 'afp',
    'bbc confirms', 'cnn confirms', 'breaking:',
    'official statement', 'הודעה רשמית',
    'confirmed dead', 'אושר כי מת', 'confirmed killed',
]


def check_breaking_news(text, source_channel=""):
    """
    Check if an OSINT alert qualifies as breaking news.
    Returns (is_breaking: bool, topic: str) tuple.
    Topic is normalized to a canonical key so all language variants merge.
    Must match a topic trigger AND (credible source OR credible attribution).
    """
    text_lower = text.lower()
    channel_lower = source_channel.lower()

    # Check exact phrase matches first
    matched_topic = None
    for topic in BREAKING_TOPICS:
        if topic in text_lower:
            matched_topic = topic
            break

    # Check compound word matches (words anywhere in text)
    if not matched_topic:
        for compound in BREAKING_COMPOUND:
            if all(w in text_lower for w in compound['words']):
                matched_topic = compound['topic']
                break

    if not matched_topic:
        return False, ""

    # Verify credibility: source channel OR text attribution
    from_credible_source = any(cs in channel_lower for cs in CREDIBLE_SOURCES)
    has_credible_attribution = any(attr in text_lower for attr in CREDIBLE_ATTRIBUTION)

    if from_credible_source or has_credible_attribution:
        # Normalize topic to canonical key for cross-language corroboration
        canonical = normalize_breaking_topic(matched_topic)
        return True, canonical

    return False, ""

# ═══════════════════════════════════════════════════════════
# TELEGRAM PUBLIC CHANNELS (t.me/s/channelname)
# ═══════════════════════════════════════════════════════════

def scan_telegram(config, state_dir, proxy_url=None):
    channels = config.get('telegram_osint_channels', [])
    keywords = config.get('osint_keywords', [])
    seen_file = os.path.join(state_dir, 'osint-telegram-seen.json')
    seen = load_state(seen_file)
    
    alerts = []
    
    for ch in channels:
        try:
            url = f'https://t.me/s/{ch}'
            if proxy_url:
                raw = fetch_via_proxy(url, proxy_url)
            else:
                raw = fetch(url, timeout=8)
            if not raw:
                continue
            
            # Parse messages: get text + message ID + timestamp
            # Message blocks contain data-post="channel/msgid"
            msg_blocks = re.findall(
                r'data-post="[^/]+/(\d+)".*?'
                r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>.*?'
                r'<time[^>]*datetime="([^"]*)"',
                raw, re.DOTALL
            )
            
            prev_ids = set(seen.get(ch, []))
            current_ids = []
            
            for msg_id, text_html, timestamp in msg_blocks:
                current_ids.append(msg_id)
                
                if msg_id in prev_ids:
                    continue
                
                # Clean HTML to text
                text = re.sub(r'<br\s*/?>', '\n', text_html)
                text = re.sub(r'<[^>]+>', '', text)
                text = h.unescape(text).strip()
                
                if not text or not matches_keywords(text, keywords):
                    continue
                
                display = text[:250].replace('\n', ' ')
                if len(text) > 250:
                    display += '...'
                
                is_breaking, breaking_topic = check_breaking_news(text, ch)
                
                alerts.append({
                    'source': 'telegram',
                    'channel': ch,
                    'msg_id': msg_id,
                    'text': display,
                    'time': timestamp,
                    'link': f'https://t.me/{ch}/{msg_id}',
                    'breaking': is_breaking,
                    'breaking_topic': breaking_topic,
                })
            
            # Keep last 30 message IDs per channel
            seen[ch] = current_ids[:50]
            time.sleep(0.3)
            
        except Exception:
            continue
    
    save_state(seen_file, seen)
    return alerts

# ═══════════════════════════════════════════════════════════
# TWITTER SYNDICATION API
# ═══════════════════════════════════════════════════════════

def scan_twitter(config, state_dir, proxy_url=None):
    accounts = config.get('twitter_accounts', [])
    keywords = config.get('osint_keywords', [])
    seen_file = os.path.join(state_dir, 'osint-twitter-seen.json')
    seen = load_state(seen_file)
    
    alerts = []
    
    for acct in accounts:
        try:
            url = f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{acct}'
            if proxy_url:
                raw = fetch_via_proxy(url, proxy_url)
            else:
                raw = fetch(url, timeout=10)
            if not raw:
                continue
            
            m = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                raw
            )
            if not m:
                continue
            
            data = json.loads(m.group(1))
            entries = data.get('props', {}).get('pageProps', {}).get('timeline', {}).get('entries', [])
            
            prev_ids = set(seen.get(acct, []))
            current_ids = []
            
            for e in entries:
                try:
                    tweet = e['content']['tweet']
                    rt = tweet.get('retweeted_status')
                    src = rt if rt else tweet
                    tid = src.get('id_str', '')
                    if not tid:
                        continue
                    current_ids.append(tid)
                    
                    if tid in prev_ids:
                        continue
                    
                    text = src.get('full_text', '')
                    if not matches_keywords(text, keywords):
                        continue
                    
                    screen = src['user']['screen_name']
                    display = text[:250].replace('\n', ' ')
                    if len(text) > 250:
                        display += '...'
                    
                    created = src.get('created_at', '')
                    
                    is_breaking, breaking_topic = check_breaking_news(text, acct)
                    
                    alerts.append({
                        'source': 'twitter',
                        'channel': f'@{acct}',
                        'account': acct,
                        'tweet_id': tid,
                        'is_rt': bool(rt),
                        'text': display,
                        'time': created,
                        'link': f'https://x.com/{screen}/status/{tid}',
                        'breaking': is_breaking,
                        'breaking_topic': breaking_topic,
                    })
                except (KeyError, TypeError):
                    continue
            
            seen[acct] = current_ids[:200]
            time.sleep(0.3)
            
        except Exception:
            continue
    
    save_state(seen_file, seen)
    return alerts

# ═══════════════════════════════════════════════════════════
# RSS FEEDS
# ═══════════════════════════════════════════════════════════

def scan_rss(config, state_dir):
    feeds = config.get('rss_feeds', [])
    keywords = config.get('osint_keywords', [])
    seen_file = os.path.join(state_dir, 'osint-rss-seen.json')
    seen = load_state(seen_file)
    
    alerts = []
    
    for feed in feeds:
        name = feed.get('name', '?')
        url = feed.get('url', '')
        if not url:
            continue
        
        try:
            raw = fetch(url, timeout=8)
            
            # Parse items (works for both RSS and Atom)
            items = re.findall(
                r'<item>(.*?)</item>|<entry>(.*?)</entry>',
                raw, re.DOTALL
            )
            
            prev_links = set(seen.get(name, []))
            current_links = []
            
            for item_match in items[:20]:
                item_xml = item_match[0] or item_match[1]
                
                # Extract title
                title_m = re.search(r'<title[^>]*>(.*?)</title>', item_xml, re.DOTALL)
                title = re.sub(r'<!\[CDATA\[|\]\]>', '', title_m.group(1)).strip() if title_m else ''
                title = h.unescape(re.sub(r'<[^>]+>', '', title))
                
                # Extract link
                link_m = re.search(r'<link[^>]*>([^<]+)</link>|<link[^>]*href="([^"]+)"', item_xml)
                link = ''
                if link_m:
                    link = (link_m.group(1) or link_m.group(2) or '').strip()
                
                # Extract pubDate
                date_m = re.search(r'<pubDate>(.*?)</pubDate>|<published>(.*?)</published>|<updated>(.*?)</updated>', item_xml)
                pub_date = ''
                if date_m:
                    pub_date = (date_m.group(1) or date_m.group(2) or date_m.group(3) or '').strip()
                
                current_links.append(link or title)
                
                if (link or title) in prev_links:
                    continue
                
                if is_irrelevant_rss(title):
                    continue
                
                if not matches_keywords(title, keywords):
                    continue
                
                is_breaking, breaking_topic = check_breaking_news(title, name)
                
                alerts.append({
                    'source': 'rss',
                    'channel': name,
                    'text': title[:200],
                    'time': pub_date,
                    'link': link,
                    'breaking': is_breaking,
                    'breaking_topic': breaking_topic,
                })
            
            # Accumulate seen IDs (don't overwrite — merge with previous)
            merged = list(prev_links | set(current_links))
            seen[name] = merged[-200:]  # cap at 200 per source
            time.sleep(0.2)
            
        except Exception:
            continue
    
    save_state(seen_file, seen)
    return alerts

# ═══════════════════════════════════════════════════════════
# USGS SEISMIC (Iran region — nuclear test detection)
# ═══════════════════════════════════════════════════════════

def scan_seismic(config, state_dir):
    seismic = config.get('usgs_seismic', {})
    if not seismic.get('enabled', False):
        return []
    
    seen_file = os.path.join(state_dir, 'osint-seismic-seen.json')
    seen_ids = set(load_state(seen_file, {}).get('ids', []))
    
    alerts = []
    
    try:
        params = (
            f"format=geojson"
            f"&minlatitude={seismic.get('min_latitude', 25)}"
            f"&maxlatitude={seismic.get('max_latitude', 40)}"
            f"&minlongitude={seismic.get('min_longitude', 44)}"
            f"&maxlongitude={seismic.get('max_longitude', 63)}"
            f"&minmagnitude={seismic.get('min_magnitude', 3.5)}"
            f"&orderby=time&limit=5"
        )
        url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?{params}"
        raw = fetch(url, timeout=10)
        data = json.loads(raw)
        
        current_ids = []
        for f_item in data.get('features', []):
            eid = f_item.get('id', '')
            current_ids.append(eid)
            
            if eid in seen_ids:
                continue
            
            props = f_item['properties']
            mag = props.get('mag', 0)
            place = props.get('place', 'Unknown')
            event_type = props.get('type', 'earthquake')
            event_time = props.get('time', 0)
            event_url = props.get('url', '')
            
            # Convert epoch ms to ISO
            dt = datetime.fromtimestamp(event_time / 1000, tz=timezone.utc)
            time_str = dt.isoformat()
            
            # Flag suspicious events (shallow, high magnitude, or "explosion" type)
            coords = f_item.get('geometry', {}).get('coordinates', [0, 0, 0])
            depth = coords[2] if len(coords) > 2 else 0
            suspicious = event_type == 'explosion' or (mag >= 4.0 and depth < 10)
            
            prefix = '⚠️ SUSPICIOUS' if suspicious else '🔴'
            text = f'{prefix} M{mag} {event_type} — {place} (depth: {depth}km)'
            
            alerts.append({
                'source': 'seismic',
                'channel': 'USGS',
                'text': text,
                'time': time_str,
                'link': event_url,
                'magnitude': mag,
                'suspicious': suspicious,
            })
        
        save_state(seen_file, {'ids': current_ids})
        
    except Exception:
        pass
    
    return alerts

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("Usage: scan-osint.py <config.json> <state_dir> [--source all|telegram|twitter|rss|seismic]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    source = 'all'
    if '--source' in sys.argv:
        idx = sys.argv.index('--source')
        if idx + 1 < len(sys.argv):
            source = sys.argv[idx + 1]
    
    config = load_config(config_path)
    config['_skill_dir'] = os.path.dirname(config_path)  # for proxy discovery
    os.makedirs(state_dir, exist_ok=True)
    
    # Build proxy URL (NordVPN or override) for rate-limited sources
    proxy_url = build_proxy_url(config)
    if proxy_url:
        print("Using proxy for Twitter/Telegram scraping", file=sys.stderr)
    
    all_alerts = []
    
    # Scanners that benefit from proxy (rate-limited scraping)
    proxied_scanners = {
        'telegram': scan_telegram,
        'twitter': scan_twitter,
    }
    # Scanners that don't need proxy (public APIs, no rate issues)
    direct_scanners = {
        'rss': scan_rss,
        'seismic': scan_seismic,
    }
    
    if source == 'all':
        for name, scanner in proxied_scanners.items():
            try:
                all_alerts.extend(scanner(config, state_dir, proxy_url=proxy_url))
            except Exception as e:
                print(f"Scanner {name} error: {e}", file=sys.stderr)
        for name, scanner in direct_scanners.items():
            try:
                all_alerts.extend(scanner(config, state_dir))
            except Exception as e:
                print(f"Scanner {name} error: {e}", file=sys.stderr)
    elif source in proxied_scanners:
        all_alerts = proxied_scanners[source](config, state_dir, proxy_url=proxy_url)
    elif source in direct_scanners:
        all_alerts = direct_scanners[source](config, state_dir)
    
    # Sort by source priority: seismic > telegram > twitter > rss
    priority = {'seismic': 0, 'telegram': 1, 'twitter': 2, 'rss': 3}
    all_alerts.sort(key=lambda a: priority.get(a.get('source', ''), 99))
    
    # Output as JSON
    json.dump(all_alerts, sys.stdout, ensure_ascii=False, indent=None)

if __name__ == '__main__':
    main()
