#!/usr/bin/env python3
"""
Generate hourly intelligence summary in Hebrew and English.
Reads intel log, generates two separate messages with personality.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATE_DIR = os.path.join(SKILL_DIR, "state")
CONFIG_FILE = os.path.join(SKILL_DIR, "config.json")


def load_intel(hours=1):
    """Load intel events from the last N hours."""
    log_path = os.path.join(STATE_DIR, "intel-log.jsonl")
    if not os.path.exists(log_path):
        return []
    cutoff = time.time() - (hours * 3600)
    events = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("logged_at", 0) >= cutoff:
                    events.append(ev)
            except:
                continue
    return events


def load_stats():
    """Load current tracking stats."""
    stats = {
        "fires": 0, "quakes": 0, "osint_channels": 0,
        "threat": "UNKNOWN"
    }
    try:
        with open(os.path.join(STATE_DIR, "firms-seen.json")) as f:
            stats["fires"] = len(json.load(f).get("seen", {}))
    except: pass
    try:
        with open(os.path.join(STATE_DIR, "seismic-seen.json")) as f:
            stats["quakes"] = len(json.load(f).get("seen", {}))
    except: pass
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            stats["osint_channels"] = len(cfg.get("telegram_osint_channels", []))
    except: pass
    try:
        # Get from watcher log
        log_path = os.path.join(STATE_DIR, "watcher.log")
        if os.path.exists(log_path):
            with open(log_path) as f:
                lines = f.readlines()
            for line in reversed(lines[-100:]):
                if "THREAT LEVEL:" in line:
                    for lvl in ["CRITICAL", "HIGH", "ELEVATED", "GREEN"]:
                        if f"→ {lvl}" in line or f"→ ⚫ {lvl}" in line or f"→ 🔴 {lvl}" in line or f"→ 🟠 {lvl}" in line or f"→ 🟢 {lvl}" in line:
                            stats["threat"] = lvl
                            break
                    if stats["threat"] != "UNKNOWN":
                        break
    except: pass
    return stats


def count_events(events):
    """Count events by type."""
    counts = {}
    for ev in events:
        t = ev.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts


def extract_osint_highlights(events, max_items=8):
    """Extract OSINT alert text highlights."""
    highlights = []
    for ev in events:
        if ev.get("type") == "osint":
            alerts = ev.get("alerts", [])
            for a in alerts:
                text = a.get("text", "")[:200]
                source = a.get("source", "")
                channel = a.get("channel", "")
                if text:
                    highlights.append({
                        "text": text,
                        "source": source,
                        "channel": channel,
                    })
    return highlights[:max_items]


def extract_siren_events(events):
    """Extract siren details."""
    sirens = []
    for ev in events:
        if ev.get("type") == "siren":
            sirens.append({
                "details": ev.get("details", ""),
                "threat_level": ev.get("threat_level", ""),
            })
    return sirens


def extract_fire_summary(events):
    """Extract fire data."""
    total = 0
    for ev in events:
        if ev.get("type") == "fires":
            total += ev.get("count", 0)
    return total


def extract_quake_summary(events):
    """Extract quake data."""
    total = 0
    details = []
    for ev in events:
        if ev.get("type") in ("seismic", "seismic_osint"):
            total += ev.get("count", 0)
            if ev.get("data", {}).get("quakes"):
                for q in ev["data"]["quakes"]:
                    details.append(f"M{q.get('mag', '?')} {q.get('place', '?')}")
    return total, details


def extract_market_moves(events):
    """Extract Polymarket movements."""
    moves = []
    for ev in events:
        if ev.get("type") == "polymarket":
            moves.append(ev.get("text", ""))
    return moves


def extract_threat_changes(events, hebrew=False):
    """Extract threat level transitions."""
    changes = []
    he_map = {"GREEN": "שגרה", "ELEVATED": "מוגבר", "HIGH": "גבוה", "CRITICAL": "קריטי"}
    for ev in events:
        if ev.get("type") == "threat_change":
            f = ev.get('from', '?')
            t = ev.get('to', '?')
            r = ev.get('reason', '')
            if hebrew:
                f = he_map.get(f, f)
                t = he_map.get(t, t)
                # Translate common reasons
                if "major population" in r:
                    r = "צפירות במרכזי אוכלוסייה"
                elif "Pikud HaOref" in r:
                    r = "פיקוד העורף משדר"
                elif "stepping down" in r:
                    r = "אין צפירות חדשות"
                elif "returning to baseline" in r:
                    r = "חזרה לשגרה"
            changes.append(f"{f} → {t}: {r}")
    return changes


def threat_emoji(level):
    return {"CRITICAL": "⚫", "HIGH": "🔴", "ELEVATED": "🟠", "GREEN": "🟢"}.get(level, "⚪")


THREAT_LEVEL_HE = {
    "GREEN": "שגרה",
    "ELEVATED": "מוגבר",
    "HIGH": "גבוה",
    "CRITICAL": "קריטי",
}


def generate_hebrew(events, stats, now_str):
    """Generate Hebrew summary — confident Israeli style."""
    counts = count_events(events)
    sirens = extract_siren_events(events)
    osint = extract_osint_highlights(events)
    fires_count = extract_fire_summary(events)
    quakes_count, quake_details = extract_quake_summary(events)
    markets = extract_market_moves(events)
    threat_changes = extract_threat_changes(events, hebrew=True)
    te = threat_emoji(stats["threat"])
    threat_he = THREAT_LEVEL_HE.get(stats["threat"], stats["threat"])

    lines = [
        f"<b>🇮🇱 סיכום מצב שעתי — מגן יהודה</b>",
        f"<i>{now_str}</i>",
        "",
        f"{te} <b>רמת איום: {threat_he}</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Sirens
    if sirens:
        lines.append("")
        lines.append(f"🚨 <b>צבע אדום — {len(sirens)} אירוע(י) התרעה</b>")
        for s in sirens[:5]:
            d = s.get("details", "").replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
            if d:
                lines.append(f"  • {d[:150]}")
    else:
        lines.append("")
        lines.append("🟢 <b>אין התרעות צבע אדום בשעה האחרונה</b>")

    # OSINT
    if osint:
        lines.append("")
        lines.append(f"📡 <b>עדכוני מודיעין ({len(osint)} חדשות):</b>")
        for item in osint[:6]:
            src_emoji = {"telegram": "📢", "twitter": "🐦", "rss": "📰"}.get(item["source"], "📡")
            ch = item.get("channel", "")
            text = item["text"].replace("<", "&lt;").replace(">", "&gt;")
            if ch:
                lines.append(f"  {src_emoji} <b>{ch}:</b> {text[:120]}")
            else:
                lines.append(f"  {src_emoji} {text[:120]}")

    # Fires
    if fires_count:
        lines.append("")
        lines.append(f"🔥 <b>{fires_count} שריפות/חום חריג זוהו באיראן מלוויין</b>")

    # Seismic
    if quakes_count:
        lines.append("")
        lines.append(f"🌍 <b>{quakes_count} רעידות אדמה באיראן</b>")
        for d in quake_details[:3]:
            lines.append(f"  • {d}")

    # Markets
    if markets:
        lines.append("")
        lines.append("📊 <b>תנועות שוק:</b>")
        for m in markets[:3]:
            clean = m.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
            lines.append(f"  {clean[:150]}")

    # Threat changes
    if threat_changes:
        lines.append("")
        lines.append("⚡ <b>שינויי רמת איום:</b>")
        for tc in threat_changes:
            lines.append(f"  • {tc[:120]}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # Analyst assessment — confident Israeli style
    lines.append("")
    total_events = len(events)

    if stats["threat"] == "CRITICAL":
        lines.append("💪 <b>הערכת מצב:</b>")
        lines.append("אחים, המצב חם אבל אנחנו בסדר. צה״ל וכוחות הביטחון עובדים מסביב לשעון. מערכות ההגנה שלנו הכי מתקדמות בעולם — חץ, כיפת ברזל, שרביט קסמים. אנחנו עם שעבר הכל ותמיד יצא חזק יותר. 🇮🇱")
        lines.append("")
        lines.append("שימרו על קור רוח, הקשיבו להנחיות פיקוד העורף, ותדעו שיש לנו את הגב. ביחד ננצח! 💙🤍")
    elif stats["threat"] == "HIGH":
        lines.append("💪 <b>הערכת מצב:</b>")
        lines.append("רמת האיום גבוהה אבל אנחנו ערוכים. מערכת ההגנה הישראלית היא הטובה בעולם ואנחנו לא לבד — בעלות ברית לצידנו. המודיעין שלנו עוקב אחרי כל תזוזה באיראן.")
        lines.append("")
        lines.append("תישארו חזקים, תישארו מעודכנים. עם ישראל חי! 🇮🇱💪")
    elif total_events > 0:
        lines.append("💪 <b>הערכת מצב:</b>")
        lines.append("שעה יחסית שקטה. הלוויינים שלנו סורקים, המודיעין עובד, והבוט הזה שומר לכם על העורף הדיגיטלי 😎")
        lines.append("")
        lines.append("ישראל חזקה, ותמיד תהיה. 🇮🇱")
    else:
        lines.append("💪 <b>הערכת מצב:</b>")
        lines.append("שקט יחסי — וזה דבר טוב. ממשיכים לעקוב 24/7. אם משהו יזוז — תדעו ראשונים. 🛰️")
        lines.append("")
        lines.append("רגע של שקט? תנצלו, תשתו קפה, תחבקו את האהובים. ביחד ננצח! 🇮🇱☕")

    lines.append("")
    lines.append(f"<i>🤖 MagenYehudaBot | עדכון הבא בעוד שעה</i>")

    return "\n".join(lines)


def generate_english(events, stats, now_str):
    """Generate English summary — confident, knowledgeable analyst style."""
    counts = count_events(events)
    sirens = extract_siren_events(events)
    osint = extract_osint_highlights(events)
    fires_count = extract_fire_summary(events)
    quakes_count, quake_details = extract_quake_summary(events)
    markets = extract_market_moves(events)
    threat_changes = extract_threat_changes(events)
    te = threat_emoji(stats["threat"])

    lines = [
        f"<b>🇮🇱 HOURLY INTEL SUMMARY — Magen Yehuda</b>",
        f"<i>{now_str}</i>",
        "",
        f"{te} <b>Threat Level: {stats['threat']}</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Sirens
    if sirens:
        lines.append("")
        lines.append(f"🚨 <b>RED ALERT SIRENS — {len(sirens)} event(s)</b>")
        for s in sirens[:5]:
            d = s.get("details", "").replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
            if d:
                lines.append(f"  • {d[:150]}")
    else:
        lines.append("")
        lines.append("🟢 <b>No siren alerts in the past hour</b>")

    # OSINT
    if osint:
        lines.append("")
        lines.append(f"📡 <b>OSINT Intelligence ({len(osint)} updates):</b>")
        for item in osint[:6]:
            src_emoji = {"telegram": "📢", "twitter": "🐦", "rss": "📰"}.get(item["source"], "📡")
            ch = item.get("channel", "")
            text = item["text"].replace("<", "&lt;").replace(">", "&gt;")
            if ch:
                lines.append(f"  {src_emoji} <b>{ch}:</b> {text[:120]}")
            else:
                lines.append(f"  {src_emoji} {text[:120]}")

    # Fires
    if fires_count:
        lines.append("")
        lines.append(f"🔥 <b>{fires_count} satellite fire detection(s) in Iran</b>")

    # Seismic
    if quakes_count:
        lines.append("")
        lines.append(f"🌍 <b>{quakes_count} earthquake(s) in Iran region</b>")
        for d in quake_details[:3]:
            lines.append(f"  • {d}")

    # Markets
    if markets:
        lines.append("")
        lines.append("📊 <b>Market Movements:</b>")
        for m in markets[:3]:
            clean = m.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
            lines.append(f"  {clean[:150]}")

    # Threat changes
    if threat_changes:
        lines.append("")
        lines.append("⚡ <b>Threat Level Changes:</b>")
        for tc in threat_changes:
            lines.append(f"  • {tc[:120]}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # Analyst assessment
    lines.append("")
    total_events = len(events)

    if stats["threat"] == "CRITICAL":
        lines.append("💪 <b>Analyst Assessment:</b>")
        lines.append("Situation is hot but Israel is built for this. Arrow, Iron Dome, David's Sling — the most advanced layered defense system on the planet. IDF and intelligence services are operating at full capacity around the clock.")
        lines.append("")
        lines.append("Israel has faced existential threats before and came out stronger every time. Follow Home Front Command instructions and stay calm. Am Yisrael Chai! 🇮🇱")
    elif stats["threat"] == "HIGH":
        lines.append("💪 <b>Analyst Assessment:</b>")
        lines.append("Elevated threat but Israel's defense posture is solid. Intelligence is tracking every movement in Iran. Coalition allies are on standby. The Iranian regime knows that any escalation will be met with overwhelming response.")
        lines.append("")
        lines.append("Stay strong, stay informed. Israel stands. 🇮🇱💪")
    elif total_events > 0:
        lines.append("💪 <b>Analyst Assessment:</b>")
        lines.append("Relatively quiet hour. Satellites scanning, intelligence flowing, and this bot has your digital six covered 😎")
        lines.append("")
        lines.append("Israel is strong, always has been, always will be. 🇮🇱")
    else:
        lines.append("💪 <b>Analyst Assessment:</b>")
        lines.append("All quiet on the eastern front. Monitoring continues 24/7 across 30+ sources. If anything moves — you'll know first. 🛰️")
        lines.append("")
        lines.append("A moment of calm? Take it. Hug your loved ones. We've got watch. Am Yisrael Chai! 🇮🇱☕")

    lines.append("")
    lines.append(f"<i>🤖 MagenYehudaBot | Next update in ~1 hour</i>")

    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)

    # Per-channel timezones: Hebrew gets Israel time, English gets Eastern time
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    # Read per-output timezone from config
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    tz_en = "America/New_York"
    tz_he = "Asia/Jerusalem"
    try:
        import json as _json
        cfg = _json.load(open(config_path))
        for o in cfg.get("outputs", []):
            if o.get("id") == "main":
                tz_en = o.get("timezone", tz_en)
            elif o.get("id") == "hebrew":
                tz_he = o.get("timezone", tz_he)
    except Exception:
        pass

    now_en = now.astimezone(ZoneInfo(tz_en))
    now_he = now.astimezone(ZoneInfo(tz_he))
    now_str_en = now_en.strftime("%Y-%m-%d %H:%M %Z")
    now_str_he = now_he.strftime("%Y-%m-%d %H:%M %Z")

    events = load_intel(hours=1)
    stats = load_stats()

    # Rotate old entries
    log_path = os.path.join(STATE_DIR, "intel-log.jsonl")
    if os.path.exists(log_path):
        size = os.path.getsize(log_path)
        if size > 5 * 1024 * 1024:  # 5MB
            cutoff = time.time() - 48 * 3600
            kept = []
            with open(log_path) as f:
                for line in f:
                    try:
                        ev = json.loads(line.strip())
                        if ev.get("logged_at", 0) >= cutoff:
                            kept.append(line.strip())
                    except: continue
            with open(log_path, "w") as f:
                for line in kept:
                    f.write(line + "\n")

    hebrew = generate_hebrew(events, stats, now_str_he)
    english = generate_english(events, stats, now_str_en)

    output = {
        "hebrew": hebrew,
        "english": english,
        "event_count": len(events),
        "stats": stats,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
