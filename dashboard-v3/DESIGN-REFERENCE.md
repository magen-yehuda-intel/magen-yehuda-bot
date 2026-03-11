# V3 Design Reference — Extracted Components

## Color System (Identical to ours — great minds think alike)
```css
:root {
  --amber: #ffb600;      /* Primary accent (headers, highlights) */
  --amber-glow: rgba(255,182,0,.07);
  --amber-dim: rgba(255,182,0,.5);
  --bg: #0a0800;          /* Pure dark background */
  --panel: #0e0c00;       /* Panel/sidebar background */
  --panel2: #131000;      /* Elevated panel */
  --border: #2a2200;      /* Default border */
  --border-lit: #3a2f00;  /* Highlighted border */
  --text: #e8c87a;        /* Primary text (warm amber) */
  --text-dim: #7a6230;    /* Secondary text */
  --text-muted: #4a3d20;  /* Tertiary text */
  --green: #39ff7a;       /* Status/Live indicator */
  --red: #ff3b3b;         /* Danger/strikes */
  --blue: #4ab8ff;        /* Naval/info */
  --purple: #cc88ff;      /* Critical severity */
  --sand: #c4a35a;        /* Resources/oil */
  --cyan: #00eeff;        /* Aircraft */
  --mil: #aaff00;         /* Military callsigns */
  --strike: #ff2222;      /* Strike events */
}
```

## Entity Color Map (by type)
```javascript
const TCOLOR = {
  'Air Base': '#ffb600',   // Amber
  'Naval':    '#4ab8ff',   // Blue
  'Army':     '#39ff7a',   // Green
  'Joint':    '#ff3b3b',   // Red
  'Forward':  '#cc88ff',   // Purple
};

const EVENT_ICON_MAP = {
  'Kinetic Strike':    { color:'#ff2222', symbol:'💥', size:28 },
  'Explosion':         { color:'#ff6600', symbol:'💥', size:24 },
  'Air Activity':      { color:'#aaff00', symbol:'✈', size:22 },
  'Naval Activity':    { color:'#cc88ff', symbol:'🚢', size:22 },
  'Ground Movement':   { color:'#ff8800', symbol:'🪖', size:22 },
  'WMD / CBRN':        { color:'#ff00ff', symbol:'☢', size:30 },
  'Air Defense':       { color:'#00eeff', symbol:'🛡', size:24 },
  'Infrastructure Hit':{ color:'#ff4400', symbol:'🔥', size:24 },
  'Cyber / EW':        { color:'#00ffcc', symbol:'📡', size:20 },
  'Diplomatic':        { color:'#39ff7a', symbol:'🤝', size:18 },
  'Civilian Incident': { color:'#ff3b3b', symbol:'🚨', size:22 },
  'Intel / OSINT':     { color:'#4ab8ff', symbol:'🔍', size:18 },
  'Unconfirmed':       { color:'#7a6230', symbol:'⚠', size:16 },
};
```

## CRT Scanline Effect
```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(
    0deg,
    transparent, transparent 3px,
    rgba(255,182,0,.01) 3px,
    rgba(255,182,0,.01) 4px
  );
}
```

## Key Animations
```css
/* Pulsing live dot */
@keyframes blink {
  0%,100% { opacity:1 }
  50% { opacity:.2 }
}

/* Critical event border pulse */
@keyframes critPulse {
  0%,100% { border-left-color: var(--purple) }
  50% { border-left-color: var(--red) }
}
```

## Cesium Entity Patterns

### Base Marker (with glow ring)
```javascript
viewer.entities.add({
  position: Cesium.Cartesian3.fromDegrees(lng, lat),
  point: {
    pixelSize: 10,
    color: c.withAlpha(0.6),
    outlineColor: c,
    outlineWidth: 2,
  },
  label: {
    text: name.toUpperCase(),
    font: '9px Orbitron',
    fillColor: c.withAlpha(0.7),
    pixelOffset: new Cesium.Cartesian2(0, -16),
    scaleByDistance: new Cesium.NearFarScalar(1e5, 1, 5e6, 0.3),
    distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 3e6),
  },
  ellipse: {
    semiMajorAxis: 45000,
    semiMinorAxis: 45000,
    material: c.withAlpha(0.04),
    outline: true,
    outlineColor: c.withAlpha(0.1),
  },
});
```

### Aircraft Billboard (rotated SVG arrow)
```javascript
// Generate colored SVG arrow rotated to heading
function planeIcon(color, heading) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
    <g transform="rotate(${heading},14,14)">
      <polygon points="14,2 8,24 14,19 20,24" fill="${color}" fill-opacity="0.9"/>
    </g></svg>`;
  return 'data:image/svg+xml;base64,' + btoa(svg);
}
```

### Satellite with Orbit Trail
```javascript
// Orbit polyline (90min ahead, 60 points)
const orbitPositions = [];
for (let m = 0; m <= 90; m += 1.5) {
  const futureTime = new Date(now.getTime() + m * 60000);
  const pv = satellite.propagate(satrec, futureTime);
  const gmst = satellite.gstime(futureTime);
  const geo = satellite.eciToGeodetic(pv.position, gmst);
  orbitPositions.push(
    satellite.degreesLong(geo.longitude),
    satellite.degreesLat(geo.latitude),
    geo.height * 1000
  );
}
viewer.entities.add({
  polyline: {
    positions: Cesium.Cartesian3.fromDegreesArrayHeights(orbitPositions),
    material: color.withAlpha(0.15),
    width: 1,
  },
});
```

## Polymarket API (No Auth)
```javascript
// Fetch conflict markets
const r = await fetch('https://gamma-api.polymarket.com/events?tag=iran&limit=20');
const events = await r.json();
// Each event has: title, slug, markets[{question, prices[yes,no], volume24h}]
```

## CelesTrak TLE (No Auth)
```
GPS:      https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle
Military: https://celestrak.org/NORAD/elements/gp.php?GROUP=military&FORMAT=tle
Stations: https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle
Weather:  https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle
Starlink: https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle
```
