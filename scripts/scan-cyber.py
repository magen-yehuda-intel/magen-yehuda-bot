#!/usr/bin/env python3
"""
scan-cyber.py — Iran-Israel cyber warfare & hacktivist monitor

Monitors Telegram channels of known hacktivist groups (pro-Iran & pro-Israel),
cyber threat intel Twitter accounts, and dark web leak aggregator feeds to detect:
  - New attack claims (DDoS, defacement, data leak, ICS/SCADA)
  - Data breach announcements targeting Israel or Iran
  - Hacktivist mobilization signals (calls to arms, coordination)
  - Infrastructure targeting (water, power, gas, telecom)

Sources:
  1. Hacktivist Telegram channels (t.me/s/ public preview scraping)
  2. Cyber threat intel Twitter accounts (syndication API)
  3. Dark web / breach aggregator RSS feeds

Usage:
    python3 scan-cyber.py <config.json> <state_dir>

Output: JSON array of cyber alerts to stdout
"""

import json
import re
import sys
import os
import time
import html as h
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


# ═══════════════════════════════════════════════════════════
# HACKTIVIST GROUP REGISTRY
# ═══════════════════════════════════════════════════════════

# Pro-Iran / Pro-Palestinian hacktivist groups
PRO_IRAN_CHANNELS = {
    # Group name → list of known Telegram handles (channels get banned/recreated)
    "Handala Hack": {
        "handles": ["HandalaHack", "HandalaHack2"],
        "affiliation": "Iran/IRGC-linked",
        "targets": "Israel govt, defense, healthcare, officials",
        "ttps": ["data_leak", "wiper", "telegram_hijack", "espionage"],
        "threat_level": "HIGH",
    },
    "CyberAv3ngers": {
        "handles": ["CyberAveng3rs"],
        "affiliation": "Iran/IRGC",
        "targets": "Critical infrastructure, ICS/SCADA, water systems",
        "ttps": ["ics_attack", "defacement", "plc_exploit"],
        "threat_level": "CRITICAL",
    },
    "Moses Staff": {
        "handles": ["MosesStaff", "moses_staff"],
        "affiliation": "Iran/IRGC",
        "targets": "Israel govt, finance, energy",
        "ttps": ["data_leak", "encryption", "extortion"],
        "threat_level": "HIGH",
    },
    "Cyber Toufan": {
        "handles": ["totoufan", "cybertoufan"],
        "affiliation": "Iran-linked",
        "targets": "Israel defense contractors, tech companies",
        "ttps": ["data_leak", "data_destruction", "hack_and_leak"],
        "threat_level": "HIGH",
    },
    "DieNet": {
        "handles": ["DieNet_v2", "DieNetOfficial"],
        "affiliation": "Pro-Iran/anti-Israel",
        "targets": "Emergency systems, broadcasting, govt",
        "ttps": ["ddos", "defacement", "psyop"],
        "threat_level": "MEDIUM",
    },
    "Dark Storm Team": {
        "handles": ["Darkstormbackup2", "darkstormchatt"],
        "affiliation": "Pro-Palestine/Pro-Russia",
        "targets": "NATO, Israel, US infrastructure",
        "ttps": ["ddos", "ddos_for_hire"],
        "threat_level": "MEDIUM",
    },
    "RipperSec": {
        "handles": ["RipperSec"],
        "affiliation": "Pro-Palestine (Malaysia)",
        "targets": "Israel defense, govt websites",
        "ttps": ["ddos", "defacement", "scada_intrusion"],
        "threat_level": "MEDIUM",
    },
    "Cyber Fattah": {
        "handles": ["CyberFattah"],
        "affiliation": "Pro-Iran",
        "targets": "Saudi, Israel, regional",
        "ttps": ["data_leak", "ddos", "reconnaissance"],
        "threat_level": "MEDIUM",
    },
    "Arabian Ghosts": {
        "handles": ["ArabianGhosts"],
        "affiliation": "Pro-Iran",
        "targets": "Israel",
        "ttps": ["ddos", "defacement"],
        "threat_level": "MEDIUM",
    },
    "Fatimion Cyber Team": {
        "handles": ["FatimionCyber"],
        "affiliation": "Iran proxy",
        "targets": "Israel, US",
        "ttps": ["ddos", "defacement"],
        "threat_level": "LOW",
    },
    "Cyber Islamic Resistance": {
        "handles": ["CyberIslamicResistance"],
        "affiliation": "Iran proxy/Hezbollah-linked",
        "targets": "Israel military, ICS",
        "ttps": ["surveillance", "data_leak", "ics_recon"],
        "threat_level": "HIGH",
    },
}

