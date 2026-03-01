# V2 Dashboard — CENTCOM Theater Operations Map
## Inspired by usvsiran.com, built better

### Design Philosophy
- **NASA Black Marble** satellite imagery as primary basemap (night lights)
- **Neon glow aesthetic** — markers emit colored light halos, pulsing animations
- **Military ops feel** — Orbitron/Rajdhani/JetBrains Mono fonts, glass panels
- **Layered toggleable data** — each data source is a separate toggle layer
- **Real-time data feeds** — aircraft, ships, satellites, fires, GPS jamming
- **Three themes**: Default (dark blue), Red Alert (dark crimson), Schematic (minimal)

---

## LAYERS (toolbar toggle buttons)

### 1. Country Borders & Fills
- **Source**: Natural Earth GeoJSON (`ne_110m_admin_0_countries.geojson`)
- **Visual**: Iran filled red (rgba), Israel filled blue, allies blue-tinted
- **Borders**: Neon-glow SVG filter, pulsing opacity animation (3s cycle)

### 2. Military Bases & Forces
- **US Forces** (blue glow family):
  - US Air Bases: ✈ blue glow, drop-shadow
  - US Naval: ⚓ cyan glow
  - USMC: 🎖 red-blue glow
  - Allied Air Defense: 🛡 cyan
- **Iran/Adversary** (red/amber glow family):
  - Nuclear Sites: ☢ amber, PULSING animation (`pulse-threat` 2s infinite)
  - Missile Sites: 🚀 orange glow
  - Naval Bases: 🚢 pink glow
  - Air Defense (SAM): 🛡 yellow glow + SAM range rings
  - Air Bases: ✈ purple glow
  - IRGC Facilities: ⚔ red glow
  - Oil & Gas: 🛢 orange glow
- **Data**: Static JSON arrays embedded or loaded from our existing data

### 3. SAM Range Rings
- **Visual**: Concentric circles around Iran AD sites
- S-300: 200km rings (dashed, amber, pulsing `defense-ring-pulse` 2.5s)
- S-400: 400km rings (solid, red)
- Bavar-373: 300km rings
- Tor-M1: 12km (short range)
- **Animation**: `defense-ring-active` opacity oscillation 0.3→0.7

### 4. Strategic Waterways
- **Strait of Hormuz**: Cyan neon line with glow filter + ⚓ marker
- **Bab el-Mandeb**: Cyan line
- **Suez Canal**: Cyan line
- **Visual**: SVG `neon-glow` filter (`#neonGlow` feGaussianBlur), opacity pulse 3s

### 5. Air Patrol Routes
- **Known CAP patterns**: Persian Gulf racetrack patterns
- **Visual**: Green dashed lines with arrow markers
- **Animation**: Dash offset animation (flowing)

### 6. Live Aircraft (ADS-B)
- **Source**: OpenSky Network or ADS-B Exchange (free tier)
  - Endpoint: `https://opensky-network.org/api/states/all?lamin=10&lomin=25&lamax=42&lomax=65`
  - Filter: Military hex codes (AE- = US military, etc.)
- **Visual**: Rotating aircraft emoji with heading, trail line
- **Polling**: Every 30s
- **Counter chip**: "✈ LIVE X (Y ↑)" in top bar

### 7. Live Ship Tracking (AIS)
- **Source**: AISStream.io WebSocket (free tier 1 connection)
  - OR MarineTraffic free API
  - OR scrape from MarineTraffic embed
- **Filter**: US Navy vessels (MMSI ranges), carrier groups
- **Visual**: 🚢 markers with heading indicator, wake trail
- **Counter chip**: "🚢 AIS X" in top bar

### 8. GPS Jamming Heatmap
- **Source**: GPSJam.org (H3 hexagonal cells)
  - `https://gpsjam.org/api/data?date=YYYY-MM-DD` (if accessible)
  - OR scrape their tile data
