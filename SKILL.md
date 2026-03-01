---
name: iran-israel-alerts
description: Monitor Iran-Israel-US military escalation and attack alerts using 80+ OSINT sources, satellite fire detection, seismic monitoring, cyber warfare tracking, military flight tracking, and real-time alert APIs. Includes interactive Leaflet strikes dashboard with 48K+ geolocated events, US/Iran military base overlays, and event type filtering. Use when checking for breaking military news, missile alerts, airstrikes, or geopolitical escalation between Iran, Israel, and the US. Triggers on questions about Iran attacks, Israel strikes, Middle East military alerts, OSINT updates, or escalation monitoring.
---

# Iran-Israel Attack Alert Monitor

Multi-source intelligence aggregation for Iran/Israel/US military escalation with adaptive threat-level system, 80+ source channels, real-time OSINT scanning, NASA satellite fire detection, USGS seismic monitoring, cyber warfare monitoring (19 hacktivist groups), wire service integration (Reuters/AP), multi-source breaking news corroboration, multi-channel bilingual dispatch with per-channel timezones, and instant Telegram delivery with auto-generated intel maps and interactive strikes dashboard.

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
│     ├─ 📢 12 Telegram channels (t.me/s/ web preview)          │
│     ├─ 🐦 13 Twitter accounts (syndication API)                │
│     ├─ 📰 7 RSS feeds (TOI, JPost, AJ, TASS, Ynet, Reuters, AP)│
│     └─ 🌍 USGS seismic (Iran region, M3.5+)                   │
│   📊 Polymarket          every 60s-5min (threat-adaptive)      │
│   🔥 NASA FIRMS fires    every 3-15min (threat-adaptive)       │
│   🌍 USGS seismic        every 3-15min (threat-adaptive)       │
│   🗺️ Intel map           auto-generated on fire/quake alerts   │
│   🌐 Iran internet       every 5-30min (blackout detection)    │
│   ✈️ Military flights     every 5-30min (OpenSky ADS-B)        │
│   ✈️ Flight radar map     hourly (FR24 air traffic + intel)    │
│   🛡️ Cyber warfare       every 5-30min                        │
│     ├─ 📢 25 hacktivist TG handles (19 groups)                │
│     ├─ 🐦 8 CTI Twitter accounts                               │
│     └─ 📰 4 dark web / breach RSS feeds                        │
│   🚢 Naval tracking      every 5-30min (AIS vessel data)      │
│   ⚔️ Strikes map data     every 6h (ACLED + local sensors)     │
│   🎯 Strike correlation   after every fire/seismic scan        │
│   📌 Pinned status        edited every 60s (live dashboard)     │
│                                                                │
│   → Instant Telegram push on changes                           │
│   → Breaking news corroboration (3+ reputable = CONFIRMED)     │
│   → Auto-escalate/deescalate threat level                      │
│   → Per-channel timezones (EN=ET, HE=IST)                     │
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
            dispatch.py → EN Channel (ET) + HE Channel (IST)
