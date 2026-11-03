/* Renderer failures must not strand the host inside Cesium's stopped-render dialog. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const switchRenderer = toggleGlobe3d;
  let failed = false;
  function banner() {
    let el=$('globe-render-failure');if(el)return el;
    el=document.createElement('div');el.id='globe-render-failure';el.setAttribute('role','alert');
    el.style.cssText='position:fixed;top:148px;left:50%;transform:translateX(-50%);z-index:1800;max-width:calc(100vw - 24px);width:480px;box-sizing:border-box;padding:12px;background:#23131ff5;border:1px solid #d98b71;border-radius:8px;color:#ffe9df;font:12px/1.5 system-ui';
    const text=document.createElement('div');text.textContent='The 3D renderer stopped. The 2D map is still available.';
    const retry=document.createElement('button');retry.type='button';retry.textContent='Retry 3D';retry.style.cssText='margin-top:8px;padding:8px 14px;cursor:pointer';retry.onclick=()=>toggleGlobe3d();
    const dismiss=document.createElement('button');dismiss.type='button';dismiss.textContent='Dismiss';dismiss.style.cssText='margin-left:8px;padding:8px 12px;cursor:pointer';dismiss.onclick=()=>{el.hidden=true;};
    el.append(text,retry,dismiss);document.body.appendChild(el);return el;
  }
  function fail(error, details) {
    const old=$('globe3d');
    const diagnostics={};
    for(const key of ['contextLost','drawingBufferWidth','drawingBufferHeight','canvasWidth','canvasHeight','devicePixelRatio','event']){
      const value=details?.[key];if(typeof value==='boolean'||(typeof value==='number'&&Number.isFinite(value))||typeof value==='string')diagnostics[key]=typeof value==='string'?value.slice(0,100):value;
    }
    window._lastGlobeRenderError={error:String(error || 'Unknown 3D rendering error').slice(0,4000),diagnostics,at:new Date().toISOString()};
    window.MagenNewsBubbles?.close();
    globe3dReady=false;
    if(!old.hidden)switchRenderer();
    // Destroy the failed browsing context instead of showing the same dead renderer on retry.
    const next=document.createElement('iframe');next.id='globe3d';next.title='3D war-room globe';next.hidden=true;next.setAttribute('allow','fullscreen');old.replaceWith(next);
    failed=true;
    $('globe3d-toggle').textContent='↻ RETRY 3D';
    $('globe3d-toggle').title='Retry 3D in a fresh renderer. The previous renderer stopped.';
    map.invalidateSize();banner().hidden=false;
  }
  window.toggleGlobe3d = () => {
    if(failed){globe3dReady=false;failed=false;}
    switchRenderer();
  };
  window.addEventListener('message',ev=>{
    const f=$('globe3d');
    if(ev.origin!==GLOBE3D_ORIGIN||ev.source!==f.contentWindow||!ev.data)return;
    if(ev.data.type==='gev:render-error')fail(ev.data.error,ev.data.diagnostics);
    if(ev.data.type==='gev:view-applied'&&ev.data.ok&&!f.hidden){const el=$('globe-render-failure');if(el)el.hidden=true;}
  });
  window.MagenMapRecovery={get failed(){return failed;}};
})();
