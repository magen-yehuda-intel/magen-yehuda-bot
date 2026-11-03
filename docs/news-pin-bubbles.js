/* Pin -> news card, across the cross-origin globe boundary. News remains host-owned. */
(() => {
  'use strict';
  const model=MagenNewsPins, $=id=>document.getElementById(id);
  let openId=null, index=0, anchor=null;
  function hydrateSelection(){
    if(selectedEventZone&&!selectedEventZone.newsEvent){
      const e=feedEvents.find(e=>e.lat===selectedEventZone.lat&&e.lon===selectedEventZone.lon&&String(e.loc||'')===selectedEventZone.label);
      if(e)selectedEventZone.newsEvent=e;
    }
  }
  function groups(){
    hydrateSelection();
    const matching=feedEvents.filter(e=>MagenSettingsAudit.newsMatches(e));
    if(selectedEventZone){
      if(!selectedEventZone.newsEvent)return [];
      const chosen=selectedEventZone.newsEvent;
      const group=model.groupEvents([chosen,...matching.filter(e=>e.lat===chosen.lat&&e.lon===chosen.lon)])[0];
      if(!group)return [];
      const key=model.storyKey(chosen);group.events.sort((a,b)=>(model.storyKey(a)===key?-1:0)-(model.storyKey(b)===key?-1:0));
      return [group];
    }
    return activeState.osint?model.groupEvents(matching).slice(0,12):[];
  }
  function close(){const el=$('news-pin-bubble');if(el)el.remove();openId=null;index=0;}
  function button(text,action){const b=document.createElement('button');b.type='button';b.textContent=text;b.style.cssText='padding:7px 12px;border:1px solid #37515d;border-radius:5px;background:#14252f;color:#d9faff;cursor:pointer';b.addEventListener('click',action);return b;}
  function render(){
    const group=groups().find(g=>g.clientId===openId);
    if(!group||!group.events.length){close();return false;}
    index=Math.max(0,Math.min(index,group.events.length-1));const news=group.events[index];
    let el=$('news-pin-bubble');if(!el){el=document.createElement('section');el.id='news-pin-bubble';el.setAttribute('role','dialog');el.setAttribute('aria-label','News at selected map pin');el.tabIndex=-1;document.body.appendChild(el);}
    el.style.cssText='position:fixed;z-index:2000;box-sizing:border-box;width:min(360px,calc(100vw - 24px));max-height:calc(100vh - 200px);overflow:auto;padding:14px;background:#091724f5;border:1px solid #39d0ff;border-radius:10px;box-shadow:0 12px 40px #000b;color:#e5f6ff;font:13px/1.5 system-ui';el.replaceChildren();
    const head=document.createElement('div');head.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px';
    const location=document.createElement('strong');location.textContent=group.label;location.dir='auto';head.append(location,button('✕',close));el.append(head);
    const source=document.createElement('div');source.style.cssText='font-size:11px;color:#8fd7e7;margin-bottom:6px';source.textContent=String(news.src||news.source||'Source unavailable');el.append(source);
    const time=document.createElement('time');const ts=Number(news.ts||news.timestamp||0);
    if(Number.isFinite(ts)&&ts>0){const date=new Date(ts*1000);time.dateTime=date.toISOString();time.textContent=date.toLocaleString();}else time.textContent=news.published_date||'Publication time unavailable';
    time.style.cssText='display:block;color:#9daebd;font-size:11px;margin-bottom:10px';el.append(time);
    const text=document.createElement('div');text.textContent=String(news.text||news.notes||'No report text available.');text.dir='auto';text.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.55';el.append(text);
    const provenance=document.createElement('div');provenance.style.cssText='font-size:10px;color:#9daebd;margin-top:10px';provenance.textContent=news.archived?'Archived source report':'Source report · not independently verified';el.append(provenance);
    const url=model.validNewsLink(news.link)||model.validNewsLink(getSrcLink(news.src||news.source||''));
    if(url){const link=document.createElement('a');link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=model.validNewsLink(news.link)?'Open original report ↗':'Open source ↗';link.style.cssText='display:inline-block;margin-top:10px;color:#6ee7ff';el.append(link);}
    const pager=document.createElement('div');pager.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px';
    const prev=button('←',()=>{index--;render();}),next=button('→',()=>{index++;render();});prev.disabled=index===0;next.disabled=index===group.events.length-1;
    prev.setAttribute('aria-label','Previous report');next.setAttribute('aria-label','Next report');const count=document.createElement('span');count.textContent=(index+1)+' of '+group.events.length+' reports at this pin';count.style.fontSize='10px';pager.append(prev,count,next);el.append(pager);
    const rect=$('globe3d').getBoundingClientRect(),width=el.offsetWidth,height=el.offsetHeight;
    const x=anchor?.x!==undefined?rect.left+anchor.x*rect.width:innerWidth/2;
    const y=anchor?.y!==undefined?rect.top+anchor.y*rect.height:innerHeight/2;
    const left=Math.max(12,Math.min(x-width/2,innerWidth-width-12));
    const top=Math.max(142,Math.min(y-height-18>=142?y-height-18:y+18,innerHeight-height-68));
    el.style.left=left+'px';el.style.top=top+'px';return true;
  }
  function open(clientId,screenX,screenY){
    if(!groups().some(g=>g.clientId===clientId))return false;
    openId=clientId;index=0;anchor=Number.isFinite(screenX)&&screenX>=0&&screenX<=1&&Number.isFinite(screenY)&&screenY>=0&&screenY<=1?{x:screenX,y:screenY}:null;
    const shown=render();if(shown)$('news-pin-bubble').focus({preventScroll:true});return shown;
  }
  const oldFly=flyToEvent;
  window.flyToEvent=(lat,lon,text,src,loc,newsEvent=null)=>{
    const event=newsEvent||feedEvents.find(e=>e.lat===lat&&e.lon===lon&&text&&String(e.text||'').startsWith(text));
    close();oldFly(lat,lon,text,src,loc,event||null);
  };
  const oldRender=renderFeed;
  window.renderFeed=()=>{hydrateSelection();oldRender();if(openId)render();};
  const oldToggle=toggleGlobe3d;
  window.toggleGlobe3d=()=>{close();oldToggle();};
  window.addEventListener('message',ev=>{
    const frame=$('globe3d');
    if(ev.origin!==GLOBE3D_ORIGIN||ev.source!==frame.contentWindow||!ev.data)return;
    if(ev.data.type==='gev:annotation-selected'&&typeof ev.data.clientId==='string')open(ev.data.clientId,ev.data.screenX,ev.data.screenY);
  });
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&openId){e.preventDefault();close();}});
  window.addEventListener('resize',()=>{if(openId)render();});
  hydrateSelection();
  if(selectedEventZone?.newsEvent)globe3dPush();
  window.MagenNewsBubbles={groups,open,close};
})();
