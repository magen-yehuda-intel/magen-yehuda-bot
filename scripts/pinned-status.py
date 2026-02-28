#!/usr/bin/env python3
"""
Pinned Live Status — Single Telegram message that gets edited in-place.
Shows real-time operational status. Gets pinned once, then updated every cycle.

Usage:
    python3 pinned-status.py <config.json> <state_dir> [--init]
    
    --init: Create the pinned message for the first time
    (without --init): Update the existing pinned message
"""

import sys
import os
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def load_config(config_path):
    with open(config_path) as f:
        return json.load(f)


def load_state(state_dir):
    """Load all state files for status display."""
    state = {}
    
    # Fires
    try:
        with open(os.path.join(state_dir, "firms-seen.json")) as f:
            d = json.load(f)
            state["fires_tracked"] = len(d.get("seen", {}))
            state["fires_last_scan"] = d.get("last_scan", "")
    except:
        state["fires_tracked"] = 0
        state["fires_last_scan"] = ""
    
    # Seismic
    try:
        with open(os.path.join(state_dir, "seismic-seen.json")) as f:
            d = json.load(f)
            state["quakes_tracked"] = len(d.get("seen", {}))
            state["quakes_last_scan"] = d.get("last_scan", "")
    except:
        state["quakes_tracked"] = 0
        state["quakes_last_scan"] = ""
    
    # OSINT seen counts
    for src in ["telegram", "twitter", "rss"]:
        try:
            with open(os.path.join(state_dir, f"osint-{src}-seen.json")) as f:
                d = json.load(f)
                state[f"osint_{src}_count"] = len(d) if isinstance(d, dict) else 0
        except:
            state[f"osint_{src}_count"] = 0
    
    # Watcher PID
    try:
        with open(os.path.join(state_dir, "watcher.pid")) as f:
            pid = int(f.read().strip())
            # Check if running
            os.kill(pid, 0)
            state["watcher_running"] = True
            state["watcher_pid"] = pid
    except:
        state["watcher_running"] = False
        state["watcher_pid"] = None
    
    # Threat level from watcher log
    state["threat_level"] = "UNKNOWN"
    try:
        log_path = os.path.join(state_dir, "watcher.log")
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                # Read last 8KB
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
    
    # Last siren from watcher log
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
                if "ACTIVE SIRENS" in line or "🚨" in line:
                    # Extract timestamp
                    if line.startswith("["):
                        ts = line[1:line.index("]")]
                        state["last_siren"] = ts
                    break
    except:
        pass
    
    # Intel log event count (last hour)
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
    
    # Pinned message ID
    try:
        with open(os.path.join(state_dir, "pinned-message-id.txt")) as f:
            state["pinned_msg_id"] = int(f.read().strip())
    except:
        state["pinned_msg_id"] = None
    
    return state


def threat_bar(level):
    """Generate a visual threat level bar."""
    levels = {
        "GREEN":    ("🟢", "█░░░░░░░░░", "ALL CLEAR"),
        "ELEVATED": ("🟠", "████░░░░░░", "ELEVATED"),
        "HIGH":     ("🔴", "███████░░░", "HIGH ALERT"),
        "CRITICAL": ("⚫", "██████████", "CRITICAL"),
    }
    emoji, bar, label = levels.get(level, ("⚪", "░░░░░░░░░░", "UNKNOWN"))
    return emoji, bar, label


