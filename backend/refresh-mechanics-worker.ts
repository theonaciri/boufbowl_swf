/** Refresh maintained ball/ability resolvers without the missing source archive.
 * Full builds consume the same files through build-worker.ts. Fail before writing
 * if the retained bundle layout changes. CPU overlays are refreshed separately.
 */
import {resolve} from "node:path";
import {guardContactThrows} from "./simulator/overlays";
const root = import.meta.dir, file = resolve(root, "build/engine.js");
const transpiler = new Bun.Transpiler({loader: "ts", target: "bun"});
let bundle = await Bun.file(file).text();
for (const [name, next] of [["ball", "turnTick"], ["abilities", null]]) {
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
bundle = guardContactThrows(bundle);
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
// Syntax validation happens before touching the retained runtime artifact.
new Bun.Transpiler({loader: "js", target: "bun"}).transformSync(bundle);
await Bun.write(file, bundle);
console.log("Refreshed retained ball/ability mechanics from maintained sources");
