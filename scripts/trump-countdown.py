#!/usr/bin/env python3
"""Trump Iran energy strike pause countdown — posts hourly to both Telegram channels.
New deadline: April 6, 2026 8:00 PM ET (00:00 UTC April 7)."""
import json, urllib.request, time
from datetime import datetime, timezone, timedelta

DEADLINE_UTC = datetime(2026, 4, 7, 0, 0, 0, tzinfo=timezone.utc)  # Apr 6, 8 PM ET = Apr 7, 00:00 UTC
TOTAL_PAUSE_HOURS = 10 * 24  # 10 days
IST = timezone(timedelta(hours=3))
ET = timezone(timedelta(hours=-4))

CONFIG_PATH = "/Users/idanshimon/.openclaw/workspace/skills/iran-israel-alerts/config.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)
BOT_TOKEN = config["telegram_bot_token"]

EN_CHAT = "@magenyehudaupdates"
HE_CHAT = "@opssheagathaariupdates"

def send(chat_id, text):
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
            return d.get("ok", False)
    except Exception as e:
        print(f"Send error ({chat_id}): {e}")
        return False

def get_bar(pct):
    filled = int(pct / 5)
    return "█" * filled + "░" * (20 - filled)

now = datetime.now(timezone.utc)
diff = DEADLINE_UTC - now
total_secs = diff.total_seconds()

if total_secs <= 0:
    expired_ago_h = abs(int(total_secs)) // 3600
    expired_ago_m = abs(int(total_secs)) % 3600 // 60
    en = ("🚨🇺🇸 <b>TRUMP ENERGY STRIKE PAUSE — EXPIRED</b> 🇮🇷🚨\n\n"
          f"⏰ <b>The 10-day pause has ended.</b>\n\n"
          f"📅 Expired: Monday, April 6 — 8:00 PM ET\n"
          f"🕐 Expired {expired_ago_h}h {expired_ago_m}m ago\n\n"
          "⚡ Trump threatened to resume strikes on Iran energy plants.\n"
          "⚠️ Note: First pause (Mar 23) was violated within hours.\n"
          "📡 Monitoring for developments...")
    he = ("🚨🇺🇸 <b>הפסקת התקיפות של טראמפ — פגה</b> 🇮🇷🚨\n\n"
          f"⏰ <b>ההפסקה של 10 ימים הסתיימה.</b>\n\n"
          f"📅 פג: יום שני, 6 באפריל — 03:00 (שעון ישראל)\n"
          f"🕐 עבר לפני {expired_ago_h} שעות ו-{expired_ago_m} דקות\n\n"
          "⚡ טראמפ איים לחדש תקיפות על תשתיות אנרגיה באיראן.\n"
          "⚠️ תזכורת: ההפסקה הראשונה (23 במרץ) הופרה תוך שעות.\n"
          "📡 עוקבים אחר התפתחויות...")
    hours, mins = 0, 0
else:
    days = int(total_secs // 86400)
    hours = int((total_secs % 86400) // 3600)
    mins = int((total_secs % 3600) // 60)
    elapsed_pct = min(100, int(((TOTAL_PAUSE_HOURS * 3600 - total_secs) / (TOTAL_PAUSE_HOURS * 3600)) * 100))
    bar = get_bar(elapsed_pct)
    
    if days <= 1:
        urgency_en = "🔴 CRITICAL — Final hours"
        urgency_he = "🔴 קריטי — הימים האחרונים"
    elif days <= 3:
        urgency_en = "🟠 HIGH — Less than 3 days"
        urgency_he = "🟠 גבוה — פחות מ-3 ימים"
    elif days <= 5:
        urgency_en = "🟡 ELEVATED — Less than 5 days"
        urgency_he = "🟡 מוגבר — פחות מ-5 ימים"
    else:
        urgency_en = "⚪ ACTIVE — Pause countdown in progress"
        urgency_he = "⚪ פעיל — הספירה לאחור נמשכת"

    deadline_et = DEADLINE_UTC.astimezone(ET).strftime("%b %d, %I:%M %p ET")
    deadline_ist = DEADLINE_UTC.astimezone(IST).strftime("%d/%m %H:%M")

    en = (f"⏸🇺🇸 <b>TRUMP ENERGY STRIKE PAUSE</b> 🇮🇷⏸\n\n"
          f"<b>🕐 {days}d {hours}h {mins}m REMAINING</b>\n"
          f"[{bar}] {elapsed_pct}%\n\n"
          f"📅 Deadline: {deadline_et}\n"
          f"📊 Status: {urgency_en}\n\n"
          f"⚡ 10-day pause on Iran energy plant strikes\n"
          f"🗣 Trump: \"Iranian Government request... talks going very well\"\n"
          f"🇮🇷 Iran denies any direct negotiations\n"
          f"⚠️ First pause (Mar 23) was violated within hours")
    
    he = (f"⏸🇺🇸 <b>הפסקת תקיפות אנרגיה — טראמפ</b> 🇮🇷⏸\n\n"
          f"<b>🕐 נותרו {days} ימים, {hours} שעות ו-{mins} דקות</b>\n"
          f"[{bar}] {elapsed_pct}%\n\n"
          f"📅 דדליין: {deadline_ist} (שעון ישראל)\n"
          f"📊 סטטוס: {urgency_he}\n\n"
          f"⚡ הפסקה של 10 ימים בתקיפת תשתיות אנרגיה באיראן\n"
          f"🗣 טראמפ: \"לבקשת ממשלת איראן... השיחות מתקדמות מצוין\"\n"
          f"🇮🇷 איראן מכחישה משא ומתן ישיר\n"
          f"⚠️ ההפסקה הראשונה (23 במרץ) הופרה תוך שעות")

ok_en = send(EN_CHAT, en)
ok_he = send(HE_CHAT, he)
remaining = f"{int(total_secs//86400)}d {int((total_secs%86400)//3600)}h" if total_secs > 0 else "EXPIRED"
print(f"[{datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')}] EN={ok_en} HE={ok_he} | {remaining}")
