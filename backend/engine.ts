/** Stateless authoritative simulation worker; stdin/stdout contain JSON lines. */
import { simulateTurn } from "../../boufbowl_server/src/simulator/engine";
import { OpponentAI } from "../../boufbowl_server/src/ai";
import { defaultOrder } from "../../boufbowl_server/src/rules";
import { addCPUPower } from "./cpu-powers";
import { cpuPlanningConfig, prepareCPUOrder } from "./cpu-orders";
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
    if (request.rules?.client_ranges) cfg.client_ranges = request.rules.client_ranges;
    if (request.rules?.abilities) cfg.abilities = request.rules.abilities;
    cfg.pitch.width_half = Math.floor(cfg.pitch.width / 2);
    cfg.pitch.height_half = Math.floor(cfg.pitch.height / 2);
    const orders = request.orders.map((order: any, team: number) => order ??
      (request.cpu?.[team] ? new OpponentAI(cpuPlanningConfig(cfg), request.ai ?? {}).buildOrder(`cpu-${team}`, request.turn, team, request.world)
        : defaultOrder(`player-${team}`, request.turn, team, request.world.entities.filter((entity: any) => entity.team_id === team))));
    // Replace generated CPU actions only; recorded/submitted orders remain immutable.
    for (let team = 0; team < orders.length; team++) {
      if (request.cpu?.[team] && request.orders[team] == null) {
        orders[team] = prepareCPUOrder(cfg,request.world,orders[team],request.ai ?? {});
        orders[team] = addCPUPower(cfg,request.world,orders[team],request.ai?.level ?? cfg.ai?.default_level ?? "normal");
      }
    }
    const warnings: unknown[] = [];
    const result = simulateTurn(cfg, request.world, orders[0], orders[1], request.turn, request.seed,
      warning => warnings.push(warning.code === "RECEPTION_REQUIRES_FEU"
        ? { ...warning, code: "RECEPTION_REQUIRES_AIR" } : warning));
    result.simulation_version += "+client-ball-2";
    result.simulation_version += "+goal-zones-1";
    if (cfg.ball.action_limited_attempts) result.simulation_version += "+ball-attempts-1";
    if (Object.values(cfg.abilities ?? {}).some((r: any) => r.target)) result.simulation_version += "+class-powers-1";
    if (cfg.movement.overextension?.enabled) result.simulation_version += "+movement-risk-1";
    if (cfg.ball.interception_uses_fire_stat || cfg.ball.require_arrival_before_turn_end || cfg.ball.contact_cancels_pending_throw ||
        Object.values(cfg.abilities ?? {}).some((r: any) => r.redirect_enemy_heal)) result.simulation_version += "+forum-semantics-2012-1";
    if (cfg.rulebook) result.simulation_version += "+rulebook:" + cfg.rulebook.id;
    if (cfg.ball.range_multiplier !== undefined || cfg.ball.attempt_out_of_range) result.simulation_version += "+pass-range-1";
    process.stdout.write(JSON.stringify({ ok: true, result, orders, warnings }) + "\n");
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(error) }) + "\n");
  }
}
