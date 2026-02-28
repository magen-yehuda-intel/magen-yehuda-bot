---
name: iran-israel-alerts
description: Monitor Iran-Israel-US military escalation and attack alerts using X/Twitter OSINT accounts, RSS feeds, and real-time alert APIs. Use when checking for breaking military news, missile alerts, airstrikes, or geopolitical escalation between Iran, Israel, and the US. Triggers on questions about Iran attacks, Israel strikes, Middle East military alerts, OSINT updates, or escalation monitoring.
---

# Iran-Israel Attack Alert Monitor

Multi-source intelligence aggregation for Iran/Israel/US military escalation with adaptive threat-level system, real-time OSINT scanning, NASA satellite fire detection, USGS seismic monitoring, and instant Telegram delivery with auto-generated intel maps.

## Quick Start

```bash
bash ctl.sh status    # See what's running
bash ctl.sh check     # One-time full SITREP (stdout)
bash ctl.sh post      # Full check → post to Telegram
bash ctl.sh start     # Start real-time watcher (adaptive threat system)
bash ctl.sh stop      # Stop real-time watcher
bash ctl.sh teardown  # 🛑 Kill everything (watcher + cron + state)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Real-Time Watcher (daemon)                        │
│                                                                │
│   🚨 Oref sirens        every 10-30s (threat-adaptive)        │
│   📡 OSINT scanner       every 30s-5min (threat-adaptive)      │
│     ├─ 📢 10 Telegram channels (t.me/s/ web preview)          │
│     ├─ 🐦 11 Twitter accounts (syndication API)                │
│     ├─ 📰 4 RSS feeds (TOI, JPost, Al Jazeera, TASS)          │
│     └─ 🌍 USGS seismic (Iran region, M3.5+)                   │
│   📊 Polymarket          every 60s-5min (threat-adaptive)      │
│   🔥 NASA FIRMS fires    every 3-15min (threat-adaptive)       │
│   🌍 USGS seismic        every 3-15min (threat-adaptive)       │
│   🗺️ Intel map           auto-generated on fire/quake alerts   │
│   🌐 Iran internet       every 5-30min (blackout detection)    │
│   ✈️ Military flights     every 5-30min (OpenSky ADS-B)        │
│   🎯 Strike correlation   after every fire/seismic scan        │
│   📌 Pinned status        edited every 60s (live dashboard)     │
│                                                                │
│   → Instant Telegram push on changes                           │
│   → Auto-escalate/deescalate threat level                      │
│   → Pikud HaOref stand-down messages detected (no escalation)  │
└──────────────────┬─────────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────────┐
│              Scheduled Reports                                  │
│   📊 Hourly: intel map + Hebrew + English summaries → Telegram  │
│   🎬 Hourly: 24h time-lapse GIF → Telegram                     │
│   📋 2-Hour Full SITREP (Oref + RSS + Poly + Oil + ADS-B)      │
└──────────────────┬─────────────────────────────────────────────┘
                   │
            Telegram Channel (@magenyehudaupdates)
```

## Sources (30+ channels)

### Real-Time Watcher Sources

| # | Source | Channels | Method | Auth |
|---|--------|----------|--------|------|
| 1 | 🚨 Pikud HaOref (sirens) | 1 | REST API (Israeli IP req.) | None |
| 2 | 📢 Telegram OSINT | 10 channels | Web preview scraping | None |
| 3 | 🐦 X/Twitter OSINT | 11 accounts | Syndication API | None |
| 4 | 📰 RSS News | 4 feeds | RSS/XML parsing | None |
| 5 | 🌍 USGS Seismic | Iran region | REST API (GeoJSON) | None |
| 6 | 📊 Polymarket | Dynamic | REST API | None |
| 7 | 🔥 NASA FIRMS | 4 satellites | Area CSV API | MAP_KEY |
| 8 | 🌐 IODA Internet | Iran ASNs | Georgia Tech API | None |
| 9 | 🔍 Direct Probes | Iranian sites | HTTP health check | None |
| 10 | ✈️ OpenSky ADS-B | ME region | REST API | None |

### Telegram OSINT Channels
- `warmonitors` — War Monitors (fastest English breaking)
- `intelslava` — Intel Slava Z (military OSINT)
- `liveuamap` — Liveuamap (mapped conflict updates)
- `AbuAliExpress` — Abu Ali Express (Hebrew OSINT king)
- `flash_news_il` — Flash News IL (Hebrew breaking)
- `idfonline` — IDF Official
- `iranintl_en` — Iran International English
- `BBCPersian` — BBC Persian
- `kann_news` — Kan News
- `aharonyediot` — Aharon Yediot (HIGH reliability Hebrew OSINT)

