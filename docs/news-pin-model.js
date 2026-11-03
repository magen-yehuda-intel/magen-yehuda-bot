/* Pure, shared news-pin model. Full news payloads stay in the host, never in the globe. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MagenNewsPins=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function located(e){return Number.isFinite(e?.lat)&&Number.isFinite(e?.lon)&&Math.abs(e.lat)<=90&&Math.abs(e.lon)<=180;}
  function pinId(e){return located(e)?'magen-news:'+String(e.lat)+':'+String(e.lon):null;}
  function storyKey(e){return JSON.stringify([e.src||e.source||'',e.ts||e.timestamp||0,e.link||'',e.text||'']);}
  function groupEvents(events){
    const groups=new Map();
    [...(events||[])].filter(located).sort((a,b)=>(b.ts||b.timestamp||0)-(a.ts||a.timestamp||0)).forEach(e=>{
      const clientId=pinId(e);let g=groups.get(clientId);
      if(!g){g={clientId,lat:e.lat,lon:e.lon,label:String(e.loc||e.src||e.source||'News location'),events:[],keys:new Set()};groups.set(clientId,g);}
      const key=storyKey(e);if(!g.keys.has(key)){g.events.push(e);g.keys.add(key);}
    });
    return [...groups.values()].map(({keys,...g})=>g);
  }
  function createPins(events,{labels=true,maxPins=12}={}){
    return groupEvents(events).slice(0,maxPins).map(g=>({type:'pin',clientId:g.clientId,latitude:g.lat,longitude:g.lon,color:({israel:'cyan',us:'cyan',iran:'red',iran_proxy:'amber'})[g.events[0].side]||'primary',label:labels?g.label.slice(0,40)+(g.events.length>1?' · '+g.events.length:''):''}));
  }
  function validNewsLink(value){try{const u=new URL(String(value));return ['https:','http:'].includes(u.protocol)?u.href:null;}catch(_){return null;}}
  return {located,pinId,storyKey,groupEvents,createPins,validNewsLink};
});