```

## Sources (80+ channels)

### Real-Time Watcher Sources

| # | Source | Channels | Method | Auth |
|---|--------|----------|--------|------|
| 1 | 🚨 Pikud HaOref (sirens) | 1 | REST API (Israeli IP req.) | None |
| 2 | 📢 Telegram OSINT | 12 channels | Web preview scraping | None |
| 3 | 🐦 X/Twitter OSINT | 13 accounts | Syndication API | None |
| 4 | 📰 RSS News | 7 feeds | RSS/XML parsing | None |
| 5 | 🌍 USGS Seismic | Iran region | REST API (GeoJSON) | None |
| 6 | 📊 Polymarket | Dynamic | REST API | None |
| 7 | 🔥 NASA FIRMS | 4 satellites | Area CSV API | MAP_KEY |
| 8 | 🌐 IODA Internet | Iran ASNs | Georgia Tech API | None |
| 9 | 🔍 Direct Probes | 3 Iranian sites | HTTP health check | None |
| 10 | ✈️ OpenSky ADS-B | ME region | REST API | None |
| 11 | ✈️ FlightRadar24 | ME region | Public feed | None |
| 12 | 🛡️ Cyber Hacktivist TG | 25 handles (19 groups) | Web preview scraping | None |
| 13 | 🛡️ Cyber CTI Twitter | 8 accounts | Syndication API | None |
| 14 | 🛡️ Cyber/DarkWeb RSS | 4 feeds | RSS/XML parsing | None |
| 15 | 🚢 Naval AIS | Persian Gulf | AIS data feeds | None |
| 16 | ⚔️ ACLED Strikes | ME region (9 countries) | REST API (OAuth2) | Free account |

### Telegram OSINT Channels
- `warmonitors` — War Monitors (fastest English breaking)
- `intelslava` — Intel Slava Z (military OSINT)
- `liveuamap` — Liveuamap (mapped conflict updates)
- `AbuAliExpress` — Abu Ali Express (Hebrew OSINT king)
- `flash_news_il` — Flash News IL (Hebrew breaking)
- `idfonline` — IDF Online (English)
- `idfofficial` — IDF Spokesman / דובר צה״ל (Hebrew, official)
- `IDFarabic` — IDF Arabic Spokesperson
- `iranintl_en` — Iran International English
- `BBCPersian` — BBC Persian
- `kann_news` — Kan News
- `aharonyediot` — Aharon Yediot (HIGH reliability Hebrew OSINT)

### RSS Feeds (7)
- Times of Israel — direct RSS
- Jerusalem Post — direct RSS
- Al Jazeera — direct RSS
- TASS — direct RSS
- Ynet (Hebrew) — direct RSS
- **Reuters** — via Google News RSS proxy (`site:reuters.com`)
- **AP News** — via Google News RSS proxy (`site:apnews.com`)

> **Note:** Direct Reuters/AP RSS feeds are behind Cloudflare/paywalls. Google News RSS filtered to `site:reuters.com` works reliably as a proxy, including `<source>` tags for attribution.

### Twitter OSINT Accounts
`@PenPizzaReport`, `@Conflict_Radar`, `@Worldsource24`, `@sentdefender`, `@beholdisrael`, `@Osint613`, `@Osinttechnical`, `@IsraelRadar_`, `@Intel_Sky`, `@ELINTNews`, `@IsraelWarRoom`, `@IDF`, `@IDFSpokesperson`

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

| Level | Hebrew | Trigger | Oref | OSINT | Poly | Fires | Intel (blackout+flights+cyber) |
|-------|--------|---------|------|-------|------|-------|-------------------------------|
| 🟢 GREEN | שגרה | No sirens >30min | 30s | 5min | 5min | 15min | 30min |
| 🟡 ELEVATED | מוגבר | Sirens <30min ago | 15s | 2min | 2min | 10min | 15min |
| 🔴 HIGH | גבוה | Active sirens NOW | 10s | 60s | 60s | 5min | 10min |
| ⚫ CRITICAL | קריטי | Major cities under fire | 10s | 30s | 60s | 3min | 5min |

All threat levels and transition reasons are fully translated for the Hebrew channel — e.g., "רמת איום: מוגבר" (not "THREAT LEVEL: ELEVATED").

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

## ✈️ Flight Radar Map (Air Traffic Intelligence)

FlightRadar24-style live map of Middle East air traffic, generated hourly as part of the intel report.

### Data Source
- **Primary**: FlightRadar24 public feed (300-400+ aircraft, full ADS-B coverage)
- **Fallback**: OpenSky Network API (~80 aircraft, free tier)
- FR24 provides aircraft type, callsign, origin/dest airports, altitude, speed, airline, registration

### Map Features
- **Dark Palantir-style map** with country borders from GeoJSON
- **Aircraft arrows** showing heading direction (yellow=civil, red=over Iran, green=US/IL military)
- **Iran airspace highlighted** with red border and dark fill
- **Side intel panel** with:
  - Traffic count (total + over Iran)
  - Airport disruption status (Iran/Iraq/Syria/Israel/Lebanon/Jordan)
  - US / Israeli military aircraft with role descriptions (e.g. "Tactical airlift", "SIGINT reconnaissance", "Strategic bomber")
  - Top origin airports

### US/Israeli Military Detection
- **US callsign prefixes**: RCH, REACH, EVAC, FORTE, JAKE, SAM, AF1, AF2, NAVY, CNV, DOOM, BOLT, IRON, LANCE, ETHYL, SHELL, TEXAS, HOMER, SNOOP, EPIC, GHOST, SNTRY, etc.
- **Israeli callsign prefixes**: IAF, ISF
- **Aircraft type matching**: C-17, KC-135, E-3, RC-135, B-52, F-35, RQ-4, MQ-9, G550, etc.
- **Registration heuristics**: N-prefix (US), 4X-prefix (Israel) for unidentified military types
- Filters out non-US/IL military (Saudi, Omani, RAF, etc.) — only shows relevant assets

### Aircraft Role Descriptions (50+ types mapped)
| Type | Role |
|------|------|
| F-35 | Stealth strike fighter |
| B-52 | Strategic bomber |
| KC-135 | Aerial refueling tanker |
| RC-135 | SIGINT reconnaissance |
| E-3 | AWACS airborne radar |
| E-6 | Nuclear command relay |
| C-17 | Strategic airlift |
| C-130 | Tactical airlift |
| RQ-4 | High-alt surveillance drone |
| MQ-9 | Armed recon drone |
| P-8A | Maritime patrol / ASW |
| G550 | SIGINT / early warning |

### Airport Disruption Monitoring
Tracks live flight counts for airports in conflict zone countries:
- **Iran**: THR, IKA, MHD, ISF, TBZ, SYZ, KER, AWZ, BND + 20 more
- **Israel**: TLV, SDV, VDA, ETH, BEV, RPN, HFA
- **Iraq**: BGW, BSR, EBL, NJF, SDA
- **Syria**: DAM, ALP, LTK
- **Lebanon**: BEY
- **Jordan**: AMM, AQJ

Status: `[X] CLOSED` (0 flights), `[!] Limited` (<5 flights), `[+] Operating` (5+ flights)

### Data Logging
Two structured logs updated on every scan:

**`state/flight-history.jsonl`** (7-day retention) — Full snapshot:
```json
{
  "ts": 1772305939, "utc": "2026-02-28T19:12:19+00:00",
  "source": "fr24", "total": 332, "over_iran": 36,
  "iran_flights": 0, "israel_flights": 1,
  "airports": {"Iran": {"count": 0, "status": "CLOSED"}, ...},
  "military": [{"callsign": "CNV3869", "type": "C130", "tag": "US", "role": "Tactical airlift", ...}],
  "top_origins": {"JED": 33, "IST": 25, ...},
  "top_dests": {"JED": 38, "CAI": 18, ...}
}
```

**`state/intel-log.jsonl`** (`flight_scan` event) — Summary for hourly reports:
```json
{
  "type": "flight_scan",
  "data": {
    "total": 332, "over_iran": 36,
    "military_count": 2, "military_callsigns": ["CNV3869", "C130"],
    "airports_closed": ["Iran", "Iraq", "Syria"],
    "airports_limited": ["Israel:1", "Lebanon:3"]
  }
}
```

### Bilingual Captions
- English channel: `✈️ Air Traffic — 332 aircraft, 36 over Iran`
- Hebrew channel: `✈️ תנועה אווירית — 332 מטוסים, 36 מעל איראן`

```bash
python3 scripts/generate-flight-map.py config.json state output.png
```

Sent automatically with every hourly report. Image dispatched to both channels with language-appropriate captions via `dispatch.py`.

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

Automated hourly report sent to Telegram via cron — five items:

1. 🗺️ **Intel Map** — Fresh satellite map with fires, quakes, borders
2. ✈️ **Flight Radar Map** — FR24 air traffic with airport disruptions, US/IL military tracker, role descriptions
3. 🇮🇱 **Hebrew Summary** (סיכום מצב שעתי — מגן יהודה) — Confident Israeli analyst style, cheers up the audience, references צה״ל, כיפת ברזל, חץ. Motivational sign-offs adjusted by threat level.
4. 🇺🇸 **English Summary** (HOURLY INTEL SUMMARY — Magen Yehuda) — Professional analyst style with personality. "Am Yisrael Chai!" energy.
5. 🎬 **24h Time-Lapse GIF** — Animated fire + seismic progression

Both summaries include: sirens, OSINT highlights, fire/seismic detections, market moves, threat changes, and an analyst assessment section.

Cron: `0 * * * *` — runs `scripts/hourly-report.sh`

## Intel Logging

Every alert the watcher sends to Telegram is also saved to `state/intel-log.jsonl` for hourly summary generation.

### Event Types Logged
| Type | Description |
|------|-------------|
| `siren` | Pikud HaOref siren alerts with details |
| `siren_standdown` | Pikud HaOref stand-down messages |
| `breaking_news` | Breaking news alerts (with corroboration status) |
| `osint` | OSINT batch (Telegram, Twitter, RSS alerts with full text) |
| `seismic_osint` | Seismic events from OSINT scanner |
| `seismic` | USGS seismic from dedicated scanner |
| `fires` | NASA FIRMS fire detections |
| `polymarket` | Market spike alerts |
| `blackout` | Iran internet blackout status changes |
| `cyber` | Cyber warfare alerts (hacktivist, CTI, breach) |
| `threat_change` | Threat level transitions with reason |
| `flight_scan` | Air traffic snapshot (total, over Iran, military, airport status) |
| `strike_correlation` | Fire + seismic coincidence detection |
| `strikes_map` | Strikes map image with hourly report |

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

## 🚨 Breaking News Detection

The OSINT scanner automatically detects breaking news by matching **topic triggers** against **credibility signals**. Both must match for an alert to be flagged as breaking.

### Topic Categories
- **Leader elimination** — Khamenei, Nasrallah, Sinwar (Hebrew + English variants, 20+ phrasings)
- **Nuclear events** — Detonation, nuclear strike, nuclear bomb
- **Compound matching** — Words appearing anywhere in text (e.g., "khamenei" + "dead")

### Credible Sources
Reuters, AP News, IDF Official (`idfonline`), Kan News, Flash News IL, Iran International, BBC Persian, Aharonovic (`aharonyediot`), BeholdIsrael, SentDefender, IsraelRadar

### Credible Attribution Keywords
Netanyahu, Biden, Trump, IDF confirms, Pentagon confirms, Reuters, Associated Press, AFP, BBC confirms, "official statement"

### Flow
1. OSINT scanner matches text against topic trigger phrases
2. Checks if source channel is credible OR text contains credible attribution
3. Both must match → alert flagged `breaking: true` with topic string
4. Watcher dispatches as `breaking_news` event at `CRITICAL` severity
5. **Corroboration engine** tracks all sources per topic (see below)

### Multi-Source Corroboration

Breaking alerts are tracked per topic in `state/breaking-corroboration.json`. When **3+ reputable sources** report the same topic within a 2-hour window, the alert upgrades from UNVERIFIED to CONFIRMED:

| Reputable Sources | Status | Header |
|-------------------|--------|--------|
| 1-2 | ⚠️ UNVERIFIED | "BREAKING NEWS" / "ידיעה חדשותית דחופה" |
| 3+ | ✅ CONFIRMED | "CONFIRMED" / "ידיעה מאומתת" |

**Reputable source list** (30+): Reuters, AP, BBC, CNN, Times of Israel, Ynet, Haaretz, Jerusalem Post, Al Jazeera, Sky News, France24, NY Times, Washington Post, Wall Street Journal, plus trusted OSINT accounts (SentDefender, IntelPoint, Aurora Intel, etc.)

**Rules:**
- Same outlet doesn't count twice (deduplication by source name)
- Entries auto-expire after 2 hours
- CONFIRMED alerts display the full list of corroborating sources
- State persists across scan cycles in `breaking-corroboration.json`

## 📡 Multi-Channel Dispatch (`dispatch.py`)

Central routing module that sends alerts to multiple Telegram channels with language-specific formatting.

### Config

```json
{
  "outputs": [
    {
      "id": "main",
      "chat_id": "@english_channel",
      "language": "en",
      "timezone": "America/New_York",
      "content": ["all"],
      "min_severity": "LOW",
      "images": "all"
    },
    {
      "id": "hebrew",
      "chat_id": "@hebrew_channel",
      "language": "he",
      "timezone": "Asia/Jerusalem",
      "content": ["siren", "siren_standdown", "siren_clear", "breaking_news", "threat_change", "osint", "fires", "seismic", "strike_correlation", "blackout", "military_flights", "cyber", "polymarket", "map", "flight_map", "summary_he", "timelapse", "pinned_status"],
      "images": "high_only"
    }
  ]
}
```

### Output Options
| Field | Values | Description |
|-------|--------|-------------|
| `language` | `"en"`, `"he"`, `"both"` | Which language text to send |
| `timezone` | IANA tz string | Timestamps for this output (e.g. `"America/New_York"`, `"Asia/Jerusalem"`) |
| `content` | `["all"]` or specific types | Event type filter |
| `min_severity` | `"LOW"` to `"CRITICAL"` | Minimum severity to send |
| `images` | `"all"`, `"high_only"`, `"critical_only"`, `"none"` | Image inclusion policy |

### Event Types
`siren`, `siren_standdown`, `siren_clear`, `breaking_news`, `threat_change`, `osint`, `fires`, `seismic`, `strike_correlation`, `blackout`, `military_flights`, `cyber`, `polymarket`, `map`, `flight_map`, `summary_he`, `summary_en`, `timelapse`, `pinned_status`

### Usage from Python
```python
from dispatch import Dispatcher
d = Dispatcher("config.json")
d.emit("breaking_news", "CRITICAL", text_he="...", text_en="...",
       image_path="map.png", image_importance="high", image_caption_he="...")
