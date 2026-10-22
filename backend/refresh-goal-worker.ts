/** Refresh only goal detection in the retained worker when the archive is absent. */
import {resolve} from "node:path";
const root=import.meta.dir, file=resolve(root,"build/engine.js");
const source=await Bun.file(resolve(root,"simulator/ball.ts")).text();
const sourceMarker="export function resolveGoals(", bundleMarker="function resolveGoals(";
const sourceStart=source.indexOf(sourceMarker);
if (sourceStart<0 || source.indexOf(sourceMarker,sourceStart+1)>=0)
  throw new Error("Expected one goal resolver at the end of simulator/ball.ts");
const transpiler=new Bun.Transpiler({loader:"ts",target:"bun"});
const compiled=transpiler.transformSync(source.slice(sourceStart)).replace(/^export /,"").trim();
if (!compiled.startsWith(bundleMarker) || (compiled.match(/^function /gm) ?? []).length!==1)
  throw new Error("Expected only the final goal resolver in simulator/ball.ts");
let bundle=await Bun.file(file).text();
const start=bundle.indexOf(bundleMarker), end=bundle.indexOf("\n// ../../boufbowl_server/src/simulator/turnTick.ts",start);
if (start<0 || end<0 || bundle.indexOf(bundleMarker,start+1)>=0)
  throw new Error("Retained worker goal resolver boundary changed");
bundle=bundle.slice(0,start)+compiled+"\n"+bundle.slice(end);
const versionMarker='result.simulation_version += "+client-ball-2";';
if (!bundle.includes(versionMarker)) throw new Error("Retained worker version marker changed");
if (!bundle.includes('result.simulation_version += "+goal-zones-1";'))
  bundle=bundle.replace(versionMarker,versionMarker+'\n    result.simulation_version += "+goal-zones-1";');
await Bun.write(file,bundle);
console.log("Refreshed retained goal detection; other simulation rules preserved");
