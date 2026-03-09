# Magen Yehuda Intel — Intelligence Collection & Processing Methodology

## Overview

Magen Yehuda is a real-time OSINT (Open Source Intelligence) monitoring system built to track the Iran-Israel military conflict. It aggregates intelligence from 85+ sources across multiple collection disciplines, processes events through automated pipelines, and delivers alerts to Telegram channels and an interactive CENTCOM Theater Operations dashboard.

**Live Dashboard:** https://magen-yehuda-intel.github.io/magen-yehuda-bot/

---

## 1. Collection Architecture

### 1.1 OSINT — Social Media Intelligence (SOCMINT)

**Telegram Channels (23 sources)**

Telegram public channels are scraped via `t.me/s/{channel}` (server-rendered HTML, no auth required). Each channel is polled every 30s-5min depending on threat level.

| Channel | Focus | Language |
|---------|-------|----------|
| warmonitors | Breaking war news | EN |
| intelslava | Russian/ME military intel | EN |
| liveuamap | Conflict mapping | EN |
| AbuAliExpress | IDF/Lebanon ops | HE |
| flash_news_il | Israeli breaking news | HE |
| idfonline | IDF Spokesman (EN) | EN |
| iranintl_en | Iran opposition media | EN |
| BBCPersian | BBC Persian service | FA |
| kann_news | Israeli Channel 12 | HE |
| aharonyediot | Israeli Yedioth | HE |
| idfofficial | IDF Spokesman (HE) | HE |
| IDFarabic | IDF Spokesman (AR) | AR |
| beholdisraelchannel | Pro-Israel analysis | EN |
| CIG_telegram | Clandestine Intel Group | EN |
| TassAgency_en | TASS Russian news | EN |
| endgameww3 | Conflict aggregator | EN |
| RWApodcast | Real World Analysis | EN |
| NotWoofers | ME military OSINT | EN |
| middle_east_spectator | ME analysis | EN |
| IranNukes | Iran nuclear tracking | EN |
| TheIntelHub | Military intel | EN |
| channel8200 | Israeli intel | HE |
| zaborona_ua | Ukraine defense | EN |

**How it works:**
1. `scan-osint.py` polls each channel's `t.me/s/` page (no API key needed)
2. Extracts message text, timestamp, message ID
3. Deduplicates via message ID tracking (`state/osint-rss-seen.json`)
4. Runs NLP location extraction (regex-based city/country matching)
5. Classifies event type (strike, missile, diplomatic, military movement, etc.)
6. Tags with geo-coordinates when location is identified

**Twitter/X Accounts (20 sources)**

| Account | Focus |
|---------|-------|
| @sentdefender | Global defense intel |
| @beholdisrael | Israel situation updates |
| @Osint613 | Israeli OSINT |
| @Osinttechnical | Technical OSINT analysis |
| @IsraelRadar_ | Missile/rocket tracking |
| @Intel_Sky | Air tracking intel |
| @ELINTNews | Electronic intelligence |
| @IDF / @IDFSpokesperson | Official IDF |
| @Aurora_Intel | Military aviation |
| @NotWoofers | ME military |
| @MideastStream | ME news aggregator |
| @Faytuks | Conflict analysis |
| @MiddleEastOSINT | Regional OSINT |
| @no_itsmyturn | Conflict reporting |
| @air_intel | Aviation intelligence |
| @PenPizzaReport | Defense analysis |
| @Conflict_Radar | Conflict monitoring |
| @Worldsource24 | Breaking news |
| @IsraelWarRoom | Israel defense |

**How it works:**
1. Scraped via Twitter embed pages or proxy services
2. Same NLP pipeline as Telegram for entity extraction
3. Cross-referenced with Telegram for corroboration

### 1.2 RSS/News Wire Intelligence

**10 RSS feeds** providing wire-service level reporting:

| Source | Language | Feed Type |
|--------|----------|-----------|
| Times of Israel | EN | Atom |
| Jerusalem Post | EN | RSS |
| Al Jazeera | EN | RSS |
| TASS | EN | RSS |
| Ynet | HE | RSS |
| Reuters (via Google News) | EN | Google News RSS proxy |
| AP News (via Google News) | EN | Google News RSS proxy |
| מעריב (Maariv) | HE | RSS |
| וואלה (Walla) | HE | RSS |
| חדשות 13 (Channel 13) | HE | RSS |