```

### Usage from Bash (stdin)
```bash
echo '{"type":"fires","severity":"HIGH","text_en":"...","text_he":"..."}' \
  | python3 scripts/dispatch.py config.json
```

### Features
- Backward-compatible: works with single `telegram_chat_id` if no `outputs` array
- Image importance decided at call site (low/medium/high/critical)
- Separate `image_caption` vs `image_caption_he` for bilingual captions
- Supports text, photo, GIF animation, and message editing
- Dispatch audit log: `state/dispatch-log.jsonl` (7-day retention, auto-rotates at 2MB)

## 📰 Wire Service Integration (Reuters/AP)

Direct Reuters and AP News RSS feeds are behind Cloudflare/paywalls. **Google News RSS** is used as a reliable proxy:

```
# Reuters filtered to Iran+Israel
https://news.google.com/rss/search?q=site:reuters.com+iran+OR+israel&hl=en-US&gl=US&ceid=US:en

# AP News filtered to Iran+Israel
https://news.google.com/rss/search?q=site:apnews.com+iran+OR+israel&hl=en-US&gl=US&ceid=US:en
```

- Google News RSS items include `<source url="...">Reuters</source>` tags for attribution
- Both are in the `CREDIBLE_SOURCES` set — alerts from Reuters/AP skip "UNVERIFIED" labeling
- Returns dozens of items per feed, updates frequently

## ⚔️ Strikes Map (`scan_strikes.py` + `generate-strikes-map.py`)

Comprehensive geolocated strikes database and visual map covering the entire Middle East theater since October 7, 2023.

### Data Layers
1. **ACLED API** — Structured conflict events with lat/lon, actors, fatalities (1-3 day lag, analyst-verified)
2. **NASA FIRMS** — Satellite thermal anomalies near known military sites
3. **USGS Seismic** — Earthquake events in Iran region
4. **Strike Correlation** — Fire+seismic coincidence detections from correlation engine
5. **OSINT Text Extraction** — Location mentions in intel-log.jsonl matched against 80+ known cities/sites

### ACLED Registration (required for Layer 1)
1. Register at [acleddata.com/register](https://acleddata.com/register/) — free, institutional email recommended
2. Accept non-commercial terms, verify email
3. Add credentials: `secrets/acled-creds.txt` (line 1: email, line 2: password) OR `config.json → strikes.acled_email/acled_password`
4. Scanner auto-handles OAuth2 (24h access token, 14-day refresh, auto-refresh)

### Config (`config.json → strikes`)
| Field | Default | Description |
|-------|---------|-------------|
| `start_date` | `"2023-10-07"` | How far back to collect |
| `window_days` | `null` | Rolling window (overrides start_date) |
| `countries` | 9 countries | ACLED country filter |
| `event_types` | 3 types | Explosions, Battles, Violence against civilians |
| `sub_event_types` | 7 types | Air/drone strike, shelling, etc. |
| `poll_interval_hours` | `6` | ACLED refresh frequency |
| `max_events` | `50000` | API row limit |
| `include_firms/seismic/correlations/osint` | `true` | Toggle each data layer |
| `min_fatalities` | `0` | Fatality filter |
| `actor_filter` | `[]` | Empty=all, or `["Israel","Iran"]` |
| `map_width/map_height` | `1600×1000` | Output image size |
| `highlight_recent_hours` | `48` | Yellow outline threshold |

### Map Visual
- Color-coded by actor side: 🔵 Israel, 🔴 Iran, 🟠 Proxies, 🔵 US
- Shape by event type: ● Airstrike, ◆ Missile, ▲ Ground, ✚ Satellite, ○ Seismic
- Size scaled by fatalities, opacity by confidence
- Sent with hourly report via dispatch

### Integration
- Watcher: `check_strikes()` runs on extended intel interval (5-30min)
- Hourly report: `--backfill` refresh + map generation + dispatch as `strikes_map` event
- State files: `strikes-data.json`, `strikes-last-fetch.json`, `strikes-map.png`, `acled-token.json`

## 🗺️ Interactive Strikes Dashboard

Standalone Leaflet-based HTML dashboard for theater operations visualization. Gist-hosted for zero-deploy sharing.

### Features
- **48,500+ geolocated events** from ACLED + FIRMS + OSINT + Pikud HaOref
- **Dark military theme** — CartoDB dark tiles, Orbitron/JetBrains Mono fonts, scanline overlay
- **Theater select** — ALL, Iran, IL/Gaza, Lebanon, Syria, Iraq, Yemen, Red Sea
- **14 conflict phase presets** — Oct 7, Ground Op, True Promise I/II, US→Houthis, Days of Repentance, US+IL→Tehran, etc.
- **Force disposition bars** — Israel (IDF), Iran (IRGC), Iran Proxies, Syria (SAA), US (CENTCOM), Gulf States
- **Country breakdown grid** with event counts and toggles
- **Zoomable timeline** — mouse wheel zoom, +/−/FIT buttons, brush selection, 13 annotated key events
- **Timeline auto-fits** to active filter range with 15% padding

### Map Overlays
- **20 US/Coalition bases** — Al Udeid (CENTCOM HQ), Al Dhafra, NSA Bahrain (5th Fleet), Incirlik, Akrotiri, Nevatim, Diego Garcia, etc. Toggleable ON/OFF
- **28 Iran military sites** — nuclear (☢️ Natanz, Isfahan, Fordow, Bushehr, Arak), missile (🚀 Dezful, Semnan, Khojir, Bid Kaneh), naval (⚓ Bandar Abbas, Chabahar, Jask), airbases (✈️ Mehrabad, Isfahan, Bushehr, Hamadan), air defense (🛡️ S-300 Tehran, Isfahan, Bushehr). Toggleable ON/OFF
- **14 Iran key sites** with proximity event counts — click to fly-to

### Event Type Filtering
- 9 event subtypes: Air/drone strike, Shelling/artillery/missile, Armed clash, Attack, Remote explosive/IED, Possible strike (FIRMS), Thermal anomaly (FIRMS), Location mention in OSINT, Suicide bomb
- Click any type to isolate on map; click again to clear; multi-select supported
- FIRMS markers: orange (#ff8800), confidence-based radius (high=5, medium=3.5, low=2.5)

### Data Sources
| Source | Events | Coverage |
|--------|--------|----------|
| ACLED | ~48,000 | Oct 7, 2023 → Feb 2025 (analyst-verified, ~1yr lag) |
| NASA FIRMS | ~380 | Real-time satellite fire detections in Iran |
| OSINT | ~175 | Intel-log text extraction (location mentions) |
| Pikud HaOref | 1+ | Siren events with coordinates |

### Mobile Support
- Full-screen map with 5-tab bottom bar (Theater, Phase, Forces, Intel, Layers)
- Slide-up sheets for panel content
- Responsive CSS for ≤768px screens

### Files
- **Template:** `scripts/strikes-dashboard.html` (~1,100 lines, no inline data)
- **Standalone:** `scripts/strikes-dashboard-standalone.html` (~3.3MB, data embedded)
- **GitHub Gist:** `cce8ab4f861d240f21dc2916e7cd187e`

### Rebuild Standalone
```bash
python3 scripts/build-dashboard-standalone.py  # Or inline build script
```

The build script injects `strikes-data.json` as `COMPACT_DATA` (ultra-compact array format: day_num, lat×1000, lon×1000, country_idx, side_idx, fatalities, subtype_idx, location_idx, actor1, actor2, confidence).

## 🛡️ Cyber Warfare Monitor (`scan_cyber.py`)

Monitors 19 hacktivist groups (25 TG handles), 8 CTI Twitter accounts, and 4 dark web/breach RSS feeds for Iran-Israel cyber operations. Classifies attacks, identifies targets, and dispatches bilingual alerts.

### Sources

**1. Hacktivist Telegram Channels (~25 channels)**

Directly monitors the public preview (`t.me/s/`) of known hacktivist group channels:

| Side | Group | Affiliation | Threat | TTPs |
|------|-------|-------------|--------|------|
| 🇮🇷 | **Handala Hack** | IRGC-linked | HIGH | Data leak, wiper, TG hijack |
| 🇮🇷 | **CyberAv3ngers** | IRGC | CRITICAL | ICS/SCADA, PLC exploit |
| 🇮🇷 | **Moses Staff** | IRGC | HIGH | Data leak, encryption, extortion |
| 🇮🇷 | **Cyber Toufan** | Iran-linked | HIGH | Hack-and-leak, data destruction |
| 🇮🇷 | **DieNet** | Pro-Iran | MEDIUM | DDoS, defacement, psyop |
| 🇮🇷 | **Dark Storm Team** | Pro-Palestine/Russia | MEDIUM | DDoS-for-hire |
| 🇮🇷 | **RipperSec** | Pro-Palestine (MY) | MEDIUM | DDoS, SCADA intrusion |
| 🇮🇷 | **Cyber Fattah** | Pro-Iran | MEDIUM | Data leak, recon |
| 🇮🇷 | **Arabian Ghosts** | Pro-Iran | MEDIUM | DDoS, defacement |
| 🇮🇷 | **Fatimion Cyber Team** | Iran proxy | LOW | DDoS |
| 🇮🇷 | **Cyber Islamic Resistance** | Hezbollah-linked | HIGH | ICS recon, surveillance |
| 🇮🇱 | **Predatory Sparrow** | Israel-linked | HIGH | ICS attack, financial disruption |
| 🇮🇱 | **Israeli Elite Force** | Pro-Israel | MEDIUM | Financial, data leak |
| 🇮🇱 | **WeRedEvils** | Pro-Israel | LOW | DDoS, defacement |

Plus CTI aggregator channels: `FalconFeedsio`, `DarkWebInformer`, `cyaboreh`, `vaboreh`, `Ransomware_gang_report`

**2. Cyber Threat Intel Twitter (8 accounts)**

`@FalconFeedsio` · `@CyberKnow20` · `@DarkWebInformer` · `@HackManac` · `@MonThreat` · `@cybaboreh` · `@BrettCallow` · `@vaboreh`

**3. Dark Web / Breach RSS Feeds (4 default)**

- Darkfeed Ransomware tracker
- CISA Advisories (US govt)
- The Hacker News
- BleepingComputer

### Attack Classification

The scanner automatically classifies attacks using keyword matching:

| Type | Severity | Indicators |
|------|----------|------------|
| 🏭 ICS/SCADA | CRITICAL | SCADA, PLC, water system, power grid, gas station |
| 📂 Data Breach | HIGH | Data leak, exfiltrated, database, credentials |
| 💀 Ransomware/Wiper | HIGH | Ransomware, wiper, encrypted, destroyed |
| 🕵️ Espionage | HIGH | APT, spyware, backdoor, surveillance |
| 🌐 DDoS | MEDIUM | DDoS, denial of service, offline |
| 🎨 Defacement | LOW | Defaced, website hacked |

### Target Detection

Determines who is being targeted (Israel 🇮🇱 or Iran 🇮🇷) based on:
1. Entity mentions in text (IDF, Mossad, IRGC, Tehran, etc.)
2. Group affiliation fallback (Pro-Iran → targets Israel, Pro-Israel → targets Iran)

### Config

Add custom cyber channels/accounts/feeds in `config.json`:

```json
{
  "cyber_telegram_channels": ["my_custom_channel"],
  "cyber_twitter_accounts": ["my_cti_analyst"],
  "cyber_rss_feeds": [
    {"name": "My Feed", "url": "https://...", "type": "cyber_news"}
  ]
}
```

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
│   ├── scan_cyber.py           # Cyber warfare & hacktivist monitor (30+ groups)
│   ├── correlate-strikes.py    # Fire + seismic strike correlation engine
│   ├── generate-fire-map.py    # Satellite intel map generator
│   ├── generate-flight-map.py  # FR24 air traffic map + intel panel
│   ├── generate-timelapse.py   # 24h animated time-lapse GIF
│   ├── generate-summary.py     # Hourly Hebrew + English analyst summaries
│   ├── generate-strikes-map.py # Dark-themed ME strikes map
│   ├── strikes-dashboard.html  # Interactive Leaflet dashboard (template)
│   ├── strikes-dashboard-standalone.html # Standalone (~3.3MB, Gist-hosted)
│   ├── pinned-status.py        # Live pinned status message (edited every 60s)
│   ├── dispatch.py             # Multi-channel alert dispatcher (EN/HE routing)
│   ├── format-fires.py         # Fire data → Telegram HTML formatter
│   ├── format-seismic.py       # Seismic data → Telegram HTML formatter
│   ├── format-osint.py         # OSINT bilingual formatter (EN/HE channel names)
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
    ├── flight-history.jsonl    # Air traffic snapshots (7-day, JSONL)
    ├── dispatch-log.jsonl      # Dispatch audit trail (7-day)
    ├── breaking-corroboration.json # Multi-source breaking news tracker (2h window)
    ├── flight-map.png          # Latest flight radar map
    ├── intel-map-latest.png
    ├── pinned-message-id-main.txt    # EN channel pinned msg ID
    ├── pinned-message-id-hebrew.txt  # HE channel pinned msg ID
    ├── last-standdown-ts.txt   # Standdown throttle timestamp
    ├── watcher-oref-last.txt   # Last Oref API response
    ├── poly_current.json       # Current Polymarket state
    ├── osint-{telegram,twitter,rss,seismic}-seen.json
    ├── cyber-{telegram,twitter,rss}-seen.json
    ├── strikes-data.json       # Unified strikes database
    ├── strikes-last-fetch.json # ACLED poll timestamp
    ├── strikes-map.png         # Latest strikes map
    ├── acled-token.json        # ACLED OAuth2 token cache
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

**Important:** crontab must include Homebrew Python in PATH for Pillow/PIL:
```bash
# First line of crontab:
PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin

