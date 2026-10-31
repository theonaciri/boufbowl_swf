import {chromium} from '../../tools/website/node_modules/playwright/index.mjs';
import {writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import path from 'node:path';
const {values}=parseArgs({options:{url:{type:'string',default:'http://127.0.0.1:9927/'},output:{type:'string',default:'.local/browser-profiling'},software:{type:'boolean',default:false},headed:{type:'boolean',default:false},trace:{type:'boolean',default:false}}});
const output=path.resolve(values.output);await mkdir(output,{recursive:true});
const args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'];
if(values.software)args.push('--enable-unsafe-swiftshader','--use-angle=swiftshader');
const browser=await chromium.launch({headless:!values.headed,args});
const captures=[];
try{
 const page=await browser.newPage({viewport:{width:688,height:1000}}),session=await page.context().newCDPSession(page),system=await browser.newBrowserCDPSession();
 page.on('pageerror',e=>console.log('PAGE ERROR '+e.message));
 await page.goto(values.url);
 for(const [name,value] of [['seconds','8'],['warmup','2'],['rounds','1']])await page.locator(`[name=${name}]`).fill(value);
 await page.locator('[name=prime]').uncheck();await page.locator('[name=option][value=baseline]').uncheck();
 await session.send('Profiler.enable');await session.send('Profiler.setSamplingInterval',{interval:1000});
 await page.locator('#start').click();
 for(const [id,label] of [['menu',' · Menu'],['orders',' · Ordres'],['stadium',' · 3D · 10 acteurs'],['cinematics',' · Animations plein écran']]){
  await page.waitForFunction(label=>document.getElementById('status').textContent.endsWith(label),label,{timeout:180000});
  await session.send('Profiler.start');
  if(values.trace)await session.send('Tracing.start',{categories:'toplevel,devtools.timeline,v8,blink,cc,gpu,disabled-by-default-gpu.service',transferMode:'ReturnAsStream'});
  const before=await system.send('SystemInfo.getProcessInfo'),start=performance.now();
  await new Promise(resolve=>setTimeout(resolve,5000));
  const after=await system.send('SystemInfo.getProcessInfo'),cpuWallSeconds=(performance.now()-start)/1000;
  const {profile}=await session.send('Profiler.stop');
  if(values.trace){
   const tracingComplete=new Promise(resolve=>session.once('Tracing.tracingComplete',resolve));await session.send('Tracing.end');
   const {stream}=await tracingComplete;let trace='';while(true){const chunk=await session.send('IO.read',{handle:stream});trace+=chunk.data;if(chunk.eof)break;}await session.send('IO.close',{handle:stream});
   await writeFile(path.join(output,`${id}.trace.json`),trace);
  }
  const cpu=after.processInfo.map(p=>{const previous=before.processInfo.find(x=>x.id===p.id);return {type:p.type,id:p.id,cpuSeconds:previous?p.cpuTime-previous.cpuTime:null};});
  const capture={id,software:values.software,headless:!values.headed,cpuWallSeconds,wallSeconds:(performance.now()-start)/1000,cpu,profile};captures.push(capture);
  await writeFile(path.join(output,`${id}.cpuprofile`),JSON.stringify(profile));
  console.log(JSON.stringify({id,wallSeconds:capture.wallSeconds,cpu}));
 }
 await page.waitForFunction(()=>!document.getElementById('start').disabled,{timeout:300000});
 const report=await page.evaluate(()=>JSON.parse(localStorage.getItem('boufbowl.browser-benchmark.v1')));
 await writeFile(path.join(output,'benchmark.json'),JSON.stringify(report,null,2));
 await writeFile(path.join(output,'profiles.json'),JSON.stringify(captures));
 console.log(JSON.stringify({done:true,runs:report.runs.length,failed:report.failedRuns,error:report.error}));
}finally{await browser.close();}
