/** Build the original simulator with our isolated ball-rule replacement. */
import { readFileSync, copyFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
const root = dirname(import.meta.path);
const result = await Bun.build({
  entrypoints: [resolve(root, "engine.ts")], target: "bun", outdir: resolve(root, "build"),
  plugins: [{ name: "client-ball-rules", setup(build) {
    build.onLoad({ filter: /[/\\]simulator[/\\]ball\.ts$/ }, args => ({
      contents: readFileSync(resolve(root, "simulator/ball.ts"), "utf8"),
      loader: "ts", resolveDir: dirname(args.path),
    }));
  }}],
});
if (!result.success) { console.error(result.logs); process.exit(1); }
copyFileSync(resolve(root, "engine_base.json"), resolve(root, "build/engine_base.json"));