# Pro-Israel hacktivist groups
PRO_ISRAEL_CHANNELS = {
    "Predatory Sparrow": {
        "handles": ["GonjeshkeDarande", "PredatorySparrow"],
        "affiliation": "Israel-linked",
        "targets": "Iran infrastructure, finance, fuel, steel",
        "ttps": ["ics_attack", "data_destruction", "financial_disruption"],
        "threat_level": "HIGH",
    },
    "Israeli Elite Force": {
        "handles": ["IsraeliEliteForce"],
        "affiliation": "Pro-Israel",
        "targets": "Iran financial systems, military platforms",
        "ttps": ["data_leak", "financial_disruption"],
        "threat_level": "MEDIUM",
    },
    "WeRedEvils": {
        "handles": ["WeRedEvils"],
        "affiliation": "Pro-Israel",
        "targets": "Iran, Hezbollah-linked targets",
        "ttps": ["ddos", "defacement", "data_leak"],
        "threat_level": "LOW",
    },
}

# Cyber threat intelligence aggregator channels
CTI_CHANNELS = {
    "FalconFeedsio": {
        "handles": ["FalconFeedsio"],
        "type": "cti_aggregator",
        "description": "Real-time cyber threat intel, dark web monitoring, breach alerts",
    },
    "DarkWebInformer": {
        "handles": ["DarkWebInformer"],
        "type": "cti_aggregator",
        "description": "Dark web breach and leak monitoring",
    },
    "cyaboreh": {
        "handles": ["cyaboreh"],
        "type": "cti_aggregator",
        "description": "Cyber threat intel focused on Middle East",
    },
    "vaboreh": {
        "handles": ["vaboreh"],
        "type": "cti_aggregator",
        "description": "Daily hacktivist claim tracker",
    },
    "Ransomware_gang_report": {
        "handles": ["Ransomware_gang_report"],
        "type": "cti_aggregator",
        "description": "Ransomware and extortion group activity tracker",
    },
}


# ═══════════════════════════════════════════════════════════
# CYBER KEYWORDS — attack indicators in hacktivist posts
# ═══════════════════════════════════════════════════════════

CYBER_KEYWORDS_EN = [
    # Attack types
    "ddos", "defacement", "defaced", "data leak", "data breach", "leaked",
    "hacked", "compromised", "ransomware", "wiper", "malware",
    "exploited", "vulnerability", "zero-day", "0day",
    # Targets
    "israel", "israeli", "iran", "iranian", "zionist",
    "idf", "mossad", "shin bet", "aman",
    "irgc", "sepah", "basij",
    "scada", "ics", "plc", "unitronics", "industrial control",
    "water system", "power grid", "gas station", "pipeline",
    "hospital", "healthcare", "bank", "financial",
    "telecom", "internet provider", "isp",
    # Infrastructure
    "critical infrastructure", "power plant", "nuclear",
    "natanz", "fordow", "isfahan", "bushehr",
    # Action words
    "operation", "target", "attack", "campaign", "breach",
    "exfiltrated", "destroyed", "encrypted", "locked",
    "proof", "evidence", "database", "credentials",
    "source code", "classified", "confidential", "secret",
]

