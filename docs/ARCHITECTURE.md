# ARCHITECTURE.md — Magen Yehuda Intelligence Platform

> **Full system architecture.** Read this before making infrastructure or design decisions.
> For dashboard-specific UI/component changes, see [OPENSPEC.md](OPENSPEC.md).

---

## System Overview

Real-time OSINT intelligence platform monitoring the Iran-Israel conflict. Collects data from 85+ sources, classifies threats with LLM, stores in Azure, dispatches alerts to Telegram, and serves an interactive dashboard via GitHub Pages.

```
┌─ DATA SOURCES ─────────────────────────────────────────────────┐
│  Pikud HaOref (sirens) · 12 Telegram channels · 13 Twitter    │
│  7 RSS feeds · USGS seismic · NASA FIRMS fires · FR24 flights │
│  ACLED conflict · MarineTraffic AIS · Cyber RSS/TG/Twitter     │
└────────────────────────────────┬───────────────────────────────┘
                                 │
┌─ COLLECTION (Mac) ─────────────┼───────────────────────────────┐
│                                ▼                               │
│  realtime-watcher.sh (main daemon, PID in state/watcher.pid)   │
│  ├── check_oref()         → Oref JSON every 10-30s            │
│  ├── check_osint()        → scan-osint.py (TG+Twitter+RSS)    │
│  ├── check_fires_seismic()→ scan-fires.py + scan-seismic.py   │
│  ├── check_military_flights() → scan-military-flights.py      │
│  ├── check_cyber()        → scan_cyber.py                     │
│  ├── check_strikes()      → scan_strikes.py (ACLED)           │
│  ├── check_blackout()     → scan-blackout.py                  │
│  ├── check_polymarket()   → Polymarket API                    │
│  └── check_strike_correlation() → correlate-strikes.py        │
│                                                                │
│  Threat Level System (adaptive polling):                       │
│  🟢 GREEN (30s/5m) → 🟡 ELEVATED (15s/2m) →                  │
│  🔴 HIGH (10s/60s) → ⚫ CRITICAL (10s/30s)                    │
│                                                                │
│  Cron Jobs:                                                    │
│  */5  * * * * → export-feed.py (intel-feed.json + git push)   │
│  */2  * * * * → fetch-fr24.sh (FR24 cache + git push)         │
│  0    * * * * → hourly-report.sh                               │
│  0    * * * * → enrich-intel.py --hours 2 (LLM enrichment)    │
│  0    * * * * → hormuz collect-and-push.sh (AIS scraper)       │
└────────────────────────────────┬───────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
┌─ PROCESSING ──────┐ ┌─ DISPATCH ──────┐ ┌─ PUSH TO CLOUD ────┐
│                    │ │                  │ │                     │
│ classify-attack.py │ │ dispatch.py      │ │ push-to-api.sh     │
│ (Azure OpenAI      │ │ (routes events   │ │ (POST /api/push/*) │
│  gpt-5-mini)       │ │  to Telegram)    │ │                     │
│                    │ │                  │ │ log-intel.py        │
│ enrich-intel.py    │ │ Channels:        │ │ (→ JSONL + Table   │
│ (batch enrichment, │ │ @magenyehuda-    │ │    Storage via      │
│  hourly cron)      │ │  updates (EN)    │ │    db.py)           │
│                    │ │ @opssheagathaar- │ │                     │
│ write-live-event.py│ │  iupdates (HE)   │ │ export-feed.py      │
│ (missile arcs →    │ │                  │ │ (→ intel-feed.json  │
│  live-events.json  │ │ Rules per output:│ │    + git push)      │
│  + git push)       │ │ language, content│ │                     │
│                    │ │ severity, images │ │ git push (GitHub    │
│ correlate-strikes  │ │                  │ │  Pages auto-deploy) │
│ (multi-source)     │ │                  │ │                     │
└────────────────────┘ └──────────────────┘ └─────────────────────┘
                                 │
┌─ AZURE (eastus) ───────────────┼───────────────────────────────┐
│                                ▼                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Container App: magen-yehuda-api (v21)                  │   │
│  │  Image: magenyehudacr.azurecr.io/magen-yehuda-api:v21   │   │
│  │  Spec: 0.5 vCPU, 1 GiB, minReplicas=1 (always-on)     │   │
│  │  Est. cost: ~$39/mo (Consumption plan)                  │   │
│  │                                                         │   │
│  │  Flask app (app.py + db.py — committed in api/)         │   │
│  │                                                         │   │
│  │  ACTIVE POLLERS (background threads):                   │   │
│  │  ├── Oref poller      (every ~5s)   → in-memory cache   │   │
│  │  ├── Aircraft poller  (every ~60s)  → in-memory cache   │   │
│  │  ├── Fires poller     (every ~4min) → in-memory cache   │   │
│  │  └── Seismic poller   (every ~70s)  → in-memory cache   │   │
│  │                                                         │   │
│  │  READ ENDPOINTS:                                        │   │
│  │  GET /              → service info (version 2.0)        │   │
│  │  GET /api/health    → poller health + cache ages        │   │
│  │  GET /api/oref      → cached siren data                 │   │
│  │  GET /api/threat    → last threat level                 │   │
│  │  GET /api/intel-feed→ recent events from Table Storage  │   │
│  │  GET /api/aircraft  → cached flight data                │   │
│  │  GET /api/fires     → cached FIRMS fire data            │   │
│  │  GET /api/seismic   → cached USGS quake data            │   │
│  │                                                         │   │
│  │  WRITE ENDPOINTS (API-key protected):                   │   │
│  │  POST /api/push/oref   → Mac pushes siren data         │   │
│  │  POST /api/push/threat → Mac pushes threat level        │   │
│  │  POST /api/push/intel  → Mac pushes intel events        │   │
│  │                                                         │   │
│  │  API Key: myi-fcf15b5484f76e9b (X-API-Key header)      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Azure Table Storage: magenyehudadata                   │   │
│  │  Auth: Entra ID (DefaultAzureCredential)                │   │
│  │  Public network: Enabled (required for Mac writes)      │   │
│  │  Shared key: Blocked by Azure Policy                    │   │
│  │                                                         │   │
│  │  Tables:                                                │   │
│  │  ├── intelevents   — OSINT events (PK=date, RK=hash)   │   │
│  │  ├── orefalerts    — Pikud HaOref siren history         │   │
│  │  ├── fireevents    — NASA FIRMS fire detections         │   │
│  │  └── seismicevents — USGS earthquake data               │   │
│  │                                                         │   │
│  │  Roles:                                                 │   │
│  │  ├── User (a3f48807): Storage Table Data Contributor    │   │
│  │  └── MI (f77d0c16):  Storage Table Data Contributor     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Azure OpenAI: openai-dev-nt6mukageprxm                 │   │
│  │  Deployment: gpt-5-mini (2025-01-01-preview)            │   │
│  │  Auth: Entra ID (cognitiveservices.azure.com)           │   │
│  │  Used by: classify-attack.py, enrich-intel.py           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Azure Container Registry: magenyehudacr (Basic, ~$5/mo)│   │
│  │  Image: magen-yehuda-api:v21 (latest)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  Subscription: ME-MngEnvMCAP356394-idanshimon-1               │
│  Resource Group: magen-yehuda-intel                            │
│  Region: eastus                                                │
│  Est. total Azure cost: ~$44/mo (covered by MSFT dev credits) │
└────────────────────────────────────────────────────────────────┘

┌─ PRESENTATION ─────────────────────────────────────────────────┐
│                                                                │
│  GitHub Pages: magen-yehuda-intel.github.io/magen-yehuda-bot/ │
│  Repo: github.com/magen-yehuda-intel/magen-yehuda-bot         │
│                                                                │
│  Static Files (auto-deployed on git push):                     │
│  ├── index.html          — Main dashboard (copy of centcom)    │
│  ├── centcom.html        — Canonical dashboard source (~189KB) │
│  ├── v2-data.js          — Required data blob (33KB) ⚠️       │
│  ├── live-events.json    — Missile arc events (written by Mac) │
│  ├── intel-feed.json     — OSINT feed (exported every 5min)    │
│  ├── fr24-cache.json     — Flight data (exported every 2min)   │
│  ├── energy-feed.json    — Energy infrastructure events        │
│  ├── oref-alerts.json    — Siren data backup                   │
│  ├── oref-history.json   — Historical siren data               │
│  ├── hormuz.html         — Hormuz shipping tracker             │
│  ├── hormuz-metrics.jsonl— Hourly AIS shipping snapshots       │
│  ├── data/iran-infrastructure.json — 108 infrastructure sites  │
│  ├── data/hormuz-timeline.json — Ship attack timeline          │
│  ├── sw.js + manifest.json — PWA support                       │
│  └── v2/index.html       — Redirect (prevents broken links)    │
│                                                                │
│  Telegram Channels:                                            │
│  ├── @magenyehudaupdates       — English, all content          │
│  └── @opssheagathaariupdates   — Hebrew, high_only images      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Inventory

### Mac (Local Machine)

| Component | Type | Schedule | Description |
|-----------|------|----------|-------------|
| `realtime-watcher.sh` | Daemon | Always-on | Main daemon — polls all sources, manages threat level, triggers dispatch |
| `scan-osint.py` | Script | Called by watcher | Unified OSINT scanner: 12 TG channels + 13 Twitter + 7 RSS + USGS |
| `scan-fires.py` | Script | Called by watcher | NASA FIRMS fire detection |
| `scan-seismic.py` | Script | Called by watcher | USGS earthquake data |
| `scan-military-flights.py` | Script | Called by watcher | OpenSky/FR24 military flight tracking |
| `scan_cyber.py` | Script | Called by watcher | Cyber threat monitoring (RSS + TG + Twitter) |
| `scan_strikes.py` | Script | Called by watcher | ACLED conflict event data |
| `scan-blackout.py` | Script | Called by watcher | Internet blackout detection |
| `scan-naval.py` | Script | Called by watcher | Naval vessel tracking |
| `classify-attack.py` | Script | On siren trigger | LLM classification of attack source/weapon (→ Azure OpenAI) |
| `write-live-event.py` | Script | On classification | Writes missile arc events to `live-events.json` + git push |
| `correlate-strikes.py` | Script | Called by watcher | Multi-source strike correlation |
| `dispatch.py` | Module | Called by watcher | Routes formatted alerts to Telegram channels (EN + HE) |
| `log-intel.py` | Script | Called by watcher | Appends events to JSONL + Azure Table Storage via `db.py` |
| `db.py` | Module | Shared library | Azure Table Storage client (Entra ID or connection string) |
| `export-feed.py` | Cron | Every 5 min | Exports `intel-feed.json` from JSONL, geocodes, git pushes |
| `fetch-fr24.sh` | Cron | Every 2 min | Fetches FR24 flight cache, git pushes |
| `enrich-intel.py` | Cron | Hourly | Batch LLM enrichment of unenriched events (→ Azure OpenAI) |
| `hourly-report.sh` | Cron | Hourly | Generates hourly summary report |
| `energy-tracker.py` | Script | Called by cron | Energy infrastructure event tracking |
| `pinned-status.py` | Script | Manual | Updates pinned status messages in Telegram channels |
| `generate-summary.py` | Script | Manual | Generates text summaries from intel data |
| `generate-dashboard-snapshot.py` | Script | Manual | Captures dashboard screenshot for Telegram |
| `generate-fire-map.py` | Script | Manual | Generates fire map image |
| `generate-flight-map.py` | Script | Manual | Generates military flight map image |
| `generate-strikes-map.py` | Script | Manual | Generates strike correlation map |
| `generate-timelapse.py` | Script | Manual | Creates timelapse GIF from snapshots |
| `build-standalone.py` | Script | Manual | Builds standalone dashboard HTML |
| `env-config.py` | Script | Docker only | Generates config.json from environment variables |
| `scrape-hormuz-timeline.py` | Script | Manual/TODO cron | Scrapes Wikipedia ship attack data for Hormuz timeline |
| `push-to-api.sh` | Script | Called by watcher | Pushes data to Azure Container App API |
| `ctl.sh` | CLI | Manual | Master control: start/stop/status/dashboard/post/teardown/rotate |

### Azure Container App (magen-yehuda-api)

| Component | Type | Description |
|-----------|------|-------------|
| Oref Poller | Background thread | Polls `oref.org.il/WarningMessages/alert/alerts.json` every ~5s |
| Aircraft Poller | Background thread | Polls flight data every ~60s |
| Fires Poller | Background thread | Polls NASA FIRMS every ~4min |
| Seismic Poller | Background thread | Polls USGS every ~70s |
| `GET /api/oref` | Endpoint | Returns cached siren data |
| `GET /api/threat` | Endpoint | Returns last threat level (pushed by Mac) |
| `GET /api/intel-feed` | Endpoint | Returns recent events from Table Storage (83 events) |
| `GET /api/aircraft` | Endpoint | Returns cached flight data |
| `GET /api/fires` | Endpoint | Returns cached fire data (2,981 fires) |
| `GET /api/seismic` | Endpoint | Returns cached seismic data (39 quakes) |
| `GET /api/health` | Endpoint | Returns poller health + cache ages |
| `POST /api/push/oref` | Endpoint | Receives siren data from Mac (API-key protected) |
| `POST /api/push/threat` | Endpoint | Receives threat level from Mac (API-key protected) |
| `POST /api/push/intel` | Endpoint | Receives intel events from Mac (API-key protected) |

> ✅ The Flask app code (`app.py` + `db.py`) is committed in the `api/` directory (extracted from Docker image v21 on 2026-03-21).

### GitHub Pages (Dashboard)

| File | Size | Role | Update Method |
|------|------|------|---------------|
| `index.html` | ~189KB | Production dashboard | Copy of centcom.html |
| `centcom.html` | ~189KB | Canonical dashboard source | Manual edit |
| `v2-data.js` | 33KB | Static data blob (bases, assets, events) | Manual ⚠️ DO NOT DELETE |
| `live-events.json` | Variable | Missile arc events | `write-live-event.py` + git push |
| `intel-feed.json` | Variable | OSINT event feed | `export-feed.py` (every 5min) |
| `fr24-cache.json` | Variable | Flight data cache | `fetch-fr24.sh` (every 2min) |
| `energy-feed.json` | Variable | Energy events | `energy-tracker.py` |
| `hormuz.html` | ~50KB | Hormuz shipping tracker | Manual edit |
| `hormuz-metrics.jsonl` | Growing | Hourly AIS snapshots | `collect-and-push.sh` (hourly) |
| `data/iran-infrastructure.json` | ~30KB | 108 infrastructure sites | Manual |
| `data/hormuz-timeline.json` | ~10KB | Ship attack timeline | `scrape-hormuz-timeline.py` |

### Telegram Channels

| Channel | ID | Language | Content | Images |
|---------|-----|----------|---------|--------|
| `@magenyehudaupdates` | — | English | All | All |
| `@opssheagathaariupdates` | — | Hebrew | All (excl. `summary_en`) | high_only |

---

## Data Flow Diagrams

### Siren Alert Flow
```
Oref API (oref.org.il)
    │
    ├──→ Mac watcher (check_oref, 10-30s based on threat level)
    │    ├── evaluate_threat_level() → adjust polling intervals
    │    ├── emit_alert() → dispatch.py → Telegram channels
    │    ├── classify-attack.py → Azure OpenAI gpt-5-mini
    │    │   └── write-live-event.py → live-events.json → git push
    │    ├── log-intel.py → JSONL + Azure Table (orefalerts)
    │    └── push-to-api.sh → POST /api/push/oref
    │
    └──→ Container App Oref poller (~5s)
         └── in-memory cache → GET /api/oref → Dashboard
