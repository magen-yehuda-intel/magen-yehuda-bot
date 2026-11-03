/* Run in an isolated browser tab. QA error signal tests recovery, not GPU root cause. */
(() => {
  const results=[];const check=(name,ok)=>results.push({name,ok:!!ok});
  const frame=document.getElementById('globe3d');
  if(frame.hidden)toggleGlobe3d();
  window.dispatchEvent(new MessageEvent('message',{origin:'https://invalid.example',source:frame.contentWindow,data:{type:'gev:render-error',error:'untrusted fixture'}}));
  check('untrusted origin cannot force fallback',!frame.hidden);
  window.dispatchEvent(new MessageEvent('message',{origin:GLOBE3D_ORIGIN,source:window,data:{type:'gev:render-error',error:'untrusted fixture'}}));
  check('wrong source window cannot force fallback',!frame.hidden);
  window.dispatchEvent(new MessageEvent('message',{origin:GLOBE3D_ORIGIN,source:frame.contentWindow,data:{type:'gev:render-error',error:'QA fixture: fragment shader compile failure'}}));
  const replacement=document.getElementById('globe3d');
  check('render failure returns to usable 2D',replacement.hidden&&document.getElementById('map').style.visibility!=='hidden');
  check('failed GPU browsing context is destroyed',replacement!==frame&&!frame.isConnected);
  check('failure is recorded and disclosed',!!window._lastGlobeRenderError&&!document.getElementById('globe-render-failure').hidden);
  check('retry starts with readiness unknown',globe3dReady===false);
  toggleGlobe3d();
  check('retry uses fresh iframe and reloads app',!replacement.hidden&&replacement.src.startsWith(GLOBE3D_ORIGIN));
  return {passed:results.filter(x=>x.ok).length,total:results.length,failures:results.filter(x=>!x.ok),results};
})();
