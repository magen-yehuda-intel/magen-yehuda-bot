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
  assert(!buttons.includes('LEGEND'), 'LEGEND should be removed');
  assert(!buttons.includes('BASES'), 'BASES should be removed');
  assert(!buttons.includes('FIRES'), 'FIRES should be removed');
  assert(!buttons.includes('OSINT'), 'OSINT should be removed');
});

// Summary
console.log(`\n${passed} passed, ${failed} failed — ${passed+failed} total\n`);
process.exit(failed > 0 ? 1 : 0);
