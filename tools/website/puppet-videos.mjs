import { chromium } from 'playwright';
import { readFileSync, mkdirSync, writeFileSync, readdirSync, unlinkSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
const directory=process.argv[3];
const tasks=JSON.parse(readFileSync(join(directory,'tasks.json'),'utf8'));
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding']});
try {
 const page=await browser.newPage({viewport:{width:1024,height:700}});
 page.on('console',m=>{if(m.type()==='error')console.error(m.text())});
 await page.goto(process.argv[2]);
 await page.evaluate(async()=>{
   const p=window.RufflePlayer.newest().createPlayer();p.style.cssText='width:1024px;height:700px';
   document.querySelector('#mount').append(p);window.puppetPlayer=p;
   await p.load({url:'/bin/site-puppets.swf',autoplay:'on',allowScriptAccess:true,unmuteOverlay:'hidden',parameters:{lang:'fr',server:'0',mock:'0',tuto:'0'}});
 });
 const results=[];
 for(const task of tasks){
   await page.evaluate(()=>window.puppetPlayer.ruffle().resume());
   await page.waitForFunction(task=>{
     try {
       const result=window.puppetPlayer.ruffle().callExternalInterface('puppetCreate',task.cls,task.gender,task.animation,
           parseInt(task.colors.hair,16),parseInt(task.colors.skin,16),parseInt(task.colors.eyes,16));
       if(String(result).startsWith('ERROR:'))throw Error(result);
       return result==='READY';
     }catch(e){if(String(e).includes('ERROR:'))throw e;return false;}
   }, task, {timeout:90000,polling:100});
   await page.waitForFunction(animation=>{
     const status=String(window.puppetPlayer.ruffle().callExternalInterface('puppetStatus'));
     return status.includes(animation+'_') && Number(status.split('|')[2])>1;
   },task.animation,{timeout:60000,polling:100});
   // Let the requested skin libraries and their frame scripts finish initializing.
   await page.waitForTimeout(1000);
   const status=await page.evaluate(()=>window.puppetPlayer.ruffle().callExternalInterface('puppetStatus'));
   const frames=Number(status.split('|')[2]);
   if(!Number.isInteger(frames)||frames<2||frames>600)throw Error('Invalid native frame count');
   async function selectFrame(frame){
     await page.evaluate(frame=>window.puppetPlayer.ruffle().callExternalInterface('puppetFrame',frame),frame);
     // Ruffle commits newly placed skin pieces during its next render ticks.
     await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))));
   }
   let bounds;
   for(let index=0;index<frames;index++){
     await selectFrame(index+1);
     bounds=await page.evaluate(reset=>window.puppetPlayer.ruffle().callExternalInterface('puppetMeasure',reset),index===0);
   }
   const state={status,bounds};
   console.log(task.character,task.animation,JSON.stringify(state));
   const path=join(directory,task.id);mkdirSync(path,{recursive:true});
   for(const name of readdirSync(path))if(/^\d{4}\.png$/.test(name))unlinkSync(join(path,name));
   for(let index=0;index<frames;index++){
     await selectFrame(index+1);
     const png=await page.evaluate(()=>window.puppetPlayer.ruffle().callExternalInterface('puppetPNG'));
     if(!png||png.startsWith('ERROR:'))throw Error(png);
     writeFileSync(join(path,String(index).padStart(4,'0')+'.png'),Buffer.from(png,'base64'));
   }
   const images=Object.fromEntries(readdirSync(path).filter(name=>/^\d{4}\.png$/.test(name)).sort().map(name=>[name,createHash('sha256').update(readFileSync(join(path,name))).digest('hex')]));
   const captured={...task,frames,...state,images};
   writeFileSync(join(path,'capture.json'),JSON.stringify(captured,null,2));
   results.push(captured);
   writeFileSync(join(directory,'frames.json'),JSON.stringify(results,null,2));
   console.log('Captured',task.id,frames,'native frames');
 }
}finally{await browser.close();}
