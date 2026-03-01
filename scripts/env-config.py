#!/usr/bin/env python3
"""Generate config.json from environment variables if it doesn't exist.

Used in Docker containers to bootstrap config from env vars.
If config.json already exists (bind-mounted), does nothing.

Environment variables:
  TELEGRAM_BOT_TOKEN    — Required. Telegram bot token
  TELEGRAM_CHAT_ID      — Main channel chat ID (e.g., @magenyehudaupdates)
  TELEGRAM_CHAT_ID_HE   — Hebrew channel chat ID (optional, e.g., @opssheagathaariupdates)
  FIRMS_MAP_KEY          — NASA FIRMS API key (optional, for fire detection)
  PUSH_API_KEY           — API push endpoint key (optional)
  NORD_USER              — NordVPN username (optional, for IL proxy)
  NORD_PASS              — NordVPN password (optional, for IL proxy)
  TIMEZONE               — Display timezone (default: Asia/Jerusalem)
  API_URL                — Cloud API URL (optional, for push endpoints)
  AZURE_TABLE_ENDPOINT   — Azure Table endpoint (optional, for DB backend)
  AZURE_TABLE_NAME       — Azure Table name (default: intelevents)
"""

import json, os, sys

SKILL_DIR = os.environ.get("SKILL_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(SKILL_DIR, "config.json")

def main():
    if os.path.exists(CONFIG_FILE):
        print(f"Config exists: {CONFIG_FILE} — skipping env bootstrap")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN env var required (or mount config.json)", file=sys.stderr)
        sys.exit(1)

    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    chat_id_he = os.environ.get("TELEGRAM_CHAT_ID_HE", "")
    tz = os.environ.get("TIMEZONE", "Asia/Jerusalem")

    config = {
        "telegram_bot_token": token,
        "telegram_chat_id": chat_id,
        "telegram_channel_name": "Alert Monitor",
        "timezone": tz,
        "oref_poll_interval": 30,
        "osint_keywords": [
            "iran", "israel", "idf", "irgc", "hamas", "hezbollah", "houthi",
            "missile", "strike", "attack", "siren", "intercept", "drone", "ballistic",
            "tehran", "isfahan", "haifa", "tel aviv", "centcom"
        ],
        "telegram_osint_channels": [
            "warmonitors", "intelslava", "liveuamap", "AbuAliExpress",
            "flash_news_il", "idfonline", "idfofficial", "IDFarabic",
            "iranintl_en", "BBCPersian", "kann_news", "aharonyediot",
            "beholdisraelchannel"
        ],
        "twitter_accounts": [
            "@IsraelRadar_", "@sentdefender", "@YWNReporter", "@manaborahma",
            "@IntelDoge", "@clabordeoffical", "@MiddleEastSpect",
            "@JoeTruzman", "@LTCPeterLerner", "@IDF", "@IDFSpokesperson",
            "@ELINTNews", "@idaborovich1"
        ],
        "twitter_keywords": ["iran", "israel", "idf", "irgc", "hezbollah", "hamas", "missile"],
        "twitter_poll_interval": 60,
        "polymarket_poll_interval": 300,
        "polymarket_spike_threshold": 5,
        "rss_feeds": [
            {"name": "Times of Israel", "url": "https://www.timesofisrael.com/feed/"},
            {"name": "Jerusalem Post", "url": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx"},
            {"name": "Al Jazeera ME", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
            {"name": "TASS", "url": "https://tass.com/rss/v2.xml"},
            {"name": "Ynet", "url": "https://www.ynet.co.il/Integration/StoryRss1854.xml"},
            {"name": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews"},
            {"name": "AP Top News", "url": "https://rsshub.app/apnews/topics/apf-topnews"},
            {"name": "Maariv", "url": "https://www.maariv.co.il/Rss/RssFeedsMivzakiChadashot"},
            {"name": "Walla", "url": "https://rss.walla.co.il/feed/1"},
            {"name": "Channel 13", "url": "https://13tv.co.il/feed/"}
        ],
        "usgs_seismic": {"min_magnitude": 3.5, "radius_km": 1500, "center_lat": 32.0, "center_lon": 53.0},
        "outputs": [
            {
                "type": "telegram",
                "chat_id": chat_id,
                "language": "en",
                "timezone": "America/New_York",
                "content": ["all"],
                "min_severity": "LOW",
                "images": "all"
            }
        ]
    }

    # Add Hebrew channel if configured
    if chat_id_he:
        config["outputs"].append({
            "type": "telegram",
            "chat_id": chat_id_he,
            "language": "he",
            "timezone": "Asia/Jerusalem",
            "content": ["all"],
            "content_exclude": ["summary_en"],
            "min_severity": "LOW",
            "images": "high_only"
        })

    # Optional: API push config
    api_url = os.environ.get("API_URL", "")
    push_key = os.environ.get("PUSH_API_KEY", "")
    if api_url:
        config["dashboard"] = {"api_url": api_url, "api_key": push_key}
    if push_key:
        config["push_api_key"] = push_key

    # Write NordVPN creds if provided
    nord_user = os.environ.get("NORD_USER", "")
    nord_pass = os.environ.get("NORD_PASS", "")
    if nord_user and nord_pass:
        secrets_dir = os.path.join(SKILL_DIR, "secrets")
        os.makedirs(secrets_dir, exist_ok=True)
        with open(os.path.join(secrets_dir, "nordvpn-auth.txt"), "w") as f:
            f.write(f"{nord_user}\n{nord_pass}\n")

    # Write FIRMS key if provided
    firms_key = os.environ.get("FIRMS_MAP_KEY", "")
    if firms_key:
        secrets_dir = os.path.join(SKILL_DIR, "secrets")
        os.makedirs(secrets_dir, exist_ok=True)
        with open(os.path.join(secrets_dir, "firms-map-key.txt"), "w") as f:
            f.write(firms_key)

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"Generated config from env vars: {CONFIG_FILE}")


if __name__ == "__main__":
    main()
