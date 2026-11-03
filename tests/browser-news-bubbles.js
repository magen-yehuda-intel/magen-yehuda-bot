/* Host contract/security checks; a separate real pointer click must verify the globe bridge. */
(() => {
  const results=[];const check=(name,ok)=>results.push({name,ok:!!ok});
  const group=MagenNewsBubbles.groups()[0];if(!group)throw new Error('Load real news before checking bubbles');
  MagenNewsBubbles.close();
  const frame=document.getElementById('globe3d');
  function send(origin,source,clientId){window.dispatchEvent(new MessageEvent('message',{origin,source,data:{type:'gev:annotation-selected',clientId,screenX:0.5,screenY:0.5}}));}
  send('https://invalid.example',frame.contentWindow,group.clientId);check('wrong origin cannot open a news bubble',!document.getElementById('news-pin-bubble'));
  send(GLOBE3D_ORIGIN,window,group.clientId);check('wrong frame cannot open a news bubble',!document.getElementById('news-pin-bubble'));
  send(GLOBE3D_ORIGIN,frame.contentWindow,'unknown-news-pin');check('unknown pin identity is ignored',!document.getElementById('news-pin-bubble'));
  send(GLOBE3D_ORIGIN,frame.contentWindow,group.clientId);
  let bubble=document.getElementById('news-pin-bubble');check('known pin opens a visible news card',!!bubble);
  check('card contains the real report text',bubble?.textContent.includes(group.events[0].text));
  check('card shows the source',bubble?.textContent.includes(group.events[0].src||group.events[0].source||'Source unavailable'));
  check('card contains publication time',!!bubble?.querySelector('time'));
  const link=bubble?.querySelector('a');check('source link uses an allowed protocol or is omitted',!link||['https:','http:'].includes(new URL(link.href).protocol));
  if(group.events.length>1){bubble.querySelector('[aria-label="Next report"]').click();bubble=document.getElementById('news-pin-bubble');check('coincident pin can show the next real report',bubble.textContent.includes(group.events[1].text));}
  bubble.querySelector('button').click();check('news card close button works',!document.getElementById('news-pin-bubble'));
  return {passed:results.filter(x=>x.ok).length,total:results.length,failures:results.filter(x=>!x.ok),results};
})();