# Hourly status report (auto-installed)
0 * * * * bash scripts/hourly-report.sh

# 2-hour full SITREP
0 */2 * * * bash scripts/post-telegram.sh --force
```

> ⚠️ Without `PATH=/opt/homebrew/bin`, cron uses macOS system Python (3.9) which lacks Pillow — causing silent failures in fire map / timelapse / flight map generation.

## Troubleshooting

### Known Issues & Fixes (Feb 2026)

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Hourly report cron silently fails | Cron's PATH uses `/usr/bin/python3` (3.9.6) missing Pillow — `set -euo pipefail` kills script | Add `PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` as first line of crontab |
| Polymarket tracks 0 markets | `STATE_DIR` bash variable not exported → Python `os.environ.get()` gets `.` → writes state to wrong path | Add `export STATE_DIR` after assignment in `realtime-watcher.sh` |
| Cyber alerts found but never dispatched | `scan-cyber.py` (hyphen) can't be Python-imported → `from scan_cyber import format_cyber_summary` fails | Renamed to `scan_cyber.py` (underscore); format uses heredoc-based Python |
| OpenSky returns HTTP 429 | Rate limiting (no API key configured) | Register free OpenSky account for higher limits, or rely on FR24 for hourly flight maps |
| Darkfeed RSS returns 404 | Feed URL changed or removed | Replace with alternative ransomware feed, or remove from config |
| Hourly summary shows "Threat Level: UNKNOWN" | `generate-summary.py` parsed watcher.log for threat level but regex didn't match log format (emoji prefixes, startup lines) | Fixed: reads `state/watcher-threat-level.txt` first (written by watcher), falls back to log parsing |
| Cyber config has empty source arrays | `config.json` cyber section had no Telegram channels, Twitter accounts, or RSS feeds configured | Add sources to `cyber.telegram_channels`, `cyber.twitter_accounts`, `cyber.rss_feeds` in config.json |
| Duplicate threat level alerts on restart | Watcher initialized `THREAT_LEVEL=GREEN` on every start, then detected stale `OREF_LAST` → spammed GREEN→CRITICAL | Fixed: watcher reads `watcher-threat-level.txt` on startup to restore last known level |
| OSINT scan "still running" skips | Slow proxy causes scan to exceed cycle interval → lock file blocks next scan | Stale locks auto-break at 120s; check proxy latency if persistent |

### Debugging Tips

```bash
# Test hourly report under simulated cron environment
env -i HOME="$HOME" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" \
  bash scripts/hourly-report.sh

# Test single monitor
python3 scripts/scan_cyber.py config.json state
python3 scripts/scan-blackout.py config.json state
python3 scripts/scan-fires.py config.json state

# Check watcher health
bash ctl.sh dashboard

# Binary search for bash syntax errors
for end in $(seq 900 1000); do head -$end scripts/realtime-watcher.sh | bash -n 2>&1 && continue; echo "Error at line $end"; break; done
```

### Environment Variables

The watcher uses these bash variables — **`STATE_DIR` must be exported** for inline Python:

| Variable | Usage | Exported? |
|----------|-------|-----------|
| `SKILL_DIR` | Base directory for all paths | No (bash only) |
| `STATE_DIR` | Runtime state files directory | **Yes** (Python reads via `os.environ`) |
| `CONFIG_FILE` | Path to config.json | No (passed as arg) |
| `THREAT_LEVEL` | Current threat level string | No (bash only) |
