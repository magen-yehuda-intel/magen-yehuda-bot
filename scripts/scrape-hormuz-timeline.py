#!/usr/bin/env python3
"""
Scrape Hormuz crisis timeline data from Wikipedia + UKMTO.
Outputs updated facilities-timeline.json for the Hormuz dashboard.
Run via cron every 6h.
"""
import json, re, sys, os
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from html.parser import HTMLParser

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data')
OUT_FILE = os.path.join(OUT_DIR, 'hormuz-timeline.json')

WIKI_URL = 'https://en.wikipedia.org/wiki/2026_Strait_of_Hormuz_crisis'
HEADERS = {'User-Agent': 'MagenYehudaBot/1.0 (crisis-tracker)'}

class WikiTableParser(HTMLParser):
    """Extract ship attack table rows from Wikipedia."""
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = ''
        self.rows = []
        self.table_count = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'table' and 'wikitable' in attrs_dict.get('class', ''):
            self.table_count += 1
            self.in_table = True
        elif self.in_table and tag == 'tr':
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = ''

    def handle_endtag(self, tag):
        if self.in_cell and tag in ('td', 'th'):
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
        elif self.in_row and tag == 'tr':
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif self.in_table and tag == 'table':
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

def fetch_wiki_attacks():
    """Fetch ship attack data from Wikipedia table."""
    req = Request(WIKI_URL, headers=HEADERS)
    html = urlopen(req, timeout=30).read().decode('utf-8')
    
    parser = WikiTableParser()
    parser.feed(html)
    
    attacks = []
    for row in parser.rows:
        # Ship attack table has columns: #, Date, Name, Flag, Type, Result, Sources
        if len(row) >= 6 and row[0].strip().isdigit():
            num = int(row[0].strip())
            date_str = row[1].strip()
            name = row[2].strip()
            flag = row[3].strip()
            ship_type = row[4].strip()
            result = row[5].strip()
            
            # Parse date
            date_match = re.search(r'(\d+)\s+March\s+2026', date_str)
            if not date_match:
                date_match = re.search(r'March\s+(\d+)', date_str)
            if date_match:
                day = int(date_match.group(1))
                date = f'2026-03-{day:02d}'
            else:
                date_match = re.search(r'(\d+)\s+February\s+2026', date_str)
                if date_match:
                    day = int(date_match.group(1))
                    date = f'2026-02-{day:02d}'
                else:
                    continue
            
            abandoned = 'abandoned' in result.lower()
            sunk = 'sunk' in result.lower() or 'sank' in result.lower()
            ablaze = 'ablaze' in result.lower() or 'fire' in result.lower()
            killed = re.search(r'(\d+)\s+(?:crew\s+)?(?:killed|dead|missing)', result.lower())
            casualties = int(killed.group(1)) if killed else 0
            
            attacks.append({
                'num': num,
                'date': date,
                'name': name,
                'flag': flag,
                'type': ship_type,
                'result': result,
                'abandoned': abandoned,
                'sunk': sunk,
                'ablaze': ablaze,
                'casualties': casualties,
            })
    
    return attacks

