#!/usr/bin/env python3
"""Trump 48h ultimatum countdown — posts hourly to both Telegram channels."""
import json, urllib.request, time
from datetime import datetime, timezone, timedelta

DEADLINE_UTC = datetime(2026, 3, 23, 23, 44, 0, tzinfo=timezone.utc)
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
    # Deadline passed
    en = ("🚨🇺🇸 <b>TRUMP ULTIMATUM — DEADLINE EXPIRED</b> 🇮🇷🚨\n\n"
          "⏰ <b>The 48-hour deadline has passed.</b>\n\n"
          f"📅 Expired: Monday, March 23 — 7:44 PM ET / 23:44 UTC\n"
          f"🕐 Expired {abs(int(total_secs))//3600}h {abs(int(total_secs))%3600//60}m ago\n\n"
          "⚡ Trump threatened to strike Iran's power plants if Hormuz was not reopened.\n"
          "📡 Monitoring for developments...")
    he = ("🚨🇺🇸 <b>האולטימטום של טראמפ — הדדליין עבר</b> 🇮🇷🚨\n\n"
          "⏰ <b>48 השעות הסתיימו.</b>\n\n"
          f"📅 פג: יום שני, 23 במרץ — 01:44 בלילה (שעון ישראל)\n"
          f"🕐 עבר לפני {abs(int(total_secs))//3600} שעות ו-{abs(int(total_secs))%3600//60} דקות\n\n"
          "⚡ טראמפ איים לתקוף תחנות כוח באיראן אם הורמוז לא ייפתח.\n"
          "📡 עוקבים אחר התפתחויות...")
else:
    hours = int(total_secs // 3600)
    mins = int((total_secs % 3600) // 60)
    elapsed_pct = min(100, int(((48*3600 - total_secs) / (48*3600)) * 100))
    bar = get_bar(elapsed_pct)
    
    # Urgency level
    if hours <= 6:
        urgency_en = "🔴 CRITICAL — Final hours"
        urgency_he = "🔴 קריטי — השעות האחרונות"
    elif hours <= 12:
        urgency_en = "🟠 HIGH — Less than 12 hours"
        urgency_he = "🟠 גבוה — פחות מ-12 שעות"
    elif hours <= 24:
        urgency_en = "🟡 ELEVATED — Less than 24 hours"
        urgency_he = "🟡 מוגבר — פחות מ-24 שעות"
    else:
        urgency_en = "⚪ ACTIVE — Countdown in progress"
        urgency_he = "⚪ פעיל — הספירה לאחור נמשכת"

    deadline_et = DEADLINE_UTC.astimezone(ET).strftime("%b %d, %I:%M %p ET")
    deadline_ist = DEADLINE_UTC.astimezone(IST).strftime("%d/%m %H:%M")

    en = (f"⏳🇺🇸 <b>TRUMP ULTIMATUM COUNTDOWN</b> 🇮🇷⏳\n\n"
          f"<b>🕐 {hours}h {mins}m REMAINING</b>\n"
          f"[{bar}] {elapsed_pct}%\n\n"
          f"📅 Deadline: {deadline_et} / 23:44 UTC\n"
          f"📊 Status: {urgency_en}\n\n"
          f"⚡ Threat: Strike Iran's power plants\n"
          f"🚢 Condition: Full reopening of Strait of Hormuz\n"
          f"🇮🇷 Iran: Vows retaliation on energy + desalination infrastructure")
    
    he = (f"⏳🇺🇸 <b>ספירה לאחור — האולטימטום של טראמפ</b> 🇮🇷⏳\n\n"
          f"<b>🕐 נותרו {hours} שעות ו-{mins} דקות</b>\n"
          f"[{bar}] {elapsed_pct}%\n\n"
          f"📅 דדליין: {deadline_ist} (שעון ישראל)\n"
          f"📊 סטטוס: {urgency_he}\n\n"
          f"⚡ איום: תקיפת תחנות כוח באיראן\n"
          f"🚢 תנאי: פתיחה מלאה של מצר הורמוז\n"
          f"🇮🇷 איראן: מאיימת בתגמול על תשתיות אנרגיה והתפלה")

ok_en = send(EN_CHAT, en)
ok_he = send(HE_CHAT, he)
print(f"[{datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')}] EN={ok_en} HE={ok_he} | {hours}h {mins}m remaining")