```

### OSINT Event Flow
```
Sources (TG channels, Twitter, RSS, USGS)
    │
    └──→ Mac watcher → scan-osint.py
         ├── log-intel.py → state/intel-log.jsonl + Azure Table (intelevents)
         ├── dispatch.py → Telegram channels (if severity meets threshold)
         └── (every 5min via cron) export-feed.py
              ├── geocode events (LOC_MAP, longest keyword match)
              ├── write docs/intel-feed.json
              └── git push → GitHub Pages
                   └── Dashboard fetches intel-feed.json
```

### Dashboard Data Flow
```
Dashboard (centcom.html in browser)
    │
    ├── On load:
    │   ├── v2-data.js (static bases, assets, coordinates)
    │   ├── Embedded _liveEvents (inline, for missile arcs)
    │   └── data/iran-infrastructure.json (fetch)
    │
    ├── Polling:
    │   ├── /api/oref (every 15s → siren banner)
    │   ├── /api/intel-feed (→ live feed panel, merged with static)
    │   ├── /api/aircraft (→ flight markers)
    │   ├── /api/fires (→ fire markers)
    │   ├── /api/seismic (→ earthquake markers)
    │   ├── live-events.json (every 30s → missile arcs)
    │   └── intel-feed.json (static, merged with API)
    │
    └── fr24-cache.json (static flight data backup)
