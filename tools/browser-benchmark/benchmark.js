import {OPTIONS,aggregate,caseOrder} from './statistics.js';
const $=id=>document.getElementById(id), storageKey='boufbowl.browser-benchmark.v1';
const phases={menu:'Menu',orders:'Ordres',stadium:'3D · 10 acteurs',cinematics:'Animations plein écran'};
let report={version:1,runs:[]},controller,frame,expectedViewport,runGeneration=0,storageAvailable=true,activeTicket=null;
try { report=JSON.parse(localStorage.getItem(storageKey)) || report; } catch {}
for(const option of OPTIONS){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.name='option';input.value=option.id;input.checked=['baseline','layers'].includes(option.id);label.append(input,option.label);$('variants').append(label);}
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const number=x=>Number.isFinite(x)?x.toFixed(1):'—';
function render(){
 const groups=aggregate(report.runs),max=Math.max(1,...groups.map(x=>Math.max(x.game?.meanMs||0,x.game?.p95Ms||0)));
 $('results').innerHTML='<table><thead><tr><th>Variante / scène</th><th>Passages</th><th>Trames</th><th>FPS moyens</th><th>Moyenne ms</th><th>P50 ms</th><th>P95 ms</th><th>P99 ms</th><th>Max ms</th><th>&gt;50 ms</th><th>Calques 3D réutilisés</th></tr></thead><tbody>'+groups.map(g=>`<tr><td>${escape(g.option.label)} · ${phases[g.phase]}<br><small>${escape(g.renderers.join(', '))}</small></td><td>${g.runs}</td><td>${g.game?.frames||0}</td>${['fps','meanMs','medianMs','p95Ms','p99Ms','maxMs','over50'].map(key=>`<td>${number(g.game?.[key])}</td>`).join('')}<td>${g.layerReuses}</td></tr>`).join('')+'</tbody></table>';
 $('chart').innerHTML=groups.length?`<p>Temps moyen <span style="color:#ace1cc">■</span> et P95 <span style="color:#f3bf70">■</span>, en millisecondes. Plus court = plus fluide.</p><svg role="img" aria-label="Comparaison des temps de trame moyens et P95" viewBox="0 0 1024 ${groups.length*52+20}">${groups.map((g,i)=>`<g transform="translate(0 ${i*52+10})"><text x="0" y="16" fill="#e5ecf7" font-size="13">${escape(g.option.label)} · ${phases[g.phase]}</text><rect x="300" y="0" width="${(g.game?.meanMs||0)/max*580}" height="14" fill="#ace1cc"/><text x="${310+(g.game?.meanMs||0)/max*580}" y="12" fill="#e5ecf7" font-size="12">${number(g.game?.meanMs)}</text><rect x="300" y="20" width="${(g.game?.p95Ms||0)/max*580}" height="14" fill="#f3bf70"/><text x="${310+(g.game?.p95Ms||0)/max*580}" y="32" fill="#e5ecf7" font-size="12">${number(g.game?.p95Ms)}</text></g>`).join('')}</svg>`:'';
 $('environment').textContent=JSON.stringify({...report,runs:report.runs.map(({phases,...run})=>({...run,phases:phases.map(({samples,raf,...phase})=>({...phase,gameFrames:samples.length,browserCallbacks:raf.length}))}))},null,2);
 if(storageAvailable)try{localStorage.setItem(storageKey,JSON.stringify(report));}catch{storageAvailable=false;$('storage-warning').hidden=false;}
}
render();
function check(){
 if(controller.signal.aborted)throw new Error('Benchmark arrêté.');
 if(document.hidden)throw new Error('Onglet masqué : mesure interrompue pour éviter un résultat biaisé.');
 if(expectedViewport&&frame&&(frame.clientWidth!==expectedViewport.width||frame.clientHeight!==expectedViewport.height||devicePixelRatio!==expectedViewport.dpr)){
  controller.abort();throw new Error('Dimensions du lecteur modifiées : comparaison interrompue.');
 }
 // An unloaded/failed previous runtime must not poison the next case.
 const current=frame&&new URL(frame.contentWindow.location.href).searchParams.get('run')===activeTicket ? frame.contentWindow : null;
 const mockError=current?.benchmarkNotices?.find(x=>x.text.startsWith('ERROR:'));
 if(mockError)throw new Error(mockError.text);
 if(current?.benchmarkError)throw new Error(current.benchmarkError);
 const fatal=current?.benchmarkLogs?.find(x=>x.includes('Error in AVM2 external interface callback'));
 if(fatal)throw new Error(fatal);
}

