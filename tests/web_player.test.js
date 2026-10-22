import {test, expect} from 'bun:test';
import {displayPreset, WEB_PRESETS} from '../web-player.js';
test('presets stay within a useful animation cadence and use supported stage qualities',()=>{
 for(const name of Object.keys(WEB_PRESETS)) {
  const p=displayPreset(name);
  expect(p.fps).toBeGreaterThanOrEqual(25);expect(p.fps).toBeLessThanOrEqual(60);
  expect(['low','medium','high']).toContain(p.quality);
 }
});
test('missing and inherited names safely select the balanced preset',()=>{
 for(const name of [undefined,null,'','invalid','__proto__','constructor','toString'])expect(displayPreset(name)).toEqual({fps:30,quality:'medium'});
});
