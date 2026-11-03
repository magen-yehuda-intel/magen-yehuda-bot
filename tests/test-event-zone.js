const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
for (const file of ['index.html', 'centcom.html']) {
  const html = fs.readFileSync(`docs/${file}`, 'utf8');
  const script = html.match(/<script>\s*\/\/ ── 3D war-room globe[\s\S]*?<\/script>/)[0].replace(/^<script>|<\/script>$/g, '');
  const elements = new Map();
  const messages = [];
  const element = id => {
    if (!elements.has(id)) elements.set(id, {hidden:true, value:'normal', style:{}, classList:{toggle(){}}, contentWindow:{postMessage(m){messages.push(m);}}});
    return elements.get(id);
  };
  const ctx = vm.createContext({document:{getElementById:element},window:{addEventListener(){}},innerWidth:1000,map:{flyTo(){}},setInterval(){},Date,Number,JSON,feedEvents:[]});
  vm.runInContext(script, ctx);
  vm.runInContext("globe3dReady = true; lockEventZone(35.69,51.39,'Tehran');", ctx);
  let view = messages.at(-1).view;
  assert.equal(view.camera.lat, 35.69);
  assert.equal(view.camera.altitude_m, 180000);
  assert.equal(view.annotations.length, 1);
  assert.equal(element('event-zone-unlock').hidden, false);
  vm.runInContext('globe3dPush()', ctx);
  assert.equal(messages.at(-1).view.camera.lon, 51.39, 'refresh preserves selected zone');
  vm.runInContext("lockEventZone(32.43,53.69,'Iran')", ctx);
  assert.equal(messages.at(-1).view.camera.altitude_m, 1200000, 'country-level coordinates are not street-precise');
  vm.runInContext('unlockEventZone()', ctx);
  assert.equal(messages.at(-1).view.camera.altitude_m, 3800000);
  assert.equal(element('event-zone-unlock').hidden, true);
  assert(html.includes('lockEventZone(lat, lon, loc || src'));
  console.log(`✓ ${file}: event focus, selected pin, update persistence, country scale, unlock`);
}
