/** Refresh local CPU overlays in the retained worker without the absent archive.
 * This does not rebuild or modify any authoritative simulation rules.
 */
import {resolve} from "node:path";
const root=import.meta.dir, file=resolve(root,"build/engine.js");
let bundle=await Bun.file(file).text();
const transpiler=new Bun.Transpiler({loader:"ts",target:"bun"});
for (const [name,next] of [["cpu-orders","cpu-powers"],["cpu-powers","engine"]]) {
  const start=bundle.indexOf(`// backend/${name}.ts`),end=bundle.indexOf(`// backend/${next}.ts`,start);
  if (start<0 || end<0) throw new Error(`Missing retained worker section: ${name}`);
  const source=(await Bun.file(resolve(root,`${name}.ts`)).text()).replace(/^import .*?;\n/gm,"");
  const compiled=transpiler.transformSync(source).replace(/^export /gm,"");
  bundle=bundle.slice(0,start)+`// backend/${name}.ts\n${compiled}\n`+bundle.slice(end);
}
bundle=bundle.replace("prepareCPUOrder(cfg, request.world, orders[team])", "prepareCPUOrder(cfg, request.world, orders[team], request.ai ?? {})");
await Bun.write(file,bundle);
console.log("Refreshed retained CPU planner and power selection");
