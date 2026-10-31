import {test,expect} from 'bun:test';
import {summarize,aggregate,caseOrder} from './statistics.js';
test('frame percentiles use nearest ranks; FPS is elapsed-time weighted',()=>{
 expect(summarize([])).toBeNull();const s=summarize([10,10,10,70]);
 expect(s.fps).toBe(40);expect(s.medianMs).toBe(10);expect(s.p95Ms).toBe(70);expect(s.over50).toBe(1);
 expect(summarize(Array.from({length:100},(_,i)=>i+1)).p95Ms).toBe(95);
});
test('aggregation pools raw frames, not per-run average FPS',()=>{
 const option={id:'a'};const s=aggregate([{option,phases:[{id:'orders',samples:[10],raf:[16]}]}, {option,phases:[{id:'orders',samples:[100,100,100],raf:[32]}]}])[0];
 expect(s.game.meanMs).toBe(77.5);expect(s.runs).toBe(2);expect(s.display.meanMs).toBe(24);
});
test('alternate rounds reverse cases without mutating selected options',()=>{
 const options=['a','b','c'];expect(caseOrder(options,3)).toEqual(['a','b','c','c','b','a','a','b','c']);expect(options).toEqual(['a','b','c']);
});
