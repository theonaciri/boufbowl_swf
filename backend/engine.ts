/** Stateless authoritative simulation worker; stdin/stdout contain JSON lines. */
import { simulateTurn } from "../../boufbowl_server/src/simulator/engine";
import { OpponentAI } from "../../boufbowl_server/src/ai";
import { defaultOrder } from "../../boufbowl_server/src/rules";
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
const base = JSON.parse(readFileSync(new URL("./engine_base.json", import.meta.url), "utf8"));
function merge(a: any, b: any): any {
  const out = structuredClone(a);
  for (const [key, value] of Object.entries(b)) out[key] = value && typeof value === "object" && !Array.isArray(value)
    ? merge(out[key] ?? {}, value) : structuredClone(value);
  return out;
}
if (process.env.BOUFBOWL_WORKER_HANDSHAKE === "1") process.stdout.write(JSON.stringify({ ready: true }) + "\n");
for await (const line of createInterface({ input: process.stdin })) {
  try {
    const request = JSON.parse(line);
    const cfg = merge(base, request.rules?.simulation ?? {});
    if (request.rules?.abilities) cfg.abilities = request.rules.abilities;
    cfg.pitch.width_half = Math.floor(cfg.pitch.width / 2);
    cfg.pitch.height_half = Math.floor(cfg.pitch.height / 2);
    const orders = request.orders.map((order: any, team: number) => order ??
      (request.cpu?.[team] ? new OpponentAI(cfg, request.ai ?? {}).buildOrder(`cpu-${team}`, request.turn, team, request.world)
        : defaultOrder(`player-${team}`, request.turn, team, request.world.entities.filter((entity: any) => entity.team_id === team))));
    const warnings: unknown[] = [];
    const result = simulateTurn(cfg, request.world, orders[0], orders[1], request.turn, request.seed,
      warning => warnings.push(warning));
    process.stdout.write(JSON.stringify({ ok: true, result, orders, warnings }) + "\n");
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(error) }) + "\n");
  }
}
