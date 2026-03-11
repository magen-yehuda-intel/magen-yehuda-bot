#!/usr/bin/env node
/**
 * Oref Dashboard Tests — Node.js runner
 * Run: node tests/test-oref-dashboard.js
 * 
 * Tests the Oref alert classification, geocoding, and filtering logic
 * extracted from centcom.html. Keep functions in sync with the dashboard.
 */

// ═══════════════════════════════════════════════════════════
// EXTRACT: Functions under test (must match centcom.html)
// ═══════════════════════════════════════════════════════════

function isStandDown(alert) {
  const text = JSON.stringify(alert.desc || alert.title || '');
  return text.includes('ניתן לצאת') || text.includes('האירוע הסתיים');
}

// Subset of OREF_GEO for testing (full list in centcom.html)
const OREF_GEO = {
  'תל אביב':       [32.0853,34.7818], 'ירושלים':       [31.7683,35.2137], 'חיפה':           [32.7940,34.9896],
  'באר שבע':       [31.2530,34.7915], 'אשדוד':         [31.8044,34.6553], 'אשקלון':         [31.6688,34.5743],
  'שדרות':         [31.5250,34.5961], 'קריית שמונה':   [33.2075,35.5706], 'קלע אלון':     [33.0200,35.6300],
  'רמת טראמפ':     [33.0000,35.7800], 'חמת גדר':       [32.6800,35.6700], 'אילת':           [29.5569,34.9498],
  'נתניה':         [32.3215,34.8532], 'פתח תקווה':     [32.0841,34.8878], 'ראשון לציון':   [31.9730,34.7925],
  'רמת גן':       [32.0680,34.8241], 'בני ברק':       [32.0834,34.8344],
};

// ═══════════════════════════════════════════════════════════
// TEST RUNNER
// ═══════════════════════════════════════════════════════════

let passed = 0, failed = 0, errors = [];

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✅ ${name}`);
  } catch (e) {
    failed++;
    errors.push({ name, error: e.message });
    console.log(`  ❌ ${name} — ${e.message}`);
  }
}

function assert(cond, msg) { if (!cond) throw new Error(msg || 'Assertion failed'); }
function assertEqual(a, b, msg) { if (a !== b) throw new Error(`${msg || ''}: expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); }

// ═══════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════

console.log('\n📋 isStandDown classification');

test('Active missile alert (cat 1) → NOT stand-down', () => {
  assert(!isStandDown({ cat: '1', title: 'ירי רקטות וטילים', desc: 'היכנסו למרחב המוגן' }));
});

test('Cat 10 incoming alert warning → NOT stand-down', () => {
  assert(!isStandDown({
    cat: '10',
    title: 'בדקות הקרובות צפויות להתקבל התרעות באזורך',
    desc: 'על תושבי האזורים הבאים לשפר את המיקום למיגון המיטבי בקרבתך.'
  }));
});

test('Stand-down ניתן לצאת → IS stand-down', () => {
  assert(isStandDown({ cat: '10', title: 'ניתן לצאת מהמרחב המוגן' }));
});

test('Stand-down האירוע הסתיים → IS stand-down', () => {
  assert(isStandDown({ cat: '10', desc: 'האירוע הסתיים' }));
});

test('Stand-down in desc only → IS stand-down', () => {
  assert(isStandDown({ title: 'עדכון', desc: 'ניתן לצאת מהמרחב המוגן' }));
});

test('Empty alert → NOT stand-down', () => {
  assert(!isStandDown({}));
});

test('Stand-down embedded in longer text → detected', () => {
  assert(isStandDown({ desc: 'עדכון: ניתן לצאת מהמרחב המוגן באזור הדרום' }));
});

console.log('\n📋 OREF_GEO geocoding');

