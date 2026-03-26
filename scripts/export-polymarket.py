#!/usr/bin/env python3
"""
export-polymarket.py — Export tracked Polymarket events to docs/polymarket.json
Fetches both individual markets (keyword match) and tracked events (by slug).
Run from cron every 5-10 minutes.
"""

import json, os, sys, urllib.request
from datetime import datetime, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
OUTPUT = os.path.join(ROOT, "docs", "polymarket.json")

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets?closed=false&limit=200&order=volume&ascending=false"
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events?slug={slug}"

# Keywords to match individual markets
KEYWORDS = ['iran', 'israel', 'idf', 'hezbollah', 'houthi', 'irgc', 'middle east', 'gaza', 'tehran', 'hormuz']
EXCLUDE = ['thailand', 'cambodia', 'china x india', 'gta', 'taylor', 'bitcoin', 'crypto', 'microstrategy', 'annex']

# Tracked event slugs (multi-outcome markets)
TRACKED_EVENTS = [
    "military-action-against-iran-ends-on",
]

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MagenYehuda/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"Fetch error {url}: {e}", file=sys.stderr)
        return None

def main():
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "markets": [],
        "events": []
    }

    # 1. Individual markets by keyword
    data = fetch_json(GAMMA_MARKETS)
    if data:
        for m in data:
            q = m.get("question", "").lower()
            if not any(kw in q for kw in KEYWORDS):
                continue
            if any(ex in q for ex in EXCLUDE):
                continue
            prices = m.get("outcomePrices", "[]")
            p = json.loads(prices) if isinstance(prices, str) else prices
            yes = float(p[0]) if isinstance(p, list) and len(p) > 0 else 0
            result["markets"].append({
                "question": m.get("question", "?"),
                "slug": m.get("slug", ""),
                "yes": round(yes * 100, 1),
                "volume": m.get("volumeNum", m.get("volume", 0)),
                "url": f"https://polymarket.com/event/{m.get('slug', '')}"
            })

    # 2. Tracked events (multi-outcome)
    for slug in TRACKED_EVENTS:
        events = fetch_json(GAMMA_EVENTS.format(slug=slug))
        if not events or not isinstance(events, list):
            continue
        evt = events[0]
        sub_markets = []
        for m in evt.get("markets", []):
            prices = m.get("outcomePrices", "[]")
            p = json.loads(prices) if isinstance(prices, str) else prices
            yes = float(p[0]) if isinstance(p, list) and len(p) > 0 else 0
            if yes > 0.001:  # Skip 0% markets
                sub_markets.append({
                    "question": m.get("question", "?"),
                    "yes": round(yes * 100, 1),
                    "volume": m.get("volumeNum", m.get("volume", 0)),
                })
        sub_markets.sort(key=lambda x: -x["yes"])
        result["events"].append({
            "title": evt.get("title", "?"),
            "slug": slug,
            "url": f"https://polymarket.com/event/{slug}",
            "markets": sub_markets
        })

    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(result['markets'])} markets + {len(result['events'])} events → {OUTPUT}")

    # Git push
    import subprocess
    try:
        subprocess.run(["git", "add", "docs/polymarket.json"], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"auto: polymarket update"], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True, capture_output=True)
        print("Pushed to GitHub Pages")
    except subprocess.CalledProcessError:
        pass  # No changes or push conflict — fine

if __name__ == "__main__":
    main()
