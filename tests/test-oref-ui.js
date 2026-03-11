#!/usr/bin/env node
/**
 * Oref Dashboard UI Tests — Node.js runner (no dependencies)
 * Run: node tests/test-oref-ui.js
 * 
 * Tests DOM state transitions for the Oref banner, siren markers, and counters.
 * Uses a minimal DOM mock — no jsdom needed.
 */

// ═══════════════════════════════════════════════════════════
// MINIMAL DOM MOCK
// ═══════════════════════════════════════════════════════════

class MockElement {
  constructor(id) {
    this.id = id;
    this.textContent = '';
    this.style = {};
    this._classes = new Set();
    this.classList = {
      add: (c) => this._classes.add(c),
      remove: (c) => this._classes.delete(c),
      contains: (c) => this._classes.has(c),
      toggle: (c) => this._classes.has(c) ? this._classes.delete(c) : this._classes.add(c),
    };
    Object.defineProperty(this.classList, 'length', { get: () => this._classes.size });
  }
  set className(v) { this._classes = new Set(v.split(' ').filter(Boolean)); }
  get className() { return [...this._classes].join(' '); }
}

const elements = {};
['oref-banner','oref-status','oref-updated','oref-conn','oref-last-siren','chip-alert','cnt-sirens'].forEach(id => {
  elements[id] = new MockElement(id);
});

// Set initial classes
elements['oref-status']._classes = new Set(['oref-status', 'safe']);

const document = { getElementById: (id) => elements[id] || new MockElement(id) };

// Mock Leaflet layer
class MockLayer {
  constructor() { this.markers = []; }
  clearLayers() { this.markers = []; }
  addLayer(m) { this.markers.push(m); }
}
class MockMarker {
  constructor(lat, lon, popup) { this.lat = lat; this.lon = lon; this.popup = popup; }
  addTo(layer) { layer.addLayer(this); return this; }
}
const layers = { sirens: new MockLayer() };
function mkPopup(title, sub, body, color) { return `<div style="border-color:${color}"><b>${title}</b><br>${sub}<br>${body}</div>`; }
function mkSirenMarker(lat, lon, popup) { return new MockMarker(lat, lon, popup); }

// ═══════════════════════════════════════════════════════════
// EXTRACT: Functions under test
// ═══════════════════════════════════════════════════════════

function isStandDown(alert) {
  const text = JSON.stringify(alert.desc || alert.title || '');
  return text.includes('ניתן לצאת') || text.includes('האירוע הסתיים');
}

const OREF_GEO = {
  'תל אביב': [32.0853,34.7818], 'ירושלים': [31.7683,35.2137], 'חיפה': [32.7940,34.9896],
  'באר שבע': [31.2530,34.7915], 'אשדוד': [31.8044,34.6553], 'אשקלון': [31.6688,34.5743],
  'שדרות': [31.5250,34.5961], 'קלע אלון': [33.0200,35.6300], 'רמת טראמפ': [33.0000,35.7800],
  'חמת גדר': [32.6800,35.6700], 'אילת': [29.5569,34.9498], 'נתניה': [32.3215,34.8532],
  'פתח תקווה': [32.0841,34.8878], 'ראשון לציון': [31.9730,34.7925], 'רמת גן': [32.0680,34.8241],
  'בני ברק': [32.0834,34.8344],
};

function updateOrefBanner(alerts, serverTs) {
  const banner = document.getElementById('oref-banner');
  const status = document.getElementById('oref-status');
  const updated = document.getElementById('oref-updated');
  if (serverTs) {
    const age = Math.round((Date.now() - new Date(serverTs).getTime()) / 60000);
    updated.textContent = age <= 1 ? 'Updated just now' : `Updated ${age}m ago`;
    if (age > 10) updated.style.color = '#f59e0b'; else updated.style.color = '';
  } else { updated.textContent = ''; }
  const activeAlerts = alerts.filter(a => !isStandDown(a));
  if (activeAlerts.length === 0) {
    banner.classList.remove('alert-active');
    status.className = 'oref-status safe';
    status.textContent = '✅ All Clear';
    document.getElementById('chip-alert').textContent = '0';
  } else {
    banner.classList.add('alert-active');
    status.className = 'oref-status danger';
    const areas = activeAlerts.map(a => a.data || a.title || a.area || '').filter(Boolean);
    status.textContent = `🚨 ACTIVE: ${activeAlerts.length} alert${activeAlerts.length > 1 ? 's' : ''} — ${areas.slice(0,3).join(', ')}${areas.length > 3 ? ' +' + (areas.length-3) + ' more' : ''}`;
    document.getElementById('chip-alert').textContent = activeAlerts.length;
  }
}