test('Major cities geocoded', () => {
  ['תל אביב', 'ירושלים', 'חיפה', 'באר שבע', 'אשדוד', 'אשקלון'].forEach(c => {
    assert(OREF_GEO[c], `Missing: ${c}`);
    assert(OREF_GEO[c][0] > 29 && OREF_GEO[c][0] < 34, `${c} lat out of range`);
    assert(OREF_GEO[c][1] > 34 && OREF_GEO[c][1] < 36.5, `${c} lon out of range`);
  });
});

test('Golan settlements geocoded', () => {
  ['קלע אלון', 'רמת טראמפ', 'חמת גדר'].forEach(p => assert(OREF_GEO[p], `Missing: ${p}`));
});

test('Unknown area → undefined', () => {
  assertEqual(OREF_GEO['nonexistent'], undefined);
});

test('All coords are valid numbers in Israel bounds', () => {
  Object.entries(OREF_GEO).forEach(([name, [lat, lon]]) => {
    assert(!isNaN(lat) && !isNaN(lon), `${name}: NaN coords`);
    assert(lat >= 29 && lat <= 34 && lon >= 34 && lon <= 36.5, `${name}: out of bounds`);
  });
});

console.log('\n📋 Alert filtering');

test('Active alerts pass, stand-downs filtered', () => {
  const alerts = [
    { cat: '1', title: 'ירי רקטות', data: ['באר שבע'] },
    { cat: '10', title: 'ניתן לצאת מהמרחב המוגן', data: ['באר שבע'] },
  ];
  const active = alerts.filter(a => !isStandDown(a));
  assertEqual(active.length, 1);
  assertEqual(active[0].cat, '1');
});

test('All stand-downs → empty', () => {
  const alerts = [
    { title: 'ניתן לצאת מהמרחב המוגן' },
    { desc: 'האירוע הסתיים' },
  ];
  assertEqual(alerts.filter(a => !isStandDown(a)).length, 0);
});

test('Empty array → empty', () => {
  assertEqual([].filter(a => !isStandDown(a)).length, 0);
});

console.log('\n📋 API response parsing');

test('Standard response with cat 10 active alert', () => {
  const resp = {
    alert_count: 1,
    alerts: [{ cat: '10', title: 'בדקות הקרובות צפויות להתקבל התרעות באזורך', data: ['קלע אלון'] }],
    timestamp: '2026-03-11T01:44:23Z'
  };
  const active = (resp.alerts || []).filter(a => !isStandDown(a));
  assertEqual(active.length, 1, 'Cat 10 incoming should NOT be filtered');
});

test('Missing alerts field → empty', () => {
  assertEqual((({}).alerts || []).length, 0);
});

console.log('\n📋 Regression guards');

test('REGRESSION: cat 10 NOT blanket-filtered', () => {
  assert(!isStandDown({ cat: '10', title: 'בדקות הקרובות צפויות להתקבל התרעות באזורך' }),
    'CRITICAL: cat 10 incoming warning must not be filtered');
});

test('REGRESSION: numeric cat works same as string', () => {
  assert(!isStandDown({ cat: 10, title: 'בדקות הקרובות צפויות' }));
  assert(isStandDown({ cat: 10, title: 'ניתן לצאת מהמרחב המוגן' }));
});

test('CRITICAL cities all present in geocoding', () => {
  const critical = ['תל אביב', 'ירושלים', 'חיפה', 'באר שבע', 'פתח תקווה',
    'ראשון לציון', 'רמת גן', 'בני ברק', 'נתניה', 'אשדוד', 'אשקלון'];
  const missing = critical.filter(c => !OREF_GEO[c]);
  assertEqual(missing.length, 0, `Missing CRITICAL cities: ${missing.join(', ')}`);
});

// ═══════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════

console.log(`\n${'═'.repeat(50)}`);
const total = passed + failed;
if (failed === 0) {
  console.log(`✅ ALL ${total} TESTS PASSED`);
} else {
  console.log(`❌ ${failed} FAILED / ${total} TOTAL`);
  errors.forEach(e => console.error(`  FAIL: ${e.name} — ${e.error}`));
}
console.log('═'.repeat(50));

process.exit(failed > 0 ? 1 : 0);
