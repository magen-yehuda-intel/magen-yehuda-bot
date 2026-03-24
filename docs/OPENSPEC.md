# OPENSPEC — Magen Yehuda CentCom Dashboard

> **Source of truth for all dashboard changes.** Read this BEFORE modifying `centcom.html` or `index.html`.
> Both files must stay in sync (index.html = copy of centcom.html).

## File Map
| File | Role |
|------|------|
| `index.html` | Production dashboard (GitHub Pages root) — copy of centcom.html |
| `centcom.html` | Working copy / canonical source |
| ~~`v2-archive.html`~~ | Removed (Mar 21 cleanup). Design notes saved in `references/v3-analysis.md` |
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
  - `boxZoom: false` — no blue rectangle on shift-click/country click
- **Data source:** `v2-data.js` (static) + API (`magen-yehuda-api` Azure Container App) + `live-events.json`
- **API URL:** `https://magen-yehuda-api.blackfield-628213bb.eastus.azurecontainerapps.io`

## UI Layout

### Wireframe — Desktop (≥1025px)
```
┌──────────────────────────────────────────────────────┐
│  🇺🇸  U.S. & ISRAEL  vs.  IRAN  🇮🇷             │ Title Bar (44px)
├──┬───────────────────────────────────────────────────┤
│  │ 🛡 PIKUD HAOREF ● Live  🇺🇸 HORMUZ HH:MM:SS  Updated │ Oref Banner
│  │ ✅ All Clear  (last: Rockets · 06:52)             │
│TB├───────────────────────────────────────────────────┤
│  │                                                   │
│☰ │                                                   │
│⭐│                    MAP                            │
│🏗│               (Leaflet)                           │
│✈ │                                                   │
│🚢│                                                   │
│🚨│                                                   │
│🔥│  [Chips: 🛡 sirens | ✈ aircraft | 🔥 fires]     │
│📌│                                                   │
│🚀│         [Strike: 24h ▾ 48h  7d]                  │
│📋│                                                   │
│📍│                                                   │
└──┴───────────────────────────────────────────────────┘
```

### Wireframe — Mobile (≤1024px)
```
┌─────────────────────────────┐
│ 🇺🇸 U.S.&ISRAEL vs IRAN 🇮🇷 │ Title Bar (36px)
├─────────────────────────────┤
│ ☰ ⭐ 🏗 ✈ 🚢 🚨 🔥 📌 🚀 📍│ Top Toolbar (scroll)
├─────────────────────────────┤
│ 🛡 PIKUD HAOREF ● Live 🇺🇸HORMUZ 17:55│ Oref Banner (top:80px)
│ ✅ All Clear                │
├─────────────────────────────┤
│                             │
│           MAP               │
│        (Leaflet)            │
│                             │
│  [Chips]                    │
│                             │
├─────────────────────────────┤
│  LAYERS  │  FEED  │ LEGEND  │ Bottom Bar (3 buttons)
└─────────────────────────────┘
```

### Title Bar
- "U.S. & ISRAEL vs. IRAN" with flag emojis
- Map/VIIRS toggle buttons (top right)
- **Mobile:** Font 9px, flags 14px, letter-spacing 0.5px, height 36px

### Pikud HaOref Banner (below toolbar)
- **Connection health**: "● Live" text pulses 2 times on each successful Oref poll (`.oref-live-pulse` animation, 1.2s). After 5 consecutive failures → "● Offline" (red). Auto-recovers.
- **Breaking News Banner** — generic `#breaking-banner` element, hidden by default (`display:none`). API: `window._showBreaking(label, popupHtml)` shows banner with pulsing red animation + click-to-expand popup; `window._hideBreaking()` hides it. Replaces the old Trump Hormuz countdown (removed Mar 24). Use for any future breaking event. Internal vars: `_breakingPopupHtml`, function `showBreakingInfo(e)`. Mobile CSS: `#breaking-banner { font-size:8px !important; padding:1px 4px !important; }`.
- **Alert states:**
  - `✅ All Clear` — green, safe. Shows last siren info below.
  - `🚨 ACTIVE SIREN — area1, area2, area3 +N more areas` — red, pulsing text (`siren-pulse` 0.8s) + entire banner pulses red glow (`banner-siren` 1.2s alternate). `alert-active` class on banner. Areas extracted from `alert.data[]` array via `flatMap`.
  - `⚠️ Recent Alert — sirens ended Xm ago` — amber/warning, 10min cooldown after active alerts end.
