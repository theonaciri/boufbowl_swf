import { cpuCount, cpuJob } from './cpu-budget.mjs';
import { chromium } from 'playwright';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
const jobs=Math.min(Number(process.argv[3] || cpuCount()),cpuCount());
const server=await chromium.launchServer({headless:true,args:['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding','--num-raster-threads=1']});
const browser=await chromium.connect(server.wsEndpoint());
let peakRSS=0;
function sampleMemory(){
  try {
    const processes=readdirSync('/proc').filter(n=>/^\d+$/.test(n)).flatMap(id=>{
      try {const stat=readFileSync(`/proc/${id}/stat`,'utf8').split(') ')[1].split(' ');
        const rss=Number(readFileSync(`/proc/${id}/status`,'utf8').match(/VmRSS:\s+(\d+)/)?.[1] || 0);
        return [{id:Number(id),parent:Number(stat[1]),rss}];}catch{return [];}
    });
    const owned=new Set([server.process().pid]);let changed=true;
    while(changed){changed=false;for(const p of processes)if(owned.has(p.parent)&&!owned.has(p.id)){owned.add(p.id);changed=true;}}
    peakRSS=Math.max(peakRSS,processes.filter(p=>owned.has(p.id)).reduce((n,p)=>n+p.rss,0)/1024);
  }catch{}
}
const timer=setInterval(sampleMemory,1000);
const started=performance.now();
try {
  const results=await Promise.all(Array.from({length:jobs},()=>cpuJob(async()=>{
    const page=await browser.newPage({viewport:{width:2048,height:1200},deviceScaleFactor:1});
    await page.goto(process.argv[2]);
    await page.waitForFunction(()=>window.result!==undefined,null,{timeout:7200000});
    const result=await page.evaluate(()=>window.result);
    if(result.errors.length)throw Error(JSON.stringify(result.errors));
    await page.close();
    return result;
  })));
  sampleMemory();
  const report={jobs,portraits:results.reduce((n,r)=>n+r.done,0),seconds:(performance.now()-started)/1000,peak_browser_rss_mib:Math.round(peakRSS),workers:results};
  writeFileSync(process.argv[4],JSON.stringify(report));
  console.log(`Rendered ${report.portraits} portraits with ${jobs} workers in ${report.seconds.toFixed(2)}s; peak browser RSS ${report.peak_browser_rss_mib} MiB`);
}finally{clearInterval(timer);await browser.close();await server.close();}