CYBER_KEYWORDS_HE = [
    "פריצה", "דליפה", "נתונים", "סייבר", "התקפה", "האקר",
    "כופרה", "נוזקה", "פגיעות", "שירות מנע",
    "מערכות שליטה", "תשתית קריטית", "בנק", "בית חולים",
    "תקשורת", "חשמל", "מים", "גז",
]

ALL_CYBER_KEYWORDS = CYBER_KEYWORDS_EN + CYBER_KEYWORDS_HE


# ═══════════════════════════════════════════════════════════
# ATTACK CLASSIFICATION
# ═══════════════════════════════════════════════════════════

ATTACK_PATTERNS = {
    "ics_scada": {
        "keywords": ["scada", "ics", "plc", "unitronics", "industrial control",
                      "water system", "power grid", "power plant", "gas station",
                      "pipeline", "critical infrastructure"],
        "severity": "CRITICAL",
        "label_en": "🏭 ICS/SCADA Attack",
        "label_he": "🏭 תקיפת מערכות שליטה תעשייתיות",
    },
    "data_breach": {
        "keywords": ["data leak", "data breach", "leaked", "exfiltrated",
                      "database", "credentials", "source code", "classified",
                      "confidential", "stolen data", "דליפה", "נתונים"],
        "severity": "HIGH",
        "label_en": "📂 Data Breach / Leak",
        "label_he": "📂 דליפת מידע",
    },
    "ransomware_wiper": {
        "keywords": ["ransomware", "wiper", "encrypted", "locked", "destroyed",
                      "כופרה", "נוזקה"],
        "severity": "HIGH",
        "label_en": "💀 Ransomware / Wiper",
        "label_he": "💀 כופרה / נוזקה הרסנית",
    },
    "ddos": {
        "keywords": ["ddos", "denial of service", "שירות מנע", "down", "offline",
                      "overloaded"],
        "severity": "MEDIUM",
        "label_en": "🌐 DDoS Attack",
        "label_he": "🌐 מתקפת מניעת שירות",
    },
    "defacement": {
        "keywords": ["defacement", "defaced", "website hacked"],
        "severity": "LOW",
        "label_en": "🎨 Website Defacement",
        "label_he": "🎨 השחתת אתר",
    },
    "espionage": {
        "keywords": ["espionage", "surveillance", "spyware", "backdoor",
                      "apt", "advanced persistent", "ריגול"],
        "severity": "HIGH",
        "label_en": "🕵️ Cyber Espionage",
        "label_he": "🕵️ ריגול סייבר",
    },
}


def classify_attack(text: str) -> dict:
    """Classify the attack type based on text content."""
    text_lower = text.lower()
    best = None
    best_score = 0

    for attack_type, info in ATTACK_PATTERNS.items():
        score = sum(1 for kw in info["keywords"] if kw in text_lower)
        if score > best_score:
            best_score = score
            best = {"type": attack_type, **info}

    if best and best_score > 0:
        return best

    return {
        "type": "general",
        "severity": "MEDIUM",
        "label_en": "⚡ Cyber Attack",
        "label_he": "⚡ תקיפת סייבר",
    }


def determine_target_side(text: str, group_affiliation: str = "") -> str:
    """Determine who is being targeted: 'israel', 'iran', 'other'."""
    text_lower = text.lower()

    israel_signals = sum(1 for kw in [
        "israel", "israeli", "zionist", "idf", "mossad", "shin bet",
        "tel aviv", "jerusalem", "haifa", "ישראל", "צה\"ל", "מוסד",
    ] if kw in text_lower)

    iran_signals = sum(1 for kw in [
        "iran", "iranian", "irgc", "sepah", "tehran", "isfahan",
        "natanz", "fordow", "bushehr", "איראן",
    ] if kw in text_lower)

    if israel_signals > iran_signals:
        return "israel"
    elif iran_signals > israel_signals:
        return "iran"

    # Fall back to group affiliation
    if "pro-iran" in group_affiliation.lower() or "irgc" in group_affiliation.lower():
        return "israel"  # Pro-Iran groups target Israel
    elif "pro-israel" in group_affiliation.lower() or "israel-linked" in group_affiliation.lower():
        return "iran"  # Pro-Israel groups target Iran

    return "other"


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════