- Last siren: shows `HH:MM` (24h clock); different day shows `MM/DD HH:MM`
- Click to open **Siren History** popup (scrollable, shows areas prominently — no wave labels)
- Polls `/api/oref` every 15s
- **Mobile:** top:80px (below mobile toolbar), full-width (left:0; right:0)

### Left Toolbar (desktop only — vertical icon strip)
- **Hidden on screens ≤1024px** (`display:none !important`)
Clickable toggle buttons with tooltips:
| Icon | Layer | Color |
|------|-------|-------|
| ☰ | Sidebar toggle | — |
| ⭐ | Military Bases | cyan |
| 🏗 | Infrastructure | amber |
| ✈️ | Aircraft/Flights | blue |
| 🚢 | Ships/Naval | blue |
| 🚨 | Sirens (Oref) | red |
| 🔥 | Fires (FIRMS) | orange |
| 📡 | Live Feed | green | Green glow circle (`.tb-feed-btn`); pulses (`notify-pulse`) on new events, clears when opened |
| 📋 | Intel Brief | cyan | Cyan glow circle (`.tb-brief-btn`); pulses on new brief, clears when opened |
| 📌 | OSINT Events | red |
| 🏚 (SVG) | Earthquakes (USGS) | purple | Inline SVG building-damage icon from svgrepo |
| 🚀 | Missile Animations | red |
| Strike window dropdown | 24h/48h/7d (default 48h, no "All") | — |
| 📍 | Geolocate | — |

### Mobile Top Toolbar (horizontal scrollable strip)
- **Visible ≤1024px**, `top:36px`, horizontally scrollable
- Same toggle icons as desktop toolbar (☰, ⭐, 🏗, ✈️, 🚢, 🚨, 🔥, OSINT, 🚀, 📍)

### Mobile Bottom Bar
3 buttons only:
- **LAYERS** | **FEED** | **BRIEF**
- FEED is center position, pulsing green circle with breathing glow animation
- Red badge on FEED shows count of events from last hour (capped at "99+"), hidden when 0
- Feed data pre-loaded on page load for badge count; **panel stays closed by default**
- Opening any panel closes the others (mutual exclusivity)

### Sidebar (desktop left, toggleable)
Grouped layer controls with dot indicators and counts:
- **Basemap:** VIIRS Night Lights toggle (🌗) — replaces floating Map/VIIRS buttons
- **Borders:** Borders, Buffer Zones, Exclusion Zones
- **U.S. Military:** Bases (29), Carrier Groups, Patrol Routes, Aircraft
- **Israel:** IDF Bases (14), Iron Dome (12), David's Sling (7), Arrow (4), Naval
- **Iran:** IRGC Bases, Nuclear Sites, Missile Sites (52), Naval, Air Defense, Airbases, Energy, SAM
- **Ships:** CSG vessels, Submarines
- **Proxy Forces:** Hezbollah, Houthi, Iraqi PMF
- **Live Data:** NASA FIRMS Fires, OSINT Events, Siren Alerts, Strike Events

### Live Feed Panel (right side)
- Real-time OSINT event feed
- Filterable by time (30m/1h/4h/24h/48h/ALL) and source (ALL/Iran/Israel/Proxy)
- Color-coded event cards with source, timestamp, flag
- Event count in header
- **Desktop:** Toggleable via 📡 toolbar button; opening closes Brief panel
- **Mobile:** Opens via FEED bottom bar button; closes on panel switch
- **Startup:** Panel hidden by default; feed data pre-loaded silently for badge count
- **Basemap toggle** shifts right (392px) when feed OR brief panel is open

