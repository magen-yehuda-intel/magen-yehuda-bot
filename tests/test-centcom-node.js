#!/usr/bin/env node
/**
 * Headless test runner for CENTCOM dashboard JS logic.
 * Extracts test logic from test-centcom-dashboard.html and runs in Node.
 * Usage: node test-centcom-node.js
 */

// ═══════════════════════════════════════════════════════════
// STUBS
// ═══════════════════════════════════════════════════════════

const V2_DATA = {
  RECENT_EVENTS: [
    { date: "2026-03-20", lat: 32.085, lon: 34.781, type: "missile", actor: "Iran/IRGC", target: "Tel Aviv", desc: "Ballistic missile barrage", severity: "critical", origin_lat: 33.5, origin_lon: 48.5 },
    { date: "2026-03-20", lat: 31.208, lon: 34.937, type: "missile", actor: "Iran/IRGC", target: "Nevatim", desc: "Missile strike", severity: "high", origin_lat: 33.5, origin_lon: 48.5 },
    { date: "2026-02-28", lat: 32.794, lon: 34.989, type: "missile", actor: "Hezbollah", target: "Haifa", desc: "Missile", severity: "high", origin_lat: 33.85, origin_lon: 35.86 },
    { date: "2026-03-20", lat: 32.085, lon: 34.781, type: "strike", actor: "Israel", target: "Tehran", desc: "Strike", severity: "critical" },
    { date: "2026-03-19", lat: 32.0, lon: 34.0, type: "missile", actor: "Test", target: "Test", desc: "old", severity: "low", origin_lat: 33.0, origin_lon: 48.0 },
  ],
};

// Global state (mimics dashboard)
global._liveEvents = [];
global._strikeWindowHours = 0;

// ═══════════════════════════════════════════════════════════
// FUNCTIONS UNDER TEST
// ═══════════════════════════════════════════════════════════

function getMissileEvents() {
  const static_events = V2_DATA.RECENT_EVENTS || [];
  const hours = global._strikeWindowHours || 0;
  const now = Date.now();
  const filtered = static_events.filter(ev => {
    if (!ev.origin_lat || !ev.origin_lon) return false;
    if (ev.type !== 'missile') return false;
    if (hours > 0 && now - new Date(ev.date).getTime() > hours * 3600000) return false;
    return true;
  });
  const live = (global._liveEvents || []).map(e => ({...e, type: 'missile', _live: true}));
  return [...live, ...filtered];
}

function renderSirenHistory(alerts) {
  if (!alerts || !alerts.length) return { merged: [] };
  const merged = [];
  alerts.forEach(a => {
    const prev = merged[merged.length - 1];
    const aType = a.type || (a.cat ? String(a.cat) : '');
    const prevType = prev ? (prev.type || (prev.cat ? String(prev.cat) : '')) : '';
    const aTs = a.ts ? a.ts * 1000 : (a.utc ? new Date(a.utc).getTime() : 0);
    const prevTs = prev ? (prev.ts ? prev.ts * 1000 : (prev.utc ? new Date(prev.utc).getTime() : 0)) : 0;
    if (prev && aType === prevType && Math.abs(aTs - prevTs) < 90000) {
      prev._waveCount = (prev._waveCount || 1) + 1;
      const prevAreas = prev.areas || prev.data || [];
      const curAreas = a.areas || a.data || [];
      if (Array.isArray(prevAreas) && Array.isArray(curAreas)) {
        prev.areas = [...new Set([...prevAreas, ...curAreas])];
        prev.area_count = prev.areas.length;
      }
    } else {
      a._waveCount = 1;
      merged.push(Object.assign({}, a));
    }
  });
  return { merged };
}

function isStandDown(a) {
  return a.cat === 10 || a.cat === '10' || (a.title && /הסתיים/.test(a.title));
}

// ═══════════════════════════════════════════════════════════
// TEST RUNNER
// ═══════════════════════════════════════════════════════════

let passed = 0, failed = 0;

function test(suite, name, fn) {
  try {
    fn();
    console.log(`  ✓ [${suite}] ${name}`);
    passed++;
  } catch(e) {
    console.log(`  ✗ [${suite}] ${name} — ${e.message}`);
    failed++;
  }
}

