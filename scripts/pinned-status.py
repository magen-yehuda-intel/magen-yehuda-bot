#!/usr/bin/env python3
"""
Pinned Live Status — Mobile-first intelligence dashboard.
Single Telegram message edited in-place every cycle.

Usage:
    python3 pinned-status.py <config.json> <state_dir> [--init]
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def load_config(config_path):
    with open(config_path) as f:
        return json.load(f)


def load_state(state_dir):
    """Load all state files for status display."""
    state = {}
    
    try:
        with open(os.path.join(state_dir, "firms-seen.json")) as f:
            d = json.load(f)
            state["fires_tracked"] = len(d.get("seen", {}))
    except:
        state["fires_tracked"] = 0
    
    try:
        with open(os.path.join(state_dir, "seismic-seen.json")) as f:
            d = json.load(f)
            state["quakes_tracked"] = len(d.get("seen", {}))
    except:
        state["quakes_tracked"] = 0
    
    try:
        with open(os.path.join(state_dir, "blackout-state.json")) as f:
            d = json.load(f)
            state["blackout_level"] = d.get("level", "NORMAL")
            state["blackout_score"] = d.get("score", 0)
    except:
        state["blackout_level"] = "NORMAL"
        state["blackout_score"] = 0
    
    try:
        with open(os.path.join(state_dir, "military-flights.json")) as f:
            d = json.load(f)
            state["mil_flights"] = d.get("total_tracked", 0)
    except:
        state["mil_flights"] = 0
    
    try:
        with open(os.path.join(state_dir, "strike-correlations.json")) as f:
            d = json.load(f)
            state["strike_corr"] = len(d.get("correlations", []))
    except:
        state["strike_corr"] = 0
    
    try:
        with open(os.path.join(state_dir, "watcher.pid")) as f:
            pid = int(f.read().strip())
            os.kill(pid, 0)
            state["watcher_running"] = True
            state["watcher_pid"] = pid
    except:
        state["watcher_running"] = False
        state["watcher_pid"] = None
    
    state["threat_level"] = "UNKNOWN"
    # Primary: read threat level file (most reliable)
    try:
        tl_path = os.path.join(state_dir, "watcher-threat-level.txt")
        if os.path.exists(tl_path):
            with open(tl_path) as f:
                lvl = f.read().strip().upper()
                if lvl in ("CRITICAL", "HIGH", "ELEVATED", "GREEN"):
                    state["threat_level"] = lvl
    except:
        pass
    # Fallback: parse watcher.log
    if state["threat_level"] == "UNKNOWN":
        try:
            log_path = os.path.join(state_dir, "watcher.log")
            if os.path.exists(log_path):
                with open(log_path, "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 8192))
                    tail = f.read().decode("utf-8", errors="replace")
                for line in reversed(tail.splitlines()):
                    for lvl in ["CRITICAL", "HIGH", "ELEVATED", "GREEN"]:
                        if f"→ {lvl}" in line or f"→ ⚫ {lvl}" in line or f"→ 🔴 {lvl}" in line or f"→ 🟠 {lvl}" in line or f"→ 🟢 {lvl}" in line:
                            state["threat_level"] = lvl
                            break
                        if f"Threat level: 🟢 {lvl}" in line or f"Threat level: {lvl}" in line:
                            state["threat_level"] = lvl
                            break
                    if state["threat_level"] != "UNKNOWN":
                        break
        except:
            pass
    
    state["last_siren"] = None
    try:
        log_path = os.path.join(state_dir, "watcher.log")
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 16384))
                tail = f.read().decode("utf-8", errors="replace")
            for line in reversed(tail.splitlines()):
                if "ACTIVE SIRENS" in line or "NEW SIRENS" in line:
                    if line.startswith("["):
                        ts = line[1:line.index("]")]
                        state["last_siren"] = ts
                    break
    except:
        pass
    
    state["intel_events_1h"] = 0
    try:
        log_path = os.path.join(state_dir, "intel-log.jsonl")
        if os.path.exists(log_path):
            cutoff = time.time() - 3600
            with open(log_path) as f:
                for line in f:
                    try:
                        ev = json.loads(line.strip())
                        if ev.get("logged_at", 0) >= cutoff:
                            state["intel_events_1h"] += 1
                    except:
                        continue
    except:
        pass
    
    try:
        with open(os.path.join(state_dir, "pinned-message-id.txt")) as f:
            state["pinned_msg_id"] = int(f.read().strip())
    except:
        state["pinned_msg_id"] = None
    
    return state


# ═══════════════════════════════════════════════════════════════
# THREAT LEVEL
# ═══════════════════════════════════════════════════════════════

THREAT_DATA = {
    "GREEN":    {"emoji": "🟢", "en": "NOMINAL",  "he": "שגרה",   "bar": "🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜"},
    "ELEVATED": {"emoji": "🟠", "en": "ELEVATED", "he": "כוננות מוגברת",  "bar": "🟧🟧🟧🟧⬜⬜⬜⬜⬜⬜"},
    "HIGH":     {"emoji": "🔴", "en": "HIGH",     "he": "גבוה",   "bar": "🟥🟥🟥🟥🟥🟥🟥⬜⬜⬜"},
    "CRITICAL": {"emoji": "⚫", "en": "CRITICAL",  "he": "קריטי",  "bar": "⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛"},
}

SCAN_FREQ = {
    "GREEN":    {"oref": "30s",  "osint": "5m",  "sat": "15m"},
    "ELEVATED": {"oref": "15s",  "osint": "2m",  "sat": "10m"},
    "HIGH":     {"oref": "10s",  "osint": "60s", "sat": "5m"},
    "CRITICAL": {"oref": "10s",  "osint": "30s", "sat": "3m"},
}

SCAN_FREQ_HE = {
    "GREEN":    {"oref": "30שׁ",  "osint": "5ד׳",  "sat": "15ד׳"},
    "ELEVATED": {"oref": "15שׁ",  "osint": "2ד׳",  "sat": "10ד׳"},
    "HIGH":     {"oref": "10שׁ",  "osint": "60שׁ", "sat": "5ד׳"},
    "CRITICAL": {"oref": "10שׁ",  "osint": "30שׁ", "sat": "3ד׳"},
}

BLACKOUT_ICONS = {
    "NORMAL": "🟢", "MINOR_ISSUES": "🟡", "DEGRADED": "🟠", "BLACKOUT": "🔴"
}


# ═══════════════════════════════════════════════════════════════
# ENGLISH STATUS
# ═══════════════════════════════════════════════════════════════

def generate_status_en(config, state):
    now = datetime.now(timezone.utc)
    t = state["threat_level"]
    td = THREAT_DATA.get(t, THREAT_DATA["GREEN"])
    w = state["watcher_running"]
    bl = BLACKOUT_ICONS.get(state["blackout_level"], "⚪")
    siren_str = state["last_siren"] or "None"

    return f"""🛡 <b>MAGEN YEHUDA</b>
