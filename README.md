# 🛡️ Iran-Israel Attack Alert Monitor

Real-time multi-source intelligence aggregation for Iran/Israel/US military escalation. Adaptive threat-level system, 25+ OSINT sources, war-room formatted reports, and instant Telegram alerts.

![Threat Levels](https://img.shields.io/badge/threat_levels-GREEN_%7C_ELEVATED_%7C_HIGH_%7C_CRITICAL-brightgreen)
![Sources](https://img.shields.io/badge/sources-25%2B_channels-blue)
![Delivery](https://img.shields.io/badge/delivery-Telegram-26A5E4)

## What It Does

Monitors 25+ intelligence sources across 6 categories, auto-adjusts polling frequency based on threat level, and pushes instant alerts to a Telegram channel:

| Source | Channels | Speed | Auth Required |
|--------|----------|-------|---------------|
| 🚨 **Pikud HaOref** | 1 (siren API) | 10-30s poll | None (Israeli IP needed) |
| 📢 **Telegram OSINT** | 9 public channels | 30s-5min | None |
| 🐦 **X/Twitter OSINT** | 11 accounts | 30s-5min | None |
| 📰 **RSS Feeds** | 4 news outlets | 30s-5min | None |
| 🌍 **USGS Seismic** | Iran region | 30s-5min | None |
| 📊 **Polymarket** | Dynamic discovery | 60s-5min | None |
| 🛢️ **Oil & Commodities** | 2h SITREP | ~5min | None |
| ✈️ **Military Aviation** | 2h SITREP | Live | None |

### Adaptive Threat-Level System

Polling frequency **automatically scales with danger**:

| Level | Trigger | OSINT Polling | Cooldown |
|-------|---------|---------------|----------|
| 🟢 GREEN | No sirens >30min | Every 5 min | — |
| 🟡 ELEVATED | Sirens <30min ago | Every 2 min | 30min→GREEN |
| 🔴 HIGH | Active sirens NOW | Every 60s | 10min→ELEV |
| ⚫ CRITICAL | Major cities under fire | Every 30s | 10min→HIGH |

Escalation is instant. Deescalation is gradual.

## Quick Start

### 1. Prerequisites

- **bash**, **curl**, **python3** (3.9+ with `zoneinfo`)
- A **Telegram bot** ([create one via @BotFather](https://t.me/BotFather))
- A **Telegram channel** (add your bot as admin)

### 2. Configure

```bash
cp config.example.json config.json
```

Edit `config.json` with your Telegram bot token and channel:

```json
{
  "timezone": "Asia/Jerusalem",
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "@your_channel_handle",
  "telegram_channel_name": "Your Channel Name"
}
```

### 3. NASA FIRMS API Key (free, 30 seconds)

The satellite fire detection needs a NASA FIRMS MAP_KEY. It's free — no verification required.

1. Go to [mail.tm](https://mail.tm) or any disposable email service
2. Copy the temp email address
3. Go to [FIRMS API registration](https://firms.modaps.eosdis.nasa.gov/api/area/) → click **Get MAP_KEY**
4. Enter the temp email — key arrives in seconds
5. Save it:
   ```bash
   mkdir -p secrets
   echo "YOUR_KEY" > secrets/firms-map-key.txt
   ```

The key is permanent with no rate limits on the area CSV endpoint.

See `config.example.json` for all available settings including OSINT sources, keywords, polling intervals, and seismic monitoring.

### 3. Run

```bash
# One-time check (stdout)
bash ctl.sh check

# Post to Telegram
bash ctl.sh post

# Start real-time watcher daemon (recommended)
bash ctl.sh start

# See what's running
bash ctl.sh status
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Real-Time Watcher (daemon)                 │
│                                                       │
│  🚨 Oref sirens         10-30s (threat-adaptive)     │
│  📡 OSINT Scanner        30s-5min (threat-adaptive)   │
│    ├─ 📢 Telegram channels (9 channels)               │
│    ├─ 🐦 Twitter syndication (11 accounts)            │
│    ├─ 📰 RSS feeds (4 outlets)                        │
│    └─ 🌍 USGS seismic (Iran region)                   │
│  📊 Polymarket           60s-5min (threat-adaptive)   │
│                                                       │
│  → Instant push on siren / OSINT match / spike       │
│  → Auto-escalate/deescalate threat level             │
└───────────────────┬───────────────────────────────────┘
                    │
┌───────────────────┴───────────────────────────────────┐
│           Scheduled SITREP (cron, every 2h)           │
│  Full 6-source check → war-room formatted report     │
└───────────────────┬───────────────────────────────────┘
                    │
             Telegram Channel
```

## OSINT Sources

### Telegram Channels (scraped via `t.me/s/` public web preview)
| Channel | Description |
|---------|-------------|
| `warmonitors` | War Monitors — fastest English breaking news |
| `intelslava` | Intel Slava Z — military OSINT |
| `liveuamap` | Liveuamap — mapped conflict updates |
| `AbuAliExpress` | Abu Ali Express — Hebrew OSINT (top Israeli source) |
| `flash_news_il` | Flash News IL — Hebrew breaking |
| `idfonline` | IDF Official |
| `iranintl_en` | Iran International — English |
| `BBCPersian` | BBC Persian |
| `kann_news` | Kan News (Israeli public broadcasting) |

### Twitter Accounts (via syndication API, no auth needed)
`@PenPizzaReport` · `@Conflict_Radar` · `@Worldsource24` · `@sentdefender` · `@beholdisrael` · `@Osint613` · `@Osinttechnical` · `@IsraelRadar_` · `@Intel_Sky` · `@ELINTNews` · `@IsraelWarRoom`

### RSS Feeds
Times of Israel · Jerusalem Post · Al Jazeera · TASS

### Seismic Monitoring
USGS earthquake data for Iran region (M3.5+) — shallow high-magnitude events or "explosion" type events are flagged as suspicious (potential nuclear test indicator).

All sources are keyword-filtered using 52 terms in Hebrew + English.

## `ctl.sh` Commands

| Command | Description |
|---------|-------------|
| `start` | Start real-time watcher daemon |
| `stop` | Stop watcher |
| `status` | Show watcher state, cron, last threat level |
| `check` | One-time full check (JSON to stdout) |
| `post` | Full check → format → post to Telegram |
| `log [N]` | Show last N lines of watcher log |
| `install-launchd` | Auto-start watcher on boot (macOS) |
| `teardown` | 🛑 Kill everything: watcher, cron, launchd, state |

## Pikud HaOref — Israeli IP Required

The Oref siren API is **geo-restricted to Israeli IPs**. The script uses a fallback chain:

1. **Custom proxy** — `secrets/proxy-override.txt` (any HTTPS/SOCKS5 proxy with Israeli IP)
2. **NordVPN** — `secrets/nordvpn-auth.txt` routes through NordVPN Israel (`il66.nordvpn.com:89`)
3. **Direct** — Falls back to direct connection
4. **Graceful failure** — All other 24+ sources still work globally

```bash
mkdir -p secrets

# Option A: NordVPN service credentials
echo "USERNAME
PASSWORD" > secrets/nordvpn-auth.txt

# Option B: Any proxy
echo "https://user:pass@host:port" > secrets/proxy-override.txt

# Option C: SSH tunnel to Israeli VPS
ssh -D 1080 user@your-server
echo "socks5://localhost:1080" > secrets/proxy-override.txt
```

No Israeli IP? No problem — you lose siren data but keep everything else.

## Cron Setup

```bash
# OpenClaw
openclaw cron add \
  --name "Iran-Israel Alert Monitor" \
  --every "2h" \
  --session isolated \
  --timeout-seconds 120 \
  --message "cd /path/to/iran-israel-alerts && bash scripts/post-telegram.sh --force"

# Standard crontab
0 */2 * * * cd /path/to/iran-israel-alerts && bash scripts/post-telegram.sh --force
```

## File Structure

```
iran-israel-alerts/
├── README.md                    # You're reading it
├── SKILL.md                     # OpenClaw skill metadata
├── config.example.json          # Template — copy to config.json
├── config.json                  # Your config (gitignored)
├── ctl.sh                       # Master control script
├── .gitignore
├── scripts/
│   ├── check-alerts.sh          # Full 6-source SITREP → JSON
│   ├── format-telegram.py       # JSON → war-room HTML
│   ├── post-telegram.sh         # check → format → Telegram
│   ├── realtime-watcher.sh      # Adaptive threat-level daemon
│   └── scan-osint.py            # Unified OSINT scanner
├── references/
│   └── sources.md               # Full OSINT source list with tiers
├── secrets/                     # gitignored
│   ├── nordvpn-auth.txt         # NordVPN creds (optional)
│   └── proxy-override.txt       # Custom proxy (optional)
└── state/                       # gitignored, auto-created
```

## Safety

⚠️ This system **never says "all clear"**. Only Pikud HaOref (Israel Home Front Command) can authorize leaving shelter. When sirens stop, the system shows "NO NEW ALERTS BROADCASTING" with a warning to follow official instructions.

## License

MIT

## Acknowledgments

- [Pikud HaOref](https://www.oref.org.il/) — Israel Home Front Command
- [Polymarket](https://polymarket.com/) — Prediction markets
- [OpenSky Network](https://opensky-network.org/) — ADS-B flight tracking
- [USGS](https://earthquake.usgs.gov/) — Seismic monitoring
- OSINT community on X/Twitter and Telegram