async function until(predicate,timeout=120000){const start=performance.now();while(true){check();const value=predicate();if(value)return value;if(performance.now()-start>timeout)throw new Error('Scène indisponible ou bloquée (délai dépassé).');await new Promise(r=>setTimeout(r,100));}}
async function wait(ms){const deadline=performance.now()+ms;await until(()=>performance.now()>=deadline,ms+1000);}
function api(name,...args){return frame.contentWindow.benchmarkAPI(name,...args);}
function state(){return api('benchmarkState');}
async function measure(id,seconds,complete){
 check();$('status').textContent=`${report.current} · ${phases[id]}`;
 const before=api('benchmarkSample',id==='stadium'?'motion':'start'),raf=[],started=performance.now();let last=0,rafId;
 const tick=now=>{if(last)raf.push(now-last);last=now;rafId=requestAnimationFrame(tick)};rafId=requestAnimationFrame(tick);
 try {if(complete)await until(complete,120000);else await wait(seconds*1000);}finally{cancelAnimationFrame(rafId);}
 const after=api('benchmarkSample','stop');
 if(id==='stadium'&&after.movedActors!==10)throw new Error(`Les dix acteurs ne sont pas en mouvement (${after.movedActors}/10).`);
 return {id,movedActors:after.movedActors,positionsBefore:before.positions,positionsAfter:after.positions,samples:after.samples,raf,targetFps:after.target,wallMs:performance.now()-started,renderBefore:before.render,renderAfter:after.render};
}
async function run(option,settings,prime=false){
 $('status').textContent=`${report.current} · chargement du lecteur`;
 const started=performance.now();frame=$('player');frame.style.pointerEvents='auto';
 expectedViewport ||= {width:frame.clientWidth,height:frame.clientHeight,dpr:devicePixelRatio};runGeneration+=1;const ticket=String(runGeneration);activeTicket=ticket;frame.src='/benchmark-runner.html?'+new URLSearchParams({option:JSON.stringify(option),fps:settings.fps,run:ticket});
 frame.scrollIntoView({block:'center'});
 await until(()=>new URL(frame.contentWindow.location.href).searchParams.get('run')===ticket && frame.contentWindow.benchmarkLoaded && frame.contentWindow.benchmarkAPI);
 await until(()=>{try{return state()?.views.some(x=>['MatchCreationView','MatchmakingView','WelcomeView'].some(name=>x.includes(name)));}catch{return false;}});
 const correctness=api('benchmarkCorrectness');
 if(!correctness || Object.values(correctness).some(x=>x!==true))throw new Error('Échec des invariants de rendu : '+JSON.stringify(correctness));
 for(const context of frame.contentWindow.benchmarkContexts)context.resume();
 if(frame.contentWindow.benchmarkContexts.some(x=>x.state==='suspended')){
  $('status').textContent='Cliquez dans le lecteur pour autoriser la musique, puis le benchmark continuera.';
  await until(()=>frame.contentWindow.benchmarkContexts.every(x=>x.state==='running'));
 }
 frame.style.pointerEvents='none';
 await wait(settings.warmup*1000);
 const measured=[];
 measured.push(await measure('menu',settings.seconds));
 api('benchmarkStart');
 await until(()=>frame.contentWindow.benchmarkNotices.some(x=>x.text.startsWith('Incoming FIELD_STATE')) && state()?.views.some(x=>x.includes('FieldView')));
 await wait(settings.warmup*1000);
 measured.push(await measure('orders',settings.seconds));
 api('benchmarkResolve');
 await until(()=>state()?.phase==='3d' && state().actors===10 && api('browserRenderStats').calls>0);
 await until(()=>frame.contentWindow.benchmarkNotices.filter(x=>x.text.startsWith('Actor moving ')).length===10);
 await wait(settings.warmup*1000);
 measured.push(await measure('stadium',settings.seconds));
 for(const key of ['Illustration_Terre_Terre','Illustration_lancer','Illustration_reception_ok_Air']){
  const before=frame.contentWindow.benchmarkNotices.length;
  api('benchmarkCutscene',key);
  await until(()=>frame.contentWindow.benchmarkNotices.slice(before).some(x=>x.text.includes('Cinematic started: '+key)||x.text.includes('Cinematic unavailable:')));
  if(frame.contentWindow.benchmarkNotices.slice(before).some(x=>x.text.includes('Cinematic unavailable:')))throw new Error('Animation indisponible : '+key);
  const phase=await measure('cinematics',0,()=>api('benchmarkCutsceneStatus'));phase.animation=key;measured.push(phase);
 }
 $('status').textContent=report.current+' · validation de fin de tour (non mesurée)';
 const finishing=performance.now();api('benchmarkFinish');
 await until(()=>frame.contentWindow.benchmarkNotices.some(x=>x.text.includes('Outgoing ResolutionDoneMessage')),300000);
 await until(()=>frame.contentWindow.benchmarkNotices.some(x=>x.text.includes('Fixture delivered')));
 await until(()=>frame.contentWindow.benchmarkNotices.filter(x=>x.text.startsWith('Incoming FIELD_STATE')).length===2);
 const resources=frame.contentWindow.performance.getEntriesByType('resource');
 const music=resources.filter(x=>x.name.includes('/sounds/music/')).map(x=>x.name);
 const audio=frame.contentWindow.benchmarkContexts.map(x=>x.state);
 const logs=frame.contentWindow.benchmarkLogs;
 return structuredClone({completionMs:performance.now()-finishing,option,prime,correctness,actualRenderer:logs.join('\n').match(/Used renderer: ([^)]+)/)?.[1] || 'non identifié',phases:measured,music,audio,audioVerified:['music_tactic_loop_01.mp3','music_resolution_loop_01.mp3'].every(name=>music.some(url=>url.endsWith(name)))&&audio.includes('running'),wallMs:performance.now()-started,
  resolutionDone:true,actors:10,notices:frame.contentWindow.benchmarkNotices,rendererLogs:logs.filter(x=>/renderer|webgpu|webgl|adapter/i.test(x)),
  visibility:'visible',viewport:{width:frame.clientWidth,height:frame.clientHeight,dpr:devicePixelRatio}});
}
async function releasePlayer(){
 const contexts=frame?.contentWindow.benchmarkContexts || [];
 frame?.contentWindow.benchmarkPlayer?.remove();
 const closed=await Promise.allSettled(contexts.filter(x=>x.state!=='closed').map(x=>x.close()));
 if(frame)frame.src='about:blank';
 if(closed.some(x=>x.status==='rejected'))throw new Error('Le contexte audio précédent ne peut pas être fermé.');
}
$('settings').addEventListener('submit',async event=>{
 event.preventDefault();const data=new FormData(event.currentTarget),selected=OPTIONS.filter(x=>data.getAll('option').includes(x.id));if(!selected.length)return;
 expectedViewport=null;controller=new AbortController();$('start').disabled=true;$('stop').disabled=false;$('error').textContent='';
 for(const fieldset of event.currentTarget.querySelectorAll('fieldset'))fieldset.disabled=true;
 $('json').disabled=$('csv').disabled=true;
 const settings={seconds:Number(data.get('seconds')),warmup:Number(data.get('warmup')),rounds:Number(data.get('rounds')),fps:Number(data.get('fps')),prime:data.has('prime')};
 const gl=document.createElement('canvas').getContext('webgl2'),debug=gl?.getExtension('WEBGL_debug_renderer_info');
 const gpu=gl ? gl.getParameter(debug ? debug.UNMASKED_RENDERER_WEBGL : gl.RENDERER) : 'WebGL2 indisponible';
 gl?.getExtension('WEBGL_lose_context')?.loseContext();
 report={version:1,at:new Date().toISOString(),settings,manifest:await fetch('/benchmark-manifest.json').then(r=>r.json()),environment:{gpu,userAgent:navigator.userAgent,cores:navigator.hardwareConcurrency,dpr:devicePixelRatio,viewport:{width:innerWidth,height:innerHeight}},runs:[],failedRuns:[]};
 const schedule=caseOrder(selected,settings.rounds);$('progress').max=schedule.length;$('progress').value=0;
 try{
  if(settings.prime){report.current='Préchauffe non mesurée';try{report.prime=await run(selected[0],settings,true);}finally{await releasePlayer();}}
  for(const [index,option] of schedule.entries()){
   report.current=`${index+1}/${schedule.length} · ${option.label}`;
   try {const result=await run(option,settings);report.runs.push(result);}
   catch(error){if(controller.signal.aborted||document.hidden)throw error;report.failedRuns.push(structuredClone({option,error:error.message,notices:frame.contentWindow.benchmarkNotices,logs:frame.contentWindow.benchmarkLogs}));}
   finally{await releasePlayer();}
   $('progress').value=index+1;render();
  }
  const incomplete=report.runs.filter(x=>!x.audioVerified);
  $('error').textContent=report.failedRuns.map(x=>x.option.label+' : '+x.error).join('\n');
  $('status').textContent=report.failedRuns.length?'Benchmark terminé avec des variantes en échec ; seules les exécutions complètes sont affichées.':incomplete.length?'Mesures terminées ; musique non vérifiée pour certaines variantes. Consulter le rapport.':'Benchmark terminé. Musique et fin de tour vérifiées pour chaque variante.';
 }catch(error){report.error=error.message;report.failure=structuredClone({notices:frame?.contentWindow.benchmarkNotices,logs:frame?.contentWindow.benchmarkLogs});$('error').textContent=error.message;$('status').textContent='Benchmark interrompu ; résultats complets conservés.';}
 finally{for(const fieldset of $('settings').querySelectorAll('fieldset'))fieldset.disabled=false;$('json').disabled=$('csv').disabled=false;delete report.current;$('start').disabled=false;$('stop').disabled=true;frame.src='about:blank';render();}
});
$('stop').onclick=()=>controller?.abort();
document.addEventListener('keydown',event=>{if(event.key==='Escape')controller?.abort();});
for(const format of ['json','csv'])$(format).onclick=()=>{
 let body,type;if(format==='json'){body=JSON.stringify(report,null,2);type='application/json';}
 else{const groups=aggregate(report.runs);body='option,scene,runs,frames,fps,mean_ms,p50_ms,p95_ms,p99_ms,max_ms,over_50ms\n'+groups.map(g=>[g.option.id,g.phase,g.runs,...['frames','fps','meanMs','medianMs','p95Ms','p99Ms','maxMs','over50'].map(x=>g.game?.[x]??'')].join(',')).join('\n');type='text/csv';}
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([body],{type}));a.download='boufbowl-browser-benchmark.'+format;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
