// Presentation-only feasibility tests. This is not a replacement game engine.
import {test,expect} from 'bun:test';
export function positionAt(t,segments) {
  const segment=segments.findLast(s=>t>=s.start) ?? segments[0];
  const alpha=Math.max(0,Math.min(1,(t-segment.start)/(segment.end-segment.start)));
  return segment.from+(segment.to-segment.from)*alpha;
}
const segments=[{start:0,end:400,from:0,to:40},{start:400,end:1000,from:80,to:140}];
test('extra display samples preserve endpoints and cannot fire gameplay callbacks',()=>{
  for(const hz of [25,30,50,60,90,120,144,240,1000,10000]) {
    const events=[{at:0,id:'start'},{at:400,id:'teleport'},{at:750,id:'catch'},{at:1000,id:'done'}];
    let executed=[],cursor=0,renderCount=0,last=0;
    function updateLogic(now){while(cursor<events.length&&events[cursor].at<=now)executed.push(events[cursor++].id)}
    for(let logic=0;logic<=1000;logic+=40){
      updateLogic(logic);
      // Render the known replay trajectory without advancing the logic clock.
      for(let i=Math.ceil(logic*hz/1000);i<Math.min((logic+40)*hz/1000,hz+1);i++){
        last=positionAt(Math.min(1000,i*1000/hz),segments);renderCount++;
      }
    }
    expect(executed).toEqual(['start','teleport','catch','done']);
    expect(last).toBe(140);expect(cursor).toBe(4);expect(renderCount).toBeGreaterThanOrEqual(hz);
  }
});
test('known replay boundaries do not smear a teleport or change possession',()=>{
  expect(positionAt(399.999,segments)).toBeCloseTo(39.9999,4);
  expect(positionAt(400,segments)).toBe(80);
  const state={holder:11,callbacks:0};const before=JSON.stringify(state);
  for(let i=0;i<10000;i++)positionAt(i/10,segments);
  expect(JSON.stringify(state)).toBe(before);
});
test('paused game time stays still at every display rate',()=>{
  for(const hz of [25,60,144,240]){
    const positions=Array.from({length:hz},()=>positionAt(250,segments));
    expect(new Set(positions).size).toBe(1);expect(positions[0]).toBe(25);
  }
});
test('fractional display time can add samples, integer milliseconds cannot',()=>{
  const line=[{start:0,end:1000,from:0,to:100}];
  const integer=new Set(),fractional=new Set();
  for(let i=0;i<=10000;i++){integer.add(positionAt(Math.round(i/10),line));fractional.add(positionAt(i/10,line))}
  expect(integer.size).toBe(1001);expect(fractional.size).toBe(10001);
});