### Missile Arc Animation System
- **3-mode cycle:** OFF → PATHS (static dotted arcs, blue glow) → ANIMATED (full rocket animation, red glow) → OFF
- **Data source:** `live-events.json` (polled every 30s via `fetchLiveEvents()`)
- **Trigger:** Events with `origin_lat`, `origin_lon`, `lat`, `lon` fields
- **TTL:** Events expire after 2 hours (`nowTs - e.ts < 7200`) — both embedded and fetched
- **Default mode:** `animated` (first-time visitors see full animation)
- **Embedded fallback:** `window._liveEvents = [];` — starts empty, populated by `fetchLiveEvents()`. Old hardcoded events were removed (Mar 24 fix — stale Mar 21 events were overriding 2h TTL filter).
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
- Fixed position overlay, opens on Oref banner click
- Deduplicates alerts within 90s window (merges areas)
- No wave labels — shows **target region** (North, Haifa & North, Center, South) as title with color-coded left border
- Summary shows first 3 area names; full area list revealed on tap
- Region classified from area names via regex (Hebrew city/region matching)
- Time: `HH:MM` 24h clock; different day: `MM/DD HH:MM`
- **Expandable items**: Tap to expand all areas (joined with `·`) + alert description (amber italic). Tap again to collapse. Hover highlight on items.
- Thin dark scrollbar on desktop (`scrollbar-width:thin`, 4px webkit, cyan-tinted track)
- Region classification (`classifyRegion`): North, Haifa & North, Center, South, or city names — severity labels (CRITICAL/LOW/MEDIUM) never shown
- **Live pulse**: Green text-shadow flash (0.8s) on `● Live` every 10s on successful Oref poll
- Shows first 4 areas in summary; "X areas total" if more than 4
- Color-coded: red=active, amber=standdown

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
| `toggleFeed()` | Show/hide feed panel; closes brief on desktop |
| `toggleBrief()` | Show/hide brief panel; closes feed on desktop |
| `loadFeed()` | Loads OSINT events into feed panel + updates badge count |
| `loadBrief()` | Fetches brief.json into brief panel |
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

## Hormuz Tracker Pipeline
- **Dashboard:** `hormuz.html` — reads `hormuz-metrics.jsonl` from same GitHub Pages origin
- **Collection script:** `~/projects/breaking-trades/articles/hormuz-crisis/collect-and-push.sh`
- **Cron:** `0 * * * *` (hourly)
- **Flow:** Cron → browser scrape MarineTraffic AIS tiles → `hormuz-tracker.py` computes metrics → append to `hormuz-metrics.jsonl` (source of truth in `~/projects/breaking-trades/articles/hormuz-crisis/`) → copy to `/tmp/hormuz-site/docs/` → `git pull --rebase` → push to GitHub Pages
- **MarineTraffic tiles:** 10 tiles at zoom 8, fetched via `XMLHttpRequest` in openclaw browser tab
- **Vessel dump:** `~/projects/breaking-trades/articles/hormuz-crisis/vessel-dump.json` (raw AIS per collection)
- **Git clone:** `/tmp/hormuz-site/` (shallow clone of `magen-yehuda-intel/magen-yehuda-bot`)
- **⚠️ Pull before push:** Script does `git pull --rebase` before pushing to avoid conflicts when dashboard changes are pushed separately

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

### 2026-03-24
- **Brief panel scrollbar:** Added thin custom scrollbar to `.brief-content` matching the live feed panel (`.feed-list`) style — `scrollbar-width:thin`, 4px webkit, `rgba(255,255,255,0.1)` thumb on transparent track. Was using default browser scrollbar.
- **Trump countdown → Breaking Banner:** Replaced `#trump-countdown` + `initTrumpCountdown()` + `showTrumpInfo()` with generic `#breaking-banner` system. Hidden by default. API: `window._showBreaking(label, popupHtml)` / `window._hideBreaking()`. Reusable for any future breaking event.
- **Stale missile arcs fixed:** Hardcoded `window._liveEvents` (2 events from Mar 21) was assigned AFTER the 2h TTL filter, overriding it. Cleared to empty array — `fetchLiveEvents()` now the sole data source.
- **Brief LLM switched:** `gpt-5.4-mini` → `gpt-5-mini` (old resource `openai-dev-nt6mukageprxm`). Reason: `gpt-5.4-mini` content filter blocks all brief generation when OSINT contains strike/attack data (`ResponsibleAIPolicyViolation`). Short windows (30min/2h/6h) still fail to parse — patched with manual brief.
- **Infrastructure layer:** Added 4 struck facilities: Isfahan Gas Administration (Kaveh St), Isfahan Pressure-Reduction Station (Kaveh St), Khorramshahr Energy Facility, Abadan Refinery (context, not confirmed hit).
- **Hormuz.html:** Added Mar 23 (ultimatum expired) + Mar 24 (US-Israeli strikes on Isfahan/Khorramshahr) timeline entries.