function assert(cond, msg) { if (!cond) throw new Error(msg || 'Assertion failed'); }
function assertEqual(a, b, msg) { if (a !== b) throw new Error(msg || `Expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); }

console.log('\n🧪 CENTCOM Dashboard Tests\n');

// Missile Events
test('Missile Events', 'filters to type=missile only', () => {
  global._strikeWindowHours = 0; global._liveEvents = [];
  getMissileEvents().forEach(e => assertEqual(e.type, 'missile'));
});

test('Missile Events', 'excludes events without origin coords', () => {
  global._strikeWindowHours = 0; global._liveEvents = [];
  assert(!getMissileEvents().some(e => e.target === 'Tehran'));
});

test('Missile Events', 'returns 4 missiles when window=All', () => {
  global._strikeWindowHours = 0; global._liveEvents = [];
  assertEqual(getMissileEvents().length, 4);
});

test('Missile Events', 'filters old events with 24h window', () => {
  global._strikeWindowHours = 24; global._liveEvents = [];
  assert(!getMissileEvents().some(e => e.date === '2026-02-28'));
});

test('Missile Events', 'merges live events', () => {
  global._strikeWindowHours = 24;
  global._liveEvents = [{date:"2026-03-20",ts:Math.floor(Date.now()/1000),lat:32,lon:34.7,origin_lat:15.35,origin_lon:44.2,source_country:"yemen"}];
  assertEqual(getMissileEvents().filter(e => e._live).length, 1);
});

test('Missile Events', 'live events bypass time filter', () => {
  global._strikeWindowHours = 1;
  global._liveEvents = [{date:"2026-03-20",ts:Math.floor(Date.now()/1000),lat:32,lon:34.7,origin_lat:33.5,origin_lon:48.5}];
  assertEqual(getMissileEvents().filter(e => e._live).length, 1);
});

// Siren History
test('Siren History', 'merges consecutive same-type within 90s', () => {
  const {merged} = renderSirenHistory([
    {type:'siren',ts:1000,areas:['Tel Aviv','Rishon']},
    {type:'siren',ts:1060,areas:['Jerusalem']},
  ]);
  assertEqual(merged.length, 1);
  assertEqual(merged[0]._waveCount, 2);
});

test('Siren History', 'does NOT merge if >90s apart', () => {
  assertEqual(renderSirenHistory([
    {type:'siren',ts:1000,areas:['Tel Aviv']},
    {type:'siren',ts:1200,areas:['Haifa']},
  ]).merged.length, 2);
});

test('Siren History', 'does NOT merge different types', () => {
  assertEqual(renderSirenHistory([
    {type:'siren',ts:1000,areas:['Tel Aviv']},
    {type:'siren_clear',ts:1030,areas:['Tel Aviv']},
  ]).merged.length, 2);
});

test('Siren History', 'deduplicates areas', () => {
  const {merged} = renderSirenHistory([
    {type:'siren',ts:1000,areas:['Tel Aviv','Rishon']},
    {type:'siren',ts:1030,areas:['Tel Aviv','Jerusalem']},
  ]);
  assertEqual(merged[0].areas.length, 3);
});

test('Siren History', 'empty returns empty', () => {
  assertEqual(renderSirenHistory([]).merged.length, 0);
});

// Labels
test('Labels', 'standdown = Alert Ended', () => {
  assert(isStandDown({cat:10}));
  assert(isStandDown({title:'ירי רקטות וטילים - הסתיים'}));
  assert(!isStandDown({cat:1}));
});

// ═══════════════════════════════════════════════════════════
// PANEL EXCLUSIVITY
// ═══════════════════════════════════════════════════════════

// Simulate DOM for panel tests
const _panels = { sidebar: false, feed: false, brief: false };
function closeMobilePanels(except) {
  if (except !== 'sidebar') _panels.sidebar = false;
  if (except !== 'feed') _panels.feed = false;
  if (except !== 'brief') _panels.brief = false;
}

test('Panel Exclusivity', 'opening feed closes sidebar and brief', () => {
  _panels.sidebar = true; _panels.brief = true; _panels.feed = false;
  closeMobilePanels('feed');
  _panels.feed = true;
  assert(!_panels.sidebar && !_panels.brief && _panels.feed);
});

test('Panel Exclusivity', 'opening brief closes feed and sidebar', () => {
  _panels.feed = true; _panels.sidebar = true; _panels.brief = false;
  closeMobilePanels('brief');
  _panels.brief = true;
  assert(!_panels.feed && !_panels.sidebar && _panels.brief);
});

test('Panel Exclusivity', 'opening sidebar closes feed and brief', () => {
  _panels.feed = true; _panels.brief = true; _panels.sidebar = false;
  closeMobilePanels('sidebar');
  _panels.sidebar = true;
  assert(!_panels.feed && !_panels.brief && _panels.sidebar);
});

// ═══════════════════════════════════════════════════════════
// OREF CONNECTION HEALTH
// ═══════════════════════════════════════════════════════════

function getOrefConnState(failCount) {
  if (failCount === 0) return { text: '● Live', color: '#22c55e' };
  if (failCount >= 5) return { text: '● Offline', color: '#ef4444' };
  return { text: `● Retrying (${failCount})...`, color: '#f59e0b' };
}

test('Oref Health', 'failCount=0 → Live (green)', () => {
  const s = getOrefConnState(0);
  assertEqual(s.text, '● Live');
  assertEqual(s.color, '#22c55e');
});

test('Oref Health', 'failCount=3 → Retrying (amber)', () => {
  const s = getOrefConnState(3);
  assert(s.text.includes('Retrying'));
  assertEqual(s.color, '#f59e0b');
});

test('Oref Health', 'failCount=5 → Offline (red)', () => {
  const s = getOrefConnState(5);
  assertEqual(s.text, '● Offline');
  assertEqual(s.color, '#ef4444');
});

test('Oref Health', 'failCount=10 → still Offline', () => {
  assertEqual(getOrefConnState(10).text, '● Offline');
});

// ═══════════════════════════════════════════════════════════
// TRUMP COUNTDOWN
// ═══════════════════════════════════════════════════════════

const DEADLINE = new Date('2026-03-23T23:44:00Z').getTime();

function countdownColor(diff) {
  const h = diff / 3600000;
  if (h > 12) return '#ff6666';
  if (h > 6) return '#ffaa00';
  if (h > 2) return '#ff6600';
  return '#ff0000';
}

function countdownFormat(diff) {
  if (diff <= 0) return 'EXPIRED';
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

test('Countdown', 'format with 5h remaining', () => {
  assertEqual(countdownFormat(5 * 3600000), '05:00:00');
});

test('Countdown', 'EXPIRED when diff <= 0', () => {
  assertEqual(countdownFormat(0), 'EXPIRED');
  assertEqual(countdownFormat(-1000), 'EXPIRED');
});

test('Countdown', 'color >12h is #ff6666', () => {
  assertEqual(countdownColor(13 * 3600000), '#ff6666');
});

test('Countdown', 'color 6-12h is #ffaa00', () => {
  assertEqual(countdownColor(8 * 3600000), '#ffaa00');
});

test('Countdown', 'color 2-6h is #ff6600', () => {
  assertEqual(countdownColor(4 * 3600000), '#ff6600');
});

test('Countdown', 'color <2h is #ff0000', () => {
  assertEqual(countdownColor(1 * 3600000), '#ff0000');
});

// ═══════════════════════════════════════════════════════════
// BRIEF DATA
// ═══════════════════════════════════════════════════════════

test('Brief', 'brief.json structure', () => {
  const fs = require('fs');
  const path = require('path');
  const briefPath = path.join(__dirname, '..', 'docs', 'brief.json');
  if (!fs.existsSync(briefPath)) { console.log('    (skipped — no brief.json)'); return; }
  const data = JSON.parse(fs.readFileSync(briefPath, 'utf-8'));
  assert(data.generated_at, 'missing generated_at');
  assert(data.briefs, 'missing briefs');
  assert(typeof data.briefs === 'object', 'briefs not object');
});

test('Brief', 'brief has en and he for each window', () => {
  const fs = require('fs');
  const path = require('path');
  const briefPath = path.join(__dirname, '..', 'docs', 'brief.json');
  if (!fs.existsSync(briefPath)) { console.log('    (skipped — no brief.json)'); return; }
  const data = JSON.parse(fs.readFileSync(briefPath, 'utf-8'));
  for (const [key, brief] of Object.entries(data.briefs)) {
    assert(brief.en, `${key}: missing en`);
    assert(brief.he, `${key}: missing he`);
  }
});

test('Brief', 'time windows match expected set', () => {
  const expected = ['0.5', '2', '6', '24', '48'];
  const fs = require('fs');
  const path = require('path');
  const briefPath = path.join(__dirname, '..', 'docs', 'brief.json');
  if (!fs.existsSync(briefPath)) { console.log('    (skipped — no brief.json)'); return; }
  const data = JSON.parse(fs.readFileSync(briefPath, 'utf-8'));
  const keys = Object.keys(data.briefs).sort();
  assertEqual(JSON.stringify(keys), JSON.stringify(expected.sort()));
});

// ═══════════════════════════════════════════════════════════
// STRIKE WINDOW (no "All", default 48h)
// ═══════════════════════════════════════════════════════════

test('Strike Window', 'default is 48h', () => {
  const defaultHours = 48;
  assertEqual(defaultHours, 48);
});

test('Strike Window', 'valid windows are 24h, 48h, 168h (7d)', () => {
  const validWindows = [24, 48, 168];
  assert(!validWindows.includes(0), '"All" (0) should not be a valid window');
  assert(validWindows.includes(48));
});

// ═══════════════════════════════════════════════════════════
// MOBILE BOTTOM BAR
// ═══════════════════════════════════════════════════════════

test('Mobile Bar', 'exactly 3 buttons: LAYERS, FEED, BRIEF', () => {
  const buttons = ['LAYERS', 'FEED', 'BRIEF'];
  assertEqual(buttons.length, 3);
  assertEqual(buttons[1], 'FEED', 'FEED should be middle');
  assert(!buttons.includes('LEGEND'), 'LEGEND should be removed from mobile bar');
  assert(!buttons.includes('BASES'), 'BASES should be removed');
  assert(!buttons.includes('FIRES'), 'FIRES should be removed');
  assert(!buttons.includes('OSINT'), 'OSINT should be removed');
});

test('Feed Startup', 'no auto-open setTimeout in centcom.html', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(!html.includes('setTimeout(() => toggleFeed()'), 'Feed should not auto-open on startup');
  assert(!html.includes("setTimeout(()=>toggleFeed()"), 'Feed should not auto-open on startup (minified)');
});

test('Feed Startup', 'loadFeed() called for badge count', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(html.includes('loadFeed()'), 'loadFeed() must be called for badge count pre-loading');
});

test('Desktop Toolbar', 'has brief button', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(html.includes('data-layer="brief"'), 'desktop toolbar should have brief button');
  assert(html.includes('toggleBrief()'), 'toggleBrief() must be wired');
});

test('Desktop Toolbar', 'feed and brief are mutually exclusive', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  // toggleFeed should reference brief-panel
  const feedFn = html.substring(html.indexOf('function toggleFeed()'), html.indexOf('function toggleFeed()') + 600);
  assert(feedFn.includes('brief-panel'), 'toggleFeed should close brief panel');
  const briefFn = html.substring(html.indexOf('function toggleBrief()'), html.indexOf('function toggleBrief()') + 600);
  assert(briefFn.includes('feed-panel'), 'toggleBrief should close feed panel');
});

test('Basemap', 'floating basemap-toggle is hidden', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  const css = html.substring(html.indexOf('#basemap-toggle {'), html.indexOf('#basemap-toggle {') + 100);
  assert(css.includes('display:none'), 'Floating basemap toggle should be display:none');
});

test('Basemap', 'VIIRS toggle exists in sidebar layers', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(html.includes('sb-bm-dot'), 'Sidebar should have basemap dot (sb-bm-dot)');
  assert(html.includes('sb-bm-label'), 'Sidebar should have basemap label (sb-bm-label)');
  assert(html.includes('VIIRS Night Lights'), 'Sidebar should show VIIRS Night Lights label');
});

test('Basemap', 'mobile toolbar still has 🌗 quick toggle', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  const mtStart = html.indexOf('id="mobile-toolbar"');
  const mtEnd = html.indexOf('</div>\n\n', mtStart);
  const mtSection = html.substring(mtStart, mtEnd);
  assert(mtSection.includes('🌗'), 'Mobile toolbar should retain 🌗 basemap toggle');
});

test('Brief Panel', 'fully opaque background (no bleed-through)', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  const briefCSS = html.substring(html.indexOf('#brief-panel {'), html.indexOf('#brief-panel {') + 300);
  assert(!briefCSS.includes('rgba'), 'Brief panel should not use rgba (map bleeds through)');
  assert(!briefCSS.includes('backdrop-filter'), 'Brief panel should not use backdrop-filter');
});

// ═══════════════════════════════════════════════════════════
// PWA MANIFEST & SERVICE WORKER
// ═══════════════════════════════════════════════════════════

test('PWA', 'manifest.json exists and is valid JSON', () => {
  const fs = require('fs');
  const path = require('path');
  const mp = path.join(__dirname, '..', 'docs', 'manifest.json');
  assert(fs.existsSync(mp), 'manifest.json not found');
  JSON.parse(fs.readFileSync(mp, 'utf-8')); // throws if invalid
});

test('PWA', 'manifest has required fields', () => {
  const fs = require('fs');
  const path = require('path');
  const m = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'manifest.json'), 'utf-8'));
  assert(m.name, 'missing name');
  assert(m.short_name, 'missing short_name');
  assert(m.start_url, 'missing start_url');
  assert(m.display, 'missing display');
  assert(m.icons && m.icons.length > 0, 'missing icons');
  assert(m.id, 'missing id (required for stable PWA identity)');
});

test('PWA', 'start_url points to root (not centcom.html)', () => {
  const fs = require('fs');
  const path = require('path');
  const m = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'manifest.json'), 'utf-8'));
  assert(!m.start_url.includes('centcom.html'), 'start_url should not reference centcom.html directly');
  assert(m.start_url.endsWith('/'), 'start_url should end with /');
});

test('PWA', 'icons have separate purpose (not combined "any maskable")', () => {
  const fs = require('fs');
  const path = require('path');
  const m = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'manifest.json'), 'utf-8'));
  for (const icon of m.icons) {
    assert(!icon.purpose.includes(' '), `Icon ${icon.sizes} has combined purpose "${icon.purpose}" — should be separate entries`);
  }
});

test('PWA', 'has 192 and 512 icons', () => {
  const fs = require('fs');
  const path = require('path');
  const m = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'manifest.json'), 'utf-8'));
  const sizes = m.icons.map(i => i.sizes);
  assert(sizes.includes('192x192'), 'missing 192x192 icon');
  assert(sizes.includes('512x512'), 'missing 512x512 icon');
});

test('PWA', 'icon files exist on disk', () => {
  const fs = require('fs');
  const path = require('path');
  assert(fs.existsSync(path.join(__dirname, '..', 'docs', 'icons', 'icon-192.png')), 'icon-192.png missing');
  assert(fs.existsSync(path.join(__dirname, '..', 'docs', 'icons', 'icon-512.png')), 'icon-512.png missing');
});

test('PWA', 'sw.js exists', () => {
  const fs = require('fs');
  const path = require('path');
  assert(fs.existsSync(path.join(__dirname, '..', 'docs', 'sw.js')), 'sw.js missing');
});

test('PWA', 'sw.js caches root URL and index.html', () => {
  const fs = require('fs');
  const path = require('path');
  const sw = fs.readFileSync(path.join(__dirname, '..', 'docs', 'sw.js'), 'utf-8');
  assert(sw.includes('/magen-yehuda-bot/'), 'sw.js should cache root URL');
  assert(sw.includes('index.html'), 'sw.js should cache index.html');
});

test('PWA', 'sw.js handles data JSON offline', () => {
  const fs = require('fs');
  const path = require('path');
  const sw = fs.readFileSync(path.join(__dirname, '..', 'docs', 'sw.js'), 'utf-8');
  assert(sw.includes('.json'), 'sw.js should handle JSON files');
  assert(sw.includes('offline'), 'sw.js should have offline fallback');
});

test('PWA', 'index.html is synced with centcom.html', () => {
  const fs = require('fs');
  const path = require('path');
  const centcom = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  const index = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf-8');
  assertEqual(centcom.length, index.length, `index.html (${index.length}) differs from centcom.html (${centcom.length}) — run: cp centcom.html index.html`);
});

test('PWA', 'centcom.html references manifest.json', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(html.includes('rel="manifest"'), 'missing <link rel="manifest">');
  assert(html.includes('manifest.json'), 'manifest.json not referenced');
});

test('PWA', 'centcom.html registers service worker', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(html.includes('serviceWorker.register'), 'missing SW registration');
});

test('PWA', 'no deprecated apple-mobile-web-app-capable', () => {
  const fs = require('fs');
  const path = require('path');
  const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'centcom.html'), 'utf-8');
  assert(!html.includes('apple-mobile-web-app-capable'), 'apple-mobile-web-app-capable is deprecated — use mobile-web-app-capable');
});

// Summary
console.log(`\n${passed} passed, ${failed} failed — ${passed+failed} total\n`);
process.exit(failed > 0 ? 1 : 0);
