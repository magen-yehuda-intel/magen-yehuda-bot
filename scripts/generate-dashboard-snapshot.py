#!/usr/bin/env python3
"""
Generate a CENTCOM theater dashboard screenshot via headless Chromium.

Loads the live centcom.html dashboard, waits for data to render,
takes a screenshot, and generates a caption from the page state.

Usage:
    python3 generate-dashboard-snapshot.py <output.png> [--caption-file <caption.txt>]
    python3 generate-dashboard-snapshot.py <output.png> [--caption-file <caption.txt>] [--width 1400] [--height 900] [--wait 8]
"""

import sys
import os
import json
import time
from datetime import datetime, timezone

DASHBOARD_URL = "https://magen-yehuda-intel.github.io/magen-yehuda-bot/centcom.html"
DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 900
DEFAULT_WAIT = 10  # seconds to let tiles + API data load


def take_screenshot(output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, wait=DEFAULT_WAIT):
    from playwright.sync_api import sync_playwright

    print(f"  🌐 Launching headless Chromium ({width}x{height})...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        print(f"  📡 Loading {DASHBOARD_URL}...")
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)

        # Close any open panels (live feed) for cleaner screenshot
        try:
            page.evaluate("""() => {
                // Close live feed panel if open
                const feedPanel = document.getElementById('feed-panel');
                if (feedPanel && feedPanel.style.display !== 'none') {
                    const closeBtn = feedPanel.querySelector('.close-btn, [onclick*="closeFeed"], [onclick*="toggleFeed"]');
                    if (closeBtn) closeBtn.click();
                }
                // Close siren history if open
                const orefPanel = document.getElementById('oref-history-panel');
                if (orefPanel) orefPanel.style.display = 'none';
            }""")
        except:
            pass

        # Wait for map tiles and data to load
        print(f"  ⏳ Waiting {wait}s for data to render...")
        time.sleep(wait)

        # Extract stats from the page for caption
        stats = page.evaluate("""() => {
            const getText = id => {
                const el = document.getElementById(id);
                return el ? el.textContent.trim() : '0';
            };
            return {
                fires: getText('cnt-fires'),
                seismic: getText('cnt-seismic'),
                correlations: getText('cnt-correlations'),
                strikes: getText('cnt-strikes'),
                osint: getText('cnt-osint'),
                aircraft: getText('cnt-aircraft'),
                orefStatus: document.getElementById('oref-status')?.textContent?.trim() || '',
            };
        }""")
        print(f"  📊 Stats: {json.dumps(stats)}")

        # Take screenshot
        page.screenshot(path=output_path, full_page=False)
        browser.close()

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✅ Saved: {output_path} ({size_kb:.0f} KB)")
    return stats


def generate_caption(stats):
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "🎯 CENTCOM Theater Operations — Live Snapshot",
        f"📅 {ts_str}",
        "",
    ]

    fires = int(stats.get("fires", 0) or 0)
    seismic = int(stats.get("seismic", 0) or 0)
    correlations = int(stats.get("correlations", 0) or 0)
    strikes = int(stats.get("strikes", 0) or 0)
    aircraft = int(stats.get("aircraft", 0) or 0)

    if fires: lines.append(f"🔥 {fires} satellite fire detections")
    if seismic: lines.append(f"🔴 {seismic} seismic events")
    if correlations: lines.append(f"⚡ {correlations} strike correlations")
    if strikes: lines.append(f"💥 {strikes} ACLED strikes")
    if aircraft: lines.append(f"✈️ {aircraft} tracked aircraft")

    oref = stats.get("orefStatus", "")
    if oref and "alert" in oref.lower():
        lines.append(f"🚨 {oref}")

    lines.extend([
        "",
        f"📡 Live dashboard: {DASHBOARD_URL}",
    ])
    return "\n".join(lines)


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/myi-dashboard-snapshot.png"
    caption_path = None
    width = DEFAULT_WIDTH
    height = DEFAULT_HEIGHT
    wait = DEFAULT_WAIT

    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--caption-file" and i + 1 < len(args): caption_path = args[i + 1]
        if a == "--width" and i + 1 < len(args): width = int(args[i + 1])
        if a == "--height" and i + 1 < len(args): height = int(args[i + 1])
        if a == "--wait" and i + 1 < len(args): wait = int(args[i + 1])

    print("🎯 Magen Yehuda Intel — Dashboard Screenshot")
    print("=" * 50)

    stats = take_screenshot(output_path, width, height, wait)
    caption = generate_caption(stats)

    print(f"\n{caption}")

    if caption_path:
        with open(caption_path, "w") as f:
            f.write(caption)
        print(f"  📝 Caption saved: {caption_path}")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
