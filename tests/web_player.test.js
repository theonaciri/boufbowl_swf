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

import {renderingExperiments} from '../web-player.js';
test('rendering experiments are off by default and reject unknown URL values',()=>{
 const defaults={renderer:'auto',detail:'original',cache:false,perspective:'subdivide',diagnostics:false};
 expect(renderingExperiments(new URLSearchParams())).toEqual(defaults);
 expect(renderingExperiments(new URLSearchParams('renderBackend=canvas&triangleDetail=NaN&geometryCache=true&perspective=wrong&renderDiagnostics=yes'))).toEqual(defaults);
});
test('experiments can be enabled independently and combined',()=>{
 for (const renderer of ['webgpu','wgpu-webgl','webgl'])
  expect(renderingExperiments(new URLSearchParams({renderBackend:renderer})).renderer).toBe(renderer);
 for (const detail of ['quality','low','medium','high'])
  expect(renderingExperiments(new URLSearchParams({triangleDetail:detail})).detail).toBe(detail);
 expect(renderingExperiments(new URLSearchParams('geometryCache=1&perspective=native&renderDiagnostics=1')))
  .toEqual({renderer:'auto',detail:'original',cache:true,perspective:'native',diagnostics:true});
});
