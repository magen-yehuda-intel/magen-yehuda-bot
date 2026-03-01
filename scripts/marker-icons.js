// marker-icons.js — Custom SVG marker icons for the Iran-Israel strikes dashboard
// 24x24px, military-style, high contrast on dark (#0a0e1a) backgrounds

function svgDataUrl(svg) {
  return 'data:image/svg+xml,' + encodeURIComponent(svg.replace(/\n\s*/g, ''));
}

const MARKER_ICONS = {
  'Shelling/Artill./tic attack': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <polygon points="12,1 14,8 21,8 15.5,12.5 17.5,20 12,15.5 6.5,20 8.5,12.5 3,8 10,8" fill="#ff2d2d" stroke="#fff" stroke-width="0.8"/>
      <circle cx="12" cy="12" r="3" fill="#ffaa00" opacity="0.9"/>
    </svg>`),

  'Air/drone strike': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <path d="M12,3 L14,9 L22,11 L14,13 L12,21 L10,13 L2,11 L10,9 Z" fill="#2d9cff" stroke="#fff" stroke-width="0.8"/>
      <circle cx="12" cy="11" r="2" fill="#0a0e1a"/>
    </svg>`),

  'Armed clash': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <line x1="4" y1="20" x2="20" y2="4" stroke="#ff8c00" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="4" y1="4" x2="20" y2="20" stroke="#ff8c00" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="12" cy="12" r="3.5" fill="none" stroke="#fff" stroke-width="1"/>
    </svg>`),

  'Attack': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" fill="none" stroke="#ff2d2d" stroke-width="1.5"/>
      <circle cx="12" cy="12" r="5" fill="none" stroke="#ff2d2d" stroke-width="1.2"/>
      <circle cx="12" cy="12" r="1.5" fill="#ff2d2d"/>
      <line x1="12" y1="1" x2="12" y2="5" stroke="#fff" stroke-width="1"/>
      <line x1="12" y1="19" x2="12" y2="23" stroke="#fff" stroke-width="1"/>
      <line x1="1" y1="12" x2="5" y2="12" stroke="#fff" stroke-width="1"/>
      <line x1="19" y1="12" x2="23" y2="12" stroke="#fff" stroke-width="1"/>
    </svg>`),

  'Remote explosive/landmine/IED': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <ellipse cx="12" cy="15" rx="7" ry="6" fill="#ffd600" stroke="#fff" stroke-width="0.8"/>
      <rect x="10" y="4" width="4" height="8" rx="1" fill="#ffd600" stroke="#fff" stroke-width="0.8"/>
      <line x1="12" y1="1" x2="12" y2="4" stroke="#ff6600" stroke-width="2" stroke-linecap="round"/>
      <line x1="10" y1="2" x2="14" y2="2" stroke="#ff6600" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`),

  'Location': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <ellipse cx="12" cy="18" rx="8" ry="3" fill="none" stroke="#00e5ff" stroke-width="1"/>
      <ellipse cx="12" cy="18" rx="5" ry="2" fill="none" stroke="#00e5ff" stroke-width="0.8" opacity="0.6"/>
      <line x1="12" y1="3" x2="12" y2="15" stroke="#00e5ff" stroke-width="1.5"/>
      <circle cx="12" cy="4" r="3" fill="#00e5ff" stroke="#fff" stroke-width="0.8"/>
    </svg>`),

  'Suicide bomb': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <circle cx="12" cy="10" r="7" fill="#8b0000" stroke="#fff" stroke-width="0.8"/>
      <circle cx="9" cy="8" r="1.5" fill="#0a0e1a"/>
      <circle cx="15" cy="8" r="1.5" fill="#0a0e1a"/>
      <path d="M8,13 Q12,17 16,13" fill="none" stroke="#0a0e1a" stroke-width="1.5"/>
      <line x1="7" y1="20" x2="10" y2="16" stroke="#8b0000" stroke-width="1.5"/>
      <line x1="17" y1="20" x2="14" y2="16" stroke="#8b0000" stroke-width="1.5"/>
    </svg>`),

  'FIRMS': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <path d="M12,2 Q14,8 18,12 Q14,10 14,16 Q12,12 10,16 Q10,10 6,12 Q10,8 12,2 Z" fill="#ff8c00" stroke="#fff" stroke-width="0.7"/>
      <path d="M12,8 Q13,11 15,13 Q13,12 13,16 Q12,13 11,16 Q11,12 9,13 Q11,11 12,8 Z" fill="#ffd600" opacity="0.8"/>
      <ellipse cx="12" cy="21" rx="5" ry="1.5" fill="#ff8c00" opacity="0.3"/>
    </svg>`),

  'Siren': svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <path d="M7,14 L7,10 Q7,4 12,4 Q17,4 17,10 L17,14 Z" fill="#ff2d2d" stroke="#fff" stroke-width="0.8"/>
      <rect x="5" y="14" width="14" height="3" rx="1" fill="#cc0000" stroke="#fff" stroke-width="0.8"/>
      <circle cx="12" cy="10" r="2" fill="#fff" opacity="0.9"/>
      <line x1="3" y1="6" x2="6" y2="8" stroke="#ff2d2d" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="21" y1="6" x2="18" y2="8" stroke="#ff2d2d" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="12" y1="17" x2="12" y2="22" stroke="#aaa" stroke-width="1.5"/>
      <line x1="8" y1="22" x2="16" y2="22" stroke="#aaa" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`)
};

const MARKER_LEGEND = [
  { type: 'Shelling/Artill./tic attack', icon: MARKER_ICONS['Shelling/Artill./tic attack'], label: 'Shelling / Artillery / Missile', color: '#ff2d2d' },
  { type: 'Air/drone strike',            icon: MARKER_ICONS['Air/drone strike'],            label: 'Air / Drone Strike',          color: '#2d9cff' },
  { type: 'Armed clash',                 icon: MARKER_ICONS['Armed clash'],                 label: 'Armed Clash',                 color: '#ff8c00' },
  { type: 'Attack',                      icon: MARKER_ICONS['Attack'],                      label: 'Attack',                      color: '#ff2d2d' },
  { type: 'Remote explosive/landmine/IED', icon: MARKER_ICONS['Remote explosive/landmine/IED'], label: 'IED / Landmine / Explosive', color: '#ffd600' },
  { type: 'Location',                    icon: MARKER_ICONS['Location'],                    label: 'OSINT Location Mention',      color: '#00e5ff' },
  { type: 'Suicide bomb',                icon: MARKER_ICONS['Suicide bomb'],                label: 'Suicide Bomb',                color: '#8b0000' },
  { type: 'FIRMS',                       icon: MARKER_ICONS['FIRMS'],                       label: 'FIRMS Fire Detection',        color: '#ff8c00' },
  { type: 'Siren',                       icon: MARKER_ICONS['Siren'],                       label: 'Siren (Pikud HaOref)',        color: '#ff2d2d' }
];

// For use in browser (global) or module environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MARKER_ICONS, MARKER_LEGEND };
}
