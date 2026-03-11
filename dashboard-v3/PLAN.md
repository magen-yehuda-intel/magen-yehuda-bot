# V3 Implementation Plan — CesiumJS + New Data Layers

## Phase 1: CesiumJS Globe (1-2 days)

### Step 1: Scaffold
- Create `docs/centcom-v3.html` alongside existing `centcom.html`
- Load CesiumJS 1.124 + satellite.js 5.0.0 from CDN
- Keep same CSS variables / color palette / Orbitron+Share Tech Mono fonts
- Free Cesium Ion token (cesium.com/ion signup)

### Step 2: Globe Init
```javascript
// Key settings from middleastracker
viewer = new Cesium.Viewer('cesiumContainer', {
  scene3DOnly: true, msaaSamples: 4,
  // disable all UI chrome
  baseLayerPicker:false, geocoder:false, homeButton:false,
  timeline:false, animation:false, navigationHelpButton:false,
  fullscreenButton:false, infoBox:false, shadows:false,
});
// VIIRS Black Marble (our signature look) OR CartoDB dark
viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
  url: VIIRS_URL, // or CartoDB dark @2x
}));
viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#050505');
viewer.scene.fog.enabled = true;
viewer.scene.fog.density = 0.0002;
viewer.resolutionScale = window.devicePixelRatio;
```

### Step 3: Port Existing Layers
Each existing layer maps to Cesium entities:

| Leaflet Layer | Cesium Entity |
|---------------|---------------|
| `L.circleMarker` (fires) | `point` with `scaleByDistance` |
| `L.circleMarker` (seismic) | `point` + `ellipse` (glow ring) |
| `L.circleMarker` (strikes) | `point` + `label` |
| `L.circleMarker` (correlations) | `point` + pulsing `ellipse` |
| `L.marker` (bases) | `billboard` (SVG) + `label` + `ellipse` |
| `L.circle` (SAM rings) | `ellipse` with semiMajorAxis in meters |
| Country borders (GeoJSON) | `polyline` with neon glow |
| Neon fills (Iran red, Israel blue) | `polygon` with alpha fill |

### Step 4: Camera & Navigation
- Default: `fromDegrees(46, 27, 4000000)`, pitch -50°
- Theater presets: flyTo animations for each region
- Scroll to zoom, drag to orbit (Cesium default)
- Keep zoom buttons (+/-) as overlay

## Phase 2: New Data Layers (1 day each)

### Polymarket Odds Panel
- Endpoint: `https://gamma-api.polymarket.com/events?tag=iran`
- Or proxy through our Azure API to avoid CORS
- Render as right sidebar section with probability bars
- Click → open Polymarket in new tab
- Refresh every 60s

### Satellite Tracking
- Fetch TLE from CelesTrak (5 groups: GPS, Military, ISS, Weather, Starlink)
- Use satellite.js SGP4 for real-time propagation
- Render as billboard + orbit trail polyline
- Toggle layer on/off
- ~180 satellites total (with limits)

### GPS Jamming Heatmap
- Requires ADS-B data with NIC field
- OpenSky free API doesn't include NIC — need ADSBX (paid) or our own receiver
- Grid: 1° cells, color by %bad NIC
- **Park this unless we get ADSBX access**

## Phase 3: UX Polish (1 day)

### 3-Panel Desktop Layout
```
┌──────────────────────────────────────────────────────────┐
│ HEADER: MAGEN YEHUDA INTEL | LIVE | Toggles | Stats     │
├────────┬──────────────────────────────────┬──────────────┤
│  LEFT  │         CESIUM GLOBE             │    RIGHT     │
│  250px │                                  │    320px     │
│        │  HUD (fires/seismic/correlations)│              │
│ OSINT  │  Oref banner (top)               │ Polymarket   │
│ Events │  Info panel (click)              │ News feed    │
│ Bases  │  Correlation details             │ Live cams    │
│ Planes │                                  │ Satellite    │
├────────┴──────────────────────────────────┴──────────────┤
│ FOOTER: Last update | Sources | Threat level             │
└──────────────────────────────────────────────────────────┘
```

### Mobile: Same approach — bottom nav tabs, panels hidden/shown

### New HUD Elements
- Satellite count badge
- Polymarket top odds ticker
- GPS jamming status (if available)

## Phase 4: Auto-Rotation Landing Mode
- When dashboard loads, start with slow globe rotation
- On first user interaction (click/scroll), stop rotation
- Resume after 60s idle

## Dependencies
- CesiumJS: ~3MB compressed (CDN, not our bundle)
- satellite.js: 28KB
- Cesium Ion token: free tier (75,000 tile requests/month)
- Polymarket API: free, no auth
- CelesTrak: free, no auth

## Migration Strategy
- Build v3 as separate file (`centcom-v3.html`)
- Test alongside current `centcom.html`
- Once stable, promote to `/centcom.html` and archive v2

## Files to Create
```
dashboard-v3/
├── ANALYSIS.md           ✅ (this analysis)
├── PLAN.md               ✅ (this file)
├── reference-source.html ✅ (their full source)
├── reference-landing.html ✅ (their landing page)
└── prototype/            (TODO - basic CesiumJS scaffold)
    └── index.html
```
