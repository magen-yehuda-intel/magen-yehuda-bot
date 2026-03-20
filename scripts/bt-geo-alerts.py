#!/usr/bin/env python3
"""bt-geo-alerts.py — Push high-impact geopolitical events to BreakingTrades Telegram.

Queries enriched intel events from Magen Yehuda DB, maps sectors to BT tickers,
and sends alerts for market_impact >= 7 events.

Usage:
    python3 bt-geo-alerts.py [--hours 1] [--min-impact 7] [--dry-run]

Cron (every 30 min):
    */30 * * * * PATH=/opt/homebrew/bin:$PATH python3 /path/to/bt-geo-alerts.py --hours 1 >> /path/to/bt-geo-alerts.log 2>&1
"""

import json
import os
import sys
import time
import hashlib
import argparse
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta

# --- Config ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "..", "state", "bt-geo-alerts-seen.json")
DB_ENDPOINT = "https://magenyehudadata.table.core.windows.net"
DB_TABLE = "intelevents"

# BT Telegram
BT_CHAT_ID = "-1003750832486"

ET = timezone(timedelta(hours=-4))

# Sector → BT tickers mapping
SECTOR_TICKERS = {
    "oil":         ["CL (WTI)", "BZ (Brent)", "XLE", "XOP", "EQNR", "CVX", "COP"],
    "natural_gas": ["NG (NatGas)", "LNG", "AIPO", "EQT"],
    "shipping":    ["INSW", "STNG", "FRO", "BDRY"],
    "defense":     ["ITA", "LMT", "RTX", "GD", "NOC"],
    "insurance":   ["RE", "RNR", "AIG"],
    "equities":    ["SPY", "QQQ"],
    "bonds":       ["TLT", "IEF"],
    "crypto":      ["BTC", "ETH"],
}

# Impact emoji scale
IMPACT_EMOJI = {
    10: "🔴🔴🔴",
    9:  "🔴🔴",
    8:  "🔴",
    7:  "🟠",
}


def get_bt_bot_token():
    """Get BT bot token from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", "breakingtradesbot", "-w"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return None


def get_azure_token():
    """Get Azure access token for Table Storage."""
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token", "--resource", "https://storage.azure.com",
             "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    except Exception:
        return None


def query_enriched_events(hours=1, min_impact=7):
    """Query enriched events from Azure Table Storage."""
    token = get_azure_token()
    if not token:
        print("[bt-geo] Failed to get Azure token")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    # Query recent partitions
    dates = set()
    d = cutoff
    while d <= datetime.now(timezone.utc):
        dates.add(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)

    events = []
    for date in sorted(dates):
        url = (f"{DB_ENDPOINT}/{DB_TABLE}()"
               f"?$filter=PartitionKey%20eq%20'{date}'%20and%20enriched%20eq%20true"
               f"&$select=PartitionKey,RowKey,ts,market_impact,market_sectors,is_breaking,severity,location,summary,event_category,target_type")
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;odata=nometadata",
            "x-ms-version": "2020-12-06",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                for e in data.get("value", []):
                    mi = e.get("market_impact", 0)
                    if isinstance(mi, str):
                        mi = int(mi) if mi.isdigit() else 0
                    ts = float(e.get("ts", 0) or 0)
                    if mi >= min_impact and ts >= cutoff.timestamp():
                        e["_mi"] = mi
                        e["_ts"] = ts
                        events.append(e)
        except Exception as ex:
            print(f"[bt-geo] DB query error for {date}: {ex}")

    events.sort(key=lambda x: x["_ts"])
    return events


def load_seen():
    """Load set of already-alerted event IDs."""
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            # Prune old entries (keep last 2000)
            if len(data) > 2000:
                data = data[-2000:]
            return set(data)
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen):
    """Save seen event IDs."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen)[-2000:], f)


def format_alert(event):
    """Format a single event as a BT Telegram alert."""
    mi = event["_mi"]
    ts = event["_ts"]
    t_et = datetime.fromtimestamp(ts, tz=ET).strftime("%I:%M %p ET")
    emoji = IMPACT_EMOJI.get(mi, "🟡")
    loc = event.get("location", "")
    summary = event.get("summary", "")
    sectors = event.get("market_sectors", "")
    is_breaking = event.get("is_breaking", False)

    # Map sectors to tickers
    sector_list = [s.strip() for s in sectors.split(",") if s.strip()] if sectors else []
    tickers = []
    for s in sector_list:
        tickers.extend(SECTOR_TICKERS.get(s, []))
    # Dedupe preserving order
    seen_t = set()
    unique_tickers = []
    for t in tickers:
        if t not in seen_t:
            unique_tickers.append(t)
            seen_t.add(t)

    lines = []
    brk = "⚡ BREAKING " if is_breaking else ""
    lines.append(f"{emoji} {brk}Geopolitical Alert (Impact {mi}/10)")
    lines.append(f"🕐 {t_et}")
    if loc:
        lines.append(f"📍 {loc}")
    lines.append(f"\n{summary}")
    if unique_tickers:
        lines.append(f"\n📊 Watch: {', '.join(unique_tickers[:10])}")
    if sector_list:
        lines.append(f"🏷️ Sectors: {', '.join(sector_list)}")

    return "\n".join(lines)


def send_telegram(token, text):
    """Send message to BT Telegram channel."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({
        "chat_id": BT_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as ex:
        print(f"[bt-geo] Telegram send failed: {ex}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=1)
    parser.add_argument("--min-impact", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"[bt-geo] Starting — lookback {args.hours}h, min_impact {args.min_impact}, dry_run={args.dry_run}")

    events = query_enriched_events(hours=args.hours, min_impact=args.min_impact)
    print(f"[bt-geo] Found {len(events)} events with impact >= {args.min_impact}")

    if not events:
        print("[bt-geo] Nothing to alert")
        return

    seen = load_seen()
    bt_token = None if args.dry_run else get_bt_bot_token()

    sent = 0
    for event in events:
        eid = f"{event['PartitionKey']}_{event['RowKey']}"
        if eid in seen:
            continue

        alert_text = format_alert(event)

        if args.dry_run:
            print(f"\n--- DRY RUN ---\n{alert_text}\n")
        else:
            if bt_token and send_telegram(bt_token, alert_text):
                print(f"[bt-geo] Sent: impact={event['_mi']} {event.get('location','?')}")
                sent += 1
                time.sleep(1)  # Rate limit
            else:
                print(f"[bt-geo] Failed to send: {eid}")
                continue

        seen.add(eid)

    save_seen(seen)
    print(f"[bt-geo] Done — sent {sent} alerts")


if __name__ == "__main__":
    main()