### 2026-03-23 (session notes — evening)
- **Trump Hormuz deadline:** `2026-03-23T23:44:00Z` (~7:44 PM ET). Expires tonight. When extending/replacing: update `const DEADLINE` in `initTrumpCountdown()` in BOTH `index.html` and `centcom.html` (~line 2805). Sync both files (`cp centcom.html index.html`). Also update changelog here.
- **Brief panel:** Client-side, on-demand — user clicks 30M/2H/6H/24H/48H to generate. "Tap a time window" is expected UX, not a bug. `brief.json` is pre-generated every 30min by cron and fetched by `loadBrief()`.
- **Live Feed:** Was showing 0 events on initial page load (connecting...) — loaded after ~1min. Normal behavior. Feed panel hidden on startup by design; pre-loads silently for badge count.
- **Hourly report dispatch error:** `⚠️ Dashboard link send failed` — looks for `dispatch.py` at `/Users/idanshimon/scripts/dispatch.py` (wrong path). Should be `scripts/dispatch.py` relative to skill dir. Minor — doesn't affect main report send.
- **Brief data fix:** `generate-brief.py` `load_events()` now merges `docs/intel-feed.json` (OSINT headlines with actual text) alongside `state/intel-log.jsonl`. Root cause: intel-log osint events have `data: {}` (watcher doesn't serialize text). Fix: 1,225→2,212 events, 2H window 1,035→5,881 chars. Brief now covers actual strikes, city-level reporting, diplomacy. **Do NOT revert.**
- **Brief context injection:** `USER_PROMPT_TEMPLATE` has a hardcoded `CONTEXT:` block (Day 24, Hormuz ultimatum, Iran mine threat). **Update this block** when strategic situation changes — new ultimatum, ceasefire, key leader killed, etc.
- **Watcher auto-restart:** Installed launchd plist `com.openclaw.iran-israel-watcher` (`~/Library/LaunchAgents/`). `KeepAlive: true`, `RunAtLoad: true`. Watcher now survives reboots and crashes. Previously: watcher just died and stayed dead (no auto-restart, no launchd). Install via `bash ctl.sh install-launchd`, unload via `launchctl unload ~/Library/LaunchAgents/com.openclaw.iran-israel-watcher.plist`.
- **Watcher was STOPPED during CRITICAL:** Found watcher dead while Oref showed active rocket sirens (ירי רקטות וטילים in Judean Hills). Restarted manually, then installed launchd for permanent fix.
- **Dispatch path fix:** `hourly-report.sh` dashboard link send used relative `scripts/dispatch.py` — fails under cron (cwd is `$HOME`). Fixed to derive absolute path from `config_file` via `os.path.abspath()`.
- **Duplicate watcher cleanup:** After `ctl.sh start` + launchd restart, had 4 watcher processes. Killed manual ones, kept launchd-managed PID only.

### 2026-03-23
- **LLM upgrade**: `gpt-5-mini` → `gpt-5.4-mini` (v2026-03-17) on `idanshimon-8986-resource` (eastus2)
- **Brief on desktop**: Added 📋 Intel Brief button to desktop toolbar (was mobile-only)
- **Feed/Brief exclusivity**: Opening feed closes brief and vice versa (both desktop and mobile)
- **Brief panel opaque**: Changed from semi-transparent `rgba` + `backdrop-filter:blur` to fully opaque `#050510` — VIIRS/map tiles no longer bleed through
- **Feed hidden on startup**: Removed auto-open (`setTimeout(toggleFeed, 500)`); feed pre-loads silently for badge count only
- **Desktop feed button**: Green pulsing circle (`.tb-feed-btn`) with red event count badge — matches mobile FEED style
- **Desktop brief button**: Cyan glow circle (`.tb-brief-btn`) — matches mobile BRIEF style
- **Red badge on both**: Desktop + mobile feed buttons show hourly event count (capped 99+)
- **Basemap toggle z-fix**: Map/VIIRS toggle (z-index 1001) now shifts right when brief panel is open (was covering EN/עב lang toggle)
- **Oref Live pulse**: "● Live" text pulses 3 times (opacity flash) on each successful Oref poll, replacing single blink
- **Feed/Brief new-content pulse**: Badges removed; buttons pulse gently (`notify-pulse`) when new events/brief arrive; clears when panel opened
- **Basemap moved to sidebar**: Floating Map/VIIRS toggle removed from map overlay; VIIRS Night Lights now a toggle row in sidebar Layers tab (under BASEMAP section). Mobile toolbar 🌗 button retained for quick access.
- **Brief prompt**: Added international news (real actions only, no generic "condemns") + 🟢 Good News section
- **RSS feeds**: Added "EU Defense" + "Good News ME" Google News RSS feeds to config
- **PWA fixes**: `start_url` → root, `id` field, split icon purpose, SW v5, data JSON offline cache, deprecated meta tag fix
- **index.html sync**: Fixed stale index.html missing brief panel; added test to catch this automatically
- **Countdown label**: Changed from `⏰` to `🇺🇸 HORMUZ` — clearly indicates Trump Hormuz ultimatum
- **Oref connection health**: "● Live" pulses 2 times (`.oref-live-pulse`, 1.2s) on each successful poll; shows "● Retrying (N)..." on failures; switches to **"● Offline"** (red) after 5 consecutive failures; auto-recovers on success
- **Mobile panel exclusivity**: Opening Feed/Legend/Layers now closes the other panels (no overlap)
- **Mobile bottom bar**: Reduced to 3 buttons — LAYERS | FEED | LEGEND; FEED is green circle
- **Strike map**: Default 48h (was 24h), removed "All" option, max 7d. `config.json` `window_days: 2`
- **Siren history**: Removed "Wave N" labels; areas shown prominently; time `HH:MM` 24h clock; `MM/DD HH:MM` for different day
- **JS fix**: `const d` variable collision broke ALL script execution — renamed to unique vars
- **Mobile breakpoint**: Raised from 768px → 1024px — hides desktop toolbar on tablets too
- **Mobile title**: Smaller (9px, flags 14px, height 36px) to fit viewport
- **Mobile Oref banner**: Pushed to `top:80px` below mobile toolbar, full-width
- **Mobile sidebar**: Starts closed (`translateX(-100%)`) on mobile

### 2026-03-21 (cleanup)
- **REMOVED v1 dashboard** (`docs/v1/`, 5.4MB) — dead, no references anywhere
- **REMOVED v2-archive.html** (5.3MB) — design notes saved to `references/`
- **REMOVED dashboard-v3/** — never-built CesiumJS plans, design notes saved to `references/`
- **COMMITTED Flask API** — `api/app.py` + `api/db.py` extracted from Docker image v21 and committed
- **PROJECT REORG:** Stale plans → `references/`, `hourly-brief.sh` → `scripts/`, cleaned runtime artifacts

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

- **FIX HORMUZ PIPELINE:** Added `git pull --rebase` before push in `collect-and-push.sh` — was failing because `/tmp/hormuz-site` clone fell behind after dashboard pushes.

### 2026-03-20
- **FIX:** Missile arc animation not triggering on page load — removed broken `/api/live-events` API call, now fetches `live-events.json` directly. Increased initial delay from 2s to 4s.
- **CHANGE:** Promoted centcom.html to index.html (root). Old V2 dashboard archived as `v2-archive.html`.

---

_Update this spec with every change. Future-you will thank present-you._

## Brief Panel (📋)

### Overview
AI-generated situation briefs from live intel events. Bilingual (EN/HE). Replaces Legend on mobile bottom bar.

### Architecture
- **Script:** `scripts/generate-brief.py` — runs every 30 min via cron
- **LLM:** Azure OpenAI `gpt-5-mini` on `openai-dev-nt6mukageprxm` (eastus). Switched from `gpt-5.4-mini` on Mar 24 — the newer model's content filter (`ResponsibleAIPolicyViolation`) blocks strike/violence OSINT. The older `gpt-5-mini` has no aggressive content filter. 24h+48h windows generate well; 30min/2h/6h return unparseable format for small event counts (patched with manual brief fallback).
- **Input:** `state/intel-log.jsonl` + `docs/intel-feed.json` (merged — see ⚠️ fix note below)
- **Output:** `docs/brief.json` — auto git-pushed to GitHub Pages
- **Time windows:** 30M, 2H, 6H, 24H, 48H (same as feed filters minus 15M)
- **Languages:** English (default) + Hebrew (RTL, dir='rtl')

### Prompt Design
- Military intelligence briefing officer persona
- Rules: direct, concise, no fluff, group by theme, add tactical context
- International news: only real actions (troops, sanctions, embargoes) — skip generic "condemns" statements
- 🟢 Good News section: interceptions, humanitarian aid, ceasefire progress, civilians rescued
- Active sirens/strikes go FIRST, bold
- End with 1-line threat trend assessment
- Output: JSON `{"en": "<html>", "he": "<html>"}`
- Under 300 words per brief
- **`USER_PROMPT_TEMPLATE` has a `CONTEXT:` block** injected before the events — includes current conflict background (Day N, active ultimatums, key threats). Update this context block when the strategic situation changes significantly (new ultimatum, ceasefire, etc.)

### ⚠️ Brief Data Source Fix (Mar 23)
**Root cause:** `intel-log.jsonl` osint events logged `type: "osint"` but `data: {}` — watcher didn't serialize the text. Brief was working off flight scans only → generic airspace output.

**Fix in `load_events()`:** Now merges two sources:
1. `state/intel-log.jsonl` — sirens, flight scans, threat changes, cyber
2. `docs/intel-feed.json` — geocoded OSINT events with actual headlines/text (Reuters, TASS, Telegram channels, RSS)

**Impact:** 1,225 → 2,212 events loaded; 2H window 1,035 → 5,881 chars. Brief now includes strike claims, city-level reporting, diplomatic developments.

**Do NOT revert** the `load_events()` merge — the intel-log osint data is structurally empty and that is a watcher-side bug that may or may not get fixed.

### Dashboard UI
- **Panel:** Same style as feed panel, right-side slide-in, full-width on mobile
- **Header:** EN/עב language toggle + time window chips (30M/2H/6H/24H/48H)
- **Content:** Rendered HTML from brief.json, RTL support via `data-lang="he"`
- **Auto-refresh:** Fetches new brief.json every 30 min
- **Mutual exclusivity:** Opening brief closes feed/sidebar and vice versa

### Mobile Bottom Bar
```
[ LAYERS ] [ FEED ] [ BRIEF ]
```

### Cron
```
*/30 * * * * /opt/homebrew/bin/python3 ~/.openclaw/workspace/skills/iran-israel-alerts/scripts/generate-brief.py >> /tmp/brief-gen.log 2>&1
```

## PWA (Progressive Web App)

### Manifest (`manifest.json`)
- **name:** "Magen Yehuda Intel", **short_name:** "MYI"
- **id:** `/magen-yehuda-bot/` (stable identity across installs)
- **start_url:** `/magen-yehuda-bot/` (serves index.html)
- **display:** standalone, **orientation:** any
- **Icons:** 192x192 + 512x512, separate `purpose: "any"` and `purpose: "maskable"` entries (no combined)
- **theme_color:** `#ff0040`, **background_color:** `#0a0a1a`

### Service Worker (`sw.js`)
- **Cache name:** `myi-v5` (bump version on shell changes)
- **Shell URLs cached:** `/`, `/index.html`, `/manifest.json`, icons
- **Strategy:** Network-first for HTML + data JSON (cache fallback for offline), cache-first for static assets
- **Data JSON:** All `.json` files (except manifest) cached with network-first + offline fallback `{"error":"offline"}`
- **API calls:** Always network, returns `{"error":"offline"}` on failure
- **Lifecycle:** `skipWaiting()` on install, `clients.claim()` on activate, auto-cleans old caches

### HTML Meta Tags
- `<link rel="manifest" href="manifest.json">`
- `<meta name="theme-color" content="#ff0040">`
- `<meta name="mobile-web-app-capable" content="yes">` (NOT apple-mobile-web-app-capable — deprecated)
- `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
- `<link rel="apple-touch-icon" href="icons/icon-192.png">`

### Rules
- **index.html MUST be synced with centcom.html** — run `cp centcom.html index.html` after every change
- Bump `CACHE_NAME` version in `sw.js` when shell files change
- Icon purpose must be separate entries (not `"any maskable"` combined)