<i>Real-Time Intelligence Monitor</i>

{td['emoji']} <b>THREAT: {td['en']}</b>
{td['bar']}

{'🟢' if w else '🔴'} Engine {'Online' if w else 'Offline'}  ·  📊 {state['intel_events_1h']} events/hr
🚨 Last Siren: {siren_str}

🇮🇷 <b>IRAN WATCH</b>
🔥 {state['fires_tracked']} fires  ·  🌍 {state['quakes_tracked']} quakes  ·  ✈️ {state['mil_flights']} mil. flights
{bl} Internet: {state['blackout_level']}  ·  🎯 {state['strike_corr']} correlations

☢️ Natanz · Fordow · Isfahan · Bushehr · Arak
🎯 Parchin · Shahrud · Bandar Abbas

📡 85+ sources  ·  4 satellites  ·  30+ cyber groups

🗺 <a href="https://magen-yehuda-intel.github.io/magen-yehuda-bot/">Live Dashboard</a>
⏱ <i>{now.strftime("%Y-%m-%d %H:%M:%S")} UTC</i>
🇮🇱 <b>Am Yisrael Chai</b> 🇮🇱"""


# ═══════════════════════════════════════════════════════════════
# HEBREW STATUS
# ═══════════════════════════════════════════════════════════════

def generate_status_he(config, state):
    now = datetime.now(timezone.utc)
    t = state["threat_level"]
    td = THREAT_DATA.get(t, THREAT_DATA["GREEN"])
    w = state["watcher_running"]
    bl = BLACKOUT_ICONS.get(state["blackout_level"], "⚪")
    siren_str = state["last_siren"] or "אין"

    R = "\u200F"
    return f"""{R}🛡 <b>מגן יהודה</b>
{R}<i>מערכת מודיעין בזמן אמת</i>

{R}{td['emoji']} <b>איום: {td['he']}</b>
{td['bar']}

{R}{'🟢' if w else '🔴'} מנוע {'פעיל' if w else 'כבוי'}  ·  📊 {state['intel_events_1h']} אירועים/שעה
{R}🚨 צפירה אחרונה: {siren_str}