**Note:** Reuters and AP direct feeds are behind Cloudflare. We use `news.google.com/rss/search?q=site:reuters.com+iran+israel` as a proxy — works reliably and includes `<source>` tags for attribution.

### 1.3 Satellite Intelligence (SATINT)

**NASA FIRMS — Fire Information for Resource Management System**

4 satellites provide near-real-time thermal anomaly detection:

| Satellite | Instrument | Resolution | Latency |
|-----------|-----------|------------|---------|
| MODIS (Terra) | Thermal IR | 1km | ~3h |
| MODIS (Aqua) | Thermal IR | 1km | ~3h |
| VIIRS (Suomi NPP) | Thermal IR | 375m | ~3h |
| VIIRS (NOAA-20) | Thermal IR | 375m | ~3h |

**How it works (`scan-fires.py`):**
1. Polls FIRMS API every 5 minutes for the full ME region (24-64°E, 12-42°N)
2. Filters by Fire Radiative Power (FRP) — higher FRP = larger fire
3. Classifies fires by age: <1h (ACTIVE/red), 1-3h (RECENT/orange), 3-6h (FADING/amber)
4. Cross-correlates with known military/industrial targets for strike identification
5. Pushed to Azure Table Storage (`fireevents` table)

**Coverage:** Israel, Lebanon, Syria, Iraq, Iran, Saudi Arabia, UAE, Yemen, Turkey, Egypt, Jordan — full Middle East theater

### 1.4 Seismic Intelligence (SEISMINT)

**USGS Earthquake Hazards Program**

| Source | Endpoint | Polling |
|--------|----------|---------|
| USGS | earthquake.usgs.gov/earthquakes/feed | Every 2 minutes |

**How it works (`scan-seismic.py`):**
1. Polls USGS GeoJSON feed for M2.5+ events in ME region
2. Flags suspicious events: **depth ≤ 5km AND magnitude ≥ 3.5** → possible underground explosion
3. Standalone Telegram alerts for M3.5+ Iran-region events
4. Pushed to Azure Table Storage (`seismicevents` table)
5. Cross-correlated with FIRMS fire data for strike confirmation

**Key insight:** Natural earthquakes are typically 10-600km deep. Explosions (nuclear tests, bunker busters) register at <5km depth. A shallow M4.0 near a known nuclear facility is a strong indicator of a military strike.

### 1.5 Strike Correlation Engine

**`correlate-strikes.py`** — Automated multi-source fusion:

```
IF fire_event.location WITHIN 50km OF seismic_event.location
AND time_difference < 30 minutes
THEN flag as POSSIBLE STRIKE

IF correlated_event WITHIN 10km OF known_target (Natanz, Fordow, Isfahan, etc.)
THEN upgrade to PROBABLE STRIKE
```

Correlation inputs:
- FIRMS thermal anomalies (fire events)
- USGS seismic events (earthquake/explosion)
- Known military/nuclear target coordinates
- OSINT text reports mentioning strikes at same location

### 1.6 Cyber Warfare Intelligence

**`scan_cyber.py`** monitors 19 hacktivist groups across 25 Telegram handles + 8 Twitter CTI accounts + 4 RSS feeds:

- Iranian groups: CyberAv3ngers, Moses Staff, Agrius, MuddyWater
- Pro-Israel groups: Predatory Sparrow, various
- Proxy groups: Hezbollah-affiliated, Houthi-affiliated
- CTI feeds: AlienVault OTX, Recorded Future, CrowdStrike

### 1.7 Military Flight Tracking

**`generate-flight-map.py`** — Live aircraft tracking:

| Source | Data | Update Rate |
|--------|------|-------------|
| Own API (aggregated) | Full ME airspace | 30 seconds |

**Military detection heuristics:**
- Callsign prefix matching: `RCH` (USAF cargo), `FORTE` (Global Hawk), `SAM` (VIP), `IAF` (Israeli AF), etc.
- Aircraft type matching: C-17, KC-135, RC-135, RQ-4, F-35, B-52, etc.
- 50+ aircraft role descriptions for intelligence context

