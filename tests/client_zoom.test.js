import {test, expect} from 'bun:test';
import {readFileSync} from 'node:fs';

// Execute the production AS3 arithmetic, removing only AS3 type annotations.
// This avoids a separate JS/Python model that can drift from the shipped code.
const runtime = readFileSync(new URL('../patches/ClientRuntime.as.inc', import.meta.url), 'utf8');
const method = runtime.match(/public static function wheelZoomTransform\([\s\S]*?\n      }/)[0];
const zoom = new Function(`return (${method.replace('public static function', 'function').replace(/:\s*(Number|Object)\b/g, '')});`)();
const width = 1920, height = 1125;
const step = (view, ax, ay, delta) => zoom(view.scale, view.x, view.y, ax, ay, delta, width, height);
const original = {scale: 1, x: 0, y: 0};
const covered = view => {
  expect(view.scale).toBeGreaterThanOrEqual(1);
  expect(view.scale).toBeLessThanOrEqual(8);
  expect(view.x).toBeLessThanOrEqual(0);
  expect(view.y).toBeLessThanOrEqual(0);
  expect(view.x + width * view.scale).toBeGreaterThanOrEqual(width - 1e-9);
  expect(view.y + height * view.scale).toBeGreaterThanOrEqual(height - 1e-9);
};

test('wheel zoom fixes the content under center, corner and off-center cursors', () => {
  for (const [ax, ay] of [[0,0],[width,height],[width/2,height/2],[321,876]]) {
    const next = step(original, ax, ay, 3);
    expect(next.scale).toBeCloseTo(1.12, 12);
    expect((ax-next.x)/next.scale).toBeCloseTo(ax, 10);
    expect((ay-next.y)/next.scale).toBeCloseTo(ay, 10);
    covered(next);
  }
});

test('inverse wheel motion preserves an interior anchor until the exact reset', () => {
  let view = original;
  for (let n=0;n<7;n++) view=step(view, 400, 700, 3);
  for (let n=0;n<6;n++) view=step(view, 400, 700, -3);
  expect(view.scale).toBeCloseTo(1.12, 12);
  expect((400-view.x)/view.scale).toBeCloseTo(400, 10);
  // Matching steps must reset exactly despite floating-point roundoff.
  view=step(view, 400, 700, -3);
  expect(view).toEqual(original);
  expect(step(view, width, 0, -30)).toEqual(original);
});

test('zooming out at another edge clamps panning and resets both axes', () => {
  let view=original;
  for(let n=0;n<30;n++) view=step(view,width,height,3);
  expect(view.scale).toBe(8);
  expect(step(view,width,height,30)).toEqual(view);
  view=step(view,0,0,-3);
  expect(view.x).toBeCloseTo(width*(1-view.scale),10);
  expect(view.y).toBeCloseTo(height*(1-view.scale),10);
  covered(view);
  for(let n=0;n<30;n++) view=step(view,0,height,-3);
  expect(view).toEqual(original);
});

test('fractional, zero and extreme deltas remain bounded through seeded cursor changes', () => {
  expect(step(original,500,500,0)).toEqual(original);
  expect(step(original,500,500,0.25).scale).toBeGreaterThan(1);
  let seed=0x12345678, view=original;
  const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/2**32;};
  for(let n=0;n<2000;n++) {
    view=step(view,random()*width,random()*height,(random()-0.5)*200);
    covered(view);
    if(view.scale===1) expect(view).toEqual(original);
  }
  for(let n=0;n<5;n++) view=step(view,random()*width,random()*height,-3000);
  expect(view).toEqual(original);
});

test('the preserved 1024x600 viewport clamps correctly at changed cursor positions', () => {
  let view={scale:8,x:-1024*7,y:-600*7};
  view=zoom(view.scale,view.x,view.y,0,0,-3,1024,600);
  expect(view.x).toBeCloseTo(1024*(1-view.scale),10);
  expect(view.y).toBeCloseTo(600*(1-view.scale),10);
  for(let n=0;n<30;n++)view=zoom(view.scale,view.x,view.y,1024,600,-3,1024,600);
  expect(view).toEqual(original);
});
