/** Build the archived simulator with isolated local gameplay overrides. */
import { readFileSync, copyFileSync, existsSync } from "node:fs";
import { dirname, resolve, basename } from "node:path";
import { overlay } from "./simulator/overlays";
const root = dirname(import.meta.path);
const archive = ["../../boufbowl_server/src", "../../../boufbowl_server/src"]
  .map(path => resolve(root, path)).find(path => existsSync(resolve(path, "simulator/engine.ts")));
if (!archive) throw new Error("Cannot find archived boufbowl_server/src simulator sources");
const result = await Bun.build({
  entrypoints: [resolve(root, "engine.ts")], target: "bun", outdir: resolve(root, "build"),
  plugins: [{ name: "client-ball-rules", setup(build) {
    build.onResolve({filter:/boufbowl_server\/src\//}, args => ({
      path: resolve(archive, args.path.split("boufbowl_server/src/")[1] + ".ts"),
    }));
    build.onResolve({filter:/^boufbowl-movement-risk$/}, () => ({path:resolve(root,"movement-risk.ts")}));
    build.onResolve({filter:/^boufbowl-rulebook$/}, () => ({path:resolve(root,"simulator/rulebook.ts")}));
    build.onLoad({ filter: /[/\\]simulator[/\\](ball|abilities|engine|movement|combat|turnTick)\.ts$|[/\\](validator|rules)\.ts$/ }, args => ({
      contents: ["ball", "abilities", "combat"].includes(basename(args.path, ".ts"))
        ? readFileSync(resolve(root, "simulator", basename(args.path)), "utf8")
        : overlay(basename(args.path, ".ts"), readFileSync(args.path, "utf8")),
      loader: "ts", resolveDir: dirname(args.path),
    }));
  }}],
});
if (!result.success) { console.error(result.logs); process.exit(1); }
copyFileSync(resolve(root, "engine_base.json"), resolve(root, "build/engine_base.json"));
