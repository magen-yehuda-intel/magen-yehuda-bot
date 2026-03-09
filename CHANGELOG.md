
## 2026-03-09 — CENTCOM Dashboard Major Update

### New Features
- **🛰️ Recon Satellite Tracking**: 10 imaging/recon satellites (WorldView-3, Pléiades Neo, EROS C3, KOMPSAT-3A, Sentinel-2A/2B, PRAETORIAN SDA, SAPPHIRE) with real-time SGP4 orbital propagation via satellite.js, ground tracks (±15 min), imaging swath overlays, green pulse when over ME
- **🚢 US Navy Fleet Layer**: 11 vessels (CVN-75 Truman, CVN-70 Vinson, LHD-5 Bataan, CG-64, DDG-55/107/109, SSGN-728 Florida, USNS Supply, INS Magen, INS Dolphin) with OSINT-based positions
- **📡 GPS Jamming Zones**: 9 known interference areas (Eastern Med, Hormuz, Tehran, Isfahan, Bushehr, Yemen, Libya, Sinai) with severity levels and pulsing high zones
- **🔥 Fire Mode Cycling**: 5-mode button (OFF/<1H/1-3H/3-6H/ALL) with colored 🔥 icon feedback
- **🚨 Pikud HaOref History**: Click the Oref banner → transparent overlay showing last 3 siren alerts
- **✈️ Aircraft from own API**: Switched from OpenSky (no CORS) to our API — 435 planes with airline, type, from/to airports

### Performance
- **Viewport-based rendering**: OSINT + fire markers only render within 2x viewport buffer, re-render on pan/zoom (300ms debounce)

### UI/UX
- Title changed to "U.S. & ISRAEL vs. IRAN"
- OSINT events OFF by default (reduce visual noise)
- Base labels ON by default
- Fires default to 1-3H timeframe
- Ticker 2x slower (48s/item, min 360s cycle) + click to pause/resume
- Fire button icon: 🔥 with colored glow (red/orange/grey) per mode instead of ⬤ circle

### Bug Fixes
- Satellites: embedded TLE data (CelesTrak has no CORS headers)
- Aircraft: routed through own API (OpenSky has no CORS headers)
- Trail loading: CORS proxy fallback for OpenSky tracks API