```

---

## State Files (Mac)

| File | Purpose |
|------|---------|
| `state/watcher.pid` | Watcher daemon PID |
| `state/watcher.log` | Main watcher log |
| `state/watcher-threat-level.txt` | Current threat level (persists across restarts) |
| `state/watcher-oref-last.txt` | Last Oref alert data (dedup) |
| `state/intel-log.jsonl` | All OSINT events (append-only, primary local store) |
| `state/enriched-intel.jsonl` | LLM-enriched events |
| `state/enriched-ids.json` | Set of already-enriched event IDs |
| `state/dispatch-log.jsonl` | Telegram dispatch history |
| `state/flight-history.jsonl` | Military flight tracking history |
| `state/osint-telegram-seen.json` | Dedup state for Telegram OSINT |
| `state/osint-twitter-seen.json` | Dedup state for Twitter OSINT |
| `state/osint-rss-seen.json` | Dedup state for RSS OSINT |
| `state/firms-seen.json` | Dedup state for FIRMS fires |
| `state/seismic-seen.json` | Dedup state for USGS seismic |
| `state/cyber-*-seen.json` | Dedup state for cyber sources |
| `state/breaking-corroboration.json` | Breaking news corroboration tracker |
| `state/oref-alert-tmp.json` | Temporary Oref alert data |
| `state/strike-correlations.json` | Multi-source strike correlation data |
| `state/blackout-state.json` | Internet blackout detection state |

---

## Configuration

### config.json (Mac)
```
timezone, telegram_bot_token, telegram_chat_id, telegram_channel_name,
oref_poll_interval, polymarket_poll_interval, polymarket_spike_threshold,
twitter_poll_interval, twitter_accounts, twitter_keywords,
telegram_osint_channels, rss_feeds, osint_keywords, usgs_seismic,
outputs (channel routing rules), cyber, strikes, dashboard, blackout_enabled
```

### Secrets (Mac — `secrets/`)
| File | Purpose |
|------|---------|
| `nordvpn-auth.txt` | NordVPN proxy credentials (for Oref if needed) |
| `acled-creds.txt` | ACLED conflict data API credentials |
| `azure-table-conn.txt` | Azure Table Storage connection string (fallback) |
| `firms-map-key.txt` | NASA FIRMS API key |
| `il66.ovpn` | NordVPN Israel server config |

### Environment Variables (Container App)
- Azure OpenAI credentials (Entra ID managed identity)
- Table Storage access (managed identity)
- API key for push endpoints

---

## Redundancy & Overlap

### Dual Data Paths (by design)
The system has intentional redundancy — data reaches the dashboard via two paths:

1. **Static files (git push):** Mac → export-feed.py → intel-feed.json → GitHub Pages → Dashboard
2. **Live API:** Mac → push-to-api.sh → Container App → `/api/intel-feed` → Dashboard

The dashboard merges both sources and deduplicates. If the API is down, static files still work. If git push fails, the API still serves live data.

### Duplicate Pollers
Both the Mac watcher AND the Container App poll some of the same sources:

| Source | Mac Watcher | Container App |
|--------|:-----------:|:-------------:|
| Oref (sirens) | ✅ | ✅ |
| Flights (FR24/OpenSky) | ✅ | ✅ |
| Fires (FIRMS) | ✅ | ✅ |
| Seismic (USGS) | ✅ | ✅ |
| OSINT (TG/Twitter/RSS) | ✅ | ❌ |
| LLM classify/enrich | ✅ | ❌ |
| Telegram dispatch | ✅ | ❌ |
| DB writes | ✅ | ❌ (reads only) |

The Container App's pollers serve as a **hot cache for the API** — the dashboard gets fast responses without hitting external APIs. The Mac watcher does the heavy lifting (OSINT, LLM, dispatch, DB writes).

---

## Project Directory Structure

```
iran-israel-alerts/
├── api/                    # Azure Container App Flask API (extracted from Docker image)
│   ├── app.py              # Flask app — pollers, REST endpoints, push API
│   └── db.py               # Azure Table Storage client (Entra ID auth)
├── scripts/                # All collection, processing, and dispatch scripts
│   ├── realtime-watcher.sh # Main daemon — orchestrates all polling
│   ├── ctl.sh              # Master control CLI (start/stop/status)
│   ├── dispatch.py         # Multi-output Telegram alert router
│   ├── scan-osint.py       # Unified OSINT scanner (TG+Twitter+RSS)
│   ├── scan-fires.py       # NASA FIRMS satellite fire detection
│   ├── scan-seismic.py     # USGS earthquake monitoring
│   ├── scan-military-flights.py  # OpenSky/FR24 flight tracking
│   ├── scan_cyber.py       # Cyber threat monitoring
│   ├── scan_strikes.py     # ACLED conflict event data
│   ├── scan-blackout.py    # Internet blackout detection
│   ├── scan-naval.py       # Naval vessel tracking
│   ├── classify-attack.py  # LLM attack classification (→ Azure OpenAI)
│   ├── write-live-event.py # Writes missile arc events → live-events.json
│   ├── correlate-strikes.py# Multi-source strike correlation
│   ├── db.py               # Azure Table Storage client (shared with api/)
│   ├── log-intel.py        # Event logger → JSONL + Azure Table
│   ├── export-feed.py      # JSONL → intel-feed.json + git push (5min cron)
│   ├── enrich-intel.py     # Batch LLM enrichment (hourly cron)
│   ├── energy-tracker.py   # Energy infrastructure event tracking
│   ├── fetch-fr24.sh       # FR24 flight cache (2min cron)
│   ├── hourly-report.sh    # Hourly status report to Telegram
│   ├── hourly-brief.sh     # Story-style hourly brief
│   ├── push-to-api.sh      # Push data to Azure Container App
│   ├── pinned-status.py    # Telegram pinned status message updater
│   ├── generate-*.py       # Map/summary/timelapse generators
│   ├── format-*.py         # Message formatters (fires, osint, seismic)
│   ├── build-standalone.py # Standalone dashboard HTML builder
│   └── *.html, *.js        # Dashboard reference files used by scripts
├── docs/                   # GitHub Pages root + project documentation
│   ├── index.html          # Production dashboard (= centcom.html)
│   ├── centcom.html        # Canonical dashboard source (~189KB)
│   ├── hormuz.html         # Strait of Hormuz shipping tracker
│   ├── v2-data.js          # Required static data blob (33KB) ⚠️ DO NOT DELETE
│   ├── *.json              # Live data feeds (intel, fires, oref, fr24, energy)
│   ├── data/               # Static assets (infrastructure, timeline)
│   ├── icons/              # PWA icons
│   ├── v2/                 # Redirect for old V2 links
│   ├── ARCHITECTURE.md     # This file
│   ├── OPENSPEC.md         # Dashboard UI specification
│   ├── TROUBLESHOOTING.md  # Debugging guide
│   └── INTELLIGENCE_METHODOLOGY.md
├── references/             # Historical plans, design notes, source docs
├── tests/                  # Dashboard test pages and scripts
├── state/                  # Runtime state files (gitignored)
├── secrets/                # API keys and credentials (gitignored)
├── logs/                   # Watcher logs (gitignored)
├── config.json             # Runtime config (gitignored)
├── config.example.json     # Config template
├── Dockerfile              # Container App image build
├── docker-compose.yml      # Local Docker dev setup
├── requirements.txt        # Python dependencies
├── SKILL.md                # OpenClaw skill definition
├── README.md               # Project overview
└── CHANGELOG.md            # Release notes
```

---

## Known Issues & Tech Debt

> **Note:** `scripts/marker-icons.js` and `scripts/v2-data.js` are dashboard assets mixed with shell/Python scripts. They're used by generated HTML dashboards in the same directory. Not ideal but functional.

1. **~~Flask app.py not in repo~~** — ✅ RESOLVED. Flask API code (`app.py` + `db.py`) extracted from Docker image v21 and committed in `api/`. (2026-03-21)
2. **Python SDK hangs** — `azure-data-tables` SDK hangs on query (curl works fine). Likely version issue with Python 3.14.
3. **Shared key blocked** — Azure Policy prevents shared key access. Only Entra ID auth works.
4. **Public network on storage** — Had to enable public network access for Mac DB writes. Ideally would be private.
5. **Watcher log path mismatch** — `ctl.sh status` checks wrong log path (timestamped logs vs `state/watcher.log`).
6. **Dashboard script dies at ~line 3470-3536** — Silent runtime failure in late init block. Root cause unknown.
7. **classify-attack.py chain not firing** — During active siren waves, the classify → write-live-event pipeline doesn't always trigger.
8. **Azure Table auth token expiry** — Tokens expire silently; `export-feed.py` DB sync fails with `AuthorizationFailure`.
9. **Duplicate watcher PIDs** — Occasionally spawns duplicate watchers that must be manually killed.
10. **No monitoring/alerting** — If the Mac watcher dies, nothing alerts. No health check for the watcher process. *(Documented, accepted for now. See Troubleshooting for mitigation options.)*

---

## Cost Summary (Current)

| Resource | Monthly Cost |
|----------|-------------|
| Container App (0.5 vCPU, 1 GiB, always-on) | ~$39 |
| ACR (Basic) | ~$5 |
| Table Storage | ~$0.10 |
| Azure OpenAI (gpt-5-mini, light usage) | ~$1-5 |
| GitHub Pages | $0 |
| Mac (electricity) | $0 |
| **Total** | **~$45-50/mo** |
| **MSFT dev credits** | **$150/mo** |
| **Out of pocket** | **$0** |

---

_Last updated: 2026-03-21. Update this doc when architecture changes._