def build_daily_timeline(attacks):
    """Build daily struck/shutdown counts from attack data + known facility events."""
    # Known facility shutdowns/strikes (hardcoded — these don't come from ship attacks)
    facility_events = [
        {'date': '2026-02-28', 'struck': 3, 'shutdown': 3, 'label': 'Iran strikes begin: Kharg, Isfahan, Haifa struck; Leviathan/Karish/Tamar shutdown'},
        {'date': '2026-03-02', 'extra_struck': 1, 'extra_shutdown': 1, 'label': 'Ras Tanura drone strike; Ras Laffan LNG shutdown'},
        {'date': '2026-03-04', 'extra_struck': 3, 'extra_shutdown': 1, 'label': 'Bushehr, Bandar Abbas, Fujairah struck; Mesaieed shutdown'},
        {'date': '2026-03-05', 'extra_struck': 1, 'extra_shutdown': 0, 'label': 'Kuwait Mina al-Ahmadi struck'},
        {'date': '2026-03-06', 'extra_struck': 0, 'extra_shutdown': 1, 'label': 'North Field shutdown'},
        {'date': '2026-03-08', 'extra_struck': 1, 'extra_shutdown': 0, 'label': 'Tehran oil depots bombed by Israel'},
        {'date': '2026-03-16', 'extra_struck': 0, 'extra_shutdown': 1, 'label': 'UAE Shah gas field suspended'},
        {'date': '2026-03-17', 'extra_struck': 1, 'extra_shutdown': 0, 'label': 'Fujairah oil hub hit again'},
        {'date': '2026-03-18', 'extra_struck': 1, 'extra_shutdown': 0, 'label': 'IDF strikes South Pars/Asaluyeh'},
        {'date': '2026-03-19', 'extra_struck': 1, 'extra_shutdown': 0, 'label': 'Yanbu SAMREF targeted'},
        {'date': '2026-03-20', 'extra_struck': 1, 'extra_shutdown': 0, 'label': 'Kuwait Mina al-Ahmadi hit again'},
    ]
    
    # Count ship attacks per day
    ship_attacks_by_day = {}
    for a in attacks:
        d = a['date']
        ship_attacks_by_day[d] = ship_attacks_by_day.get(d, 0) + 1
    
    # Build cumulative timeline
    all_dates = set()
    for a in attacks:
        all_dates.add(a['date'])
    for f in facility_events:
        all_dates.add(f['date'])
    all_dates.add('2026-02-27')  # pre-war baseline
    
    timeline = []
    cum_struck = 0
    cum_shutdown = 0
    facility_map = {f['date']: f for f in facility_events}
    
    for d in sorted(all_dates):
        ship_count = ship_attacks_by_day.get(d, 0)
        fac = facility_map.get(d, {})
        
        if d == '2026-02-27':
            timeline.append({'date': d, 'struck': 0, 'shutdown': 0, 'ships_attacked': 0, 'label': 'Pre-war baseline'})
            continue
        
        if d == '2026-02-28':
            cum_struck = fac.get('struck', cum_struck)
            cum_shutdown = fac.get('shutdown', cum_shutdown)
        else:
            cum_struck += ship_count + fac.get('extra_struck', 0)
            cum_shutdown += fac.get('extra_shutdown', 0)
        
        label_parts = []
        if ship_count > 0:
            label_parts.append(f'{ship_count} ship(s) attacked')
        if fac.get('label'):
            label_parts.append(fac['label'])
        
        timeline.append({
            'date': d,
            'struck': cum_struck,
            'shutdown': cum_shutdown,
            'ships_attacked': ship_count,
            'label': '; '.join(label_parts) if label_parts else 'No new incidents',
        })
    
    return timeline

def main():
    print(f'[{datetime.now(timezone.utc).isoformat()}] Scraping Wikipedia ship attacks...')
    attacks = fetch_wiki_attacks()
    print(f'  Found {len(attacks)} verified ship attacks')
    
    total_casualties = sum(a['casualties'] for a in attacks)
    total_abandoned = sum(1 for a in attacks if a['abandoned'])
    total_sunk = sum(1 for a in attacks if a['sunk'])
    print(f'  Casualties: {total_casualties}, Abandoned: {total_abandoned}, Sunk: {total_sunk}')
    
    timeline = build_daily_timeline(attacks)
    latest = timeline[-1] if timeline else {}
    print(f'  Timeline: {len(timeline)} days, latest: {latest.get("date")} — {latest.get("struck")} struck, {latest.get("shutdown")} shutdown')
    
    output = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'source': 'Wikipedia 2026 Strait of Hormuz crisis + ISW + Reuters',
        'attacks': attacks,
        'timeline': timeline,
        'summary': {
            'total_attacks': len(attacks),
            'total_casualties': total_casualties,
            'total_abandoned': total_abandoned,
            'total_sunk': total_sunk,
            'latest_struck': latest.get('struck', 0),
            'latest_shutdown': latest.get('shutdown', 0),
        }
    }
    
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f'  Written to {OUT_FILE}')
    
    # Also copy to hormuz-crisis project
    alt = os.path.expanduser('~/projects/breaking-trades/articles/hormuz-crisis/hormuz-timeline.json')
    try:
        with open(alt, 'w') as f:
            json.dump(output, f, indent=2)
        print(f'  Also written to {alt}')
    except Exception as e:
        print(f'  Warning: could not write to {alt}: {e}')

    # Git push to GitHub Pages
    import subprocess
    docs_dir = os.path.dirname(OUT_DIR)  # docs/
    try:
        subprocess.run(['git', 'add', 'data/hormuz-timeline.json'], cwd=docs_dir, capture_output=True, timeout=10)
        diff = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=docs_dir, capture_output=True, timeout=10)
        if diff.returncode != 0:
            subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], cwd=docs_dir, capture_output=True, timeout=30)
            subprocess.run(['git', 'commit', '-m', f'auto: hormuz timeline update {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}'], cwd=docs_dir, capture_output=True, timeout=10)
            r = subprocess.run(['git', 'push', 'origin', 'main'], cwd=docs_dir, capture_output=True, timeout=30, text=True)
            if r.returncode == 0:
                print('  Pushed to GitHub Pages')
            else:
                print(f'  Push failed: {r.stderr.strip()}')
        else:
            print('  No changes to push')
    except Exception as e:
        print(f'  Git push error: {e}')

if __name__ == '__main__':
    main()
