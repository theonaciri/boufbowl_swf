import { renderTasks } from './cpu-budget.mjs';
import {chromium} from 'playwright';
import {readFileSync,writeFileSync,mkdirSync,renameSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
const directory=process.argv[3];
const tasks=JSON.parse(readFileSync(join(directory,'pending.json')));
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding','--num-raster-threads=1']});
try{
 await renderTasks(tasks, async()=>{
 const page=await browser.newPage({viewport:{width:2560,height:1500}});
 await page.goto(process.argv[2]);
 await page.evaluate(async()=>{
  const original=HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext=function(type,attrs){return original.call(this,type,/webgl/.test(type)?{...attrs,preserveDrawingBuffer:true}:attrs)};
  const p=window.RufflePlayer.newest().createPlayer();p.style.cssText='width:2560px;height:1500px;display:block';document.querySelector('#mount').append(p);window.p=p;
  await p.load({url:'/bin/capture-home.swf',quality:'high',backgroundColor:'#111111',allowScriptAccess:true,autoplay:'on',unmuteOverlay:'hidden',parameters:{lang:'fr',server:'0',mock:'0',tuto:'0'}});
 });

 return page;
 }, async(task,page)=>{
 const flush=()=>page.evaluate(()=>new Promise(requestAnimationFrame));

  await page.evaluate(()=>window.p.ruffle().resume());
  const data={name:task.name,actors:JSON.stringify(task.actors)};
  await page.waitForFunction(d=>{try{const s=window.p.ruffle().callExternalInterface('cinemaCreate',d.name,d.actors);if(String(s).startsWith('ERROR'))throw Error(s);return Number(s)>0}catch(e){if(String(e).includes('ERROR:'))throw e;return false}},data,{timeout:90000,polling:100});
  const count=Number(await page.evaluate(d=>window.p.ruffle().callExternalInterface('cinemaCreate',d.name,d.actors),data));
  const folder=join(directory,task.slug);mkdirSync(folder,{recursive:true});
  const encoder=spawn('ffmpeg',['-y','-v','error','-threads','1','-filter_threads','1','-f','image2pipe','-framerate','25','-c:v','png','-i','pipe:0','-an','-c:v','ffv1','-level','3','-threads','1',join(folder,'native.building.mkv')],{stdio:['pipe','inherit','inherit']});
  const completion=once(encoder,'close');
  const slots=new Set();const heroes=new Set();
  const started=performance.now();
  try{
   for(let frame=1;frame<=count;frame++){
    await page.evaluate(n=>window.p.ruffle().callExternalInterface('cinemaFrame',n),frame);
    await page.evaluate(n=>window.p.ruffle().callExternalInterface('cinemaFreeze',n),frame);
    await page.evaluate(()=>window.p.ruffle().resume());
    await flush();
    for(let attempt=0;attempt<6;attempt++){
      const ready=await page.evaluate(()=>JSON.parse(window.p.ruffle().callExternalInterface('cinemaGroups')).every(g=>g.visible && g.label?.startsWith('cg_')));
      if(ready)break;
      await flush();
    }
    await page.evaluate(()=>window.p.ruffle().suspend());
    const result=await page.evaluate(()=>{
      const canvas=window.p.shadowRoot.querySelector('canvas');
      const groups=JSON.parse(window.p.ruffle().callExternalInterface('cinemaGroups'));
      return {png:canvas.toDataURL('image/png').split(',')[1],width:canvas.width,height:canvas.height,groups};
    });
    if(result.width!==2560||result.height!==1500)throw Error('Unexpected render size: '+result.width+'x'+result.height);
    for(const group of result.groups){
      const slot=Number(group.name.split('_')[1]);slots.add(slot);
      if(group.visible&&group.label?.startsWith('cg_')){
        const hero=Number(group.label.slice(3));heroes.add(hero);
        if(hero!==task.actors[slot-1]?.hero)throw Error('Incorrect legendary skin: '+JSON.stringify(group));
      }
    }
    const png=Buffer.from(result.png,'base64');
    if(!encoder.stdin.write(png))await once(encoder.stdin,'drain');
    if(frame%25===0)console.log(task.slug,frame+'/'+count,((performance.now()-started)/1000).toFixed(1)+'s');
   }
   encoder.stdin.end();
   const [code]=await completion;if(code!==0)throw Error('Lossless capture encoding failed');
  }catch(error){encoder.kill();throw error}
  const expected=task.actors.map(a=>a.hero).sort((a,b)=>a-b);
  if(JSON.stringify([...heroes].sort((a,b)=>a-b))!==JSON.stringify(expected))throw Error('Legend cast was not rendered: '+JSON.stringify([...heroes]));
  renameSync(join(folder,'native.building.mkv'),join(folder,'native.mkv'));
  const native_sha256=createHash('sha256').update(readFileSync(join(folder,'native.mkv'))).digest('hex');
  const metadata={...task,native_sha256,frames:count,seconds:count/25,verified_skin_labels:[...heroes],actor_slots:[...slots]};
  writeFileSync(join(folder,'capture.json'),JSON.stringify(metadata,null,2));
  console.log('Captured',task.slug,count,'native vector frames');
 });
}finally{await browser.close()}
