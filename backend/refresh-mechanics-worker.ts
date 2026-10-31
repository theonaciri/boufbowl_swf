/** Refresh maintained ball/ability resolvers without the missing source archive.
 * Full builds consume the same files through build-worker.ts. Fail before writing
 * if the retained bundle layout changes. CPU overlays are refreshed separately.
 */
import {resolve} from "node:path";
import {guardContactThrows,rulebookOverlay,passRangeOverlay} from "./simulator/overlays";
const root = import.meta.dir, file = resolve(root, "build/engine.js");
const transpiler = new Bun.Transpiler({loader: "ts", target: "bun"});
let bundle = await Bun.file(file).text();
for (const [name, next] of [["combat", "throwTarget"], ["ball", "turnTick"], ["abilities", null]]) {
  const marker = `// ../../boufbowl_server/src/simulator/${name}.ts`;
  const nextMarker = next ? `// ../../boufbowl_server/src/simulator/${next}.ts` : "// ../../boufbowl_server/src/validator.ts";
  const start = bundle.indexOf(marker), end = bundle.indexOf(nextMarker, start);
  if (start < 0 || end < 0 || bundle.indexOf(marker, start + 1) >= 0)
    throw new Error(`Retained worker ${name} boundary changed`);
  const source = (await Bun.file(resolve(root, `simulator/${name}.ts`)).text())
    .replace(/^import[\s\S]*?from\s+["'][^"']+["'];\n/gm, "");
  const compiled = transpiler.transformSync(source).replace(/^export /gm, "");
  bundle = bundle.slice(0, start) + marker + "\n" + compiled + "\n" + bundle.slice(end);
}
const rulebookMarker = "// backend/simulator/rulebook.ts";
const movementMarker = "// backend/movement-risk.ts", rngMarker = "// ../../boufbowl_server/src/rng.ts";
const riskStart = bundle.indexOf(rulebookMarker) >= 0 ? bundle.indexOf(rulebookMarker) : bundle.indexOf(movementMarker);
const riskEnd = bundle.indexOf(rngMarker,riskStart);
if (riskStart < 0 || riskEnd < 0) throw new Error("Retained movement/rulebook boundary changed");
const strip = (source: string) => source.replace(/^import[\s\S]*?from\s+["'][^"']+["'];\n/gm, "");
const shared = transpiler.transformSync(strip(await Bun.file(resolve(root,"simulator/rulebook.ts")).text())).replace(/^export /gm, "");
const risk = transpiler.transformSync(strip(await Bun.file(resolve(root,"movement-risk.ts")).text())).replace(/^export /gm, "");
bundle = bundle.slice(0,riskStart)+rulebookMarker+"\n"+shared+"\n"+movementMarker+"\n"+risk+"\n"+bundle.slice(riskEnd);
bundle = guardContactThrows(bundle);
bundle = passRangeOverlay('rules',passRangeOverlay('turnTick',bundle));
bundle = rulebookOverlay("turnTick",rulebookOverlay("engine",bundle));
const anchor = 'result.simulation_version += "+movement-risk-1";';
if (!bundle.includes(anchor)) throw new Error("Retained worker version boundary changed");
const suffix = 'result.simulation_version += "+forum-semantics-2012-1";';
const versionStatement = `if (cfg.ball.interception_uses_fire_stat || cfg.ball.require_arrival_before_turn_end || cfg.ball.contact_cancels_pending_throw ||
        Object.values(cfg.abilities ?? {}).some(r => r.redirect_enemy_heal)) ${suffix}`;
if (bundle.includes(suffix)) {
  const end = bundle.indexOf(suffix) + suffix.length;
  const start = bundle.lastIndexOf("if (cfg.ball.interception_uses_fire_stat", end);
  if (start < 0) throw new Error("Recovered mechanics version guard changed");
  bundle = bundle.slice(0, start) + versionStatement + bundle.slice(end);
} else bundle = bundle.replace(anchor, anchor + "\n    " + versionStatement);
const bookVersion = 'if (cfg.rulebook) result.simulation_version += "+rulebook:" + cfg.rulebook.id;';
if (!bundle.includes(bookVersion)) bundle = bundle.replace(suffix,suffix+"\n    "+bookVersion);
const rangeVersion = 'if (cfg.ball.range_multiplier !== undefined || cfg.ball.attempt_out_of_range) result.simulation_version += "+pass-range-1";';
if (!bundle.includes(rangeVersion)) bundle = bundle.replace(bookVersion,bookVersion+"\n    "+rangeVersion);
// Syntax validation happens before touching the retained runtime artifact.
new Bun.Transpiler({loader: "js", target: "bun"}).transformSync(bundle);
await Bun.write(file, bundle);
console.log("Refreshed retained ball/ability mechanics from maintained sources");