def load_state(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def save_state(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_via_proxy(url, proxy_url, timeout=15):
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "--proxy", proxy_url,
             "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
             url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except Exception:
        return None


def build_proxy_url(config):
    skill_dir = config.get("_skill_dir", "")
    override_path = os.path.join(skill_dir, "secrets", "proxy-override.txt")
    nord_path = os.path.join(skill_dir, "secrets", "nordvpn-auth.txt")
    if os.path.isfile(override_path):
        with open(override_path) as f:
            return f.read().strip()
    elif os.path.isfile(nord_path):
        with open(nord_path) as f:
            lines = f.read().strip().split("\n")
        if len(lines) >= 2:
            user, passwd = lines[0].strip(), lines[1].strip()
            return f"https://{user}:{passwd}@il66.nordvpn.com:89"
    return None


def matches_cyber_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALL_CYBER_KEYWORDS)


# ═══════════════════════════════════════════════════════════
# TELEGRAM HACKTIVIST CHANNEL SCANNER
# ═══════════════════════════════════════════════════════════

def scan_hacktivist_telegram(config, state_dir, proxy_url=None):
    """Scan all known hacktivist group Telegram channels for new posts."""
    seen_file = os.path.join(state_dir, "cyber-telegram-seen.json")
    seen = load_state(seen_file)
    alerts = []

    # Merge all channel groups
    all_groups = {}
    all_groups.update(PRO_IRAN_CHANNELS)
    all_groups.update(PRO_ISRAEL_CHANNELS)
    all_groups.update(CTI_CHANNELS)

    # Also include user-configured cyber channels
    extra_channels = config.get("cyber_telegram_channels", [])

    for group_name, info in all_groups.items():
        handles = info.get("handles", [])
        affiliation = info.get("affiliation", info.get("type", ""))
        threat_level = info.get("threat_level", "MEDIUM")

        for handle in handles:
            try:
                url = f"https://t.me/s/{handle}"
                if proxy_url:
                    raw = fetch_via_proxy(url, proxy_url)
                else:
                    raw = fetch(url, timeout=8)
                if not raw:
                    continue

                msg_blocks = re.findall(
                    r'data-post="[^/]+/(\d+)".*?'
                    r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>.*?'
                    r'<time[^>]*datetime="([^"]*)"',
                    raw, re.DOTALL
                )

                prev_ids = set(seen.get(handle, []))
                current_ids = []

                for msg_id, text_html, timestamp in msg_blocks:
                    current_ids.append(msg_id)
                    if msg_id in prev_ids:
                        continue

                    text = re.sub(r"<br\s*/?>", "\n", text_html)
                    text = re.sub(r"<[^>]+>", "", text)
                    text = h.unescape(text).strip()

                    if not text or not matches_cyber_keywords(text):
                        continue

                    # Classify the attack
                    attack = classify_attack(text)
                    target_side = determine_target_side(text, affiliation)

                    display = text[:300].replace("\n", " ")
                    if len(text) > 300:
                        display += "..."

                    alerts.append({
                        "source": "cyber_telegram",
                        "channel": handle,
                        "group_name": group_name,
                        "affiliation": affiliation,
                        "group_threat_level": threat_level,
                        "msg_id": msg_id,
                        "text": display,
                        "time": timestamp,
                        "link": f"https://t.me/{handle}/{msg_id}",
                        "attack_type": attack["type"],
                        "attack_label_en": attack["label_en"],
                        "attack_label_he": attack["label_he"],
                        "severity": attack["severity"],
                        "target_side": target_side,
                    })

                seen[handle] = current_ids[:50]
                time.sleep(0.5)  # slower for hacktivist channels (more scrutiny)

            except Exception as e:
                print(f"  Cyber TG scan error ({handle}): {e}", file=sys.stderr)
                continue

    # Extra user-configured channels
    for handle in extra_channels:
        try:
            url = f"https://t.me/s/{handle}"
            if proxy_url:
                raw = fetch_via_proxy(url, proxy_url)
            else:
                raw = fetch(url, timeout=8)
            if not raw:
                continue

            msg_blocks = re.findall(
                r'data-post="[^/]+/(\d+)".*?'
                r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>.*?'
                r'<time[^>]*datetime="([^"]*)"',
                raw, re.DOTALL
            )

            prev_ids = set(seen.get(handle, []))
            current_ids = []

            for msg_id, text_html, timestamp in msg_blocks:
                current_ids.append(msg_id)
                if msg_id in prev_ids:
                    continue

                text = re.sub(r"<br\s*/?>", "\n", text_html)
                text = re.sub(r"<[^>]+>", "", text)
                text = h.unescape(text).strip()

                if not text or not matches_cyber_keywords(text):
                    continue

                attack = classify_attack(text)
                target_side = determine_target_side(text)
                display = text[:300].replace("\n", " ")
                if len(text) > 300:
                    display += "..."

                alerts.append({
                    "source": "cyber_telegram",
                    "channel": handle,
                    "group_name": handle,
                    "affiliation": "unknown",
                    "group_threat_level": "MEDIUM",
                    "msg_id": msg_id,
                    "text": display,
                    "time": timestamp,
                    "link": f"https://t.me/{handle}/{msg_id}",
                    "attack_type": attack["type"],
                    "attack_label_en": attack["label_en"],
                    "attack_label_he": attack["label_he"],
                    "severity": attack["severity"],
                    "target_side": target_side,
                })

            seen[handle] = current_ids[:50]
            time.sleep(0.3)
        except Exception:
            continue

    save_state(seen_file, seen)
    return alerts


# ═══════════════════════════════════════════════════════════
# TWITTER CTI ACCOUNTS
# ═══════════════════════════════════════════════════════════

CTI_TWITTER_ACCOUNTS = [
    "FalconFeedsio",     # Real-time cyber threat intel + dark web monitoring
    "CyberKnow20",       # Hacktivist tracking, group activity mapping
    "DarkWebInformer",   # Dark web breach alerts
    "HackManac",         # Ransomware and breach news
    "MonThreat",         # Threat intelligence aggregator
    "cybaboreh",         # Middle East cyber threat focus
    "BrettCallow",       # Ransomware analyst
    "vaboreh",           # Hacktivist claims tracker
]


def scan_cyber_twitter(config, state_dir, proxy_url=None):
    """Scan cyber threat intel Twitter accounts for Iran/Israel cyber news."""
    seen_file = os.path.join(state_dir, "cyber-twitter-seen.json")
    seen = load_state(seen_file)
    alerts = []

    # Merge default CTI accounts with user-configured ones
    accounts = list(CTI_TWITTER_ACCOUNTS)
    accounts.extend(config.get("cyber_twitter_accounts", []))
    accounts = list(dict.fromkeys(accounts))  # dedupe preserving order

    for acct in accounts:
        try:
            url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{acct}"
            if proxy_url:
                raw = fetch_via_proxy(url, proxy_url)
            else:
                raw = fetch(url, timeout=10)
            if not raw:
                continue

            m = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                raw
            )
            if not m:
                continue

            data = json.loads(m.group(1))
            entries = (data.get("props", {}).get("pageProps", {})
                       .get("timeline", {}).get("entries", []))

            prev_ids = set(seen.get(acct, []))
            current_ids = []

            for e in entries:
                try:
                    tweet = e["content"]["tweet"]
                    rt = tweet.get("retweeted_status")
                    src = rt if rt else tweet
                    tid = src.get("id_str", "")
                    if not tid:
                        continue
                    current_ids.append(tid)

                    if tid in prev_ids:
                        continue

                    text = src.get("full_text", "")
                    if not matches_cyber_keywords(text):
                        continue

                    # Must also mention Iran or Israel context
                    text_lower = text.lower()
                    has_context = any(kw in text_lower for kw in [
                        "iran", "israel", "iranian", "israeli",
                        "irgc", "idf", "mossad", "tehran", "tel aviv",
                        "hezbollah", "hamas", "palestinian",
                        "handala", "cyberav3ngers", "moses staff",
                        "cyber toufan", "predatory sparrow", "gonjeshke",
                        "dienet", "rippersec", "dark storm",
                    ])
                    if not has_context:
                        continue

                    screen = src["user"]["screen_name"]
                    display = text[:300].replace("\n", " ")
                    if len(text) > 300:
                        display += "..."

                    attack = classify_attack(text)
                    target_side = determine_target_side(text)

                    alerts.append({
                        "source": "cyber_twitter",
                        "channel": f"@{acct}",
                        "account": acct,
                        "tweet_id": tid,
                        "is_rt": bool(rt),
                        "text": display,
                        "time": src.get("created_at", ""),
                        "link": f"https://x.com/{screen}/status/{tid}",
                        "attack_type": attack["type"],
                        "attack_label_en": attack["label_en"],
                        "attack_label_he": attack["label_he"],
                        "severity": attack["severity"],
                        "target_side": target_side,
                    })
                except (KeyError, TypeError):
                    continue

            seen[acct] = current_ids[:200]
            time.sleep(0.3)

        except Exception as e:
            print(f"  Cyber Twitter scan error ({acct}): {e}", file=sys.stderr)
            continue

    save_state(seen_file, seen)
    return alerts


