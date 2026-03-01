// marker-icons.js — Custom SVG marker icons for strikes dashboard
// Design: NATO APP-6 inspired, high contrast on dark (#0a0e1a), 32×32 viewBox
// Each icon has a distinct silhouette identifiable at 16px+

function svgIcon(svg, size) {
  size = size || 32;
  return 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="'+size+'" height="'+size+'" viewBox="0 0 32 32">' + svg + '</svg>'
  );
}

const MARKER_SVG = {
  // 💥 Shelling / Artillery / Missile — Red starburst explosion
  'Shelling/artillery/missile attack': (color) => svgIcon(`
    <defs><radialGradient id="g1" cx="50%" cy="50%"><stop offset="0%" stop-color="#fff" stop-opacity="0.9"/>
    <stop offset="40%" stop-color="${color||'#ff2d2d'}" stop-opacity="0.8"/><stop offset="100%" stop-color="${color||'#ff2d2d'}" stop-opacity="0"/></radialGradient></defs>
    <circle cx="16" cy="16" r="14" fill="url(#g1)"/>
    <polygon points="16,1 18.5,11 28,8 21,15 31,16 21,17 28,24 18.5,21 16,31 13.5,21 4,24 11,17 1,16 11,15 4,8 13.5,11" fill="${color||'#ff2d2d'}" opacity="0.95"/>
    <circle cx="16" cy="16" r="5" fill="#fff" opacity="0.85"/>
    <circle cx="16" cy="16" r="2.5" fill="${color||'#ff2d2d'}"/>
  `),

  // ✈️ Air/Drone Strike — Jet silhouette with impact burst
  'Air/drone strike': (color) => svgIcon(`
    <defs><radialGradient id="g2" cx="50%" cy="70%"><stop offset="0%" stop-color="#fff" stop-opacity="0.6"/>
    <stop offset="100%" stop-color="${color||'#2d9cff'}" stop-opacity="0"/></radialGradient></defs>
    <circle cx="16" cy="20" r="10" fill="url(#g2)"/>
    <path d="M16,3 L18,10 L26,13 L18,14 L20,22 L16,17 L12,22 L14,14 L6,13 L14,10 Z" 
      fill="${color||'#2d9cff'}" stroke="#fff" stroke-width="0.5" opacity="0.95"/>
    <path d="M13,24 L16,20 L19,24" fill="none" stroke="#ffaa00" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="14" y1="26" x2="18" y2="26" stroke="#ff6600" stroke-width="1" opacity="0.7"/>
  `),

  // ⚔️ Armed Clash — Crossed rifles/swords
  'Armed clash': (color) => svgIcon(`
    <line x1="6" y1="26" x2="26" y2="6" stroke="${color||'#ff8c00'}" stroke-width="3" stroke-linecap="round"/>
    <line x1="6" y1="6" x2="26" y2="26" stroke="${color||'#ff8c00'}" stroke-width="3" stroke-linecap="round"/>
    <polygon points="24,4 28,4 28,8" fill="${color||'#ff8c00'}"/>
    <polygon points="4,4 8,4 4,8" fill="${color||'#ff8c00'}"/>
    <polygon points="24,28 28,28 28,24" fill="${color||'#ff8c00'}"/>
    <polygon points="4,28 8,28 4,24" fill="${color||'#ff8c00'}"/>
    <circle cx="16" cy="16" r="4" fill="#0a0e17" stroke="${color||'#ff8c00'}" stroke-width="1.5"/>
    <circle cx="16" cy="16" r="1.5" fill="${color||'#ff8c00'}"/>
  `),

  // 🎯 Attack — Crosshair/target reticle
  'Attack': (color) => svgIcon(`
    <circle cx="16" cy="16" r="12" fill="none" stroke="${color||'#ff2d2d'}" stroke-width="1.5" opacity="0.7"/>
    <circle cx="16" cy="16" r="7" fill="none" stroke="${color||'#ff2d2d'}" stroke-width="1.5" opacity="0.85"/>
    <circle cx="16" cy="16" r="2.5" fill="${color||'#ff2d2d'}"/>
    <line x1="16" y1="1" x2="16" y2="8" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="16" y1="24" x2="16" y2="31" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="1" y1="16" x2="8" y2="16" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="24" y1="16" x2="31" y2="16" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
  `),

  // 💣 Remote Explosive / IED — Classic bomb
  'Remote explosive/landmine/IED': (color) => svgIcon(`
    <circle cx="16" cy="18" r="10" fill="${color||'#ffd600'}" stroke="#fff" stroke-width="0.8" opacity="0.9"/>
    <rect x="14" y="5" width="4" height="7" rx="1.5" fill="${color||'#ffd600'}" stroke="#fff" stroke-width="0.7"/>
    <line x1="16" y1="2" x2="16" y2="5" stroke="#ff6600" stroke-width="2" stroke-linecap="round"/>
    <circle cx="16" cy="1.5" r="1.5" fill="#ff4400" opacity="0.9"/>
    <text x="16" y="21" text-anchor="middle" font-family="sans-serif" font-size="9" font-weight="bold" fill="#0a0e17">IED</text>
  `),

  // 📡 OSINT Location Mention — Radar pulse
  'Location mention in OSINT': (color) => svgIcon(`
    <circle cx="16" cy="16" r="14" fill="none" stroke="${color||'#00e5ff'}" stroke-width="0.7" opacity="0.3"/>
    <circle cx="16" cy="16" r="10" fill="none" stroke="${color||'#00e5ff'}" stroke-width="0.8" opacity="0.5"/>
    <circle cx="16" cy="16" r="6" fill="none" stroke="${color||'#00e5ff'}" stroke-width="1" opacity="0.7"/>
    <circle cx="16" cy="16" r="3" fill="${color||'#00e5ff'}" opacity="0.9"/>
    <line x1="16" y1="16" x2="28" y2="8" stroke="${color||'#00e5ff'}" stroke-width="1.2" opacity="0.8"/>
  `),

  // 💀 Suicide Bomb — Skull with blast ring
  'Suicide bomb': (color) => svgIcon(`
    <circle cx="16" cy="16" r="13" fill="none" stroke="${color||'#8b0000'}" stroke-width="2" opacity="0.5" stroke-dasharray="3,2"/>
    <circle cx="16" cy="14" r="8" fill="${color||'#8b0000'}" stroke="#fff" stroke-width="0.7"/>
    <circle cx="13" cy="12" r="2" fill="#0a0e17"/>
    <circle cx="19" cy="12" r="2" fill="#0a0e17"/>
    <rect x="12" y="17" width="8" height="2" rx="1" fill="#0a0e17"/>
    <line x1="13" y1="17" x2="13" y2="19" stroke="${color||'#8b0000'}" stroke-width="1"/>
    <line x1="16" y1="17" x2="16" y2="19" stroke="${color||'#8b0000'}" stroke-width="1"/>
    <line x1="19" y1="17" x2="19" y2="19" stroke="${color||'#8b0000'}" stroke-width="1"/>
    <path d="M10,22 L16,26 L22,22" fill="none" stroke="${color||'#8b0000'}" stroke-width="1.5"/>
  `),

  // 🔥 Possible Strike (FIRMS) — Flame
  'Possible strike (FIRMS)': (color) => svgIcon(`
    <path d="M16,2 C18,8 23,10 22,16 C22,20 20,24 16,28 C12,24 10,20 10,16 C9,10 14,8 16,2 Z" 
      fill="${color||'#ff8800'}" stroke="#fff" stroke-width="0.5" opacity="0.9"/>
    <path d="M16,10 C17,13 19,14 19,17 C19,19 18,21 16,23 C14,21 13,19 13,17 C13,14 15,13 16,10 Z" 
      fill="#ffd600" opacity="0.85"/>
    <ellipse cx="16" cy="29" rx="6" ry="1.5" fill="${color||'#ff8800'}" opacity="0.25"/>
  `),

  // 🌡️ Thermal Anomaly (FIRMS) — Heat shimmer
  'Thermal anomaly (FIRMS)': (color) => svgIcon(`
    <path d="M8,28 C8,20 12,22 12,14 C12,10 10,8 10,4" fill="none" stroke="${color||'#ff8800'}" stroke-width="2" stroke-linecap="round" opacity="0.5"/>
    <path d="M16,28 C16,20 20,22 20,14 C20,10 18,8 18,4" fill="none" stroke="${color||'#ff8800'}" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
    <path d="M24,28 C24,20 28,22 28,14 C28,10 26,8 26,4" fill="none" stroke="${color||'#ff8800'}" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
    <circle cx="16" cy="16" r="4" fill="${color||'#ff8800'}" opacity="0.6"/>
  `),

  // 🚨 Siren Alert — Alert beacon
  'Siren alert': (color) => svgIcon(`
    <path d="M8,18 L8,12 C8,6 12,3 16,3 C20,3 24,6 24,12 L24,18 Z" fill="${color||'#ff2d2d'}" stroke="#fff" stroke-width="0.8"/>
    <rect x="6" y="18" width="20" height="4" rx="1.5" fill="#cc0000" stroke="#fff" stroke-width="0.7"/>
    <circle cx="16" cy="12" r="3" fill="#fff" opacity="0.85"/>
    <path d="M4,8 L7,10" stroke="${color||'#ff2d2d'}" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
    <path d="M28,8 L25,10" stroke="${color||'#ff2d2d'}" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
    <line x1="16" y1="22" x2="16" y2="29" stroke="#888" stroke-width="2"/>
    <line x1="10" y1="29" x2="22" y2="29" stroke="#888" stroke-width="2" stroke-linecap="round"/>
  `),
};
