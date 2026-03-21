# OPENSPEC — Magen Yehuda CentCom Dashboard

> **Source of truth for all dashboard changes.** Read this BEFORE modifying `centcom.html` or `index.html`.
> Both files must stay in sync (index.html = copy of centcom.html).

## File Map
| File | Role |
|------|------|
| `index.html` | Production dashboard (GitHub Pages root) — copy of centcom.html |
| `centcom.html` | Working copy / canonical source |
| `v2-archive.html` | Archived old V2 intel dashboard (5.3MB, do NOT restore) |
| `v2-data.js` | Required data blob (33KB) — RECENT_EVENTS, base/asset data. **DO NOT DELETE** |
| `live-events.json` | Live missile events for arc animation. Written by `write-live-event.py` during attacks |
| `hormuz.html` | Strait of Hormuz shipping tracker dashboard |
| `hormuz-metrics.jsonl` | Hourly AIS shipping snapshots for Hormuz dashboard |
| `intel-feed.json` | Exported OSINT feed (geocoded events from intel-log.jsonl) |
| `sw.js` | Service worker (PWA offline support) |
| `manifest.json` | PWA manifest |

## Architecture
- **Single-file HTML** (~189KB, 3700 lines) — all CSS, JS, and inline data
- **Leaflet.js** map with CARTO dark basemap + VIIRS night lights toggle
- **Data source:** `v2-data.js` (static) + API (`magen-yehuda-api` Azure Container App) + `live-events.json`
- **API URL:** `https://magen-yehuda-api.blackfield-628213bb.eastus.azurecontainerapps.io`

## UI Layout

### Title Bar
- "U.S. & ISRAEL vs. IRAN" with flag emojis
- Map/VIIRS toggle buttons (top right)

### Pikud HaOref Banner (top left)
- Live connection indicator (green dot)
- Status: "All Clear" (green) / "ACTIVE SIREN" (red pulsing)
- Last siren timestamp
- Click to open **Siren History** popup (scrollable, shows waves with severity)
- Polls `/api/oref` every 15s

### Left Toolbar (desktop — vertical icon strip)
Clickable toggle buttons with tooltips:
| Icon | Layer | Color |
|------|-------|-------|
| ☰ | Sidebar toggle | — |
| 🗺 | Borders/Boundaries | blue |
| ⭐ | Military Bases | cyan |
| 🏗 | Infrastructure | amber |
| ✈️ | Aircraft/Flights | blue |
| 🚢 | Ships/Naval | blue |
| 🛡 | SAM/AD Sites | green |
| ↻ | Patrol Routes (desktop only) | purple |
| 🌊 | Waterways | cyan |
| 🚨 | Sirens (Oref) | red |
| 🔥 | Fires (FIRMS) | orange |
| 📌 | OSINT Events | red |
| 🚀 | Missile Animations | red |
| Strike window dropdown | 1h/4h/24h/48h/ALL | — |
| 📋 | Legend | — |
| 🌗 | Basemap toggle (Carto/VIIRS) | — |
| 📍 | Geolocate | — |

### Mobile Toolbar (bottom horizontal bar)
Same icons as desktop, horizontally scrollable. Tabs at bottom:
- LAYERS | BASES | FEED | FIRES | OSINT | LEGEND

### Sidebar (desktop left, toggleable)
Grouped layer controls with dot indicators and counts:
- **Borders:** Borders, Buffer Zones, Exclusion Zones
- **U.S. Military:** Bases (29), Carrier Groups, Patrol Routes, Aircraft
- **Israel:** IDF Bases (14), Iron Dome (12), David's Sling (7), Arrow (4), Naval
- **Iran:** IRGC Bases, Nuclear Sites, Missile Sites (52), Naval, Air Defense, Airbases, Energy, SAM
- **Ships:** CSG vessels, Submarines
- **Proxy Forces:** Hezbollah, Houthi, Iraqi PMF
- **Live Data:** NASA FIRMS Fires, OSINT Events, Siren Alerts, Strike Events

### Live Feed Panel (right side)
- Real-time OSINT event feed
- Filterable by time (15m/1h/4h/24h/48h/ALL) and source (ALL/Iran/Israel/Proxy)
- Color-coded event cards with source, timestamp, flag
- Event count in header