# ═══════════════════════════════════════════════════════════
# DARK WEB / BREACH RSS FEEDS
# ═══════════════════════════════════════════════════════════

DEFAULT_CYBER_RSS = [
    {
        "name": "Darkfeed Ransomware",
        "url": "https://darkfeed.io/rss.xml",
        "type": "ransomware_tracker",
    },
    {
        "name": "CISA Advisories",
        "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "type": "govt_advisory",
    },
    {
        "name": "The Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "type": "cyber_news",
    },
    {
        "name": "BleepingComputer",
        "url": "https://www.bleepingcomputer.com/feed/",
        "type": "cyber_news",
    },
]


def scan_cyber_rss(config, state_dir):
    """Scan cyber news and dark web RSS feeds for Iran/Israel content."""
    seen_file = os.path.join(state_dir, "cyber-rss-seen.json")
    seen = load_state(seen_file)
    alerts = []

    feeds = list(DEFAULT_CYBER_RSS)
    feeds.extend(config.get("cyber_rss_feeds", []))

    for feed in feeds:
        name = feed.get("name", "?")
        url = feed.get("url", "")
        feed_type = feed.get("type", "cyber_news")
        if not url:
            continue

        try:
            raw = fetch(url, timeout=10)

            items = re.findall(
                r"<item>(.*?)</item>|<entry>(.*?)</entry>",
                raw, re.DOTALL
            )

            prev_links = set(seen.get(name, []))
            current_links = []

            for item_match in items[:20]:
                item_xml = item_match[0] or item_match[1]

                title_m = re.search(r"<title[^>]*>(.*?)</title>", item_xml, re.DOTALL)
                title = re.sub(r"<!\[CDATA\[|\]\]>", "", title_m.group(1)).strip() if title_m else ""
                title = h.unescape(re.sub(r"<[^>]+>", "", title))

                link_m = re.search(r'<link[^>]*>([^<]+)</link>|<link[^>]*href="([^"]+)"', item_xml)
                link = ""
                if link_m:
                    link = (link_m.group(1) or link_m.group(2) or "").strip()

                desc_m = re.search(r"<description[^>]*>(.*?)</description>", item_xml, re.DOTALL)
                desc = ""
                if desc_m:
                    desc = re.sub(r"<!\[CDATA\[|\]\]>", "", desc_m.group(1))
                    desc = h.unescape(re.sub(r"<[^>]+>", "", desc)).strip()

                date_m = re.search(
                    r"<pubDate>(.*?)</pubDate>|<published>(.*?)</published>|<updated>(.*?)</updated>",
                    item_xml
                )
                pub_date = ""
                if date_m:
                    pub_date = (date_m.group(1) or date_m.group(2) or date_m.group(3) or "").strip()

                key = link or title
                current_links.append(key)

                if key in prev_links:
                    continue

                # Check for Iran/Israel relevance
                combined = f"{title} {desc}".lower()
                has_context = any(kw in combined for kw in [
                    "iran", "israel", "iranian", "israeli",
                    "irgc", "idf", "mossad", "tehran",
                    "hezbollah", "hamas",
                    "handala", "cyberav3ngers", "moses staff",
                    "cyber toufan", "predatory sparrow",
                    "middle east", "persian",
                ])
                if not has_context:
                    continue

                attack = classify_attack(f"{title} {desc}")
                target_side = determine_target_side(f"{title} {desc}")

                alerts.append({
                    "source": "cyber_rss",
                    "channel": name,
                    "feed_type": feed_type,
                    "text": title[:250],
                    "description": desc[:200] if desc else "",
                    "time": pub_date,
                    "link": link,
                    "attack_type": attack["type"],
                    "attack_label_en": attack["label_en"],
                    "attack_label_he": attack["label_he"],
                    "severity": attack["severity"],
                    "target_side": target_side,
                })

            seen[name] = current_links[:30]
            time.sleep(0.2)

        except Exception as e:
            print(f"  Cyber RSS scan error ({name}): {e}", file=sys.stderr)
            continue

    save_state(seen_file, seen)
    return alerts