def generate_status_message(config, state):
    """Generate the pinned status message HTML."""
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%H:%M UTC")
    now_full = now.strftime("%Y-%m-%d %H:%M UTC")
    
    threat = state["threat_level"]
    emoji, bar, label = threat_bar(threat)
    
    # Watcher status
    if state["watcher_running"]:
        watcher_icon = "🟢"
        watcher_text = "ONLINE"
    else:
        watcher_icon = "🔴"
        watcher_text = "OFFLINE"
    
    # Build the message
    lines = []
    
    # Header
    lines.append("╔══════════════════════════════╗")
    lines.append("║  🛡️  <b>MAGEN YEHUDA</b>  🛡️  ║")
    lines.append("║   <i>Live Intelligence Status</i>   ║")
    lines.append("╚══════════════════════════════╝")
    lines.append("")
    
    # Threat Level - Big and prominent
    lines.append(f"  {emoji} <b>THREAT LEVEL: {label}</b>")
    lines.append(f"  <code>[{bar}]</code>")
    lines.append("")
    
    # System Status
    lines.append("┌─────── 📡 SYSTEM ────────┐")
    lines.append(f"│ {watcher_icon} Watcher: <b>{watcher_text}</b>")
    lines.append(f"│ 🕐 Updated: <b>{now_str}</b>")
    if state["last_siren"]:
        lines.append(f"│ 🚨 Last Siren: <b>{state['last_siren']}</b>")
    else:
        lines.append(f"│ 🚨 Last Siren: <b>None recently</b>")
    lines.append(f"│ 📊 Events (1h): <b>{state['intel_events_1h']}</b>")
    lines.append("└──────────────────────────┘")
    lines.append("")
    
    # Monitoring Grid
    lines.append("┌────── 🎯 MONITORING ─────┐")
    lines.append(f"│ 🚀 Oref Sirens     {'✅ LIVE' if state['watcher_running'] else '❌ OFF'}")
    lines.append(f"│ 📢 Telegram OSINT  ✅ 10 channels")
    lines.append(f"│ 🐦 X/Twitter       ✅ 11 accounts")
    lines.append(f"│ 📰 RSS Feeds       ✅ 4 feeds")
    lines.append(f"│ 📊 Polymarket      ✅ LIVE")
    lines.append(f"│ 🔥 NASA FIRMS      ✅ 4 satellites")
    lines.append(f"│ 🌍 USGS Seismic    ✅ M2.5+")
    lines.append(f"│ 🗺️ Intel Map       ✅ AUTO")
    lines.append("└──────────────────────────┘")
    lines.append("")
    
    # Iran Tracking
    lines.append("┌───── 🇮🇷 IRAN WATCH ─────┐")
    lines.append(f"│ 🔥 Fires:  <b>{state['fires_tracked']}</b> tracked")
    lines.append(f"│ 🌍 Quakes: <b>{state['quakes_tracked']}</b> tracked")
    lines.append("│")
    lines.append("│ ☢️ <b>Nuclear Sites:</b>")
    lines.append("│  Natanz · Fordow · Isfahan")
    lines.append("│  Bushehr · Arak")
    lines.append("│ 🎯 <b>Military:</b>")
    lines.append("│  Parchin · Shahrud")
    lines.append("│  Bandar Abbas")
    lines.append("│ 🏛️ Tehran  🛢️ Kharg Island")
    lines.append("└──────────────────────────┘")
    lines.append("")
    
    # Scan Frequencies
    freq = {
        "GREEN":    {"oref": "30s", "osint": "5m", "sat": "15m"},
        "ELEVATED": {"oref": "15s", "osint": "2m", "sat": "10m"},
        "HIGH":     {"oref": "10s", "osint": "60s", "sat": "5m"},
        "CRITICAL": {"oref": "10s", "osint": "30s", "sat": "3m"},
    }
    f = freq.get(threat, freq["GREEN"])
    
    lines.append("┌──── ⚡ SCAN FREQUENCY ────┐")
    lines.append(f"│ 🚀 Sirens:    every <b>{f['oref']}</b>")
    lines.append(f"│ 📡 OSINT:     every <b>{f['osint']}</b>")
    lines.append(f"│ 🛰️ Satellite: every <b>{f['sat']}</b>")
    lines.append("└──────────────────────────┘")
    lines.append("")
    
    # Footer
    lines.append(f"<i>🤖 MagenYehudaBot — 24/7 Automated</i>")
    lines.append(f"<i>Last refresh: {now_full}</i>")
    lines.append(f"<i>🇮🇱 עם ישראל חי 🇮🇱</i>")
    
    return "\n".join(lines)


def send_message(bot_token, chat_id, text):
    """Send a new message and return message_id."""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if result.get("ok"):
        return result["result"]["message_id"]
    raise RuntimeError(f"Send failed: {result}")


def edit_message(bot_token, chat_id, message_id, text):
    """Edit an existing message."""
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/editMessageText",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        return result.get("ok", False)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "message is not modified" in body:
            return True  # No change needed
        print(f"Edit failed: {body}", file=sys.stderr)
        return False


def pin_message(bot_token, chat_id, message_id):
    """Pin a message in the channel."""
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "disable_notification": True,
    }
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/pinChatMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"Pin failed: {e}", file=sys.stderr)
        return False


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
    chat_id = config["telegram_chat_id"]
    
    status_text = generate_status_message(config, state)
    
    if init_mode or state["pinned_msg_id"] is None:
        # Create new message
        print("Creating new pinned status message...", file=sys.stderr)
        msg_id = send_message(bot_token, chat_id, status_text)
        
        # Save message ID
        with open(os.path.join(state_dir, "pinned-message-id.txt"), "w") as f:
            f.write(str(msg_id))
        
        # Pin it
        pinned = pin_message(bot_token, chat_id, msg_id)
        print(f"✅ Message {msg_id} created and {'pinned' if pinned else 'pin failed'}", file=sys.stderr)
        print(msg_id)
    else:
        # Edit existing message
        msg_id = state["pinned_msg_id"]
        ok = edit_message(bot_token, chat_id, msg_id, status_text)
        if ok:
            print(f"✅ Pinned message {msg_id} updated", file=sys.stderr)
        else:
            # Message might have been deleted — recreate
            print("⚠️ Edit failed, recreating...", file=sys.stderr)
            msg_id = send_message(bot_token, chat_id, status_text)
            with open(os.path.join(state_dir, "pinned-message-id.txt"), "w") as f:
                f.write(str(msg_id))
            pin_message(bot_token, chat_id, msg_id)
            print(f"✅ New message {msg_id} created and pinned", file=sys.stderr)
        print(msg_id)


if __name__ == "__main__":
    main()
