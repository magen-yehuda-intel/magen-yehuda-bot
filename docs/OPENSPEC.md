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
| ↻ | Patrol Routes | purple |
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
- **Data source:** `live-events.json` (polled every 30s via `fetchLiveEvents()`)
- **Trigger:** Events with `origin_lat`, `origin_lon`, `lat`, `lon` fields
- **Visual:** SVG bezier arcs from origin to target, animated rocket emoji traveling along path
- **Effects:** Pulsing origin dot, impact ripples at target, progressive trail
- **Cycle:** 8s per loop, staggered start per arc
- **Toggle:** 🚀 button in toolbar, persisted in localStorage (`missileAnim`)
- **Functions:** `fetchLiveEvents()` → `renderMissileArcs()` → `startArcAnimation()` / `setStaticArcs()`
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
- `v2-data.js` — **REQUIRED** (inline data: bases, assets, recent events, coordinates)
- `live-events.json` — missile arc events (written by watcher during attacks)
- API `/api/oref` — live siren data
- API `/api/feed` — OSINT event feed
- API `/api/threat` — current threat level

## Changelog

### 2026-03-20
- **FIX:** Missile arc animation not triggering on page load — removed broken `/api/live-events` API call, now fetches `live-events.json` directly. Increased initial delay from 2s to 4s.
- **CHANGE:** Promoted centcom.html to index.html (root). Old V2 dashboard archived as `v2-archive.html`.

---

_Update this spec with every change. Future-you will thank present-you._