# ═══════════════════════════════════════════════════════════
# ALERT FORMATTING
# ═══════════════════════════════════════════════════════════

SIDE_EMOJI = {
    "israel": "🇮🇱",
    "iran": "🇮🇷",
    "other": "🌐",
}

SIDE_LABEL_EN = {
    "israel": "targeting Israel",
    "iran": "targeting Iran",
    "other": "",
}

SIDE_LABEL_HE = {
    "israel": "נגד ישראל",
    "iran": "נגד איראן",
    "other": "",
}


def format_cyber_alert_en(alert: dict) -> str:
    """Format a single cyber alert in English."""
    attack_label = alert.get("attack_label_en", "⚡ Cyber Attack")
    group = h.escape(alert.get("group_name", alert.get("channel", "?")))
    affiliation = alert.get("affiliation", "")
    text = h.escape(alert["text"][:200])
    link = alert.get("link", "")
    side = alert.get("target_side", "other")
    side_emoji = SIDE_EMOJI.get(side, "")
    side_label = SIDE_LABEL_EN.get(side, "")
    link_tag = f' <a href="{link}">[↗]</a>' if link else ""

    header = f"{attack_label}"
    if side_label:
        header += f" {side_emoji} {side_label}"

    source_line = f"<b>{group}</b>"
    if affiliation and affiliation not in ("unknown", ""):
        source_line += f" ({h.escape(affiliation)})"

    return f"{header}\n{source_line}: {text}{link_tag}"