### Twitter OSINT Accounts
`@PenPizzaReport`, `@Conflict_Radar`, `@Worldsource24`, `@sentdefender`, `@beholdisrael`, `@Osint613`, `@Osinttechnical`, `@IsraelRadar_`, `@Intel_Sky`, `@ELINTNews`, `@IsraelWarRoom`

### SITREP-Only Sources (2-hour cron)
| # | Source | Method | Auth |
|---|--------|--------|------|
| 8 | 🛢️ Oil/Commodities | OilPriceAPI | None |
| 9 | ✈️ Military Aviation | OpenSky ADS-B | None |

## 🔥 NASA FIRMS Satellite Fire Detection

Monitors thermal anomalies across Iran using 4 NASA satellites to detect fires, explosions, and bombing near military/nuclear sites.

### How It Works

```bash
# Standalone test
python3 scripts/scan-fires.py config.json state           # Scan for new fires
python3 scripts/scan-fires.py config.json state --seed     # Seed baseline (no alerts)
python3 scripts/format-fires.py < fires.json               # Format for Telegram
```

### Satellites
- **VIIRS SNPP** — Suomi NPP (375m resolution)
- **VIIRS NOAA-20** — Joint Polar Satellite System
- **VIIRS NOAA-21** — Latest generation
- **MODIS** — Terra/Aqua (1km resolution, highest coverage)

