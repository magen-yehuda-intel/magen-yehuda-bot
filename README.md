# 🛡️ Magen Yehuda Bot — Iran-Israel Real-Time Intelligence Monitor

Multi-source intelligence aggregation for Iran/Israel/US military escalation. Adaptive threat-level system, 30+ OSINT sources, satellite fire detection, seismic monitoring, flight tracking, internet blackout detection, strike correlation, wire service integration, bilingual alerts, and instant Telegram delivery.

![Threat Levels](https://img.shields.io/badge/threat_levels-GREEN_%7C_ELEVATED_%7C_HIGH_%7C_CRITICAL-brightgreen)
![Sources](https://img.shields.io/badge/sources-30%2B_channels-blue)
![Delivery](https://img.shields.io/badge/delivery-Telegram-26A5E4)
![Languages](https://img.shields.io/badge/languages-English_%2B_Hebrew-ff69b4)

## What It Does

Monitors 40+ intelligence sources across 12 categories, auto-adjusts polling frequency based on threat level, auto-detects breaking news from credible sources, and pushes instant bilingual alerts to Telegram channels:

| Source | Channels | Speed | Auth Required |
|--------|----------|-------|---------------|
| 🚨 **Pikud HaOref** (sirens) | Israeli siren API | 10-30s | None (Israeli IP) |
| 📢 **Telegram OSINT** | 10 public channels | 30s-5min | None |
| 🐦 **X/Twitter OSINT** | 11 accounts | 30s-5min | None |
| 📰 **RSS Feeds** | 7 news outlets | 30s-5min | None |
| 🌍 **USGS Seismic** | Iran region (M2.5+) | 30s-5min | None |
| 📊 **Polymarket** | Prediction markets | 60s-5min | None |
| 🔥 **NASA FIRMS** | 4 satellites | 3-15min | Free MAP_KEY |
| 🌐 **Internet Blackout** | IODA + direct probes | 5-30min | None |
| ✈️ **Military Flights** | ADS-B (OpenSky) | 5-30min | None |
| ✈️ **Flight Radar** | FR24 air traffic | Hourly map | None |
| 🎯 **Strike Correlation** | Fire + seismic fusion | After each scan | None |
| 🛡️ **Cyber Warfare** | ~25 hacktivist TG channels | 5-30min | None |
| 🛡️ **Cyber CTI Twitter** | 8 CTI accounts | 5-30min | None |
| 🛡️ **Dark Web / Breach RSS** | 4+ feeds | 5-30min | None |

### Key Features

- **Adaptive threat system** — Polling scales from 5min (GREEN) to 30s (CRITICAL) based on siren activity
- **Breaking news detection** — Auto-identifies critical events from credible sources (Reuters, AP, IDF, etc.)
- **Multi-channel dispatch** — Route alerts to English and/or Hebrew channels with language-specific formatting
- **Satellite fire detection** — 4 NASA satellites, proximity to 23 known nuclear/military/oil sites
- **Internet blackout early warning** — Iran historically cuts internet before military operations
- **Strike correlation engine** — Automatic fire + seismic coincidence detection (50km/30min window)
- **US/Israeli military flight tracking** — 50+ aircraft type→role mappings, filtered to relevant assets only
- **Live pinned status dashboard** — Single message edited every 60s with full system state
- **Bilingual hourly reports** — Intel map + flight map + Hebrew summary + English summary + 24h time-lapse GIF
- **Wire service integration** — Reuters and AP News via Google News RSS proxy (direct feeds are Cloudflared)
- **Cyber warfare monitor** — 30+ hacktivist groups (Handala, CyberAv3ngers, Predatory Sparrow, etc.), CTI Twitter, dark web feeds
- **Attack classification** — Auto-categorizes ICS/SCADA, data breach, ransomware, DDoS, espionage with severity scoring

## Quick Start

### 1. Prerequisites

- **Python 3.9+** with `Pillow` (`pip3 install Pillow`)
- **bash**, **curl**, **jq**
- A **Telegram bot** ([create via @BotFather](https://t.me/BotFather))
- A **Telegram channel** (add your bot as admin)

### 2. Configure

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "@your_channel",
  "outputs": [
    {
      "id": "main",
      "chat_id": "@your_english_channel",
      "language": "en",
      "content": ["all"],
      "images": "all"
    },
    {
      "id": "hebrew",
      "chat_id": "@your_hebrew_channel",
      "language": "he",
      "content": ["all"],
      "images": "high_only"
    }
  ]
}
```

### 3. NASA FIRMS API Key (free, 30 seconds)

Fire detection needs a free NASA FIRMS MAP_KEY — no verification required.

1. Go to [mail.tm](https://mail.tm) or any temp email service
2. Copy the temp email address
3. Go to [FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/area/) → **Get MAP_KEY**
4. Enter the email — key arrives instantly
5. Save it:
   ```bash
   mkdir -p secrets
   echo "YOUR_KEY" > secrets/firms-map-key.txt
   ```

The key is permanent with no rate limits.

### 4. Run

```bash
# One-time check (stdout)
bash ctl.sh check

# Start real-time watcher daemon
bash ctl.sh start

# Full dashboard
bash ctl.sh dashboard

# Stop
bash ctl.sh stop
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Real-Time Watcher (daemon)                    │
│                                                            │
│  🚨 Oref sirens        every 10-30s (threat-adaptive)     │
│  📡 OSINT scanner       every 30s-5min                     │
│    ├─ 📢 10 Telegram channels (t.me/s/ web preview)       │
│    ├─ 🐦 11 Twitter accounts (syndication API)             │
│    ├─ 📰 7 RSS feeds (TOI, JPost, AJ, TASS, Ynet,        │
│    │      Reuters, AP News via Google News proxy)          │
│    └─ 🌍 USGS seismic (Iran region, M3.5+)                │
│  📊 Polymarket          every 60s-5min                     │
│  🔥 NASA FIRMS fires    every 3-15min                      │
│  🌐 Iran internet       every 5-30min (blackout detect)   │
│  ✈️ Military flights     every 5-30min (ADS-B)            │
│  🎯 Strike correlation  after fire/seismic scans          │
│  📌 Pinned status       edited every 60s (live dashboard) │
│                                                            │
│  → dispatch.py routes to EN + HE channels                  │
│  → Breaking news auto-detection (credible sources)         │
│  → Auto-escalate/deescalate threat level                   │
└──────────────────┬─────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────┐
│              Hourly Reports (cron)                          │
│  🗺️ Intel map + ✈️ Flight map + 🇮🇱 Hebrew + 🇺🇸 English   │
│  🎬 24h time-lapse GIF                                     │
└──────────────────┬─────────────────────────────────────────┘
                   │
          dispatch.py (multi-output router)
           ├─ 🇺🇸 English Channel
           └─ 🇮🇱 Hebrew Channel
```

## Multi-Channel Dispatch

The `dispatch.py` module routes every alert to multiple Telegram channels based on configurable rules:

```json
{
  "outputs": [
    {
      "id": "main",
      "chat_id": "@english_channel",
      "language": "en",
      "content": ["all"],
      "min_severity": "LOW",
      "images": "all"
    },
    {
      "id": "hebrew",
      "chat_id": "@hebrew_channel",
      "language": "he",
      "content": ["siren", "breaking_news", "osint", "fires"],
      "min_severity": "LOW",
      "images": "high_only"
    }
  ]
}
```

### Output Options

| Field | Values | Description |
|-------|--------|-------------|
| `language` | `"en"`, `"he"`, `"both"` | Which language text to send |
| `content` | `["all"]` or specific types | Event type filter |
| `min_severity` | `"LOW"` to `"CRITICAL"` | Minimum severity to send |
| `images` | `"all"`, `"high_only"`, `"critical_only"`, `"none"` | Image inclusion policy |

### Event Types

`siren`, `siren_standdown`, `siren_clear`, `breaking_news`, `threat_change`, `osint`, `fires`, `seismic`, `strike_correlation`, `blackout`, `military_flights`, `polymarket`, `map`, `flight_map`, `summary_he`, `summary_en`, `timelapse`, `pinned_status`

### Usage from Python

```python
from dispatch import Dispatcher
d = Dispatcher("config.json")
d.emit("breaking_news", "CRITICAL",
       text_he="🚨 חדשות חדשותיות...",
       text_en="🚨 Breaking news...")
```

### Usage from Bash

```bash
echo '{"type":"fires","severity":"HIGH","text_en":"🔥 3 new fires...","text_he":"🔥 3 שריפות חדשות..."}' \
  | python3 scripts/dispatch.py config.json
```

## Breaking News Detection

The OSINT scanner automatically detects breaking news by matching **topic triggers** against **credibility signals**:

### How It Works

1. **Topic match** — Text contains a high-value phrase (e.g., "Khamenei killed", "nuclear detonation")
2. **Credibility check** — Source is credible OR text contains credible attribution
3. Both must match → alert is flagged `breaking: true` with topic

### Credible Sources

Reuters, AP News, IDF Official, Kan News, Flash News IL, Iran International, BBC Persian, Aharonovic, BeholdIsrael, SentDefender, IsraelRadar

### Credible Attribution Keywords

Netanyahu, Biden, Trump, IDF confirms, Pentagon confirms, Reuters, Associated Press, AFP, BBC confirms, "official statement"

### Topic Categories

- **Leader elimination** — Khamenei, Nasrallah, Sinwar (Hebrew + English variants)
- **Nuclear events** — Nuclear detonation, nuclear strike, nuclear bomb
- **Compound matching** — Words appearing anywhere in text (e.g., "khamenei" + "dead")

## OSINT Sources (40+ channels)

### Telegram OSINT Channels (10)
| Channel | Description |
|---------|-------------|
| `warmonitors` | War Monitors — fastest English breaking |
| `intelslava` | Intel Slava Z — military OSINT |
| `liveuamap` | Liveuamap — mapped conflict updates |
| `AbuAliExpress` | Abu Ali Express — Hebrew OSINT king |
| `flash_news_il` | Flash News IL — Hebrew breaking |
| `idfonline` | IDF Official |
| `iranintl_en` | Iran International English |
| `BBCPersian` | BBC Persian |
| `kann_news` | Kan News (Israeli public broadcasting) |
| `aharonyediot` | Aharon Yediot — HIGH reliability Hebrew OSINT |

### Twitter Accounts (11)
`@PenPizzaReport` · `@Conflict_Radar` · `@Worldsource24` · `@sentdefender` · `@beholdisrael` · `@Osint613` · `@Osinttechnical` · `@IsraelRadar_` · `@Intel_Sky` · `@ELINTNews` · `@IsraelWarRoom`

### RSS Feeds (7)
| Feed | URL |
|------|-----|
| Times of Israel | Direct RSS |
| Jerusalem Post | Direct RSS |
| Al Jazeera | Direct RSS |
| TASS | Direct RSS |
| Ynet (Hebrew) | Direct RSS |
| **Reuters** | Google News RSS proxy (`site:reuters.com`) |
| **AP News** | Google News RSS proxy (`site:apnews.com`) |

> **Note:** Reuters and AP direct RSS feeds are behind Cloudflare/paywalls. We use Google News RSS search filtered to `site:reuters.com` and `site:apnews.com` as a reliable proxy. Items include `<source>` tags for attribution.

### Keyword Filtering (56 terms)

Hebrew + English keywords covering: military operations, weapons systems, political leaders, nuclear facilities (Natanz, Fordow), defense systems (Iron Dome, Arrow, David's Sling, THAAD), and key figures (Khamenei/חמינאי).

## 🔥 NASA FIRMS Satellite Fire Detection

4 NASA satellites monitor thermal anomalies across Iran to detect fires, explosions, and bombing near military/nuclear sites.

### Satellites
- **VIIRS SNPP** — 375m resolution
- **VIIRS NOAA-20** — Joint Polar Satellite System
- **VIIRS NOAA-21** — Latest generation
- **MODIS** — Terra/Aqua (1km resolution, highest coverage)

### Features
- Point-in-polygon Iran filtering (excludes neighboring countries)
- FRP-based priority (≥50 MW = HIGH, ≥15 = MEDIUM)
- Proximity alerts for 23 known nuclear/military/oil sites
- Reverse geocoding via Nominatim
- Deduplication with persistent state

### Priority Classification
| Priority | Trigger |
|----------|---------|
| 🚨 CRITICAL | Near nuclear site or capital (<30km) |
| 🔴 HIGH | Near military/oil site (<30km) OR FRP ≥50 MW |
| 🟡 MEDIUM | FRP ≥15 MW |
| ⚪ LOW | FRP <15 MW, no nearby sites |

## 🌐 Iran Internet Blackout Detection

Monitors Iran's internet as an early warning signal — Iran has historically cut internet before/during military operations.

### Sources
1. **IODA (Georgia Tech)** — BGP, active probing, Google traffic data for Iran ASNs
2. **Direct probes** — HTTP pings to irna.ir, president.ir, mehrnews.com with latency tracking

### Assessment Levels
| Level | Score | Description |
|-------|-------|-------------|
| 🟢 NORMAL | 0-9 | Operating normally |
| 🟠 MINOR_ISSUES | 10-24 | Some fluctuations |
| 🟡 DEGRADED | 25-49 | Significant disruptions — possible throttling |
| ⚫ BLACKOUT | 50+ | Major outage — internet cut off |

### Features
- 24h history bar chart in Telegram
- Visual threat meter (`████░░░░░░░░░░░░░░░░ 20/100`)
- Probe latency per Iranian site (with labels: state news, presidency, etc.)
- Max once/hour alerts (15 min for BLACKOUT)
- Intelligence signal: NORMAL during strikes = possible loss of command authority

## 🎯 Strike Correlation Engine

Automatically correlates fire + seismic events to detect kinetic strikes. When a fire and earthquake occur within **50km and 30 minutes**, it's flagged as a possible strike.

### Confidence Scoring
| Factor | Score |
|--------|-------|
| Distance <10km | +0.3 |
| Distance 10-30km | +0.2 |
| Time <10min | +0.3 |
| Near known site | +0.2 |
| Base | +0.1 |

## ✈️ Military Flight Tracking

### ADS-B Monitoring (OpenSky)
- Coverage: lat 20-42, lon 40-65 (full ME region)
- Classified by callsign prefix: RCH (airlift), DUKE (ISR), DOOM (bomber), SHELL (tanker), SNTRY (C2)
- US/Israeli military only — filters out Saudi, Omani, RAF, etc.

### Flight Radar Map (FR24)
- FlightRadar24 public feed (300-400+ aircraft)
- Dark Palantir-style map with country borders
- Color-coded: yellow=civil, red=over Iran, green=US/IL military
- Side intel panel: airport disruptions, military aircraft with role descriptions
- 50+ aircraft type→role mappings (F-35, B-52, KC-135, RC-135, E-3, etc.)
- Bilingual captions

### Airport Disruption Monitoring
Tracks live flight counts for airports in: Iran (30+), Israel (7), Iraq (5), Syria (3), Lebanon (1), Jordan (2)

Status: `[X] CLOSED` (0 flights), `[!] Limited` (<5), `[+] Operating` (5+)

## 🗺️ Intel Map & Time-Lapse GIF

### Intel Map
- ESRI satellite tile basemap (768x512px)
- Iran highlighted with gold border
- Fire dots color-coded by priority, sized by FRP
- Earthquake ring markers with magnitude labels
- 23 known sites marked (Natanz, Fordow, Isfahan, etc.)
- Auto-generated on every fire/seismic alert

### 24h Time-Lapse GIF
- Animated fire + seismic progression over 24 hours
- Known sites marked, fire dots animate chronologically
- Progress bar + timestamp + event counter
- 36 frames with variable pacing

## Adaptive Threat-Level System

| Level | Trigger | Oref | OSINT | Fires | Intel |
|-------|---------|------|-------|-------|-------|
| 🟢 GREEN | No sirens >30min | 30s | 5min | 15min | 30min |
| 🟡 ELEVATED | Sirens <30min ago | 15s | 2min | 10min | 15min |
| 🔴 HIGH | Active sirens NOW | 10s | 60s | 5min | 10min |
| ⚫ CRITICAL | Major cities | 10s | 30s | 3min | 5min |

Major cities: תל אביב, ירושלים, חיפה, באר שבע, and 13 more.

### Pikud HaOref Stand-Down Detection
- THREAT alerts (cat 1-7: missiles, rockets, UAVs) → escalate
- STANDDOWN alerts ("ניתן לצאת מהמרחב המוגן") → informational message, NO escalation
- 5-minute throttle on standdown messages

## 📌 Live Pinned Status Dashboard

Single Telegram message edited every 60s with:
- Current threat level with visual bar
- System status (all monitoring sources)
- Iran Watch: tracked fires, quakes, nuclear sites
- Scan frequencies by threat level
- Separate Hebrew/English versions with proper RTL formatting

## Hourly Reports

5-part automated report sent every hour:

1. 🗺️ **Intel Map** — Satellite map with fires, quakes, borders
2. ✈️ **Flight Radar Map** — Air traffic + military tracker
3. 🇮🇱 **Hebrew Summary** — Confident Israeli analyst style
4. 🇺🇸 **English Summary** — Professional analyst with personality
5. 🎬 **24h Time-Lapse GIF** — Animated progression

Summary personality adapts by threat level: CRITICAL=empowering, HIGH=confident, normal=chill, quiet=relaxed.

## `ctl.sh` Commands

| Command | Description |
|---------|-------------|
| `start` | Start real-time watcher daemon |
| `stop` | Stop watcher |
| `status` | Show watcher state, cron, last threat level |
| `dashboard` | Full dashboard: processes, state, logs, resources |
| `check` | One-time full check (JSON to stdout) |
| `post` | Full check → format → post to Telegram |
| `log [N]` | Show last N lines of watcher log |
| `rotate` | Force log rotation |
| `install-launchd` | Auto-start on boot (macOS) |
| `teardown` | 🛑 Kill everything |

## Pikud HaOref — Israeli IP Required

The Oref siren API is geo-restricted to Israeli IPs:

```bash
mkdir -p secrets

# Option A: NordVPN service credentials
printf "USERNAME\nPASSWORD" > secrets/nordvpn-auth.txt

# Option B: Any HTTPS/SOCKS5 proxy
echo "https://user:pass@host:port" > secrets/proxy-override.txt

# Option C: SSH tunnel to Israeli VPS
ssh -D 1080 user@your-server
echo "socks5://localhost:1080" > secrets/proxy-override.txt
```

No Israeli IP? You lose siren data but keep everything else.

## Wire Service Integration (Reuters/AP)

Direct Reuters and AP News RSS feeds are behind Cloudflare/paywalls. We use **Google News RSS** as a proxy:

```
# Reuters (Iran+Israel filtered)
https://news.google.com/rss/search?q=site:reuters.com+iran+OR+israel&hl=en-US&gl=US&ceid=US:en

# AP News (Iran+Israel filtered)
https://news.google.com/rss/search?q=site:apnews.com+iran+OR+israel&hl=en-US&gl=US&ceid=US:en
```

- Items include `<source>` tags identifying Reuters/AP origin
- Both are treated as **credible sources** — alerts skip "UNVERIFIED" label
- Works reliably, returns dozens of items per feed

## 🛡️ Cyber Warfare Monitor

Monitors 30+ hacktivist groups, cyber threat intel aggregators, and dark web breach feeds for Iran-Israel cyber operations. Auto-classifies attacks and dispatches bilingual alerts.

### Hacktivist Groups Monitored

**Pro-Iran / Pro-Palestinian:**

| Group | Affiliation | Threat | Known TTPs |
|-------|-------------|--------|------------|
| **Handala Hack** | IRGC-linked | HIGH | Data leak, wiper malware, Telegram hijack |
| **CyberAv3ngers** | IRGC | CRITICAL | ICS/SCADA attacks, PLC exploits (water, power) |
| **Moses Staff** | IRGC | HIGH | Data leak, encryption, extortion |
| **Cyber Toufan** | Iran-linked | HIGH | Hack-and-leak, data destruction |
| **DieNet** | Pro-Iran | MEDIUM | DDoS (emergency systems, broadcasting) |
| **Dark Storm Team** | Pro-Palestine/Russia | MEDIUM | DDoS-for-hire |
| **RipperSec** | Pro-Palestine (Malaysia) | MEDIUM | DDoS, SCADA intrusion |
| **Cyber Fattah** | Pro-Iran | MEDIUM | Data leak, reconnaissance |
| **Cyber Islamic Resistance** | Hezbollah-linked | HIGH | ICS recon, surveillance |

**Pro-Israel:**

| Group | Affiliation | Threat | Known TTPs |
|-------|-------------|--------|------------|
| **Predatory Sparrow** | Israel-linked | HIGH | ICS destruction (steel mills, gas stations, banks) |
| **Israeli Elite Force** | Pro-Israel | MEDIUM | Financial systems, data leak |

### CTI Twitter Accounts (8)

`@FalconFeedsio` · `@CyberKnow20` · `@DarkWebInformer` · `@HackManac` · `@MonThreat` · `@cybaboreh` · `@BrettCallow` · `@vaboreh`

### Dark Web / Breach RSS Feeds

- **Darkfeed** — Ransomware victim tracker
- **CISA Advisories** — US government cybersecurity alerts
- **The Hacker News** — Cyber news with Iran/Israel filtering
- **BleepingComputer** — Breach and malware news

### Attack Auto-Classification

| Category | Severity | Trigger Keywords |
|----------|----------|-----------------|
| 🏭 ICS/SCADA | CRITICAL | SCADA, PLC, water system, power grid, pipeline |
| 📂 Data Breach | HIGH | Data leak, database, credentials, source code |
| 💀 Ransomware/Wiper | HIGH | Ransomware, wiper, encrypted, destroyed |
| 🕵️ Espionage | HIGH | APT, spyware, backdoor, surveillance |
| 🌐 DDoS | MEDIUM | DDoS, denial of service, offline |
| 🎨 Defacement | LOW | Defaced, website hacked |

### Target Detection

Automatically identifies whether Israel 🇮🇱 or Iran 🇮🇷 is being targeted based on text analysis + group affiliation fallback.

### Custom Sources

```json
{
  "cyber_telegram_channels": ["my_custom_channel"],
  "cyber_twitter_accounts": ["my_cti_analyst"],
  "cyber_rss_feeds": [
    {"name": "My Feed", "url": "https://...", "type": "cyber_news"}
  ]
}
```

## File Structure

```
iran-israel-alerts/
├── README.md                    # This file
├── SKILL.md                     # OpenClaw skill metadata
├── ctl.sh                       # Master control script
├── config.example.json          # Template → copy to config.json
├── config.json                  # Your config (gitignored)
├── .gitignore
├── scripts/
│   ├── realtime-watcher.sh      # Adaptive threat-level daemon
│   ├── dispatch.py              # Multi-channel alert router
│   ├── scan-osint.py            # Unified OSINT scanner (TG+X+RSS+seismic)
│   ├── scan-fires.py            # NASA FIRMS fire scanner
│   ├── scan-seismic.py          # USGS earthquake scanner
│   ├── scan-blackout.py         # Iran internet blackout detector
│   ├── scan-military-flights.py # US military ADS-B tracker
│   ├── scan-naval.py            # Naval vessel tracker
│   ├── scan-cyber.py            # Cyber warfare & hacktivist monitor
│   ├── correlate-strikes.py     # Fire+seismic strike correlation
│   ├── generate-fire-map.py     # Satellite intel map generator
│   ├── generate-flight-map.py   # FR24 air traffic map + intel panel
│   ├── generate-timelapse.py    # 24h animated time-lapse GIF
│   ├── generate-summary.py      # Hourly Hebrew+English summaries
│   ├── format-osint.py          # OSINT bilingual formatter
│   ├── format-fires.py          # Fire data formatter
│   ├── format-seismic.py        # Seismic data formatter
│   ├── format-telegram.py       # War-room HTML formatter
│   ├── pinned-status.py         # Live pinned status dashboard
│   ├── log-intel.py             # JSONL intel event logger
│   ├── hourly-report.sh         # Hourly cron: map+summaries+GIF
│   ├── check-alerts.sh          # Full SITREP → JSON
│   └── post-telegram.sh         # check → format → Telegram
├── references/
│   ├── sources.md               # Full source list with ratings
│   └── borders.geojson          # Country borders (17 countries)
├── secrets/                     # gitignored, chmod 600
│   ├── firms-map-key.txt        # NASA FIRMS API key
│   ├── nordvpn-auth.txt         # NordVPN creds (optional)
│   └── proxy-override.txt       # Custom proxy (optional)
└── state/                       # gitignored, auto-created
    ├── watcher.pid / watcher.log
    ├── watcher-threat-level.txt
    ├── firms-seen.json
    ├── seismic-seen.json
    ├── blackout-state.json / blackout-history.json
    ├── military-flights.json
    ├── naval-state.json
    ├── strike-correlations.json
    ├── intel-log.jsonl           # All alert events (48h retention)
    ├── flight-history.jsonl      # Air traffic snapshots (7-day)
    ├── dispatch-log.jsonl        # Dispatch audit trail (7-day)
    ├── intel-map-latest.png
    ├── flight-map.png
    ├── pinned-message-id.txt
    ├── osint-{telegram,twitter,rss,seismic}-seen.json
    ├── cyber-{telegram,twitter,rss}-seen.json
    └── logs/                     # Rotated watcher logs (max 5)
```

## Cron Setup

```bash
# Hourly report (map + summaries + GIF)
0 * * * * cd /path/to/iran-israel-alerts && bash scripts/hourly-report.sh

# 2-hour full SITREP
0 */2 * * * cd /path/to/iran-israel-alerts && bash scripts/post-telegram.sh --force

# OpenClaw cron
openclaw cron add --name "Iran-Israel Report" --every "2h" --session isolated --timeout-seconds 120 \
  --message "cd /path/to/iran-israel-alerts && bash scripts/post-telegram.sh --force"
```

## Safety

⚠️ This system **never says "all clear"**. Only Pikud HaOref (Israel Home Front Command) can authorize leaving shelter. When sirens stop, the system shows "NO NEW ALERTS BROADCASTING" with a warning to follow official instructions.

## License

MIT

## Acknowledgments

- [Pikud HaOref](https://www.oref.org.il/) — Israel Home Front Command
- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) — Satellite fire detection
- [USGS](https://earthquake.usgs.gov/) — Seismic monitoring
- [IODA](https://ioda.inetintel.cc.gatech.edu/) — Internet outage detection
- [OpenSky Network](https://opensky-network.org/) — ADS-B flight tracking
- [FlightRadar24](https://www.flightradar24.com/) — Air traffic data
- [Polymarket](https://polymarket.com/) — Prediction markets
- [Google News RSS](https://news.google.com/) — Wire service proxy for Reuters/AP
- OSINT community on X/Twitter and Telegram