function updateSirensFromOref(alerts) {
  layers.sirens.clearLayers();
  let count = 0;
  const active = alerts.filter(a => !isStandDown(a));
  active.forEach(a => {
    (a.data || []).forEach(area => {
      const coords = OREF_GEO[area];
      if (!coords) return;
      count++;
      mkSirenMarker(coords[0], coords[1], mkPopup(`🚨 ${a.title||'Alert'}`, area, `📍 ${area}<br>🔴 ACTIVE NOW`, '#ef4444')).addTo(layers.sirens);
    });
  });
  document.getElementById('chip-alert').textContent = count || '0';
  const sc = document.getElementById('cnt-sirens');
  if (sc) sc.textContent = count;
}

// ═══════════════════════════════════════════════════════════
// TEST RUNNER
// ═══════════════════════════════════════════════════════════

let passed = 0, failed = 0, errors = [];
function test(name, fn) {
  // Reset DOM
  elements['oref-banner']._classes = new Set();
  elements['oref-status']._classes = new Set(['oref-status', 'safe']);
  elements['oref-status'].textContent = '✅ All Clear';
  elements['oref-updated'].textContent = '';
  elements['oref-updated'].style = {};
  elements['chip-alert'].textContent = '0';
  elements['cnt-sirens'].textContent = '0';
  layers.sirens.clearLayers();
  try { fn(); passed++; console.log(`  ✅ ${name}`); }
  catch (e) { failed++; errors.push({ name, error: e.message }); console.log(`  ❌ ${name} — ${e.message}`); }
}
function assert(c, m) { if (!c) throw new Error(m || 'Assertion failed'); }
function assertEqual(a, b, m) { if (String(a) !== String(b)) throw new Error(`${m || ''}: expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); }
const now = () => new Date().toISOString();

// ═══════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════

console.log('\n📋 Banner state transitions');

test('No alerts → All Clear, no alert-active', () => {
  updateOrefBanner([], now());
  assert(!elements['oref-banner'].classList.contains('alert-active'));
  assert(elements['oref-status'].classList.contains('safe'));
  assert(elements['oref-status'].textContent.includes('All Clear'));
  assertEqual(elements['chip-alert'].textContent, '0');
});

test('Active alert → ACTIVE with alert-active class', () => {
  updateOrefBanner([{ cat: '1', title: 'ירי רקטות', data: ['תל אביב'] }], now());
  assert(elements['oref-banner'].classList.contains('alert-active'));
  assert(elements['oref-status'].classList.contains('danger'));
  assert(elements['oref-status'].textContent.includes('ACTIVE'));
});

test('Multiple alerts → correct count', () => {
  updateOrefBanner([{ cat: '1', data: ['תל אביב'] }, { cat: '2', data: ['חיפה'] }], now());
  assert(elements['oref-status'].textContent.includes('2 alerts'));
  assertEqual(elements['chip-alert'].textContent, '2');
});

test('REGRESSION: Cat 10 incoming → shows ACTIVE', () => {
  updateOrefBanner([{ cat: '10', title: 'בדקות הקרובות צפויות להתקבל התרעות באזורך', data: ['קלע אלון'] }], now());
  assert(elements['oref-banner'].classList.contains('alert-active'), 'cat 10 incoming MUST be active');
});

test('Stand-down only → All Clear', () => {
  updateOrefBanner([{ cat: '10', title: 'ניתן לצאת מהמרחב המוגן' }], now());
  assert(!elements['oref-banner'].classList.contains('alert-active'));
  assert(elements['oref-status'].textContent.includes('All Clear'));
});

test('Active → clear transition', () => {
  updateOrefBanner([{ cat: '1', data: ['חיפה'] }], now());
  assert(elements['oref-banner'].classList.contains('alert-active'));
  updateOrefBanner([], now());
  assert(!elements['oref-banner'].classList.contains('alert-active'));
});

test('Mixed active + stand-down → only active counted', () => {
  updateOrefBanner([
    { cat: '1', title: 'ירי רקטות', data: ['באר שבע'] },
    { cat: '10', title: 'ניתן לצאת מהמרחב המוגן', data: ['אשקלון'] },
  ], now());
  assert(elements['oref-status'].textContent.includes('1 alert'));
});

console.log('\n📋 Timestamp freshness');

test('Recent → "Updated just now"', () => {
  updateOrefBanner([], now());
  assert(elements['oref-updated'].textContent.includes('just now') || elements['oref-updated'].textContent.includes('1m'));
});

test('Stale (>10min) → amber', () => {
  updateOrefBanner([], new Date(Date.now() - 15 * 60000).toISOString());
  assertEqual(elements['oref-updated'].style.color, '#f59e0b');
});

test('No timestamp → empty', () => {
  updateOrefBanner([], null);
  assertEqual(elements['oref-updated'].textContent, '');
});

console.log('\n📋 Siren markers');

test('Known areas → markers placed', () => {
  updateSirensFromOref([{ cat: '1', data: ['תל אביב', 'חיפה', 'באר שבע'] }]);
  assertEqual(layers.sirens.markers.length, 3);
});

test('Unknown areas → 0 markers, no crash', () => {
  updateSirensFromOref([{ cat: '1', data: ['fake_place'] }]);
  assertEqual(layers.sirens.markers.length, 0);
});

test('Stand-down → 0 markers', () => {
  updateSirensFromOref([{ cat: '10', title: 'ניתן לצאת מהמרחב המוגן', data: ['תל אביב'] }]);
  assertEqual(layers.sirens.markers.length, 0);
});

test('Clear after active → markers removed', () => {
  updateSirensFromOref([{ cat: '1', data: ['תל אביב'] }]);
  assertEqual(layers.sirens.markers.length, 1);
  updateSirensFromOref([]);
  assertEqual(layers.sirens.markers.length, 0);
});

test('Correct coordinates for known city', () => {
  updateSirensFromOref([{ cat: '1', data: ['אילת'] }]);
  const m = layers.sirens.markers[0];
  assert(Math.abs(m.lat - 29.5569) < 0.01, `lat: ${m.lat}`);
  assert(Math.abs(m.lon - 34.9498) < 0.01, `lon: ${m.lon}`);
});

test('Popup contains area name and ACTIVE NOW', () => {
  updateSirensFromOref([{ cat: '1', title: 'ירי רקטות', data: ['שדרות'] }]);
  assert(layers.sirens.markers[0].popup.includes('שדרות'));
  assert(layers.sirens.markers[0].popup.includes('ACTIVE NOW'));
});

test('Multiple alerts → combined markers', () => {
  updateSirensFromOref([
    { cat: '1', data: ['תל אביב', 'חיפה'] },
    { cat: '2', data: ['באר שבע'] },
  ]);
  assertEqual(layers.sirens.markers.length, 3);
});

test('Large area list → handles all', () => {
  const areas = Object.keys(OREF_GEO);
  updateSirensFromOref([{ cat: '1', data: areas }]);
  assertEqual(layers.sirens.markers.length, areas.length);
});

console.log('\n📋 Counters');

test('chip-alert matches marker count', () => {
  updateSirensFromOref([{ cat: '1', data: ['תל אביב', 'חיפה'] }]);
  assertEqual(elements['chip-alert'].textContent, '2');
});

test('cnt-sirens matches marker count', () => {
  updateSirensFromOref([{ cat: '1', data: ['תל אביב', 'חיפה', 'באר שבע'] }]);
  assertEqual(elements['cnt-sirens'].textContent, '3');
});

test('Counters reset to 0 on clear', () => {
  updateSirensFromOref([{ cat: '1', data: ['תל אביב'] }]);
  updateSirensFromOref([]);
  assertEqual(elements['chip-alert'].textContent, '0');
  assertEqual(elements['cnt-sirens'].textContent, '0');
});

console.log('\n📋 CSS classes');

test('Safe → has "safe", no "danger"', () => {
  updateOrefBanner([], now());
  assert(elements['oref-status'].classList.contains('safe'));
  assert(!elements['oref-status'].classList.contains('danger'));
});

test('Active → has "danger", no "safe"', () => {
  updateOrefBanner([{ cat: '1', data: ['תל אביב'] }], now());
  assert(elements['oref-status'].classList.contains('danger'));
  assert(!elements['oref-status'].classList.contains('safe'));
});

test('Full alert-active toggle cycle', () => {
  assert(!elements['oref-banner'].classList.contains('alert-active'));
  updateOrefBanner([{ cat: '1', data: ['חיפה'] }], now());
  assert(elements['oref-banner'].classList.contains('alert-active'));
  updateOrefBanner([], now());
  assert(!elements['oref-banner'].classList.contains('alert-active'));
  updateOrefBanner([{ cat: '2', data: ['באר שבע'] }], now());
  assert(elements['oref-banner'].classList.contains('alert-active'));
});

console.log('\n📋 Integration');

test('Full poll cycle: API response → banner + markers + counters', () => {
  const alerts = [{ cat: '10', title: 'בדקות הקרובות צפויות', data: ['קלע אלון', 'רמת טראמפ', 'חמת גדר'] }];
  updateOrefBanner(alerts, now());
  updateSirensFromOref(alerts);
  assert(elements['oref-banner'].classList.contains('alert-active'));
  assertEqual(layers.sirens.markers.length, 3);
  assertEqual(elements['cnt-sirens'].textContent, '3');
});

test('10 rapid polls → no leaks', () => {
  for (let i = 0; i < 10; i++) {
    const a = i % 2 === 0 ? [{ cat: '1', data: ['תל אביב', 'חיפה'] }] : [];
    updateOrefBanner(a, now());
    updateSirensFromOref(a);
  }
  assertEqual(layers.sirens.markers.length, 0);
  assertEqual(elements['chip-alert'].textContent, '0');
});

// ═══════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════

console.log(`\n${'═'.repeat(50)}`);
const total = passed + failed;
if (failed === 0) {
  console.log(`✅ ALL ${total} UI TESTS PASSED`);
} else {
  console.log(`❌ ${failed} FAILED / ${total} TOTAL`);
  errors.forEach(e => console.error(`  FAIL: ${e.name} — ${e.error}`));
}
console.log('═'.repeat(50));
process.exit(failed > 0 ? 1 : 0);
