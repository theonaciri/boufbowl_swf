export function summarize(samples) {
  if (!samples.length) return null;
  const ordered = [...samples].sort((a,b)=>a-b), n = ordered.length;
  const percentile = p => ordered[Math.max(0, Math.ceil(n*p)-1)];
  const total = samples.reduce((a,b)=>a+b,0), mean = total/n;
  return {frames:n,elapsedMs:total,meanMs:mean,fps:1000/mean,medianMs:percentile(.5),
    p95Ms:percentile(.95),p99Ms:percentile(.99),maxMs:ordered[n-1],
    over50:samples.filter(x=>x>50).length,over100:samples.filter(x=>x>100).length,
    low1Fps:1000/(ordered.slice(-Math.max(1,Math.ceil(n*.01))).reduce((a,b)=>a+b,0)/Math.max(1,Math.ceil(n*.01)))};
}
export function aggregate(runs) {
  const groups = new Map();
  for (const run of runs) {
   const seen = new Set();
   for (const phase of run.phases) {
    const key=run.option.id+':'+phase.id;
    if(!groups.has(key)) groups.set(key,{option:run.option,phase:phase.id,samples:[],raf:[],runs:0,renderers:[]});
    const group=groups.get(key);const renderer=run.actualRenderer||'non identifié';if(!group.renderers.includes(renderer))group.renderers.push(renderer);group.samples.push(...phase.samples);group.raf.push(...phase.raf);if(!seen.has(key)){group.runs++;seen.add(key);}
  }
  }
  return [...groups.values()].map(({samples,raf,...group})=>({...group,game:summarize(samples),display:summarize(raf)}));
}
export function caseOrder(options, rounds) {
  return Array.from({length:rounds},(_,n)=>(n%2 ? [...options].reverse() : options)).flat();
}
export const OPTIONS = [
  {id:'baseline',label:'Référence sans cache global',client:'/benchmark-reference.swf'},
  {id:'grid-layer',label:'Rendu actuel · grille en un calque'},
];