def format_cyber_alert_he(alert: dict) -> str:
    """Format a single cyber alert in Hebrew."""
    attack_label = alert.get("attack_label_he", "⚡ תקיפת סייבר")
    group = h.escape(alert.get("group_name", alert.get("channel", "?")))
    text = h.escape(alert["text"][:200])
    link = alert.get("link", "")
    side = alert.get("target_side", "other")
    side_emoji = SIDE_EMOJI.get(side, "")
    side_label = SIDE_LABEL_HE.get(side, "")
    link_tag = f' <a href="{link}">[↗]</a>' if link else ""

    header = f"\u200F{attack_label}"
    if side_label:
        header += f" {side_emoji} {side_label}"

    return f"{header}\n\u200F<b>{group}</b>: {text}{link_tag}"


def format_cyber_summary(alerts: list) -> dict:
    """Format all cyber alerts into bilingual summary text."""
    if not alerts:
        return {"text_he": "", "text_en": "", "count": 0}

    # Sort by severity
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: sev_order.get(a.get("severity", "MEDIUM"), 2))

    lines_en = ["🛡️ <b>CYBER INTELLIGENCE</b>", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
    lines_he = ["\u200F🛡️ <b>מודיעין סייבר</b>", "\u200F━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]

    # Stats header
    targeting_israel = sum(1 for a in alerts if a.get("target_side") == "israel")
    targeting_iran = sum(1 for a in alerts if a.get("target_side") == "iran")
    stats_en = f"📊 {len(alerts)} events"
    stats_he = f"\u200F📊 {len(alerts)} אירועים"
    if targeting_israel:
        stats_en += f" | 🇮🇱 {targeting_israel} vs Israel"
        stats_he += f" | 🇮🇱 {targeting_israel} נגד ישראל"
    if targeting_iran:
        stats_en += f" | 🇮🇷 {targeting_iran} vs Iran"
        stats_he += f" | 🇮🇷 {targeting_iran} נגד איראן"
    lines_en.append(stats_en)
    lines_he.append(stats_he)
    lines_en.append("")
    lines_he.append("")

    # Individual alerts (cap at 8)
    for a in alerts[:8]:
        lines_en.append(format_cyber_alert_en(a))
        lines_he.append(format_cyber_alert_he(a))
        lines_en.append("")
        lines_he.append("")

    if len(alerts) > 8:
        lines_en.append(f"... +{len(alerts) - 8} more cyber events")
        lines_he.append(f"\u200F... +{len(alerts) - 8} אירועי סייבר נוספים")

    return {
        "text_en": "\n".join(lines_en),
        "text_he": "\n".join(lines_he),
        "count": len(alerts),
    }


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("Usage: scan-cyber.py <config.json> <state_dir>", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    state_dir = sys.argv[2]

    with open(config_path) as f:
        config = json.load(f)
    config["_skill_dir"] = os.path.dirname(os.path.abspath(config_path))

    os.makedirs(state_dir, exist_ok=True)

    proxy_url = build_proxy_url(config)
    if proxy_url:
        print("Using proxy for cyber Telegram/Twitter scanning", file=sys.stderr)

    all_alerts = []

    # 1. Hacktivist Telegram channels
    try:
        tg_alerts = scan_hacktivist_telegram(config, state_dir, proxy_url=proxy_url)
        all_alerts.extend(tg_alerts)
        print(f"  Cyber TG: {len(tg_alerts)} alerts from hacktivist channels", file=sys.stderr)
    except Exception as e:
        print(f"  Cyber TG error: {e}", file=sys.stderr)

    # 2. CTI Twitter accounts
    try:
        tw_alerts = scan_cyber_twitter(config, state_dir, proxy_url=proxy_url)
        all_alerts.extend(tw_alerts)
        print(f"  Cyber Twitter: {len(tw_alerts)} alerts from CTI accounts", file=sys.stderr)
    except Exception as e:
        print(f"  Cyber Twitter error: {e}", file=sys.stderr)

    # 3. Cyber RSS feeds
    try:
        rss_alerts = scan_cyber_rss(config, state_dir)
        all_alerts.extend(rss_alerts)
        print(f"  Cyber RSS: {len(rss_alerts)} alerts from feeds", file=sys.stderr)
    except Exception as e:
        print(f"  Cyber RSS error: {e}", file=sys.stderr)

    # Sort by severity
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_alerts.sort(key=lambda a: sev_order.get(a.get("severity", "MEDIUM"), 2))

    # Output raw alerts
    json.dump(all_alerts, sys.stdout, ensure_ascii=False, indent=None)


if __name__ == "__main__":
    main()