### Missile Arc Animation System
- **3-mode cycle:** OFF → PATHS (static dotted arcs, blue glow) → ANIMATED (full rocket animation, red glow) → OFF
- **Data source:** `live-events.json` (polled every 30s via `fetchLiveEvents()`)
- **Trigger:** Events with `origin_lat`, `origin_lon`, `lat`, `lon` fields
- **TTL:** Events expire after 2 hours (`nowTs - e.ts < 7200`) — both embedded and fetched
- **Default mode:** `animated` (first-time visitors see full animation)
- **Auto-force:** Fresh critical live events force `animated` mode + write to localStorage
- **Cleanup:** When no fresh events exist, stale arc SVG is removed from map
- **Visual:** SVG bezier arcs from origin to target, animated rocket emoji traveling along path
- **Effects:** Pulsing origin dot, impact ripples at target, progressive trail
- **Cycle:** 8s per loop, staggered start per arc
- **Toggle:** 🚀 button in toolbar, persisted in localStorage (`missileMode` — replaces legacy `missileAnim`)
- **Functions:** `fetchLiveEvents()` → `renderMissileArcs()` → `startArcAnimation()` / `setStaticArcs()`
- **Test utilities:** `window._test.demo()` / `window._test.demoOff()` (console only, 3 demo arcs)
- **Origin coords in `write-live-event.py`:** Iran(33.5,48.5), Yemen(15.35,44.2), Lebanon(33.85,35.86), Iraq(33.3,44.4), Syria(33.5,36.3), Gaza(31.42,34.35)

### Legend Overlay
- Toggleable overlay explaining all map symbols, colors, and severity levels

### Siren History Popup
- Fixed position overlay showing past siren waves
- Each wave: title, severity badge, timestamp, affected areas
- Waves merged when updates arrive within same alert cycle

## Map Layers Detail
- **CARTO dark** basemap (default) / **VIIRS** night lights
- **Marker clustering** with custom colored cluster icons per category
- **Iran glow effect:** Red radial gradient over Iran territory
- **Strike events:** Color by actor, shape by type, size by fatalities (from ACLED + FIRMS + seismic)
- **Ship markers:** Real naval positions with vessel type icons
- **Patrol routes:** Animated dashed polylines

## Key Functions
| Function | Purpose |
|----------|---------|
| `fetchLiveEvents()` | Polls live-events.json, triggers missile arcs |
| `renderMissileArcs()` | Creates SVG overlay with bezier arcs |
| `startArcAnimation()` | Animates rockets along arc paths (8s cycle) |
| `updateArcPositions()` | Repositions arcs on map move/zoom |
| `pollOref()` | Fetches siren data from API every 15s |
| `renderStrikeEvents()` | Renders ACLED/FIRMS strike markers |
| `fetchLiveFeed()` | Loads OSINT events into right panel |
| `isolateIranLayer(key)` | Solo-view a specific Iran infrastructure layer |
| `mtToggle(layer, el)` | Mobile toolbar layer toggle |
| `toggleSidebar()` | Show/hide desktop sidebar |
| `setBasemap(name)` | Switch between CARTO dark and VIIRS |

## Data Dependencies
- `v2-data.js` — **REQUIRED** (inline data: bases, assets, recent events, coordinates) — **DO NOT DELETE**
- `live-events.json` — missile arc events (written by watcher during attacks)
- `intel-feed.json` — OSINT event feed for live feed panel (exported by `export-feed.py`)
- `hormuz-metrics.jsonl` — Strait of Hormuz shipping tracker data (hourly AIS snapshots)
- `iran-infrastructure.json` — (in `data/`) Iranian critical infrastructure: power, water, telecom, transport, industrial
- API `/api/oref` — live siren data
- API `/api/intel-feed` — real-time OSINT event feed (merged with static `intel-feed.json`)
- API `/api/threat` — current threat level