- **Visual**: Hexagonal cells colored by interference level
  - High: red (#ef4444), opacity 0.55
  - Medium: orange, opacity 0.35
  - Low: yellow, opacity 0.2

### 9. FIRMS Fire Hotspots
- **Source**: Already have! FIRMS API (our existing scan-fires.py)
- **Visual**: 🔥 markers with pulsing glow animation
- **Size**: Confidence-based (high=large, low=small)

### 10. Reconnaissance Satellites
- **Source**: CelesTrak TLE data → SGP4 propagation in JS
  - Key sats: USA-224 (KH-11), USA-314, Ofek-16, Eros-B
  - TLE: `https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle`
- **Visual**: 🛰 markers with orbit trace line, overhead pass countdown
- **Counter chip**: "SAT X (Y overpasses)" in top bar

### 11. OSINT Events
- **Source**: Our existing intel-log.jsonl + GeoConfirmed API
  - GeoConfirmed: `https://geoconfirmed.org/api/v2/locations?region=iran`
- **Visual**: 📌 markers with `missile-impact` animation for recent strikes
- **Categories**: recent_24h (bright red pulse), recent_7d (orange), older (dim)

### 12. Aviation NOTAMs
- **Source**: ICAO API or FAA NOTAM API
  - `https://notams.aim.faa.gov/notamSearch/` (free)
- **Visual**: ⚠ markers for airspace closures
- **Significance**: Active NOTAMs often precede military operations

---

## UI COMPONENTS

### Top Bar (Title)
- 🇺🇸 **U.S. & Allies** vs. Islamic Republic of **IRAN** 🇮🇷
- Gradient glow line beneath (blue → white → red)
- Blue text-shadow for "U.S.", red text-shadow for "IRAN"

### Toolbar (left vertical strip, round gold buttons)
- Icon for each layer toggle
- Active state: colored background + glow
- Inactive: glass blur dark
- Tooltip on hover

### Counter Chips (bottom-left horizontal)
- 🛡 ALERT: Active alert count (red pulse when >0)
- 🛰 SAT: Tracked satellites (overhead count)
- ✈ LIVE: Aircraft tracked (military count)
- 🚢 AIS: Ships tracked
- **Glass cards with backdrop-filter: blur(4px)**

### Sidebar (slide from left)
- **LAYERS tab**: Toggle each data layer with counts
  - Section headers: US FORCES / IRAN-ADVERSARY / OVERLAYS
  - Quick filters: "Show All", "US Forces Only", "Iran Targets Only"
- **ASSETS tab**: Searchable list of all assets
- **Glass panel**: `background: linear-gradient(rgb(10,15,30), rgb(7,11,22))`

### Legend Panel (bottom-right)
- Color-coded force type dots
- Two columns layout

### Map Controls
- Zoom +/−
- Basemap toggle: "Map" (CARTO dark) / "VIIRS" (satellite night lights)

---

## CSS ANIMATIONS (from usvsiran.com)

```css
@keyframes pulse-threat {
  0%, 100% { box-shadow: 0 0 8px rgba(245,158,11,0.4); }
  50% { box-shadow: 0 0 24px rgba(245,158,11,0.8), 0 0 48px rgba(245,158,11,0.3); }
}

@keyframes defense-ring-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.7; }
}

@keyframes missile-impact-anim {
  0%, 100% { opacity: 0.8; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.4); }
}

@keyframes neon-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 0.85; }
}

@keyframes pin-bounce {
  0% { opacity: 0; transform: translateY(-20px) scale(1.2); }
  60% { opacity: 1; transform: translateY(2px) scale(0.95); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes alert-pulse-anim {
  0%, 100% { opacity: 0.8; stroke-width: 2px; }
  50% { opacity: 0.3; stroke-width: 4px; }
}
```

## MARKER STYLING
- **All markers**: `backdrop-filter: blur(2px)`, round border, emoji center
- **Hover**: `transform: scale(1.4)`, glow box-shadow expands
- **Transition**: `transform 0.2s, box-shadow 0.2s`
- **filter: drop-shadow(COLOR 0 0 8px)** for glow effect
- **Cluster icons**: Blur bg, cyan border, count number

---

## BASEMAPS

1. **VIIRS Black Marble** (default):
   `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}/20.png`
   
2. **CARTO Dark**:
   `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`

---

## DATA FILES TO BUILD

### Static Data (embedded in HTML)
1. `v2-bases.json` — US + allied military bases (25+ entries)
2. `v2-iran-military.json` — Nuclear (18), Missile (52), Naval (9), AD (26), Air (29), IRGC (8), Oil & Gas (38)
3. `v2-sam-ranges.json` — AD site coords + system type + range in km
4. `v2-waterways.json` — GeoJSON lines for Hormuz, Bab el-Mandeb, Suez
5. `v2-patrol-routes.json` — CAP racetrack patterns (GeoJSON lines)

### Live Data (fetched at runtime)
6. Aircraft: OpenSky API every 30s
7. Ships: AIS data every 60s
8. GPS Jamming: GPSJam H3 cells daily
9. Fires: FIRMS API every 15min
10. OSINT: Our intel-feed.json every 60s
11. Satellites: CelesTrak TLEs + SGP4.js propagation

### Country GeoJSON
12. Natural Earth 110m countries: `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson`

---

## IMPLEMENTATION ORDER

### Phase 1: Core Map + Static Layers (2h)
1. HTML skeleton with NASA Black Marble basemap + CARTO toggle
2. Title bar with gradient glow
3. Country borders with neon glow + Iran red fill
4. Military bases with glowing emoji markers + hover effects
5. SAM range rings with pulsing animation
6. Toolbar with layer toggles

### Phase 2: Live Data Layers (2h)
7. FIRMS fire overlay (from our existing data)
8. OSINT events layer (from intel-feed.json)
9. GPS Jamming heatmap (from GPSJam)
10. Strategic waterways + air patrol routes
11. Counter chips with live counts

### Phase 3: Real-Time Feeds (2h)
12. Aircraft tracking (ADS-B/OpenSky)
13. Ship tracking (AIS)
14. Satellite tracking (TLE + SGP4)
15. Sidebar with LAYERS + ASSETS tabs
16. Legend panel

### Phase 4: Polish + Deploy (1h)
17. Mobile responsive
18. Three themes (default/red-alert/schematic)
19. Keyboard shortcuts
20. Build standalone + deploy to GitHub Pages
