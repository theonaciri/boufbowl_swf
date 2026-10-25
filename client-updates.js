export function newerRelease(first,second) {
  const valid=/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
  if(!valid.test(first)||!valid.test(second))return false;
  const a=first.split('.').map(Number),b=second.split('.').map(Number);
  for(let i=0;i<3;i++)if(a[i]!==b[i])return a[i]>b[i];
  return false;
}
export function watchWebUpdates({version,container,fetcher=fetch,reload=()=>location.reload()}) {
  let busy=false,shown=false;
  const check=async()=>{
    if(busy||shown||document.hidden)return;
    busy=true;
    try {
      const response=await fetcher('updates.json?check='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(10000)});
      if(!response.ok)return;
      const envelope=await response.json();
      if(typeof envelope.payload!=='string'||envelope.payload.length>131072)return;
      const manifest=JSON.parse(envelope.payload),item=manifest.platforms?.web;
      if(manifest.schema!==1||!item||!newerRelease(item.version,version))return;
      shown=true;
      const notice=document.createElement('aside');notice.id='client-update';notice.setAttribute('role','status');
      const text=document.createElement('span');text.textContent=`Boufbowl ${item.version} est disponible. Rechargez après votre match.`;
      const button=document.createElement('button');button.type='button';button.textContent='METTRE À JOUR';
      button.addEventListener('click',()=>{if(confirm('Recharger le jeu ? Faites-le après votre match.'))reload();});
      const dismiss=document.createElement('button');dismiss.type='button';dismiss.textContent='PLUS TARD';dismiss.addEventListener('click',()=>notice.remove());
      notice.append(text,button,dismiss);container.append(notice);
    } catch { /* An offline update service must not stop play. */ }
    finally {busy=false;}
  };
  check();const timer=setInterval(check,30*60*1000);
  document.addEventListener('visibilitychange',check);
  return ()=>{clearInterval(timer);document.removeEventListener('visibilitychange',check);};
}