## Pipeline Scripts
| Script | Purpose |
|--------|---------|
| `export-feed.py` | Exports `intel-feed.json` from `intel-log.jsonl`; geocodes events via `LOC_MAP` (longest keyword match) |
| `write-live-event.py` | Writes missile arc events to `live-events.json` + auto git-push |
| `classify-attack.py` | Classifies Oref siren waves → triggers `write-live-event.py` |
| `realtime-watcher.sh` | Main daemon: polls Oref, OSINT, fires, seismic, cyber, aircraft |
| `scan-osint.py` | Unified OSINT scanner (12 TG + 13 Twitter + 7 RSS + USGS) |
| `hormuz-tracker.py` | Browser-based MarineTraffic AIS scraper for Hormuz shipping |
| `dispatch.py` | Multi-output alert router to Telegram channels |
| `log-intel.py` | Appends structured events to JSONL + Azure Table DB |

## GPS Jamming Layer
- **NOT live data** — 9 hardcoded zones from EUROCONTROL/OPSGROUP reports
- Zones: Eastern Mediterranean, Northern Iraq, Strait of Hormuz, Tehran, Isfahan/Natanz, Bushehr, Yemen/Bab el-Mandeb, Eastern Libya, Sinai/Suez
- Severity levels: high (red pulse), medium (orange), low (yellow)
- Links to gpsjam.org for live reference
- Source data: ADS-B Exchange NACp (aircraft GPS accuracy) — no public API available

## Infrastructure Layer (🏗)
- **Status:** Button exists, NO render function or data wired yet
- **Planned categories:** Power Plants (⚡), Water (💧), Telecom/IT (📡), Transport (🚢), Industrial (🏭)
- **Existing energy data:** `IRAN_ENERGY` (39 entries) + `GULF_ENERGY` in `v2-data.js` — oil/gas/refinery/petrochemical
- **New data:** `data/iran-infrastructure.json` — power plants, water, telecom, transport, industrial (~70 entries)
- **Planned mode:** OFF → All Infrastructure → OFF (energy layer to be re-homed under infra)

## Changelog

### 2026-03-21 (session)
- **3-MODE ARCS:** Replaced binary missile toggle with OFF → PATHS → ANIMATED → OFF cycle. PATHS=static dotted arcs (blue glow), ANIMATED=full rocket animation (red glow). State persisted via `localStorage.missileMode`.
- **DEFAULT ANIMATED:** Changed default missile mode from `off` to `animated` for first-time visitors.
- **2H TTL:** Both embedded and fetched live events expire after 2 hours. Stale arcs cleaned up when no fresh events exist.
- **FIX ROOT CAUSE:** Removed `_arcSvg = null` reset at line ~3477 that destroyed arc SVG after `renderMissileArcs()` created it (synchronous execution order bug).
- **EARLY INIT RULE:** All critical state (`_liveEvents`, `_missileMode`) must be in early init block (~line 1997), not late block (~line 3470+) — script silently dies between 3470-3536 at runtime.
- **DEMO → TEST UTILS:** Moved demo mode to `window._test.demo()` / `window._test.demoOff()` (console only). Removed long-press UI, toast notifications.
- **REMOVED SATELLITES:** Deleted 328 lines — recon satellite feature (CelesTrak TLE, satellite.js SGP4, orbital tracks). Was broken and not useful.
- **REMOVED PATROL (partial):** Air patrol routes removed from mobile toolbar and sidebar; kept in desktop toolbar asset filter.
- **FIX GEOCODING:** Added Diego Garcia to `LOC_MAP` in `export-feed.py`. Changed `detect_location()` to longest keyword match (was first match — "hormuz" matched before "diego garcia").
- **HORMUZ TRACKER:** Fixed stale data (since Mar 8) — collection script was pushing to wrong repo. Now updating hourly.
- **INFRA DATA:** Added `data/iran-infrastructure.json` with ~70 entries (power plants, water, telecom, transport, industrial). Not yet wired into dashboard.

### 2026-03-20
- **FIX:** Missile arc animation not triggering on page load — removed broken `/api/live-events` API call, now fetches `live-events.json` directly. Increased initial delay from 2s to 4s.
- **CHANGE:** Promoted centcom.html to index.html (root). Old V2 dashboard archived as `v2-archive.html`.

---

_Update this spec with every change. Future-you will thank present-you._
