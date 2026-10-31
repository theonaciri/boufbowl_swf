import {test,expect} from 'bun:test';
import {readFile,mkdtemp,mkdir,copyFile,writeFile,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {chromium} from 'playwright';
import {ruleCalculator} from '../../rules-calculator-model.js';
import {rulesPage} from './rules.mjs';
const root=path.resolve(import.meta.dir,'../..');
const config=JSON.parse(await readFile(path.join(root,'resources/game_config.json'),'utf8'));
const model=ruleCalculator(config.rules);

test('calculators preserve server probability limits, eligibility and configured range',()=>{
  for(const [orders,failure] of [[1,35],[2,20],[3,5]])expect(model.throwFailure(10,orders,10)).toBeCloseTo(failure);
  expect(model.throwFailure(10,3,13)).toBeCloseTo(11);
  expect(model.throwFailure(10,3,13.01)).toBe(100);
  expect(model.throwFailure(30,0,0)).toBe(100);
  expect(model.catchFailure(10,1)).toBeCloseTo(25);
  expect(model.catchFailure(10,3)).toBeCloseTo(5);
  expect(model.catchFailure(30,3)).toBeCloseTo(1);
  expect(model.catchFailure(0,0,true)).toBe(100);
  expect(model.pickupFailure(10,2,1,2,0)).toBeCloseTo(15);
  expect(model.pickupFailure(10,2,1,3,1)).toBeCloseTo(25);
  expect(model.pickupFailure(30,0,0,0,0)).toBe(100);
  const movement=model.movement(10,[0,0,0,3],0);
  expect(movement.failure).toBe(0);
  expect(model.movement(10,[0,0,0,3],movement.safe).failure).toBeCloseTo(100*.01/1.8);
  expect(model.movement(10,[0,0,0,3],movement.maximum+.01).failure).toBeNull();
  expect(model.stun(10)).toBe(1);expect(model.stun(30)).toBe(.1);
  expect(model.combat(0)).toBe(50);expect(model.combat(6)).toBeCloseTo(85);
});

test('page generation embeds changed configuration and formulas without a game build',async()=>{
 const directory=await mkdtemp(path.join(os.tmpdir(),'boufbowl-rules-'));
 try{
  for(const name of ['regles.html','resources/rulebook.json','assets/site/restoration/inventory.json']){
   await mkdir(path.dirname(path.join(directory,name)),{recursive:true});await copyFile(path.join(root,name),path.join(directory,name));
  }
  const changed=structuredClone(config);changed.rules.simulation.ball.range_multiplier=1.6;changed.rules.simulation.simulation.distance_penalty=.04;
  await writeFile(path.join(directory,'resources/game_config.json'),JSON.stringify(changed));
  const html=await rulesPage(directory);
  const embedded=JSON.parse(html.match(/id="rules-calculator-config">([^<]+)<\/script>/)[1]);
  expect(embedded.simulation.ball.range_multiplier).toBe(1.6);
  expect(ruleCalculator(embedded).range(3)).toBe(16);
  expect(html).toContain('× 1,6');expect(html).toContain('− 4 × distance');
  expect((html.match(/data-calculator=/g)||[]).length).toBe(6);
 }finally{await rm(directory,{recursive:true,force:true});}
});

test('mobile controls update charts, limit orders, reset and keep formulas collapsed',async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:360,height:800}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const html=(await rulesPage(root)).replace(/<link\b[^>]*>/g,'').replace(/<script\b[^>]*src=[^>]+><\/script>/g,'');
  await page.setContent(html);
  await page.addStyleTag({path:path.join(root,'home.css')});await page.addStyleTag({path:path.join(root,'rules.css')});
  const bundle=await Bun.build({entrypoints:[path.join(root,'rules-calculators.js')],target:'browser',format:'iife'});
  expect(bundle.success).toBe(true);await page.addScriptTag({content:await bundle.outputs[0].text()});
  expect(await page.locator('details[data-calculator][open]').count()).toBe(0);
  for(const id of ['pass','catch','pickup','movement','stun','combat']){
   const panel=page.locator(`[data-calculator="${id}"]`);await panel.locator('summary').click();
   await panel.locator('svg path').first().waitFor({state:'attached'});expect(await panel.locator('svg path').count()).toBeGreaterThan(0);
   expect(await panel.locator('.rule-readout').innerText()).not.toBe('');
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
  const pass=page.locator('[data-calculator="pass"]');const before=await pass.locator('.rule-readout').innerText();
  await pass.locator('[data-setting="stat"]').evaluate(el=>{el.value='30';el.dispatchEvent(new Event('input',{bubbles:true}));});
  expect(await pass.locator('.rule-readout').innerText()).not.toBe(before);
  await pass.locator('.rule-reset').click();expect(await pass.locator('.rule-readout').innerText()).toBe(before);
  const pickup=page.locator('[data-calculator="pickup"]');await pickup.locator('[data-setting="fire"]').evaluate(el=>{el.value='3';el.dispatchEvent(new Event('input',{bubbles:true}));});
  expect(await pickup.locator('[data-setting="air"]').inputValue()).toBe('0');
  expect(errors).toEqual([]);
 }finally{await browser.close();}
});
