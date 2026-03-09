#!/usr/bin/env python3
"""Format alert check output as a war-room style Telegram HTML message."""
import sys
import html
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

raw = sys.stdin.read()

try:
    data = json.loads(raw)
except:
    print(html.escape(raw[:4000]))
    sys.exit(0)

now = data.get("timestamp_fmt", datetime.now().strftime("%Y-%m-%d %H:%M %Z"))
score = data.get("threat_score", 0)
level = data.get("threat_level", "LOW")
tz_str = data.get("timezone", "Asia/Jerusalem")
channel_handle = data.get("telegram_chat_id", "")
channel_name = data.get("telegram_channel_name", "Alert Monitor")

# Threat level visual
if score >= 40:
    level_bar = "🔴🔴🔴🔴🔴"
    level_label = "CRITICAL"
    level_icon = "🚨"
elif score >= 20:
    level_bar = "🟠🟠🟠🟠⚫"
    level_label = "HIGH"
    level_icon = "⚠️"
elif score >= 8:
    level_bar = "🟡🟡🟡⚫⚫"
    level_label = "ELEVATED"
    level_icon = "🟡"
else:
    level_bar = "🟢🟢⚫⚫⚫"
    level_label = "LOW"
    level_icon = "✅"

# Build a situation summary line from signals and data
summary_parts = []
oref = data.get("oref", {})
if oref.get("status") == "active":
    summary_parts.append("🚨 Active sirens across Israel")
elif oref.get("status") == "clear":
    summary_parts.append("No active sirens")
else:
    summary_parts.append("Siren data unavailable")

# Count today's headlines
headlines = data.get("headlines", [])
today_count = sum(1 for h in headlines if "Yest" not in h.get("time", "") and "/" not in h.get("time", ""))
if today_count > 5:
    summary_parts.append(f"{today_count} breaking updates today")
elif today_count > 0:
    summary_parts.append(f"{today_count} update{'s' if today_count > 1 else ''} today")

# Polymarket top signal
markets = data.get("polymarket", [])
for m in markets[:1]:
    q = m.get("q", "")
    yes = m.get("yes", 0)
    if yes >= 0.5:
        # Shorten the question
        q_short = q.replace("Will ", "").replace("?", "").strip()
        if len(q_short) > 50:
            q_short = q_short[:47] + "..."
        summary_parts.append(f"Markets: {yes:.0%} {q_short}")

summary = " · ".join(summary_parts)

msg = []

# ═══ HEADER ═══
msg.append("")
msg.append(f"{level_icon} <b>{html.escape(channel_name.upper())} — SITREP</b>")
msg.append("")
msg.append(f"📅 {now}")
msg.append(f"{level_bar} <b>{level_label}</b>")
msg.append(f"<i>{html.escape(summary)}</i>")
msg.append("")

# ═══ SIRENS ═══
if oref.get("status") == "active":
    msg.append("🚨🚨🚨 <b>ACTIVE SIRENS</b> 🚨🚨🚨")
    for alert in oref.get("alerts", []):
        loc = html.escape(alert.get("location", "?"))
        atype = html.escape(alert.get("type", "?"))
        total = alert.get("total_areas", 0)
        total_str = f" ({total} areas)" if total > 5 else ""
        msg.append(f"  🔴 <b>{atype}</b>{total_str}")
        msg.append(f"     📍 {loc}")
        desc = alert.get("desc", "")
        if desc:
            desc_clean = html.escape(desc)
            if len(desc_clean) > 200:
                desc_clean = desc_clean[:197] + "..."
            msg.append(f"     <i>{desc_clean}</i>")
    msg.append("")

# ═══ HEADLINES ═══
if headlines:
    msg.append(f"📰 <b>LATEST</b>")
    msg.append("")
    for h in headlines[:6]:
        ts = h.get("time", "")
        source = h.get("source", "")
        title = h.get("title", "")
        url = h.get("url", "")

        time_str = f"<code>{ts}</code>" if ts else ""
        src = f"<b>{html.escape(source)}</b>" if source else ""

        if url:
            msg.append(f" {time_str} ▸ {src}: <a href=\"{html.escape(url)}\">{html.escape(title)}</a>")
        else:
            msg.append(f" {time_str} ▸ {src}: {html.escape(title)}")
    msg.append("")

# ═══ MARKETS ═══
if markets:
    msg.append("📊 <b>PREDICTION MARKETS</b>")
    msg.append("")
    for m in markets[:4]:
        q = m.get("q", "?")
        yes = m.get("yes", 0)
        delta = m.get("delta")

        filled = round(yes * 10)
        bar = "█" * filled + "░" * (10 - filled)

        if yes >= 0.7:
            emoji = "🔴"
        elif yes >= 0.4:
            emoji = "🟠"
        elif yes >= 0.2:
            emoji = "🟡"
        else:
            emoji = "⚪"

        delta_str = ""
        if delta is not None:
            arrow = "📈" if delta > 0 else "📉"
            delta_str = f" {arrow}{delta:+.0f}pp"

        msg.append(f"  {emoji} <code>{bar}</code> <b>{yes:.0%}</b>{delta_str}")
        msg.append(f"     {html.escape(q)}")
    msg.append("")

# ═══ COMMODITIES ═══
commodities = data.get("commodities", [])
if commodities:
    parts = []
    for c in commodities:
        name = c.get("name", "?")
        price = c.get("price", 0)
        change = c.get("change") or 0
        short = name.replace(" Crude Oil", "").replace(" (Henry Hub)", "")
        sign = "+" if change > 0 else ""
        parts.append(f"<b>{html.escape(short)}</b> ${price:,.2f} ({sign}{change:.1f}%)")
    msg.append("🛢️ " + " · ".join(parts))
    msg.append("")

# ═══ FOOTER ═══
msg.append("")
if channel_handle:
    msg.append(f"📡 <b>{html.escape(channel_handle)}</b> | {html.escape(channel_name)}")
else:
    msg.append(f"📡 <b>{html.escape(channel_name)}</b>")

print("\n".join(msg))
