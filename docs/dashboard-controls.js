/* Shared settings adapter for both Magen renderers. No control silently targets a hidden map. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const legacyOnly = new Set(['military','infra','nuclear','missiles','naval','ad','airbases','irgc','energy','sam','waterways','patrol','gpsjam','gulfenergy','sirens','strikes','correlations']);
  const countryNames = ['Iran','Israel','Lebanon','Syria','Iraq','Jordan','Saudi Arabia','United Arab Emirates','Yemen','Oman','Kuwait','Qatar'];
  const defaults = Object.fromEntries(Object.keys(activeState).map(k => [k, ['borders','osint','sirens'].includes(k)]));
  let density = 'sparse', globeSites = false, batch = false, lastAck = null, readyTimer, saveTimer;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem('centcom-config') || 'null'); } catch (_) {}
  const originalLegend = $('legend')?.innerHTML;
  const originals = {toggleLayer, cycleAircraft, cycleFires, renderFeed, renderOSINTMarkers, renderAssetList, toggleMissileAnims, toggleGlobe3d, closeMobilePanels, switchTab};
  function notice(text) {
    let el = $('map-setting-status');
    if (!el) { el = document.createElement('div'); el.id = 'map-setting-status'; el.setAttribute('role','status'); el.style.cssText = 'position:fixed;left:50%;bottom:58px;transform:translateX(-50%);z-index:1400;background:#0a0f1eee;border:1px solid #2aa;border-radius:6px;padding:8px 12px;color:#bff;font:11px monospace;max-width:85vw;text-align:center;pointer-events:none'; document.body.appendChild(el); }
    el.hidden = false; el.textContent = text;
    clearTimeout(saveTimer); saveTimer = setTimeout(() => { el.hidden = true; }, 7000);
  }
  function is3D() { return !$('globe3d').hidden; }
  function need2D(reason) {
    if (!is3D()) return;
    toggleGlobe3d();
    notice(reason + ' — showing the 2D map. Use 3D GLOBE to return.');
  }
  function sync() {
    Object.keys(activeState).forEach(k => {
      document.querySelectorAll(`[data-layer="${k}"]`).forEach(el => el.classList.toggle('active', !!activeState[k]));
    });
    updateSidebarRows(); updateMobileButtons(); updateLayerCount(); _updateMissileUI();
    if ($('globe-borders')) $('globe-borders').checked = activeState.borders;
    if ($('globe-density')) $('globe-density').value = density;
    if ($('globe-sites')) $('globe-sites').checked = globeSites;
    document.querySelectorAll('#feed-time-bar .feed-time-chip').forEach(el => el.classList.toggle('active', Number(el.dataset.hours) === feedTimeHours));
    for (const id of ['strike-window','strike-window-mobile','strike-window-sidebar']) if ($(id)) $(id).value = String(window._strikeWindowHours || 48);
    if (!batch && globe3dReady) globe3dPush();
  }
  window.updateMobileButtons = () => {
    const colors = {fires:'active-orange',osint:'active-red',sirens:'active-red',infra:'active-orange',aircraft:'active-green',animations:'active-red'};
    document.querySelectorAll('.mt-btn[data-mt]').forEach(el => {
      const k = el.dataset.mt;
      if (!(k in activeState) && k !== 'animations') return;
      el.classList.remove('active','active-orange','active-red','active-green','active-amber');
      if (k === 'animations' ? window._missileMode !== 'off' : activeState[k]) el.classList.add(colors[k] || 'active');
      if (k === 'aircraft') el.title = 'Aircraft: ' + AIRCRAFT_MODES[aircraftMode];
      if (k === 'fires') el.title = 'Fires: ' + FIRE_MODES[fireMode];
      if (k === 'animations') el.title = 'Missiles: ' + window._missileMode;
    });
    for (const k of ['feed','brief','sidebar','legend']) {
      const open = $(k === 'feed' ? 'feed-panel' : k === 'brief' ? 'brief-panel' : k)?.classList.contains(k === 'legend' ? 'visible' : 'open');
      document.querySelectorAll(`[data-layer="${k}"]`).forEach(el => el.classList.toggle('active',!!open));
    }
  };
  window.closeMobilePanels = except => { originals.closeMobilePanels(except); updateMobileButtons(); };
  window.filterSidebarLayers = q => {
    const query = String(q || '').toLowerCase();
    document.querySelectorAll('#tab-layers .sb-row').forEach(row => { row.hidden = !!query && !row.textContent.toLowerCase().includes(query); row.style.display = row.hidden ? 'none' : ''; });
  };
  window.toggleLayer = name => {
    if (name === 'labels' && is3D()) { density = density === 'off' ? 'sparse' : 'off'; sync(); return; }
    if (name === 'aircraft') return cycleAircraft();
    if (name === 'fires') return cycleFires();
    if (legacyOnly.has(name)) need2D('This exact overlay is 2D-only');
    if (name === 'ships' && !is3D()) notice('2D fleet positions are a static estimate, not live AIS.');
    originals.toggleLayer(name); sync();
  };
  window.isolateIranLayer = name => toggleLayer(name);
  window.cycleAircraft = () => { originals.cycleAircraft(); if (aircraftMode === 3) need2D('Civilian-only aircraft filtering is 2D-only'); sync(); };
  window.cycleFires = () => { originals.cycleFires(); if (fireMode > 0) need2D('Exact fire-age filtering uses the Magen 2D data'); sync(); };
  window.mtToggle = name => { if (name === 'aircraft') cycleAircraft(); else if (name === 'fires') cycleFires(); else toggleLayer(name); };
  window.mobileQuickToggle = name => mtToggle(name);
  window.toggleMissileAnims = () => { need2D('Missile paths and animations are 2D-only'); originals.toggleMissileAnims(); updateMobileButtons(); };
  window.setStrikeWindow = value => {
    need2D('Strike time filtering is 2D-only');
    const n = Number(value); window._strikeWindowHours = [24,48,168].includes(n) ? n : 48;
    localStorage.setItem('strikeWindow', window._strikeWindowHours);
    sync(); renderStrikeEvents(); renderMissileArcs();
  };
  window.applyStrikeWindow = () => setStrikeWindow($('strike-window').value);
  for (const id of ['strike-window','strike-window-mobile','strike-window-sidebar']) {
    const el = $(id); if (!el) continue;
    el.innerHTML = '<option value="24">24h</option><option value="48">48h</option><option value="168">7d</option>';
    el.removeAttribute('onchange'); el.addEventListener('change', () => setStrikeWindow(el.value));
  }
  const oldBasemap = setBasemap;
  window.setBasemap = name => { need2D('Standard / VIIRS basemaps are 2D-only'); oldBasemap(name); };
  function newsMatches(e, ignoreCategories = false) {
    const now = Date.now()/1000, ts = e.ts || e.timestamp || 0;
    const src = String(e.src || e.source || '').toLowerCase(), type = String(e.type || e.sub_event_type || '').toLowerCase();
    return (!feedTimeHours || ts >= now - feedTimeHours*3600) && ts <= now + 600 &&
      !/nasa|firms/.test(src) && !type.includes('fire') &&
      (ignoreCategories || !feedActiveCats.size || feedActiveCats.has(e.side || 'unknown')) &&
      (!feedQuery || feedSearchText(e).includes(feedQuery));
  }
  window.buildCatChips = () => {
    const bar = $('feed-cat-bar'); if (!bar) return;
    const data = feedEvents.filter(e => newsMatches(e, true));
    bar.replaceChildren();
    [['','ALL'], ...Object.entries(SIDE_LABELS)].forEach(([key,label]) => {
      const b = document.createElement('span'); b.className = 'feed-cat-chip'; b.dataset.cat = key || 'all';
      b.classList.toggle('active', key ? feedActiveCats.has(key) : !feedActiveCats.size);
      b.textContent = label + ' ' + data.filter(e => !key || (e.side || 'unknown') === key).length;
      b.addEventListener('click', () => { if (!key) feedActiveCats.clear(); else if (feedActiveCats.has(key)) feedActiveCats.delete(key); else feedActiveCats.add(key); renderFeed(); });
      bar.appendChild(b);
    });
  };
  window.renderOSINTMarkers = events => originals.renderOSINTMarkers((events || []).filter(e => newsMatches(e)));
  window.syncMapToFeed = () => { if (window._osintEvents) renderOSINTMarkers(window._osintEvents); if (globe3dReady) globe3dPush(); };
  window.renderFeed = () => { originals.renderFeed(); buildCatChips(); syncMapToFeed(); };
  function applyLayers(state, exact2D = false) {
    batch = true;
    Object.keys(activeState).forEach(k => {
      activeState[k] = !!state[k];
      if (activeState[k]) layers[k].addTo(map); else map.removeLayer(layers[k]);
    });
    aircraftMode = activeState.aircraft ? Math.max(1,aircraftMode) : 0;
    fireMode = activeState.fires ? Math.max(1,fireMode) : 0;
    if (activeState.aircraft) loadAircraft(); if (activeState.fires) loadFIRMS();
    if (activeState.seismic) loadSeismic(); if (activeState.osint) loadOSINT();
    if (activeState.ships && !is3D()) loadShips(); if (activeState.gpsjam) loadGPSJam();
    if (exact2D) need2D('This preset contains Magen-specific 2D overlays');
    batch = false; sync();
  }
  function stopMissiles() {
    window._missileMode = 'off'; window._missileAnimActive = false;
    localStorage.setItem('missileMode','off'); renderMissileArcs();
    if (window._feedHighlight) { map.removeLayer(window._feedHighlight); window._feedHighlight = null; }
  }
  window.clearAllLayers = () => { stopMissiles(); globeSites = false; selectedEventZone = null; $('event-zone-unlock').hidden = true; applyLayers({}); notice('All overlays and selected-event highlights cleared.'); };
  window.showAllLayers = () => applyLayers(Object.fromEntries(Object.keys(activeState).map(k=>[k,true])), true);
  window.showUSOnly = () => applyLayers({borders:true,military:true,patrol:true}, true);
  window.showIranOnly = () => applyLayers({borders:true,nuclear:true,missiles:true,naval:true,ad:true,airbases:true,irgc:true,energy:true,sam:true}, true);
  window.saveConfig = () => {
    const cfg = {version:2, activeState:{...activeState}, aircraftMode,fireMode,feedTimeHours,feedCats:[...feedActiveCats],feedSearch:$('feed-search')?.value || '',currentBasemap,density,globeSites,globeMap:$('globe3d-map').value,globeStyle:$('globe3d-style').value,selectedEventZone,renderer:is3D()?'3d':'2d',strikeWindow:window._strikeWindowHours,missileMode:window._missileMode,briefFontPct};
    localStorage.setItem('centcom-config',JSON.stringify(cfg)); notice('Map, layers, filters, zone and display settings saved.');
  };
  window.resetConfig = () => {
    localStorage.removeItem('centcom-config'); localStorage.removeItem('strikeWindow'); localStorage.removeItem('missileMode');
    density = 'sparse'; globeSites = false; selectedEventZone = null; $('event-zone-unlock').hidden = true;
    feedTimeHours = 2; feedActiveCats.clear(); feedQuery=''; if ($('feed-search')) $('feed-search').value='';
    aircraftMode=0;fireMode=0;window._strikeWindowHours=48;stopMissiles();map.stop();map.setView([28,52],5);
    $('globe3d-map').value='esri-imagery';$('globe3d-style').value='normal';oldBasemap('carto');
    briefFontPct=100;applyBriefFont();
    applyLayers(defaults); if (!is3D()) toggleGlobe3d(); renderFeed(); globe3dPush(true); notice('Reset to sparse 3D view, regional borders and a 2-hour news window.');
  };
  window.renderAssetList = filter => {
    originals.renderAssetList(filter === undefined ? $('asset-search')?.value : filter);
    const list=$('asset-list'); if (!list) return;
    list.querySelectorAll('[onclick]').forEach(row => {
      const m = row.getAttribute('onclick').match(/map\.flyTo\(\[([^,]+),([^\]]+)\]/); if (!m) return;
      row.removeAttribute('onclick'); row.setAttribute('role','button');row.tabIndex=0;
      const action=()=>flyToEvent(Number(m[1]),Number(m[2]),'', '',row.querySelector('.sb-row-name')?.textContent || 'Asset');
      row.addEventListener('click',action);row.addEventListener('keydown',e=>{if(e.key==='Enter')action();});
    });
  };
  window.switchTab = tab => { originals.switchTab(tab); if(tab==='assets')renderAssetList($('asset-search')?.value); };
  window.globe3dPins = (events, nowS) => (events || []).filter(e => Number.isFinite(e.lat) && Number.isFinite(e.lon) && Math.abs(e.lat)<=90 && Math.abs(e.lon)<=180 && newsMatches(e))
    .sort((a,b)=>(b.ts||0)-(a.ts||0)).slice(0,12).map(e=>({type:'pin',latitude:e.lat,longitude:e.lon,color:({israel:'cyan',us:'cyan',iran:'red',iran_proxy:'amber'})[e.side] || 'primary',label:density==='off'?'':String(e.loc || e.src || '').slice(0,40)}));
  window.globe3dView = (includeCamera = true) => {
    const enabled = [];
    if(activeState.aircraft && aircraftMode!==3) { if(aircraftMode===2)enabled.push('military');else enabled.push('military','flights'); }
    if(activeState.ships)enabled.push('ais-live-vessels');
    if(activeState.seismic)enabled.push('earthquakes');
    if(globeSites)enabled.push('military-installations');
    const annotations = activeState.borders ? countryNames.map(target=>({type:'area',target,color:'cyan',label:''})) : [];
    if(selectedEventZone)annotations.push({type:'pin',latitude:selectedEventZone.lat,longitude:selectedEventZone.lon,color:'cyan',label:selectedEventZone.label});
    else if(activeState.osint)annotations.push(...globe3dPins(feedEvents,Date.now()/1000));
    const view = {layers:enabled,map:$('globe3d-map').value,style:$('globe3d-style').value,annotations:annotations.slice(0,24),detection:{enabled:density!=='off',densityPct:density==='balanced'?50:25,allocationStrategy:'elastic'}};
    if(includeCamera)view.camera=selectedEventZone ? {lat:selectedEventZone.lat,lon:selectedEventZone.lon,altitude_m:selectedEventZone.altitude,heading_deg:0,pitch_deg:-90} : {lat:30.5,lon:47,altitude_m:3800000,heading_deg:0,pitch_deg:-90};
    return view;
  };
  let dispatchTimer = null, pendingCamera = false;
  window.globe3dPush = (includeCamera = false) => {
    const f=$('globe3d'); if(!globe3dReady||f.hidden)return;
    pendingCamera = pendingCamera || includeCamera;
    clearTimeout(dispatchTimer);
    dispatchTimer = setTimeout(() => {
      if(!globe3dReady||f.hidden){pendingCamera=false;return;}
      const id='magen-'+(++globe3dSeq); window._lastGlobeCommand={id,view:globe3dView(pendingCamera)};pendingCamera=false;
      f.contentWindow.postMessage({type:'gev:view',...window._lastGlobeCommand},GLOBE3D_ORIGIN);
    },40);
  };
  window.lockEventZone = (lat,lon,label) => {
    if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)return;
    const regional=/^(iran|israel|lebanon|syria|iraq|yemen|united states|persian gulf|middle east)$/i.test(String(label).trim());
    selectedEventZone={lat,lon,label:String(label).slice(0,60),altitude:regional?1200000:180000};
    map.flyTo([lat,lon],regional?5:8,{duration:0.8});
    $('event-zone-unlock').hidden=false;$('event-zone-unlock').textContent='🔒 '+selectedEventZone.label+' · Unlock zone';
    if(innerWidth<=1024)closeMobilePanels();globe3dPush(true);
  };
  window.unlockEventZone = () => {selectedEventZone=null;$('event-zone-unlock').hidden=true;if(window._feedHighlight){map.removeLayer(window._feedHighlight);window._feedHighlight=null;}map.flyTo([28,52],5,{duration:0.8});globe3dPush(true);};
  function refreshLegend() {
    const el=$('legend');if(!el)return;
    el.innerHTML = is3D() ? '<div class="legend-title">3D MAP LEGEND</div><button class="legend-close" onclick="toggleLegend()">✕</button><div style="font-size:11px;line-height:1.8">Cyan country areas: regional borders<br>Cyan / red / amber pins: news source side, not verified strike attribution<br>Selected news: one labeled cyan pin<br>Aircraft, vessels, quakes and military sites: independent globe providers<br>Exact Magen overlays are marked 2D.</div>' : originalLegend;
  }
  window.toggleGlobe3d = () => {
    originals.toggleGlobe3d();map.invalidateSize();refreshLegend();
    const previousBatch=batch;batch=true;sync();batch=previousBatch;
    if(is3D()){if(!batch)globe3dPush(!!selectedEventZone);startReadyTimer();}
  };
  map.on('locationfound', e => lockEventZone(e.latlng.lat,e.latlng.lng,'Your location'));
  map.on('locationerror', e => notice('Location unavailable: '+e.message));
  function startReadyTimer(){clearTimeout(readyTimer);if(!globe3dReady)readyTimer=setTimeout(()=>{if(is3D()&&!globe3dReady){toggleGlobe3d();notice('3D viewer did not become ready; the 2D map remains available.');}},30000);}
  window.addEventListener('message',ev=>{
    const f=$('globe3d');if(ev.origin!==GLOBE3D_ORIGIN||ev.source!==f.contentWindow||!ev.data)return;
    if(ev.data.type==='gev:ready'){globe3dReady=true;clearTimeout(readyTimer);globe3dPush(!!selectedEventZone);}
    if(ev.data.type==='gev:view-applied'){lastAck=ev.data;window._lastGlobeAck=lastAck;if(!lastAck.ok)notice('3D setting failed: '+(lastAck.error || JSON.stringify(lastAck.steps?.filter(s=>!s.ok))));}
  });
  $('globe3d').addEventListener('load',()=>{ /* readiness is confirmed by the embed message, not HTML load */ });
  for (const [k,label] of [['gulfenergy','Gulf energy assets'],['sam','SAM range rings'],['waterways','Strategic waterways'],['patrol','Static air patrol routes'],['gpsjam','Static GPS-interference zones']]) {
    const row=document.createElement('div');row.className='sb-row';row.setAttribute('onclick', `toggleLayer('${k}')`);row.innerHTML='<span class="sb-row-name">'+label+'</span>'; $('tab-layers').insertBefore(row,document.querySelector('.sb-actions'));
  }
  if ($('chip-ais')) { $('chip-ais').textContent='—'; $('chip-ais').parentElement.title='Provider AIS count is not exposed to Magen; unknown, not zero.'; }
  if ($('chip-live')) { const count=$('cnt-aircraft'); if(count)new MutationObserver(()=>{$('chip-live').textContent=activeState.aircraft?count.textContent:'—';}).observe(count,{childList:true,characterData:true,subtree:true}); }
  const installRow=document.createElement('button');installRow.type='button';installRow.className='sb-action-btn';installRow.textContent='Install Magen app';installRow.onclick=()=>{if(_deferredInstall)pwaInstall();else notice('Use your browser’s Install app / Add to Home Screen menu.');};document.querySelector('.sb-actions').appendChild(installRow);
  const display=document.createElement('div');display.className='sb-section-title';display.textContent='MAP DISPLAY';
  const controls=document.createElement('div');controls.innerHTML='<div class="sb-row map-display-toggle" id="borders-control"><label><input id="globe-borders" type="checkbox"> Regional country borders</label></div><div class="sb-row"><label class="sb-row-name" for="globe-density" title="Object detection labels; country names and selected-event labels remain">3D object labels</label><select id="globe-density"><option value="off">Off</option><option value="sparse" selected>Sparse</option><option value="balanced">Balanced</option></select></div><div class="sb-row map-display-toggle"><label><input id="globe-sites" type="checkbox"> 3D military-site inventory</label></div><div style="padding:8px 14px;font-size:10px;color:#aab">Marked 2D overlays switch to that map. Static inventory is not live operational intelligence. 3D news pins: up to 12 newest matching events.</div>';
  $('tab-layers').insertBefore(controls,$('tab-layers').children[1]);$('tab-layers').insertBefore(display,controls);
  $('globe-borders').onchange=()=>toggleLayer('borders');
  $('globe-density').onchange=e=>{density=e.target.value;if(!is3D())toggleGlobe3d();globe3dPush();};$('globe-sites').onchange=e=>{globeSites=e.target.checked;if(!is3D())toggleGlobe3d();globe3dPush();};
  document.querySelectorAll('#tab-layers .sb-row[onclick],.tb-btn[onclick]').forEach(row=>{
    const m=row.getAttribute('onclick').match(/(?:toggleLayer|isolateIranLayer)\('([^']+)'\)/);
    if(m&&legacyOnly.has(m[1])){row.title='Exact Magen overlay: opens in 2D';const name=row.querySelector('.sb-row-name');if(name)name.append(' · 2D');}
  });
  document.querySelectorAll('[data-mt="animations"]').forEach(el=>{el.removeAttribute('onclick');el.onclick=()=>toggleMissileAnims();});
  document.querySelectorAll('.tb-tooltip').forEach(el=>{el.textContent=el.textContent.replace('Recent Strikes (Feb 28–Mar 8)','Recent Strikes (selected window)');});
  const shipRow=document.querySelector("#tab-layers .sb-row[onclick=\"toggleLayer('ships')\"]");if(shipRow){shipRow.querySelector('.sb-row-name').textContent='Vessels: 3D live AIS / 2D fleet estimate';shipRow.querySelector('.sb-row-count').hidden=true;}
  const labelRow=document.querySelector('[data-layer="ships"] .tb-tooltip');if(labelRow)labelRow.textContent='Ships: 3D live AIS / 2D static fleet estimate';
  if(!saved){Object.assign(activeState,defaults);fireMode=0;stopMissiles();}
  if(saved?.version===2){
    density=['off','sparse','balanced'].includes(saved.density)?saved.density:'sparse';globeSites=!!saved.globeSites;
    if([24,48,168].includes(saved.strikeWindow)){window._strikeWindowHours=saved.strikeWindow;localStorage.setItem('strikeWindow',saved.strikeWindow);}
    if(['off','paths','animated'].includes(saved.missileMode)){window._missileMode=saved.missileMode;window._missileAnimActive=saved.missileMode!=='off';localStorage.setItem('missileMode',saved.missileMode);renderMissileArcs();}
    if(BRIEF_FONT_STEPS.includes(saved.briefFontPct)){briefFontPct=saved.briefFontPct;applyBriefFont();}
    feedTimeHours=[0,0.5,1,2,6,24,48].includes(saved.feedTimeHours)?saved.feedTimeHours:2;
    feedActiveCats=new Set((saved.feedCats||[]).filter(k=>k in SIDE_LABELS));if($('feed-search'))$('feed-search').value=saved.feedSearch||'';feedQuery=feedNorm(saved.feedSearch||'');
    $('globe3d-map').value=['esri-imagery','osm'].includes(saved.globeMap)?saved.globeMap:'esri-imagery';$('globe3d-style').value=saved.globeStyle||'normal';
    if(saved.currentBasemap==='viirs')oldBasemap('viirs');
    if(saved.renderer==='2d'&&is3D())toggleGlobe3d();
    if(saved.selectedEventZone)lockEventZone(saved.selectedEventZone.lat,saved.selectedEventZone.lon,saved.selectedEventZone.label);
  }
  applyLayers(activeState);sync();refreshLegend();startReadyTimer();
  window.MagenSettingsAudit={legacyOnly:[...legacyOnly],countries:countryNames,newsMatches,get density(){return density;},get lastAck(){return lastAck;},is3D};
})();