### Features
- **Point-in-polygon Iran filtering** — Excludes Iraq/Afghanistan/Pakistan fires even if in bounding box
- **FRP-based priority** — Fire Radiative Power determines alert urgency (≥50 MW = HIGH, ≥15 = MEDIUM)
- **Proximity to 23 known sites** — Nuclear (Natanz, Fordow, Isfahan, Bushehr, Arak), military (Parchin, Shahrud, Bandar Abbas), oil (Kharg Island), capital (Tehran)
- **Reverse geocoding** — Nominatim converts coordinates to city/province names (cached, 1 req/sec, max 20/scan)
- **Deduplication** — Tracks seen fires in `state/firms-seen.json`, only alerts on new detections
- **API key required** — Free, see [Getting a FIRMS API Key](#getting-a-firms-api-key) below. Store in `secrets/firms-map-key.txt`

### Priority Classification
| Priority | Trigger |
|----------|---------|
| 🚨 CRITICAL | Near nuclear site or capital (<30km) |
| 🔴 HIGH | Near military/oil site (<30km) OR FRP ≥50 MW |
| 🟡 MEDIUM | FRP ≥15 MW |
| ⚪ LOW | FRP <15 MW, no nearby sites |

### Getting a FIRMS API Key

NASA FIRMS requires a free API key (MAP_KEY). The registration form asks for an email — they send the key instantly, no verification needed.

**Quick method using a disposable email:**

1. Go to https://mail.tm or any temp email service
2. Copy the generated email address
3. Go to https://firms.modaps.eosdis.nasa.gov/api/area/
4. Click "Get MAP_KEY" → enter the temp email
5. Check the temp inbox — key arrives within seconds
6. Save it:
   ```bash
   mkdir -p secrets
   echo "YOUR_KEY_HERE" > secrets/firms-map-key.txt
   ```

The key is permanent and has no rate limits for the area CSV endpoint. No real email required — NASA just needs *something* to send the key to.

**Alternative:** Use your real email at the same URL if you prefer. Same instant delivery.

## 🌍 USGS Seismic Activity Monitoring

Real-time earthquake detection in Iran (M2.5+) via USGS FDSNWS API. Identifies potentially suspicious seismic events near nuclear facilities.

### How It Works

```bash
# Standalone test
python3 scripts/scan-seismic.py config.json state             # Scan for new quakes
python3 scripts/scan-seismic.py config.json state --seed       # Seed baseline
python3 scripts/scan-seismic.py config.json state --days 7     # Look back 7 days
python3 scripts/format-seismic.py < seismic.json               # Format for Telegram
```

### Features
- **Iran bounding box** — lat 25-40, lon 44-63.5 (full coverage)
- **Proximity to 10 known sites** — Same nuclear/military/oil sites as fire detection
- **Suspicious event flagging** — Shallow (<10km depth) + moderate magnitude (≥3.5) near nuclear sites
- **Explosion type detection** — USGS classifies some events as "explosion" — auto-flagged CRITICAL
- **Deduplication** — Tracks in `state/seismic-seen.json`, 7-day retention
- **No API key needed** — USGS is free and open

### Priority Classification
| Priority | Trigger |
|----------|---------|
| 🚨 CRITICAL | Type = explosion, OR shallow + near nuclear site |
| 🔴 HIGH | M5.0+ OR near nuclear site |
| 🟡 MEDIUM | M4.0+ |
| ⚪ LOW | M2.5-3.9 |

### Why It Matters
Shallow high-magnitude events near nuclear facilities could indicate:
- Underground nuclear tests
- Bunker-buster strikes on hardened facilities
- Large conventional bombing campaigns

## 🗺️ Auto-Generated Intel Map

Every fire/seismic alert includes a satellite imagery map sent as a Telegram photo.

### Features
- **ESRI satellite tile basemap** (zoom level 5, 768x512px)
- **Country borders** — GeoJSON from Natural Earth, all neighbors labeled
- **Iran highlighted** — Gold border with subtle fill tint
- **Fire dots** — Color-coded by priority, sized by FRP, glow effects
- **Earthquake markers** — Concentric ring style with magnitude + depth labels
- **Suspicious triangle** — Purple ⚠️ overlay for suspicious seismic events
- **Known sites** — Diamond markers with labels (Natanz, Fordow, etc.)
- **Legend** — Dynamic, shows active layers (fires/quakes/both)
- **Timestamp** — UTC time in title bar

```bash
# Standalone generation
python3 scripts/generate-fire-map.py fires.json output.png
python3 scripts/generate-fire-map.py fires.json output.png --seismic seismic.json
```

### Dependencies
- `Pillow` (PIL) — `pip3 install Pillow`
- Downloads ESRI tiles at runtime (6 tiles per map, cached by OS)
- Border data in `references/borders.geojson` (17 countries, 473KB)

## Adaptive Threat-Level System

The watcher automatically adjusts monitoring frequency based on siren activity:

| Level | Trigger | Oref | OSINT | Poly | Fires | Intel (blackout+flights) |
|-------|---------|------|-------|------|-------|--------------------------|
| 🟢 GREEN | No sirens >30min | 30s | 5min | 5min | 15min | 30min |
| 🟡 ELEVATED | Sirens <30min ago | 15s | 2min | 2min | 10min | 15min |
| 🔴 HIGH | Active sirens NOW | 10s | 60s | 60s | 5min | 10min |
| ⚫ CRITICAL | Major cities under fire | 10s | 30s | 60s | 3min | 5min |

### Pikud HaOref Stand-Down Detection

The watcher classifies every Oref API response before escalating:
- **THREAT** alerts (cat 1-7: missiles, rockets, UAVs) → escalate normally
- **STANDDOWN** alerts ("ניתן לצאת מהמרחב המוגן") → send ✅ message, NO escalation
- Prevents false escalation on informational "you can leave shelter" broadcasts

## 🌐 Iran Internet Blackout Detection

Monitors Iran's internet connectivity as an early warning signal — Iran has historically cut internet before/during military operations.

### Sources
1. **IODA (Georgia Tech)** — BGP, active probing, Google traffic, MERIT telescope data for Iran ASNs
2. **Direct probes** — HTTP pings to irna.ir, president.ir, mehrnews.com with latency tracking

### Assessment Levels
| Level | Score | Description |
|-------|-------|-------------|
| 🟢 NORMAL | 0-9 | Internet operating normally |
| 🟠 MINOR_ISSUES | 10-24 | Some connectivity fluctuations (common, may not be military) |
| 🟡 DEGRADED | 25-49 | Significant disruptions — possible throttling |
| ⚫ BLACKOUT | 50+ | Major outage — internet appears cut off |

### Features
- **24h history graph** — Visual bar chart in Telegram showing connectivity trend
- **Threat meter** — `████░░░░░░░░░░░░░░░░ 20/100` visual bar
- **Probe latency** — Shows each Iranian website's response time
- **Throttled alerts** — Max once/hour (every 15 min for BLACKOUT level)
- **State tracking** — `state/blackout-state.json` + `state/blackout-history.json`

```bash
python3 scripts/scan-blackout.py config.json state       # Check status
python3 scripts/scan-blackout.py config.json state --seed # Seed baseline
```

## 🎯 Strike Correlation Engine

Automatically correlates fire + seismic events to detect possible kinetic strikes. When a fire and earthquake occur within 50km and 30 minutes of each other, it's flagged as a possible strike.

### How It Works
- Loads recent fires from `firms-seen.json` (parses lat/lon from key format `lat_lon_date`)
- Loads recent quakes from `seismic-seen.json` + USGS API for coordinates
- Computes haversine distance between all fire-quake pairs
- Scores confidence based on distance + time proximity
- Identifies nearest known military/nuclear site

### Confidence Scoring
| Factor | Score |
|--------|-------|
| Distance <10km | +0.3 |
| Distance 10-30km | +0.2 |
| Time <10min apart | +0.3 |
| Near known site | +0.2 |
| Base | +0.1 |

```bash
python3 scripts/correlate-strikes.py state    # Run correlation
```

Runs automatically after every fire+seismic scan in the watcher loop.

## ✈️ US Military Flight Tracking

Monitors military aircraft over the Middle East using OpenSky Network ADS-B data.

### Coverage
- **Bounding box**: lat 20-42, lon 40-65 (full ME region)
- **Classification by callsign prefix**: RCH/REACH (airlift), DUKE/DARK (ISR), DOOM/BONE (bomber), SHELL/TEXACO (tanker), SNTRY/MAGIC (C2)
- **Classification by ICAO24 hex ranges**: US military transponder blocks
- **Categories**: ISR, BOMBER, TANKER, C2, AIRLIFT, NUCLEAR_CAPABLE, UNKNOWN_MIL

### Alerts
- New military aircraft entering the zone triggers Telegram alert
- Shows callsign, altitude, speed, aircraft category
- Heavy tanker/bomber activity may indicate imminent strike sortie

```bash
python3 scripts/scan-military-flights.py config.json state         # Scan
python3 scripts/scan-military-flights.py config.json state --seed  # Seed baseline
```

## 🚢 Naval Vessel Tracking

Monitors military vessel movements in Persian Gulf, Strait of Hormuz, Gulf of Oman.

### Features
- **US Navy vessel database** — CVNs (carriers), DDGs (destroyers), CGs (cruisers), SSGNs (subs), LHDs
- **IRGC Navy detection** — Iranian fast attack boats, frigates, support ships
- **Zone classification** — Strait of Hormuz, Persian Gulf, Gulf of Oman, Arabian Sea
- **Naval base proximity** — Bandar Abbas, NSA Bahrain (5th Fleet), Jask, Bushehr, Al Dhafra, Duqm, Diego Garcia

```bash
python3 scripts/scan-naval.py config.json state         # Scan
python3 scripts/scan-naval.py config.json state --seed   # Seed baseline
```

Note: Most AIS APIs are paywalled. Script structure supports multiple data sources; currently uses public AIS feeds.

## 🎬 24h Time-Lapse GIF

Animated satellite map showing fire + seismic event progression over the last 24 hours.

### Features
- **ESRI satellite tile basemap** with Iran gold border + all neighbor borders
- **Known sites marked** — Natanz, Fordow, Isfahan, Bushehr, Arak, Tehran, Parchin, Shahrud, etc.
- **Fire dots** animate in chronologically — color by priority, sized by FRP, glow effects
- **Earthquake rings** pulse with magnitude labels
- **Progress bar + timestamp** header, event counter, legend
- **Smart frame pacing** — slow start (empty map), fast event progression, hold on final state
- **36 frames**, variable duration per frame

```bash
python3 scripts/generate-timelapse.py config.json state output.gif --hours 24
```

Sent automatically with every hourly report.

## 📌 Pinned Live Status Message

A single Telegram message edited every 60 seconds with current system status — pinned to the top of the channel.

### Shows
- Current threat level with visual bar
- System online/offline status
- Monitoring grid (all source types active/inactive)
- Iran Watch: tracked fires, quakes, nuclear/military sites
- Scan frequency by current threat level
- Last update timestamp

**Escalation** is instant (sirens detected → immediately bump level).
**Deescalation** is gradual (cooldown timers prevent premature step-down).

Major cities triggering CRITICAL: תל אביב, ירושלים, חיפה, באר שבע, פתח תקווה, ראשון לציון, רמת גן, בני ברק, חולון, בת ים, הרצליה, נתניה, אשדוד, אשקלון, רחובות, מודיעין, גבעתיים

## Hourly Status Report

Automated hourly report sent to Telegram via cron — three separate messages:

1. 🗺️ **Intel Map** — Fresh satellite map with fires, quakes, borders
2. 🇮🇱 **Hebrew Summary** (סיכום מצב שעתי — מגן יהודה) — Confident Israeli analyst style, cheers up the audience, references צה״ל, כיפת ברזל, חץ. Motivational sign-offs adjusted by threat level.
3. 🇺🇸 **English Summary** (HOURLY INTEL SUMMARY — Magen Yehuda) — Professional analyst style with personality. "Am Yisrael Chai!" energy.

Both summaries include: sirens, OSINT highlights, fire/seismic detections, market moves, threat changes, and an analyst assessment section.

Cron: `0 * * * *` — runs `scripts/hourly-report.sh`

## Intel Logging

Every alert the watcher sends to Telegram is also saved to `state/intel-log.jsonl` for hourly summary generation.

### Event Types Logged
| Type | Description |
|------|-------------|
| `siren` | Pikud HaOref siren alerts with details |
| `osint` | OSINT batch (Telegram, Twitter, RSS alerts with full text) |
| `seismic_osint` | Seismic events from OSINT scanner |
| `seismic` | USGS seismic from dedicated scanner |
| `fires` | NASA FIRMS fire detections |
| `polymarket` | Market spike alerts |
| `threat_change` | Threat level transitions with reason |

### Usage
```bash
# Read last 2 hours of intel
python3 scripts/log-intel.py state --read --since 2

# Read only siren events
python3 scripts/log-intel.py state --read --type siren

# Rotate old entries (keeps 48h)
python3 scripts/log-intel.py state --rotate
```

- Auto-rotates at 5MB, retains 48 hours of data
- Each line is a JSON object with `logged_at` (epoch) and `logged_utc` timestamps

## OSINT Scanner

The unified Python scanner (`scripts/scan-osint.py`) handles Telegram, Twitter, RSS, and inline seismic:

```bash
python3 scripts/scan-osint.py config.json state --source all
python3 scripts/scan-osint.py config.json state --source telegram
python3 scripts/scan-osint.py config.json state --source twitter
python3 scripts/scan-osint.py config.json state --source rss
python3 scripts/scan-osint.py config.json state --source seismic
```

Features:
- Keyword filtering (52 keywords, Hebrew + English)
- Deduplication via per-source seen-state files
- NordVPN proxy support for rate-limited sources
- Graceful error handling per source
- JSON output for integration with watcher

## Pikud HaOref — Israeli IP Requirement

The Oref siren API is **geo-restricted to Israeli IPs**. The script handles this with a fallback chain:

1. **Custom proxy** → `secrets/proxy-override.txt`
2. **NordVPN** → `secrets/nordvpn-auth.txt` routes through `il66.nordvpn.com:89`
3. **Direct** → Falls back to direct connection
4. **Graceful failure** → Reports Oref unavailable; all other sources still work

### Setup options

```bash
mkdir -p secrets

# Option A: NordVPN (service credentials, NOT login)
echo "USERNAME\nPASSWORD" > secrets/nordvpn-auth.txt

# Option B: Any HTTPS/SOCKS5 proxy
echo "https://user:pass@host:port" > secrets/proxy-override.txt

# Option C: SSH tunnel
ssh -D 1080 user@israeli-vps
echo "socks5://localhost:1080" > secrets/proxy-override.txt

# Option D: Skip it — most sources still work globally
```

## Safety Rules

⚠️ **Never say "all clear"** — Only Pikud HaOref can tell people it's safe to leave shelter. The system shows "NO NEW ALERTS BROADCASTING" when sirens stop, with a warning to follow official instructions.

## Threat Level Scoring (SITREP)

| Signal | Points |
|--------|--------|
| Active Pikud HaOref sirens | +30 |
| Major oil spike (>10%) | +25 |
| Polymarket price spike (≥5pp) | +15 |
| High oil move (5-10%) | +15 |
| Heavy news cycle (>8 headlines) | +8 |
| Elevated oil (3-5%) | +8 |
| Active news (4-8 headlines) | +5 |

| Score | Level | Action |
|-------|-------|--------|
| 0-7 | 🟢 LOW | No auto-post (use `--force`) |
| 8-19 | 🟡 ELEVATED | Auto-post |
| 20-39 | 🟠 HIGH | Auto-post |
| 40+ | 🔴 CRITICAL | Immediate alert |

## `ctl.sh` Commands

| Command | Description |
|---------|-------------|
| `start` | Start real-time watcher daemon |
| `stop` | Stop watcher |
| `status` | Show watcher state, cron, last threat level |
| `dashboard` | 📊 Full dashboard: processes, state, logs, resources |
| `check` | One-time full check (JSON to stdout) |
| `post` | Full check → format → post to Telegram |
| `log [N]` | Show last N lines of watcher log |
| `rotate` | Force log rotation + show archive status |
| `install-launchd` | Auto-start watcher on boot (macOS) |
| `teardown` | 🛑 Kill everything: watcher, cron, launchd, state |

Aliases: `dash`, `ps` → `dashboard`

## Log Rotation

- Watcher log rotates at **500KB** (checked every 5min during runtime + on start)
- Keeps **5 archived logs** in `state/logs/`
- `ctl.sh rotate` forces rotation check + shows archive status
- `ctl.sh dashboard` shows log size and archive count

## Scan Overlap Protection

- OSINT scan uses a lock file (`state/osint-scan.lock`) to prevent concurrent scans
- If a scan is still running when the next cycle fires, it skips with a log message
- Stale locks (>120s) auto-break to prevent permanent deadlock
- Twitter/Telegram scraping goes through NordVPN proxy (curl subprocess) to avoid home IP rate limits

## File Structure

```
iran-israel-alerts/
├── SKILL.md                    # This file
├── README.md                   # Open-source documentation
├── ctl.sh                      # Master control (start/stop/status/teardown)
├── config.example.json         # Template — copy to config.json
├── config.json                 # Your config (gitignored)
├── .gitignore
├── scripts/
│   ├── realtime-watcher.sh     # Background daemon (adaptive threat system)
│   ├── check-alerts.sh         # Full SITREP (structured JSON output)
│   ├── post-telegram.sh        # Check → format → post to Telegram
│   ├── format-telegram.py      # JSON → war-room HTML formatter
│   ├── scan-osint.py           # Unified OSINT scanner (TG + X + RSS + seismic)
│   ├── scan-fires.py           # NASA FIRMS fire scanner for Iran
│   ├── scan-seismic.py         # USGS earthquake scanner for Iran
│   ├── scan-blackout.py        # Iran internet blackout detector (IODA + probes)
│   ├── scan-military-flights.py # US military ADS-B flight tracker (OpenSky)
│   ├── scan-naval.py           # Naval vessel tracker (Persian Gulf AIS)
│   ├── correlate-strikes.py    # Fire + seismic strike correlation engine
│   ├── generate-fire-map.py    # Satellite intel map generator
│   ├── generate-timelapse.py   # 24h animated time-lapse GIF
│   ├── generate-summary.py     # Hourly Hebrew + English analyst summaries
│   ├── pinned-status.py        # Live pinned status message (edited every 60s)
│   ├── format-fires.py         # Fire data → Telegram HTML formatter
│   ├── format-seismic.py       # Seismic data → Telegram HTML formatter
│   ├── log-intel.py            # JSONL intel event logger
│   └── hourly-report.sh        # Hourly: map + summaries + GIF → Telegram
├── references/
│   ├── sources.md              # Full source list with ratings
│   └── borders.geojson         # Country borders GeoJSON (17 countries)
├── secrets/                    # gitignored, chmod 600
│   ├── nordvpn-auth.txt        # NordVPN service credentials (optional)
│   ├── proxy-override.txt      # Custom proxy override (optional)
│   └── firms-map-key.txt       # NASA FIRMS API key
└── state/                      # Auto-created, runtime data (gitignored)
    ├── watcher.pid / watcher.log
    ├── watcher-threat-level.txt
    ├── firms-seen.json
    ├── seismic-seen.json
    ├── blackout-state.json / blackout-history.json
    ├── military-flights.json
    ├── naval-state.json
    ├── strike-correlations.json
    ├── intel-log.jsonl
    ├── intel-map-latest.png
    ├── pinned-message-id.txt
    ├── osint-{telegram,twitter,rss,seismic}-seen.json
    └── logs/                   # Rotated watcher logs (max 5)
```

## Setup

### Requirements
- Python 3.9+ with `Pillow` (`pip3 install Pillow`)
- `curl`, `jq`, `bash`
- NASA FIRMS API key (free: https://firms.modaps.eosdis.nasa.gov/api/area/)

### Quick Setup
```bash
cp config.example.json config.json
# Edit config.json with your Telegram bot token, chat ID, FIRMS key
mkdir -p secrets
echo "YOUR_FIRMS_KEY" > secrets/firms-map-key.txt
bash ctl.sh start
```

### Cron Jobs
```bash
# Hourly status report (auto-installed)
0 * * * * bash scripts/hourly-report.sh

# 2-hour full SITREP
0 */2 * * * bash scripts/post-telegram.sh --force
```
