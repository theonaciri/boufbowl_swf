import { fileURLToPath } from "node:url";

// Coordinate all downloadable platforms under one CPU budget.
const python = process.env.PYTHON || Bun.which("python3") || Bun.which("python");
if (!python) {
  console.error("Python 3 is required to prepare the game and media. Install python3, then rerun bun run build.");
  process.exit(1);
}
const child = Bun.spawn([python, "-m", "tools.build_players", ...Bun.argv.slice(2)], {
  cwd: fileURLToPath(new URL("..", import.meta.url)),
  env: { ...process.env, BUN: process.execPath },
  stdin: "inherit", stdout: "inherit", stderr: "inherit",
});
process.exit(await child.exited);
