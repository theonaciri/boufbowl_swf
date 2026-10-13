/** One isolated movement turn from the sibling authoritative simulator.
 * This probe does not start its network server or open its databases.
 */
import { loadGameConfig, validateConfig } from "../../boufbowl_server/src/config";
import { simulateTurn } from "../../boufbowl_server/src/simulator/engine";
import type { Entity, Order, WorldState } from "../../boufbowl_server/src/types";
import { readFileSync } from "node:fs";

const local = JSON.parse(readFileSync(new URL("../resources/game_config.json", import.meta.url), "utf8"));
const cfg = loadGameConfig();
// This compatibility probe deliberately uses the replacement engine's own stat
// semantics. Only fields already supported by that engine are overlaid.
for (const [section, values] of Object.entries(local.rules.simulation)) {
  (cfg as any)[section] = { ...(cfg as any)[section], ...(values as object) };
}
validateConfig(cfg);
const entities: Entity[] = [];
for (const team of [0, 1]) {
  for (let index = 1; index <= 5; index++) {
    entities.push({ id: (team + 1) * 10 + index, team_id: team,
      position: { q: team === 0 ? -5 : 5, r: index - 3 }, orientation: 0,
      stats: { strength: 10, agility: 10, endurance: 10, precision: 10 },
      hp: local.rules.classes.defaults.health, max_hp: local.rules.classes.defaults.health,
      class_name: "Iop", ability_uses_remaining: local.rules.match.class_ability_uses,
      elements: { TERRE: 0, FEU: 0, AIR: 0, EAU: 0 },
      status: { stunned: false, knocked_down: false, carrying_ball: false } });
  }
}
const initial: WorldState = { entities, ball: { position: { q: 0, r: 0 }, holder_entity_id: null, in_flight: false }, tick: 0 };
const orders: Order[] = [0, 1].map(team => ({ player_id: `flash-probe-${team}`, turn_number: 1,
  nonce: `flash-probe-${team}-1`, team_index: team,
  actions: entities.filter(e => e.team_id === team).map(e => ({ entity_id: e.id, action_type: "move",
    params: { target_position: { q: e.position.q + (team === 0 ? 2 : -2), r: e.position.r },
      elements: { TERRE: 0, FEU: 0, AIR: 0, EAU: 3 } } })) }));
const warnings: unknown[] = [];
const result = simulateTurn(cfg, initial, orders[0], orders[1], 1, 12345, warning => warnings.push(warning));
if (warnings.length) throw new Error(`Probe order warnings: ${JSON.stringify(warnings)}`);
process.stdout.write(JSON.stringify({ format_version: 1, rules_version: local.rules_version,
  stat_semantics: "replacement-engine-provisional", initial, orders, result }, null, 2) + "\n");