### 1.8 Pikud HaOref (Israeli Home Front Command)

Real-time siren alerts from Israel's official civil defense system:

- Polled every 10 seconds via API
- Categorizes: Rockets & Missiles, Hostile Aircraft, Earthquake, Tsunami, Radiological
- Immediate Telegram alert on any active siren
- History stored in Azure Table (`orefalerts`)

---

## 2. Processing Pipeline

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────┐
│  Collection  │──▶│  Processing  │──▶│   Correlation  │──▶│   Delivery   │
│              │   │              │   │                │   │              │
│ • Telegram   │   │ • Dedup      │   │ • Fire+Seismic │   │ • Telegram   │
│ • Twitter    │   │ • NLP/Regex  │   │ • Target match │   │ • Dashboard  │
│ • RSS        │   │ • Geocoding  │   │ • Corroborate  │   │ • Azure DB   │
│ • FIRMS      │   │ • Classify   │   │ • Confidence   │   │ • API        │
│ • USGS       │   │ • Timestamp  │   │                │   │              │
│ • OpenSky    │   │              │   │                │   │              │
│ • Oref       │   │              │   │                │   │              │
└─────────────┘   └──────────────┘   └────────────────┘   └──────────────┘
```

### Deduplication
- **Telegram:** Message ID per channel (monotonically increasing)
- **RSS:** Link URL hash, accumulated with 1000-entry cap per feed
- **FIRMS:** Lat/lon/timestamp composite key
- **Seismic:** USGS event ID

### Event Classification
Events are tagged with:
- `type`: strike, missile, diplomatic, military_movement, fire, seismic, cyber, siren
- `source`: Channel/feed name
- `location`: Extracted city/country + lat/lon
- `timestamp`: Unix epoch (UTC)
- `confidence`: Based on source credibility + corroboration count

### Threat Level System
Adaptive polling based on situation:

| Level | Polling Rate | Trigger |
|-------|-------------|---------|
| 🟢 GREEN | 5 min | Baseline |
| 🟡 ELEVATED | 2 min | Multiple OSINT reports |
| 🔴 HIGH | 1 min | Confirmed strikes/sirens |
| ⚫ CRITICAL | 30 sec | Active siren + multiple sources |

---

## 3. Delivery

### Telegram Channels
- **@magenyehudaupdates** — English, all content, all images
- **@opssheagathaariupdates** — Hebrew, high-priority only

Routing via `dispatch.py`:
- Reads `outputs` config array
- Routes based on language, content type, severity, image rules
- Supports text, photo, animation, edit operations
- Bilingual image captions

### CENTCOM Dashboard
Interactive Leaflet.js map at `centcom.html`:

**Layers:**
- US military bases (25 locations)
- Iran nuclear sites (18, with pulsing ☢️ markers)
- Iran missile sites (52)
- Iran air defense + SAM range rings
- Iran air bases (29)
- Iran oil & gas infrastructure (38) — with **struck facility** markers (💥 pulsing red)
- Gulf regional energy (30+)
- Strategic waterways (Hormuz, Suez, Bab el-Mandeb)
- IRGC bases (8)
- Live aircraft (500+ via API, 30s refresh, military callsign detection)
- FIRMS fire detections (gradient by age)
- USGS earthquakes (purple circles, suspicious shallow events highlighted)
- OSINT strike markers (blinking 💥 for <2h events matching strike keywords)
- Recon satellites (10 satellites, SGP4 orbit propagation)
- US Navy fleet (11 vessels, SVG carrier/submarine/supply ship icons)
- GPS jamming zones (9 regions, severity-colored pulsing circles)
- Pikud HaOref siren overlay

**Features:**
- Real-time live feed with source links and fly-to-event
- localStorage config persistence (Save/Clear/Reset)
- Aircraft mode cycling (ALL/MIL/CIV/OFF)
- Fire mode cycling (<1H/1-3H/3-6H/ALL/OFF)
- Legend panel
- Mobile-responsive bottom toolbar

### Azure Backend
- Container App: `magen-yehuda-api` (Flask/gunicorn, consumption plan ~$0/mo)
- Table Storage: `intelevents`, `orefalerts`, `seismicevents`, `fireevents`
- API endpoints: `/api/intel-feed`, `/api/seismic`, `/api/oref/history`, `/api/aircraft`

---

## 4. Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Telegram `t.me/s/` over API | No auth needed, server-rendered, fast, message IDs for dedup |
| Google News RSS as wire proxy | Reuters/AP behind Cloudflare; Google RSS reliable + has `<source>` tags |
| FIRMS 4-satellite fusion | Redundancy + 375m resolution catches smaller fires |
| Seismic depth <5km flag | Natural quakes are deep; shallow events near known targets = likely strike |
| 50km/30min correlation window | Balances false positives vs detection — fire and seismic data have latency |
| NordVPN proxy for Oref | Oref API geo-blocked outside Israel; IL proxy server resolves |
| Own aircraft API (not OpenSky) | OpenSky has no CORS headers; own API adds airline/type/military flag enrichment |
| Static fleet positions | No live AIS API with CORS; OSINT-sourced positions updated manually |
| Embedded TLEs for satellites | CelesTrak has no CORS; TLE data changes slowly, embed + SGP4 in-browser |

---

## 5. Lessons Learned

1. **Never interpret visual data without baselines** — Tanker clusters at Fujairah look alarming but are normal (world's largest bunkering zone)
2. **Corroboration needs sticky confirmation** — Sliding windows cause confirmed stories to regress; stamp once confirmed
3. **Hebrew + English topic normalization required** — "חמינאי חוסל" and "khamenei killed" must map to same canonical key
4. **Source lists must include all configured sources** — TASS was configured but not in CREDIBLE_SOURCES, silently dropped
5. **Evaluate state BEFORE composing messages** — Threat level was stale because evaluation ran after send
6. **Never say "all clear" in alert systems** — Only official authorities can declare safety

---

## 6. Source Credibility Tiers

| Tier | Sources | Weight |
|------|---------|--------|
| **Official** | IDF Spokesman, Pikud HaOref, IRGC official | 3x |
| **Wire Service** | Reuters, AP, TASS | 2.5x |
| **Established OSINT** | sentdefender, Intel_Sky, Aurora_Intel | 2x |
| **Aggregator** | warmonitors, intelslava, liveuamap | 1.5x |
| **Unverified** | Single-source, no corroboration | 1x |

Breaking news requires 3+ credible sources (weighted) for confirmation.

---

## 7. File Structure

```
iran-israel-alerts/
├── config.json                 # Channel lists, API keys, output config
├── ctl.sh                      # Master control script (start/stop/status)
├── scripts/
│   ├── realtime-watcher.sh     # Main daemon (~1500 lines)
│   ├── dispatch.py             # Multi-output alert router
│   ├── scan-osint.py           # Telegram + Twitter + RSS scanner
│   ├── scan-fires.py           # NASA FIRMS thermal detection
│   ├── scan-seismic.py         # USGS earthquake monitor
│   ├── scan-blackout.py        # Iran internet blackout detection
│   ├── scan-military-flights.py # US military ADS-B tracking
│   ├── scan_cyber.py           # Cyber warfare monitor
│   ├── scan_strikes.py         # Strikes data aggregator
│   ├── correlate-strikes.py    # Fire+seismic strike correlation
│   ├── generate-summary.py     # Bilingual analyst summaries
│   ├── generate-fire-map.py    # Satellite intel map
│   ├── generate-flight-map.py  # Air traffic intel map
│   ├── generate-strikes-map.py # Cartopy strikes visualization
│   ├── pinned-status.py        # Live Telegram status message
│   ├── hourly-report.sh        # Scheduled report pipeline
│   ├── v2-dashboard.html       # CENTCOM Theater Ops dashboard
│   ├── v2-data.js              # Static military/infra asset data
│   └── build-standalone.py     # Dashboard build script
├── docs/
│   ├── centcom.html            # Deployed dashboard (GitHub Pages)
│   ├── index.html              # Root redirect → centcom
│   └── hormuz.html             # Hormuz crisis dashboard
└── state/                      # Runtime state files
    ├── osint-rss-seen.json     # RSS dedup state
    └── watcher-threat-level.txt # Current threat level
```

---

*Last updated: March 9, 2026*
*System: Magen Yehuda Intel v2 — CENTCOM Theater Operations*
