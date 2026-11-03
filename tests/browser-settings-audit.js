/* Execute in an isolated Magen browser tab, with live data loaded. Mutates only browser preferences, then resets. */
(() => {
  const results=[];
  const check=(name,ok)=>results.push({name,ok:!!ok});
  const $=id=>document.getElementById(id);
  check('shared settings adapter loaded',!!window.MagenSettingsAudit);
  check('strike windows have all three options',['strike-window','strike-window-mobile','strike-window-sidebar'].every(id=>$(id).options.length===3));
  filterSidebarLayers('nuclear');check('layer search filters nonmatching rows',[...document.querySelectorAll('#tab-layers .sb-row')].some(x=>x.hidden));filterSidebarLayers('');
  check('cleared layer search restores every row',[...document.querySelectorAll('#tab-layers .sb-row')].every(x=>!x.hidden));
  showIranOnly();check('Iran-only excludes Gulf energy',activeState.energy&&!activeState.gulfenergy);check('static preset opens visible 2D',$('globe3d').hidden);
  clearAllLayers();check('Clear removes every layer',Object.values(activeState).every(x=>!x));check('Clear turns missiles off',window._missileMode==='off');
  showAllLayers();check('Show All enables every layer',Object.values(activeState).every(Boolean));
  showUSOnly();check('US preset excludes Iran sublayers',activeState.military&&!activeState.nuclear&&!activeState.energy&&!activeState.gulfenergy);
  resetConfig();check('Reset clears all Iran sublayers',['nuclear','missiles','naval','ad','airbases','irgc','energy','gulfenergy','sam'].every(k=>!activeState[k]));check('Reset returns to 3D',!$('globe3d').hidden);
  const view=globe3dView(false);check('background settings preserve user camera',!('camera' in view));check('regional country areas configured',view.annotations.filter(a=>a.type==='area').length===12);check('default labels are sparse',view.detection.enabled&&view.detection.densityPct===25);
  $('globe-density').value='off';$('globe-density').dispatchEvent(new Event('change'));check('labels OFF reaches 3D view',!globe3dView(false).detection.enabled);
  $('globe-density').value='sparse';$('globe-density').dispatchEvent(new Event('change'));
  toggleLayer('borders');check('border toggle removes country areas',!globe3dView(false).annotations.some(a=>a.type==='area'));toggleLayer('borders');
  $('globe-sites').checked=true;$('globe-sites').dispatchEvent(new Event('change'));check('3D military sites toggle reaches provider',globe3dView(false).layers.includes('military-installations'));
  for(const name of MagenSettingsAudit.legacyOnly){
    if($('globe3d').hidden)toggleGlobe3d();
    const before=activeState[name];toggleLayer(name);
    check(name+' exact overlay routes to visible 2D',$('globe3d').hidden&&activeState[name]);
  }
  resetConfig();cycleAircraft();check('aircraft ALL reaches globe',globe3dView(false).layers.includes('flights'));cycleAircraft();check('aircraft MIL excludes civilian provider',globe3dView(false).layers.includes('military')&&!globe3dView(false).layers.includes('flights'));cycleAircraft();check('civilian-only filtering opens 2D',$('globe3d').hidden&&aircraftMode===3);
  resetConfig();cycleFires();check('first fire click enables age-filtered fires',fireMode===1&&activeState.fires&&$('globe3d').hidden);
  setStrikeWindow(168);check('strike selection stays synchronized',['strike-window','strike-window-mobile','strike-window-sidebar'].every(id=>$(id).value==='168'));
  resetConfig();lockEventZone(35.69,51.39,'Tehran');check('news selects requested 3D camera',globe3dView(true).camera.lat===35.69);check('zone remains selected through settings update',globe3dView(false).annotations.some(a=>a.type==='pin'&&a.latitude===35.69));check('unlock button is visible',!$('event-zone-unlock').hidden);unlockEventZone();check('unlock restores wide camera',globe3dView(true).camera.altitude_m===3800000&&$('event-zone-unlock').hidden);
  const briefBefore=document.querySelector('#brief-time-bar .active')?.dataset.hours;
  document.querySelector('#feed-time-bar [data-hours="6"]').click();check('feed time does not deselect brief window',document.querySelector('#brief-time-bar .active')?.dataset.hours===briefBefore);
  $('feed-search').value='no-match-magen-audit-847321';renderFeed();check('empty news filter shows no cards',!$('feed-list').querySelector('.feed-item'));check('empty news filter clears 3D pins',!globe3dView(false).annotations.some(a=>a.type==='pin'));check('empty news filter clears 2D OSINT',layers.osint.getLayers().length===0);
  $('feed-search').value='';renderFeed();
  const fontBefore=briefFontPct;$('brief-font-up').click();check('brief font control merged',briefFontPct>fontBefore);$('brief-font-down').click();
  lockEventZone(32.43,53.69,'Iran');saveConfig();const saved=JSON.parse(localStorage.getItem('centcom-config'));check('Save includes shared map/filter/display state',saved.version===2&&saved.density&&saved.globeMap&&saved.feedTimeHours===6&&saved.selectedEventZone?.label==='Iran');
  resetConfig();check('Reset removes saved config',localStorage.getItem('centcom-config')===null);
  return {passed:results.filter(x=>x.ok).length,total:results.length,failures:results.filter(x=>!x.ok),results};
})();
