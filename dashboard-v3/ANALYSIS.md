# Dashboard V3 — MiddleEastTracker.com Deep Analysis

> Reverse-engineered from https://middleastracker.com on 2026-03-10
> Author: Kash | For: Idan

---

## TL;DR — What He Built, What We Can Steal

MiddleEastTracker is a **single-file (~107KB) monolithic HTML app** using CesiumJS for a 3D globe, Netlify serverless functions for API proxying, Outseta for auth/billing, Supabase for verified strikes DB, and AI classification (GPT-4) on Telegram OSINT feeds. It's impressive but beatable — our data pipeline is already stronger (we have 85+ sources, he has ~20), and Cesium is the only major tech upgrade we'd need.

**Worth adopting:**
1. CesiumJS 3D globe (the killer feature — tilted earth view with orbit camera)
2. Polymarket prediction markets integration
3. GPS jamming detection from ADS-B NIC values
4. Satellite tracking via CelesTrak TLE + satellite.js
5. AI-classified OSINT events (he uses GPT-4, we could use our existing pipeline)
6. Live webcam feeds (YouTube embeds from ME conflict zones)

**Not worth copying:**
1. Outseta auth (we're free/open-source)
2. Netlify serverless (we already have Azure Container Apps)
3. His strike data (129 manually curated events vs our 49K ACLED events)
4. His hardcoded SAMPLE_STRIKES fallback data

---

## 1. Tech Stack Breakdown

### Frontend
| Component | Their Stack | Our Current Stack |
|-----------|-------------|-------------------|
| **Map engine** | CesiumJS 1.124 (3D globe) | Leaflet 1.9 (2D tiles) |
| **Basemap** | CartoDB dark_all @2x (512px retina tiles) | VIIRS Black Marble / CARTO dark |
| **Fonts** | Orbitron (headings) + Share Tech Mono (body) | Similar (we use Orbitron too) |
| **Styling** | CSS custom properties, military HUD aesthetic | Similar HUD aesthetic |
| **Framework** | Vanilla JS, single HTML file (~107KB) | Vanilla JS, single HTML file |
| **Satellite tracking** | satellite.js 5.0.0 (CelesTrak TLE) | ❌ Not implemented |
| **Analytics** | PostHog (EU instance) | ❌ Not implemented |
| **CRT effect** | Scanline overlay via `body::after` repeating-linear-gradient | We have similar |

### Backend (Netlify Functions)
| Function | Purpose | Data Source |
|----------|---------|-------------|
| `opensky-proxy` | Aircraft ADS-B data | OpenSky Network → ADSBX fallback |
| `strikes-proxy` | Verified strike events | Supabase (primary) → Twitter OSINT → GDELT (fallback chain) |
| `polymarket-proxy` | Prediction market odds | Polymarket API |
| `news-proxy` | News + OSINT feed | Telegram scraping → GPT-4 classification → RSS news |
| `twitter-osint` | Twitter OSINT classifier | Twitter → GPT-4 event extraction |
| `acled-proxy` | Conflict event data | GDELT (not ACLED despite name) |

### Auth & Billing
- **Outseta** (`avio-software.outseta.com`) — handles registration, login, subscription
- Free 7-day trial → paid subscription
- Token stored in localStorage, callback redirects to `index.html`
- Landing page shows blurred sidebar/right panel as teaser

### Database
- **Supabase** — stores verified strike events (129 events as of now)
- Manual curation: `id`, `lat`, `lng`, `type`, `event_type`, `location`, `description`, `date`, `actor`, `fatalities`
- Much smaller dataset than our 49K ACLED events

---

## 2. CesiumJS — The 3D Globe (The Big Upgrade)

### What It Does
- Full 3D WebGL globe with tilted perspective camera
- Smooth `flyTo()` animations when clicking entities
- Distance-based scale/visibility (`scaleByDistance`, `distanceDisplayCondition`)
- MSAA 4x anti-aliasing + FXAA
- Retina support (`resolutionScale = devicePixelRatio`)
- Fog effect for atmosphere (`density: 0.0002`)
- Scene3DOnly mode (no 2D/Columbus view switching)

### Globe Settings (Copy-Worthy)
```javascript
Cesium.Ion.defaultAccessToken = '...'; // Free tier available
viewer = new Cesium.Viewer('cesiumContainer', {
  baseLayerPicker: false, geocoder: false, homeButton: false,
  sceneModePicker: false, selectionIndicator: false, timeline: false,
  animation: false, navigationHelpButton: false, fullscreenButton: false,
  infoBox: false, shadows: false, shouldAnimate: true, scene3DOnly: true,
  imageryProvider: false, msaaSamples: 4,
  requestRenderMode: false, maximumRenderTimeChange: Infinity,
});
// CartoDB dark retina tiles
viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
  url: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
  maximumLevel: 18, tileWidth: 512, tileHeight: 512, credit: 'CartoDB',
}));
viewer.scene.globe.enableLighting = false;
viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0a1a0d');
viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#050805');
viewer.scene.fog.enabled = true;
viewer.scene.fog.density = 0.0002;
viewer.scene.globe.maximumScreenSpaceError = 1.5; // sharper tiles
viewer.scene.fxaa = true;
viewer.resolutionScale = window.devicePixelRatio || 1;
```

### Camera
- Initial: `Cesium.Cartesian3.fromDegrees(46, 27, 4000000)` — centered on Persian Gulf
- Pitch: -60° (tilted view, not top-down)
- Landing page has slow auto-rotation: `rotAngle += 0.001` in `requestAnimationFrame`

### Entity Rendering Approach
- **Bases**: `point` + `label` + `ellipse` (glow ring) — 14 bases
- **Planes**: `billboard` (colored SVG arrow rotated to heading) + `label` — refreshed every 30s
- **Strikes**: `point` + `label` + optional `ellipse` for high-fatality events — pulsing animation for recent
- **Satellites**: `billboard` (SVG satellite icon) + `label` + `polyline` (orbit trail, 90min ahead)
- **GPS Jamming**: `polygon` (hex grid cells) + `label` — 1° resolution
- **OSINT Events**: `point` + `label` + optional `ellipse` (glow ring for Critical/High)
- **Resources**: `polygon` (oil fields, chokepoints) + `label`
- **AOR Boundary**: `polyline` (amber, 20% alpha)

### Performance Notes
- All entities use `scaleByDistance` and `distanceDisplayCondition` for LOD
- Plane data cached for 25s (skip fetch if <25s since last)
- Simulation fallback: `genSimPlanes()` generates 16 fake aircraft if API fails
- `requestRenderMode: false` = continuous rendering (GPU-heavy but smooth)

---

## 3. Data Sources — Comparison

### Their Sources
| Source | Data Type | Refresh | Notes |
|--------|-----------|---------|-------|
| OpenSky Network | Aircraft ADS-B | 30s | Primary — free tier, AOR bounding box |
| ADS-B Exchange (ADSBX) | Aircraft ADS-B | 30s | Fallback when OpenSky down |
| Supabase DB | Verified strikes | 5min | 129 manually curated events |
| GDELT | Conflict events | 5min | Fallback for strikes |
| Polymarket | Prediction odds | 60s | Iran/Israel conflict markets |
| Telegram (via proxy) | OSINT raw feed | Manual/API | ~20 channels, GPT-4 classified |
| Twitter (via proxy) | OSINT raw feed | Manual/API | Unknown count |
| RSS News | Headlines | API call | Google News, etc. |
| CelesTrak | Satellite TLEs | On load | GPS, Military, ISS, Weather, Starlink |

### Our Sources (Already Operational)
| Source | Data Type | Refresh | Notes |
|--------|-----------|---------|-------|
| 12 Telegram channels | OSINT | 30s-5min | Direct scraping |
| 13 Twitter accounts | OSINT | Polling | Via API |
| 7 RSS feeds | News | Polling | Hebrew + English |
| 10 RSS feeds (total) | News | Polling | ToI, JPost, Al Jazeera, TASS, Reuters, AP, etc. |
| NASA FIRMS (4 satellites) | Fire detection | 5min | VIIRS, MODIS |
| USGS Earthquake | Seismic | 5min | M3.5+ in Iran region |
| ACLED API | Conflict events | Daily | **49,000 events** (vs their 129) |
| Pikud HaOref | Siren alerts | 30s | Real-time Israeli alerts |
| OpenSky | Military flights | FR24 primary | With role detection |
| IODA + probes | Internet blackout | 5min | Iran connectivity |
| 19 hacktivist groups | Cyber warfare | Polling | 25 TG handles, 8 Twitter CTI |

### What They Have That We Don't
1. **Polymarket prediction markets** — Easy to add (public API, no auth needed)
2. **Satellite tracking** — CelesTrak TLE + satellite.js (GPS, Military, ISS, Weather, Starlink)
3. **GPS Jamming detection** — Computed from ADS-B NIC values (Navigation Integrity Category)
4. **AI event classification** — GPT-4 classifies raw OSINT into event types with geo, severity, confidence
5. **Live webcam feeds** — YouTube embeds (9 streams from war zones)
6. **Supabase real-time DB** — Verified strike database

### What We Have That They Don't
1. **49,000 ACLED events** vs 129 curated strikes
2. **NASA FIRMS fire detection** (satellite thermal data)
3. **Strike correlation model** (seismic + fire pairing with scoring)
4. **Pikud HaOref real-time sirens**
5. **Iran internet blackout monitoring**
6. **Cyber warfare tracking** (19 hacktivist groups)
7. **Bilingual (Hebrew + English) dispatch**
8. **Telegram channel auto-dispatch** (they're a paywall website)
9. **Military base overlays** (25 US + 18 Iran nuclear + 52 missiles + 9 naval + 26 air defense with SAM range rings)
10. **Dashboard snapshot generator** (automated Telegram-ready images)

---

## 4. OSINT Classification Schema

Their GPT-4 classifier produces structured events:

```json
{
  "title": "raw text from source",
  "source": "🛰 CIG Intel",
  "time": "just now",
  "url": "https://t.me/...",
  "publishedAt": "2026-03-10T05:22:10.626Z",
  "_src": "Telegram",
  "_tg": "CIG_telegram",
  "_views": "",
  "_fullText": "full raw text",
  "event_type": "Kinetic Strike",  // classified
  "event_emoji": "💥",
  "severity": "Medium",
  "severity_score": 65,
  "confidence": "Probable",
  "confidence_emoji": "🔵",
  "actors": ["US Military"],
  "theater": ["Iran"],
  "location_mentions": ["Tehran"],
  "tags": ["airstrike", "iran"],
  "summary": "AI-generated summary",
  "mappable": true,
  "lat": 35.68,
  "lon": 51.39
}
```

**Event types:** Kinetic Strike, Explosion, Air Activity, Naval Activity, Ground Movement, WMD/CBRN, Air Defense, Infrastructure Hit, Cyber/EW, Diplomatic, Civilian Incident, Intel/OSINT, Unconfirmed

**Confidence levels:** Confirmed, Probable, Unverified

**Severity levels:** Critical, High, Medium, Low (with score 0-100)

---

## 5. GPS Jamming Detection (Novel Feature)

Computes jamming from ADS-B **NIC (Navigation Integrity Category)** field:
- NIC ≥ 5 = Good GPS
- NIC < 5 = Bad GPS (likely jammed or spoofed)
- Grid: 1° × 1° cells across AOR
- Renders hexagonal polygons with color coding:
  - 🔴 RED (>10% bad NIC) = Likely jamming
  - 🟡 YELLOW (2-10%) = Possible interference  
  - 🟢 GREEN (<2%) = Normal

**This is clever and easy to implement.** We already get ADS-B data — we just need to bucket NIC values into grid cells.

---

## 6. Satellite Tracking (CelesTrak + satellite.js)

### TLE Sources
| Group | URL | Limit | Color |
|-------|-----|-------|-------|
| GPS | celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops | 40 | Green |
| Military | celestrak.org/NORAD/elements/gp.php?GROUP=military | 60 | Orange |
| ISS/Stations | celestrak.org/NORAD/elements/gp.php?GROUP=stations | 10 | Yellow |
| Weather | celestrak.org/NORAD/elements/gp.php?GROUP=weather | 30 | Cyan |
| Starlink | celestrak.org/NORAD/elements/gp.php?GROUP=starlink | 40 | Blue |

### Rendering
- satellite.js SGP4 propagation for real-time position
- 90-minute ahead orbit trail (polyline, 60 points at 1.5min intervals)
- SVG satellite icon billboard
- Labels scale by distance

---

## 7. Polymarket Integration

**Dead simple.** Fetches from their proxy, but the actual Polymarket API is public:
- `https://gamma-api.polymarket.com/events?tag=iran` (or similar)
- Returns: markets with question, yes/no prices, volume, slug
- They render as colored probability bars (green=likely, red=unlikely)
- Click → open Polymarket page

Markets tracked: Iran-Israel conflict timeline, US strikes, ground troops, ceasefire, Hormuz closure, regime change, successor, etc.

**Easy win for us.** Add a Polymarket panel to centcom.html.

---

## 8. UI/UX Architecture

### Layout (Desktop)
```
┌─────────────────────────────────────────────────────┐
│ HEADER: Logo | LIVE pill | Toggles | Stats | Clock  │
├────────┬──────────────────────────┬─────────────────┤
│  LEFT  │                          │     RIGHT       │
│  255px │    CESIUM 3D GLOBE       │     315px       │
│        │                          │                 │
│ Tabs:  │   HUD overlays (left)    │ Video feed      │
│ Bases  │   Legend (right)         │ Camera switcher │
│ Planes │   Info panel (bottom-R)  │ Polymarket odds │
│ Strikes│   Zoom btns (top-R)     │ News/OSINT feed │
│ Events │                          │                 │
├────────┴──────────────────────────┴─────────────────┤
│ FOOTER: Status | Last update | Source badges        │
└─────────────────────────────────────────────────────┘
```

### Mobile
- Sidebar + right panel hidden; bottom nav bar for switching views
- `@media(max-width:900px)` breakpoint

### Color Palette
```css
:root {
  --amber: #ffb600;     /* Primary accent */
  --bg: #0a0800;        /* Background */
  --panel: #0e0c00;     /* Panel background */
  --border: #2a2200;    /* Border */
  --border-lit: #3a2f00; /* Lit border */
  --text: #e8c87a;      /* Primary text */
  --text-dim: #7a6230;  /* Dim text */
  --text-muted: #4a3d20; /* Muted text */
  --green: #39ff7a;     /* Status/OK */
  --red: #ff3b3b;       /* Danger */
  --blue: #4ab8ff;      /* Naval/Info */
  --purple: #cc88ff;    /* Critical */
  --sand: #c4a35a;      /* Resources */
  --cyan: #00eeff;      /* Aircraft */
  --mil: #aaff00;       /* Military */
  --strike: #ff2222;    /* Strikes */
}
```

### Animations
- `blink` — pulsing green dot (1.4s infinite)
- `critPulse` — alternating purple/red border for critical events (2s)
- `spin` — loading spinner rotation
- CRT scanline effect via `body::after` repeating gradient
- Globe auto-rotation on landing page

### Key UX Patterns
1. **Sidebar tabs** — Bases / Planes / Strikes / Events (click to switch)
2. **Filter buttons** — per tab (base type, plane type, strike type, event type)
3. **Info panel** — bottom-right slide-up on entity click (base details, plane info, strike data)
4. **News tabs** — OSINT / News / All with refresh button
5. **Connection log** — scrolling debug console at bottom of right panel
6. **Countdown timer** — 30s until next plane data refresh
7. **Live webcam** — YouTube iframes with camera switcher bar

---

## 9. Monetization / Auth Flow

1. Landing page shows real globe (rotating) + blurred sidebars + CTA overlay
2. "START 7-DAY FREE TRIAL" → Outseta popup (email/password)
3. Token stored in localStorage
4. Main app checks token on load → redirects to landing if expired
5. All Netlify functions appear to be open (no auth check visible in client) — data is technically accessible without paying

---

## 10. Performance Observations

### Good
- Single HTML file (no build step, no framework overhead)
- Entity pooling (removes old entities before re-rendering)
- Plane data caching (25s minimum between fetches)
- MSAA + FXAA for visual quality
- Retina tile support (512px @2x tiles)
- Distance-based LOD on all entities
- `AbortSignal.timeout(10000)` on satellite fetches

### Questionable
- **107KB single file** — no code splitting, no lazy loading
- **`requestRenderMode: false`** — continuous GPU rendering even when idle
- **All entities in one Cesium viewer** — no instancing for planes/strikes
- **No web worker** — satellite propagation runs on main thread
- **Sample data fallback** — hardcoded 20+ sample strikes, 10+ sample odds (bloats file)
- **No service worker** — no offline support (we already have PWA)

---

## 11. Recommended V3 Architecture for Magen Yehuda

### Phase 1: CesiumJS Migration
1. Replace Leaflet with CesiumJS 1.124
2. Keep same CartoDB dark + VIIRS basemap toggle
3. Port all existing layers (fires, seismic, strikes, correlations, bases, SAM rings)
4. Add tilted perspective camera with -60° pitch
5. Add entity LOD (scaleByDistance, distanceDisplayCondition)

### Phase 2: New Data Layers
1. **Polymarket odds panel** — public API, render as probability bars
2. **Satellite tracking** — CelesTrak TLE + satellite.js (GPS, Military, Starlink)
3. **GPS Jamming heatmap** — computed from OpenSky NIC values
4. **AI OSINT classification** — pipe our existing OSINT through event classifier

### Phase 3: UX Enhancements
1. **3-panel layout** — left sidebar (entities) + globe + right sidebar (odds/news/cams)
2. **Info panel** — bottom-right slide-up on entity click
3. **Live webcam feeds** — YouTube embeds from ME conflict zones
4. **Event timeline** — scrollable OSINT feed with severity coloring
5. **Auto-rotation** on idle (landing page style)

### What NOT to Do
- ❌ Don't add auth/paywall (we're open source, this is a public service)
- ❌ Don't use Outseta/Supabase (we have Azure)
- ❌ Don't hardcode sample data (we have real data pipelines)
- ❌ Don't drop our unique features (siren alerts, FIRMS correlation, cyber tracking)

---

## 12. Libraries & CDN URLs

```html
<!-- CesiumJS 1.124 -->
<link href="https://cesium.com/downloads/cesiumjs/releases/1.124/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
<script src="https://cesium.com/downloads/cesiumjs/releases/1.124/Build/Cesium/Cesium.js"></script>

<!-- Satellite.js 5.0.0 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/satellite.js/5.0.0/satellite.min.js"></script>

<!-- Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">

<!-- Cesium Ion Token (free tier) -->
Cesium.Ion.defaultAccessToken = 'GET_YOUR_OWN'; // Free at cesium.com/ion
```

---

## 13. Their OSINT Sources (Telegram Channels)

From their news-proxy response, these Telegram channels are scraped:
- `CIG_telegram` (CIG Intel)
- Plus ~20 others (not fully enumerated in client code)

We already scrape 12+ Telegram channels with better coverage.

---

## 14. Live Camera Feeds

They embed YouTube live streams — 9 camera buttons:
- War zone locations across ME
- Simple `<iframe>` embeds
- Camera bar for switching

This is low-effort, high-impact. We could add a similar panel.

---

## Bottom Line

**MiddleEastTracker is a well-executed CesiumJS app with ~5 data sources and GPT-4 classification.** We already beat it on data breadth (85+ sources), data depth (49K events vs 129), and unique features (siren alerts, fire correlation, cyber tracking, bilingual dispatch). The gap is **presentation** — the 3D globe is genuinely impressive and makes the data feel more real.

**V3 priority: CesiumJS + Polymarket + Satellite tracking.** Everything else is incremental.
