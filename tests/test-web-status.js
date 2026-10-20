#!/usr/bin/env node
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const pages = ['index.html', 'centcom.html'].map(name => ({
  name,
  source: fs.readFileSync(path.join(root, 'docs', name), 'utf8'),
}));
const hormuz = fs.readFileSync(path.join(root, 'docs', 'hormuz.html'), 'utf8');

function extractFunction(source, name, context = {}) {
  const match = source.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}`));
  assert.ok(match, `Expected function ${name}`);
  return vm.runInNewContext(`(${match[0]})`, context);
}

function test(name, fn) {
  fn();
  console.log(`✓ ${name}`);
}

for (const page of pages) {
  test(`${page.name}: starts with unknown alert state`, () => {
    assert.match(page.source, /id="oref-status">Awaiting alert data<\/div>/);
    assert.match(page.source, /id="oref-conn"[^>]*>● Connecting<\/span>/);
    assert.doesNotMatch(page.source, /initTrumpPauseCountdown|PAUSE EXPIRED|STRIKE PAUSE/);
    assert.doesNotMatch(page.source, /status\.textContent\s*=\s*['"`]✅ All Clear/);
    assert.match(page.source, /No new alerts — follow official instructions/);
    assert.match(page.source, /Alert status unavailable — follow official instructions/);
    assert.match(page.source, /if \(chipAlert\) chipAlert\.textContent = '—'/);
    assert.match(page.source, /Static force and energy inventory — data as of March 8, 2026/);
  });

  test(`${page.name}: rejects stale or unknown alert snapshots`, () => {
    const isFresh = extractFunction(page.source, 'orefDataIsFresh');
    const now = Date.now();
    assert.equal(isFresh({alerts: [], cache_age_seconds: 10}, now), true);
    assert.equal(isFresh({alerts: [], cache_age_seconds: 121}, now), false);
    assert.equal(isFresh({alerts: [], cache_age_seconds: null}, now), false);
    assert.equal(isFresh({alerts: [], timestamp: new Date(now-300000).toISOString()}, now), true);
    assert.equal(isFresh({alerts: [], timestamp: new Date(now-400000).toISOString()}, now), false);
    assert.equal(isFresh({alerts: []}, now), false);
  });

  test(`${page.name}: filters fresh live events and clears stale arcs`, () => {
    const filter = extractFunction(page.source, 'filterFreshLiveEvents');
    const now = 10000;
    const events = [
      { ts: now, origin_lat: 1, origin_lon: 1, id: 'now' },
      { ts: now - 899, origin_lat: 1, origin_lon: 1, id: 'fresh' },
      { ts: now - 900, origin_lat: 1, origin_lon: 1, id: 'expired' },
      { ts: now + 1, origin_lat: 1, origin_lon: 1, id: 'future' },
      { ts: now, origin_lat: 0, origin_lon: 1, id: 'no-origin' },
    ];
    assert.deepEqual(filter(events, now).map(event => event.id), ['now', 'fresh']);
    assert.deepEqual([...filter(null, now)], []);

    let removed = false;
    let cancelled;
    const context = {
      cancelAnimationFrame(id) { cancelled = id; },
      window: {
        _liveEvents: [{ id: 'stale' }],
        _arcAnimId: 42,
        _arcSvg: { remove() { removed = true; } },
        _arcPaths: [{}],
      },
    };
    const clearWithWindow = extractFunction(page.source, 'clearLiveEvents', context);
    clearWithWindow();
    assert.equal(context.window._liveEvents.length, 0);
    assert.equal(context.window._arcSvg, null);
    assert.equal(context.window._arcAnimId, null);
    assert.equal(context.window._arcPaths.length, 0);
    assert.equal(removed, true);
    assert.equal(cancelled, 42);
    assert.match(page.source, /\.catch\(e => \{[\s\S]*?clearLiveEvents\(\);[\s\S]*?\}\);/);
  });
}

test('Hormuz page clearly marks historical data and narrative as archived', () => {
  assert.match(hormuz, /<title>Hormuz Crisis Tracker — Archived Historical Dashboard<\/title>/);
  assert.match(hormuz, /ARCHIVED — historical page \(archive marker: March 26, 2026\); dated entries through March 30\. Not current status/);
  assert.match(hormuz, /Archived Situation Report — Mar 30, 2026/);
  assert.match(hormuz, /Archived Headlines \(through Mar 30, 2026\)/);
  assert.match(hormuz, /Archived AIS Monitoring Zones — Historical Vessel Density/);
  assert.match(hormuz, /Facility statuses last verified March 7, 2026; historical, not current/);
  assert.doesNotMatch(hormuz, /Live Situation Report|Latest Headlines|Live Vessel Density|content: `Current:/);
});

test('all inline JavaScript in affected pages parses', () => {
  const files = [...pages, { name: 'hormuz.html', source: hormuz }];
  let scripts = 0;
  for (const file of files) {
    const tags = /<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi;
    for (const match of file.source.matchAll(tags)) {
      const [, attrs, body] = match;
      if (/\bsrc\s*=/.test(attrs) || !body.trim()) continue;
      const type = attrs.match(/\btype=["']([^"']+)["']/i)?.[1];
      if (type && !/(?:java|ecma)script/i.test(type)) continue;
      new vm.Script(body, { filename: `${file.name} inline script` });
      scripts++;
    }
  }
  assert.ok(scripts > 0, 'Expected inline scripts to check');
  console.log(`  parsed ${scripts} inline scripts`);
});