{R}🇮🇷 <b>זירת איראן</b>
{R}🔥 {state['fires_tracked']} שריפות  ·  🌍 {state['quakes_tracked']} רעידות  ·  ✈️ {state['mil_flights']} טיסות צבאיות
{R}{bl} אינטרנט: {state['blackout_level']}  ·  🎯 {state['strike_corr']} קורלציות

{R}☢️ נתנז · פורדו · אספהאן · בושהר · אראק
{R}🎯 פרצ׳ין · שאהרוד · בנדר עבאס

{R}📡 85+ מקורות  ·  4 לוויינים  ·  30+ קבוצות סייבר

{R}🗺 <a href="https://magen-yehuda-intel.github.io/magen-yehuda-bot/">לוח מבצעים</a>
{R}⏱ <i>{now.strftime("%Y-%m-%d %H:%M:%S")} UTC</i>
{R}🇮🇱 <b>עם ישראל חי</b> 🇮🇱"""


# ═══════════════════════════════════════════════════════════════
# TELEGRAM API
# ═══════════════════════════════════════════════════════════════

def send_message(bot_token, chat_id, text):
    data = json.dumps({
        "chat_id": chat_id, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=data, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if result.get("ok"):
        return result["result"]["message_id"]
    raise RuntimeError(f"Send failed: {result}")


def edit_message(bot_token, chat_id, message_id, text):
    data = json.dumps({
        "chat_id": chat_id, "message_id": message_id,
        "text": text, "parse_mode": "HTML", "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/editMessageText",
        data=data, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        return result.get("ok", False)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "message is not modified" in body:
            return True
        print(f"Edit failed: {body}", file=sys.stderr)
        return False


def pin_message(bot_token, chat_id, message_id):
    data = json.dumps({
        "chat_id": chat_id, "message_id": message_id,
        "disable_notification": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/pinChatMessage",
        data=data, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("ok", False)
    except:
        return False


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 pinned-status.py <config.json> <state_dir> [--init]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    init_mode = "--init" in sys.argv
    
    config = load_config(config_path)
    state = load_state(state_dir)
    bot_token = config["telegram_bot_token"]
    
    outputs = config.get("outputs", [])
    if not outputs:
        outputs = [{"id": "default", "chat_id": config["telegram_chat_id"],
                     "content": ["all"], "language": "en"}]
    
    for output in outputs:
        content_filter = output.get("content", ["all"])
        if "all" not in content_filter and "pinned_status" not in content_filter:
            continue
        
        chat_id = output.get("chat_id", "")
        if not chat_id:
            continue
        
        out_id = output.get("id", "default")
        lang = output.get("language", "en")
        
        if lang == "he":
            status_text = generate_status_he(config, state)
        else:
            status_text = generate_status_en(config, state)
        
        pinned_file = os.path.join(state_dir, f"pinned-message-id-{out_id}.txt")
        if out_id in ("default", "main"):
            legacy = os.path.join(state_dir, "pinned-message-id.txt")
            if not os.path.isfile(pinned_file) and os.path.isfile(legacy):
                pinned_file = legacy
        
        existing_msg_id = None
        try:
            with open(pinned_file) as f:
                existing_msg_id = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            pass
        
        if init_mode or existing_msg_id is None:
            print(f"Creating pinned status [{out_id}] ({chat_id})...", file=sys.stderr)
            msg_id = send_message(bot_token, chat_id, status_text)
            
            save_file = os.path.join(state_dir, f"pinned-message-id-{out_id}.txt")
            with open(save_file, "w") as f:
                f.write(str(msg_id))
            if out_id in ("default", "main"):
                with open(os.path.join(state_dir, "pinned-message-id.txt"), "w") as f:
                    f.write(str(msg_id))
            
            pinned = pin_message(bot_token, chat_id, msg_id)
            print(f"✅ [{out_id}] #{msg_id} {'pinned' if pinned else 'pin failed'}", file=sys.stderr)
            print(msg_id)
        else:
            ok = edit_message(bot_token, chat_id, existing_msg_id, status_text)
            if not ok:
                print(f"⚠️ [{out_id}] Edit failed, recreating...", file=sys.stderr)
                msg_id = send_message(bot_token, chat_id, status_text)
                save_file = os.path.join(state_dir, f"pinned-message-id-{out_id}.txt")
                with open(save_file, "w") as f:
                    f.write(str(msg_id))
                if out_id in ("default", "main"):
                    with open(os.path.join(state_dir, "pinned-message-id.txt"), "w") as f:
                        f.write(str(msg_id))
                pin_message(bot_token, chat_id, msg_id)
                print(f"✅ [{out_id}] #{msg_id} recreated+pinned", file=sys.stderr)
            print(existing_msg_id)


if __name__ == "__main__":
    main()
