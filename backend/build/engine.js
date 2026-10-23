// @bun
// ../../boufbowl_server/src/hex.ts
var HEX_DIRECTIONS = [
  { q: 1, r: 0 },
  { q: 1, r: -1 },
  { q: 0, r: -1 },
  { q: -1, r: 0 },
  { q: -1, r: 1 },
  { q: 0, r: 1 }
];
function hexEqual(a, b) {
  return a.q === b.q && a.r === b.r;
}
function axialToCube(h) {
  return { x: h.q, y: -h.q - h.r, z: h.r };
}
function hexDistance(a, b) {
  const ac = axialToCube(a);
  const bc = axialToCube(b);
  return (Math.abs(ac.x - bc.x) + Math.abs(ac.y - bc.y) + Math.abs(ac.z - bc.z)) / 2;
}
function hexNeighbors(h) {
  return HEX_DIRECTIONS.map((d) => ({ q: h.q + d.q, r: h.r + d.r }));
}
function pitchBounds(pitch) {
  const width = pitch.width ?? 2 * pitch.width_half + 1;
  const height = pitch.height ?? 2 * pitch.height_half + 1;
  const minColumn = -Math.floor(width / 2), minRow = -Math.floor(height / 2);
  return { width, height, minColumn, maxColumn: minColumn + width - 1, minRow, maxRow: minRow + height - 1 };
}
function isInBounds(h, pitch, heightHalf) {
  const bounds = pitchBounds(typeof pitch === "number" ? { width_half: pitch, height_half: heightHalf } : pitch);
  const column = h.q + Math.floor(h.r / 2);
  return h.r >= bounds.minRow && h.r <= bounds.maxRow && column >= bounds.minColumn && column <= bounds.maxColumn;
}
function hexRound(h) {
  let q = Math.round(h.q);
  let r = Math.round(h.r);
  const s = Math.round(-h.q - h.r);
  const qDiff = Math.abs(q - h.q);
  const rDiff = Math.abs(r - h.r);
  const sDiff = Math.abs(s - (-h.q - h.r));
  if (qDiff > rDiff && qDiff > sDiff)
    q = -r - s;
  else if (rDiff > sDiff)
    r = -q - s;
  return { q, r };
}

// ../../boufbowl_server/src/coordinates.ts
var SIMULATION_SCALE = 1e4;

// backend/movement-risk.ts
function referenceDistance(cfg, elements) {
  const r = cfg.client_ranges;
  return elements.TERRE * r.earth_distance_bonus + elements.FEU * r.fire_distance_bonus + elements.AIR * r.air_distance_bonus + elements.EAU * r.water_distance_bonus;
}
function resolveMovementRisk(context, tick) {
  const { cfg, state, movements, rng, events } = context;
  const risk = cfg.movement.overextension;
  if (!risk?.enabled || !cfg.client_ranges)
    return;
  context.rangeRisk ??= new Map;
  for (const [id, m] of movements) {
    const e = state.entities.find((actor) => actor.id === id);
    if (!e || e.hp <= 0 || e.status.knocked_down || e.status.stunned)
      continue;
    let test = context.rangeRisk.get(id);
    if (!test) {
      const action = context.actions.find((a) => a.entity_id === id && ["move", "follow"].includes(a.action_type));
      const safe = Math.max(0, referenceDistance(cfg, action.params.elements ?? e.elements) + (e.range_bonus ?? 0));
      test = {
        safe,
        max: Math.max(safe, referenceDistance(cfg, action.params.elements ?? e.elements) * cfg.client_ranges.max_distance_factor + (e.range_bonus ?? 0)),
        origin: m.risk_origin,
        probability: 0,
        success: true,
        score: e.stats.endurance,
        distance: 0
      };
      context.rangeRisk.set(id, test);
    }
    test.distance = hexDistance(test.origin, m.current);
    if (test.distance <= test.safe || test.max <= test.safe)
      continue;
    test.draw ??= rng.nextFloat();
    const ratio = Math.max(0, Math.min(1, (test.distance - test.safe) / (test.max - test.safe)));
    test.probability = risk.fall_probability_at_max * Math.pow(ratio, risk.exponent);
    if (test.draw >= test.probability)
      continue;
    test.success = false;
    e.status.knocked_down = true;
    m.done = true;
    const landing = m.next && m.progress > SIMULATION_SCALE / 2 ? m.next : m.current;
    e.position = { ...landing };
    e.precise_position = { q: landing.q * SIMULATION_SCALE, r: landing.r * SIMULATION_SCALE };
    m.current = { ...landing };
    m.next = undefined;
    m.progress = 0;
    const carried = state.ball.holder_entity_id === id;
    events.push({ tick, type: "fall", actor: id, params: {
      position: { ...e.position },
      has_ball: carried,
      probability: test.probability,
      random_draw: test.draw,
      distance: test.distance,
      safe_range: test.safe,
      max_range: test.max
    } });
    if (carried) {
      e.status.carrying_ball = false;
      state.ball = { position: { ...e.position }, holder_entity_id: null, in_flight: false };
      events.push({ tick, type: "ball_drop", actor: id, params: { position: { ...e.position } } });
    }
  }
}
function publishMovementTests(context) {
  for (const [id, test] of context.rangeRisk ?? [])
    context.events.push({ tick: context.state.tick, type: "movement_test", actor: id, params: {
      success: test.success,
      probability: test.probability,
      random_draw: test.draw ?? null,
      distance: test.distance,
      safe_range: test.safe,
      max_range: test.max,
      inherent_score: test.score
    } });
}

// ../../boufbowl_server/src/rng.ts
import { createHash } from "crypto";

class DeterministicRNG {
  state;
  constructor(seed) {
    this.state = BigInt(seed);
    if (this.state === 0n)
      this.state = 1n;
  }
  next() {
    let x = this.state;
    x ^= x << 13n;
    x ^= x >> 7n;
    x ^= x << 17n;
    this.state = BigInt.asUintN(64, x);
    return Number(x & 0xffffffffn);
  }
  nextFloat() {
    return this.next() / 4294967296;
  }
  nextInt(min, max) {
    return Math.floor(this.nextFloat() * (max - min)) + min;
  }
  chance(probability) {
    return this.nextFloat() < probability;
  }
}
function hashWorldState(state) {
  return createHash("sha256").update(canonicalJSON({
    ...state,
    entities: [...state.entities].sort((a, b) => a.id - b.id)
  })).digest("hex");
}
function canonicalJSON(value) {
  if (value === null || typeof value !== "object")
    return JSON.stringify(value);
  if (Array.isArray(value))
    return "[" + value.map(canonicalJSON).join(",") + "]";
  const object = value;
  return "{" + Object.keys(object).filter((k) => object[k] !== undefined).sort().map((k) => JSON.stringify(k) + ":" + canonicalJSON(object[k])).join(",") + "}";
}

// ../../boufbowl_server/src/constants.ts
var VERSION = {
  PROTOCOL: "1.0.0",
  SIMULATION: "2.5.0",
  API: "1.0.0"
};
var SERVER_CONFIG = {
  PORT: parseInt(process.env.PORT || "3000", 10),
  HOST: process.env.HOST || "localhost"
};
var GAME_STRUCTURE = Object.freeze({ TEAM_SIZE: 5, ELEMENT_SLOTS: 3 });

// ../../boufbowl_server/src/rules.ts
var EMPTY_ELEMENTS = {
  TERRE: 0,
  FEU: 0,
  AIR: 0,
  EAU: 0
};
function maxMovementDistance(cfg, elements) {
  if (cfg.movement.overextension !== undefined && cfg.client_ranges)
    return referenceDistance(cfg, elements) * cfg.client_ranges.max_distance_factor;
  const base = cfg.movement.base_movement_range ?? 7;
  const eauBonus = cfg.movement.eau_range_bonus_per_action ?? 2;
  const airBonus = cfg.movement.air_range_bonus_per_action ?? 1;
  const terrePenalty = cfg.movement.terre_range_penalty_per_action ?? 1;
  let d = base;
  d += elements.EAU * eauBonus;
  d += elements.AIR * airBonus;
  d -= elements.TERRE * terrePenalty;
  return Math.max(1, d);
}
function maxThrowRange(cfg, elements) {
  return cfg.ball.base_range + elements.AIR * cfg.actions.element_effects.air.range_modifier;
}
function canThrow(elements) {
  return elements.AIR >= 1;
}
function canPickup(cfg, elements) {
  return cfg.actions.element_effects.feu.used_for_pickup ? elements.FEU >= 1 || cfg.actions.element_effects.air.used_for_pickup === true && elements.AIR >= 1 : true;
}
function canRevive(cfg, elements) {
  return elements.EAU >= cfg.combat.revive.required_eau_actions_to_get_up;
}
function movementSpeed(cfg, elements) {
  const base = cfg.movement.base_speed_cells_per_sec;
  const eau = elements.EAU * cfg.movement.eau_speed_bonus_per_action;
  const terre = elements.TERRE * cfg.movement.terre_speed_penalty_per_action;
  const air = elements.AIR * cfg.movement.air_speed_bonus_per_action;
  return Math.max(0.1, base + eau - terre + air);
}
function duelDamage(cfg, attackerTerre) {
  return cfg.combat.duel.damage_on_win + attackerTerre;
}
function throwInRange(cfg, from, to, elements) {
  return hexDistance(from, to) <= maxThrowRange(cfg, elements);
}
function defaultElements() {
  return { TERRE: 0, FEU: 0, AIR: 0, EAU: GAME_STRUCTURE.ELEMENT_SLOTS };
}
function defaultOrder(playerId, turnNumber, teamIndex, entities) {
  return {
    player_id: playerId,
    turn_number: turnNumber,
    team_index: teamIndex,
    nonce: `default-${teamIndex}-${turnNumber}`,
    actions: entities.map((e) => ({
      entity_id: e.id,
      action_type: "wait",
      params: { elements: defaultElements() }
    }))
  };
}
function attackPower(cfg, strength, terre) {
  return strength + terre * cfg.actions.element_effects.terre.attack_bonus_per;
}
function dodgeSucceeds(contest) {
  return contest.defender_feu > contest.attacker_terre && contest.defender_agility >= contest.attacker_agility;
}

// ../../boufbowl_server/src/simulator/movement.ts
var SCALE = SIMULATION_SCALE;
var fixed = (p) => ({
  q: Math.round(p.q * SCALE),
  r: Math.round(p.r * SCALE)
});
var fractional = (p) => ({
  q: p.q / SCALE,
  r: p.r / SCALE
});
function withinRadius(a, b, radius) {
  return distanceSquared(a, b) <= Math.round(radius * SCALE) ** 2;
}
function distanceSquared(a, b) {
  const q = a.q - b.q, r = a.r - b.r;
  return q * q + q * r + r * r;
}
var key = (h) => `${h.q},${h.r}`;
function detour(m, occupied, cfg) {
  if (occupied.has(key(m.target)))
    return;
  const queue = [{ p: m.current, distance: 0 }];
  const seen = new Set([key(m.current)]);
  for (let i = 0;i < queue.length; i++) {
    const node = queue[i];
    if (node.distance >= m.budget - m.traveled)
      continue;
    for (const next of hexNeighbors(node.p)) {
      const k = key(next);
      if (seen.has(k) || occupied.has(k) || !isInBounds(next, cfg.pitch))
        continue;
      const first = node.first ?? next;
      if (hexEqual(next, m.target))
        return first;
      seen.add(k);
      queue.push({ p: next, first, distance: node.distance + 1 });
    }
  }
}
function setupMovements(cfg, state, actions, _size) {
  const table = new Map;
  for (const e of state.entities)
    e.precise_position = fixed(e.position);
  for (const action of actions) {
    if (action.action_type !== "move" && action.action_type !== "follow")
      continue;
    const e = state.entities.find((e) => e.id === action.entity_id);
    const follow = action.action_type === "follow" ? action.params.follow_ball === true ? "ball" : action.params.target_entity_id : undefined;
    const target = follow === "ball" ? state.ball.position : follow !== undefined ? state.entities.find((other) => other.id === follow)?.position : action.params.target_position;
    if (!e || e.hp <= 0 || !target)
      continue;
    table.set(e.id, {
      risk_origin: { ...e.position },
      target: { ...target },
      current: { ...e.position },
      budget: Math.max(0, Math.floor(maxMovementDistance(cfg, e.elements) + (e.range_bonus ?? 0))),
      traveled: 0,
      done: hexEqual(e.position, target),
      progress: 0,
      pause: 0,
      follow,
      speed: Math.max(1, Math.round((movementSpeed(cfg, e.elements) + e.stats.endurance * cfg.movement.speed_per_endurance) * cfg.tick_system.tick_dt_seconds * SCALE))
    });
  }
  return table;
}
function stepMovements(state, table, size, cfg, tick, seed) {
  const steps = [];
  for (const m of table.values())
    if (m.follow !== undefined && m.traveled < m.budget) {
      const holder = state.entities.find((e) => e.id === state.ball.holder_entity_id);
      const target = m.follow === "ball" ? holder?.position ?? state.ball.position : state.entities.find((e) => e.id === m.follow && e.hp > 0)?.position;
      if (target) {
        m.target = { ...target };
        m.done = false;
      } else
        m.done = true;
    }
  const occupied = new Set(state.entities.filter((e) => e.hp > 0).map((e) => key(table.get(e.id)?.current ?? e.position)));
  for (const m of table.values())
    if (m.next)
      occupied.add(key(m.next));
  const ids = [...table.keys()].sort((a, b) => a - b);
  const offset = ids.length ? ((seed >>> 0) + tick) % ids.length : 0;
  for (const id of [...ids.slice(offset), ...ids.slice(0, offset)]) {
    const m = table.get(id);
    const e = state.entities.find((e) => e.id === id);
    if (m.done || e.hp <= 0 || e.status.knocked_down || e.status.stunned)
      continue;
    if (m.pause > 0) {
      m.pause--;
      continue;
    }
    let available = m.speed;
    while (available > 0 && !m.done) {
      if (!m.next) {
        if (m.traveled >= m.budget || hexEqual(m.current, m.target)) {
          m.done = true;
          break;
        }
        m.next = hexNeighbors(m.current).filter((n) => isInBounds(n, cfg.pitch) && !occupied.has(key(n)) && hexDistance(n, m.target) < hexDistance(m.current, m.target)).sort((a, b) => hexDistance(a, m.target) - hexDistance(b, m.target))[0] ?? detour(m, occupied, cfg);
        if (!m.next)
          break;
        occupied.add(key(m.next));
      }
      const from = { ...e.precise_position };
      const distance = Math.min(SCALE - m.progress, available);
      m.progress += distance;
      available -= distance;
      e.precise_position = {
        q: m.current.q * SCALE + (m.next.q - m.current.q) * m.progress,
        r: m.current.r * SCALE + (m.next.r - m.current.r) * m.progress
      };
      e.position = hexRound(fractional(e.precise_position));
      steps.push({
        entityId: id,
        from,
        to: { ...e.precise_position },
        hex: { ...e.position }
      });
      if (m.progress === SCALE) {
        occupied.delete(key(m.current));
        m.current = m.next;
        m.next = undefined;
        m.progress = 0;
        m.traveled++;
        if (hexEqual(m.current, m.target) || m.traveled >= m.budget)
          m.done = true;
      }
    }
  }
  return steps;
}
function finalizePositions(state, table, _size) {
  for (const e of state.entities) {
    const m = table.get(e.id);
    if (m)
      e.position = { ...m.next && m.progress > SCALE / 2 ? m.next : m.current };
    delete e.precise_position;
  }
  const holder = state.entities.find((e) => e.id === state.ball.holder_entity_id);
  if (holder)
    state.ball.position = { ...holder.position };
}

// ../../boufbowl_server/src/simulator/combat.ts
function resolveDuels(cfg, state, actions, rng, tick, dueledPairs) {
  const events = [];
  const elements = new Map(state.entities.map((e) => [e.id, e.elements]));
  const trigger = cfg.combat.trigger_distance_cells;
  for (let i = 0;i < state.entities.length; i++) {
    for (let j = i + 1;j < state.entities.length; j++) {
      const a = state.entities[i];
      const b = state.entities[j];
      if (a.team_id === b.team_id || a.power_locked && b.power_locked)
        continue;
      if (a.status.stunned || b.status.stunned || a.status.knocked_down || a.hp <= 0 || b.status.knocked_down || b.hp <= 0)
        continue;
      const pairKey = `${Math.min(a.id, b.id)}_${Math.max(a.id, b.id)}`;
      if (dueledPairs.has(pairKey))
        continue;
      if (withinRadius(a.precise_position ?? fixed(a.position), b.precise_position ?? fixed(b.position), trigger)) {
        const ea = elements.get(a.id) ?? { TERRE: 0, FEU: 0, AIR: 0, EAU: 0 };
        const eb = elements.get(b.id) ?? { TERRE: 0, FEU: 0, AIR: 0, EAU: 0 };
        const outcome = performDuel(cfg, a, b, ea, eb, rng);
        dueledPairs.add(pairKey);
        events.push({
          tick,
          type: outcome.defenderDodged ? "dodge" : "duel",
          actor: outcome.attacker.id,
          params: { defender: outcome.defender.id }
        });
        events.push(...duelEvents(outcome, tick));
        if (outcome.ballDropped) {
          state.ball = {
            holder_entity_id: null,
            in_flight: false,
            position: { ...outcome.defender.position }
          };
        }
      }
    }
  }
  for (const entity of state.entities) {
    if (entity.hp <= 0 || entity.status.knocked_down) {
      if (!entity.status.knocked_down)
        events.push({ tick, type: "ko", actor: entity.id, params: {} });
      entity.status.knocked_down = true;
      if (state.ball.holder_entity_id === entity.id) {
        entity.status.carrying_ball = false;
        state.ball.holder_entity_id = null;
        state.ball.in_flight = false;
        state.ball.position = { ...entity.position };
        events.push({
          tick,
          type: "ball_drop",
          actor: entity.id,
          params: { position: { ...entity.position } }
        });
      }
    }
  }
  return events;
}
function performDuel(cfg, a, b, ea, eb, rng) {
  const powerA = attackPower(cfg, a.stats.strength, ea.TERRE) + (a.attack_bonus ?? 0);
  const powerB = attackPower(cfg, b.stats.strength, eb.TERRE) + (b.attack_bonus ?? 0);
  const aAttacks = a.power_locked ? false : b.power_locked ? true : powerA >= powerB;
  const attacker = aAttacks ? a : b;
  const defender = aAttacks ? b : a;
  const atk = aAttacks ? ea : eb;
  const def = aAttacks ? eb : ea;
  if (dodgeSucceeds({
    attacker_terre: atk.TERRE,
    defender_feu: def.FEU,
    attacker_agility: attacker.stats.agility,
    defender_agility: defender.stats.agility
  })) {
    return {
      attacker,
      defender,
      damage: 0,
      defenderDodged: true,
      defenderKO: false,
      ballDropped: false
    };
  }
  if (powerA === powerB && !a.power_locked && !b.power_locked) {
    const tieDamage = cfg.combat.duel.damage_on_tie + atk.TERRE;
    attacker.hp = Math.max(0, attacker.hp - tieDamage);
    defender.hp = Math.max(0, defender.hp - tieDamage);
    return {
      attacker,
      defender,
      damage: tieDamage,
      defenderDodged: false,
      defenderKO: false,
      ballDropped: false,
      tie: true
    };
  }
  const damage = duelDamage(cfg, atk.TERRE);
  defender.hp = Math.max(0, defender.hp - damage);
  const diff = Math.abs(powerA - powerB);
  const koChance = Math.min(cfg.simulation.fall_max, cfg.simulation.fall_base + diff * cfg.simulation.fall_per_power);
  const defenderKO = defender.hp <= 0 || rng.chance(koChance);
  let ballDropped = false;
  if (defenderKO) {
    defender.status.knocked_down = true;
    if (defender.status.carrying_ball) {
      defender.status.carrying_ball = false;
      ballDropped = true;
    }
  }
  return {
    attacker,
    defender,
    damage,
    defenderDodged: false,
    defenderKO,
    ballDropped
  };
}
function duelEvents(outcome, tick) {
  const events = [];
  if (outcome.tie) {
    events.push({
      tick,
      type: "damage",
      actor: outcome.attacker.id,
      params: { damage: outcome.damage, hp: outcome.attacker.hp }
    });
    events.push({
      tick,
      type: "damage",
      actor: outcome.defender.id,
      params: { damage: outcome.damage, hp: outcome.defender.hp }
    });
    return events;
  }
  if (outcome.damage > 0) {
    events.push({
      tick,
      type: "damage",
      actor: outcome.defender.id,
      params: { damage: outcome.damage, hp: outcome.defender.hp }
    });
  }
  if (outcome.defenderKO) {
    events.push({ tick, type: "ko", actor: outcome.defender.id, params: {} });
    if (outcome.ballDropped) {
      events.push({
        tick,
        type: "ball_drop",
        actor: outcome.defender.id,
        params: { position: { ...outcome.defender.position } }
      });
    }
  }
  return events;
}

// ../../boufbowl_server/src/simulator/throwTarget.ts
function receiverPositionAfter(cfg, receiver, movement, ticks) {
  if (!movement || movement.done || receiver.hp <= 0 || receiver.status.knocked_down || receiver.status.stunned)
    return fractional(receiver.precise_position ?? fixed(receiver.position));
  let current = { ...movement.current }, { next, progress } = movement;
  let remainingCells = movement.budget - movement.traveled;
  let distance = movement.speed * Math.max(0, ticks - movement.pause);
  while (distance > 0 && remainingCells > 0) {
    if (!next) {
      if (hexEqual(current, movement.target))
        break;
      next = hexNeighbors(current).filter((p) => isInBounds(p, cfg.pitch) && hexDistance(p, movement.target) < hexDistance(current, movement.target)).sort((a, b) => hexDistance(a, movement.target) - hexDistance(b, movement.target))[0];
      if (!next)
        break;
    }
    const step = Math.min(SCALE - progress, distance);
    progress += step;
    distance -= step;
    if (progress === SCALE) {
      current = next;
      next = undefined;
      progress = 0;
      remainingCells--;
    }
  }
  return next ? fractional({ q: current.q * SCALE + (next.q - current.q) * progress, r: current.r * SCALE + (next.r - current.r) * progress }) : current;
}
function targetedThrow(cfg, start, receiver, movement) {
  const cellsPerTick = cfg.ball.throw_speed_cells_per_sec * cfg.tick_system.tick_dt_seconds;
  const current = fractional(receiver.precise_position ?? fixed(receiver.position));
  const remaining = movement && !movement.done ? Math.max(0, movement.budget - movement.traveled) : 0;
  const latest = Math.max(1, Math.ceil((hexDistance(start, current) + remaining + 1) / cellsPerTick));
  for (let ticks = 1;ticks <= latest; ticks++) {
    const target = hexRound(receiverPositionAfter(cfg, receiver, movement, ticks));
    if (hexDistance(start, target) <= cellsPerTick * ticks)
      return { target, flightTicks: ticks };
  }
  throw new Error("Receiver projection exceeded its distance bound");
}

// ../../boufbowl_server/src/simulator/ball.ts
const active = (e) => e.hp > 0 && !e.status.knocked_down && !e.status.stunned && !e.power_locked, point = (e) => e.precise_position ?? fixed(e.position), clamp = (cfg, p) => Math.max(cfg.simulation.probability_min, Math.min(cfg.simulation.probability_max, p)), attemptBooks = new WeakMap, actionLimited = (cfg) => cfg.ball.action_limited_attempts === !0;
function usedAttempts(state, id) {
  let book = attemptBooks.get(state);
  if (!book) {
    book = new Map;
    attemptBooks.set(state, book);
  }
  let used = book.get(id);
  if (!used) {
    used = { air: 0, fire: 0, lastTick: -1 };
    book.set(id, used);
  }
  return used;
}
function remaining(state, e, kind) {
  return Math.max(0, (kind === "air" ? e.elements.AIR : e.elements.FEU) - usedAttempts(state, e.id)[kind]);
}
function attempt(state, e, tick, kind) {
  const used = usedAttempts(state, e.id);
  if (used.lastTick === tick || remaining(state, e, kind) <= 0)
    return !1;
  used[kind]++;
  used.lastTick = tick;
  return !0;
}
function groundCandidate(cfg, state, e) {
  return active(e) && withinRadius(point(e), fixed(state.ball.position), cfg.ball.pickup_range) && (remaining(state, e, "air") > 0 || remaining(state, e, "fire") > 0);
}
function hasPendingPickups(cfg, state) {
  return actionLimited(cfg) && !state.ball.in_flight && state.ball.holder_entity_id === null && state.entities.some((e) => groundCandidate(cfg, state, e));
}
function resolveThrows(cfg, state, actions, rng, tick, consumed = new Set, movements) {
  const events = [], flights = [];
  for (const action of actions) {
    if (action.action_type !== "throw" || consumed.has(action.entity_id) || tick < cfg.simulation.throw_delay_ticks)
      continue;
    const e = state.entities.find((e) => e.id === action.entity_id);
    if (!e || !active(e) || state.ball.holder_entity_id !== e.id || !canThrow(e.elements))
      continue;
    const targetEntity = state.entities.find((e) => e.id === action.params.target_entity_id), start = fractional(point(e)), predicted = targetEntity ? targetedThrow(cfg, start, targetEntity, movements?.get(targetEntity.id)) : void 0, target = predicted?.target ?? action.params.target_position;
    if (!target || !throwInRange({ ...cfg, ball: { ...cfg.ball, base_range: cfg.ball.base_range + (e.range_bonus ?? 0) } }, start, target, e.elements))
      continue;
    const distance = hexDistance(start, target), landTick = tick + (predicted?.flightTicks ?? Math.max(1, Math.ceil(distance / cfg.ball.throw_speed_cells_per_sec / cfg.tick_system.tick_dt_seconds)));
    if (cfg.ball.require_arrival_before_turn_end && landTick >= cfg.tick_system.max_ticks_per_turn)
      continue;
    consumed.add(e.id);
    e.status.carrying_ball = !1;
    state.ball.holder_entity_id = null;
    state.ball.in_flight = !0;
    const precision = clamp(cfg, cfg.simulation.throw_base + e.stats.precision * cfg.simulation.throw_stat + e.elements.AIR * cfg.probabilities.air_precision_per_action - distance * cfg.simulation.distance_penalty), success = rng.chance(precision), landing = hexRound(target);
    events.push({
      tick,
      type: "throw",
      actor: e.id,
      params: {
        start_position: start,
        target_position: landing,
        target_entity_id: targetEntity?.id ?? null,
        success,
        precision,
        land_tick: landTick,
        arc_height: cfg.ball.arc_height_cells
      }
    });
    flights.push({
      start: fixed(start),
      startTick: tick,
      thrower: e.id,
      success,
      attempted: [],
      target: landing,
      targetEntityId: targetEntity?.id ?? null,
      landTick
    });
  }
  return { events, flights };
}
function resolveReceptions(cfg, state, rng, tick, flights, onBlockedReception) {
  const events = [];
  if (!state.ball.in_flight)
    return events;
  const f = flights.at(-1);
  if (!f || tick < f.startTick || tick > f.landTick)
    return events;
  const duration = f.landTick - f.startTick, elapsed = tick - f.startTick, end = fixed(f.target), pos = {
    q: f.start.q + Math.trunc((end.q - f.start.q) * elapsed / duration),
    r: f.start.r + Math.trunc((end.r - f.start.r) * elapsed / duration)
  }, height = Math.trunc(4 * Math.round(cfg.ball.arc_height_cells * SCALE) * elapsed * (duration - elapsed) / (duration * duration));
  state.ball.position = hexRound(fractional(pos));
  events.push({
    tick,
    type: "ball_move",
    params: { position: fractional(pos), height: height / SCALE }
  });
  if (elapsed > 0 && height <= Math.round(cfg.ball.intercept_height_threshold * SCALE) && (f.success || actionLimited(cfg))) {
    const thrower = state.entities.find((e) => e.id === f.thrower), limited = actionLimited(cfg), reachable = state.entities.filter((e) => active(e) && e.id !== f.thrower && (!limited || e.id === f.targetEntityId || e.team_id !== thrower.team_id) && withinRadius(point(e), pos, (limited ? e.id === f.targetEntityId : e.team_id === thrower.team_id) ? cfg.ball.catch_radius_cells : cfg.ball.intercept_radius_cells)).sort((a, b) => distanceSquared(point(a), pos) - distanceSquared(point(b), pos) || a.id - b.id);
    if (!limited && onBlockedReception && (cfg.ball.reception_requires_air ?? !0)) {
      const teams = new Set(reachable.map((e) => e.team_id));
      for (const team of teams) {
        const teammates = reachable.filter((e) => e.team_id === team);
        if (!teammates.some((e) => e.elements.AIR >= 1))
          onBlockedReception(teammates[0].id);
      }
    }
    const candidates = reachable.filter((e) => limited ? e.id === f.targetEntityId ? f.success && remaining(state, e, "air") > 0 : remaining(state, e, "fire") > 0 : (!(cfg.ball.reception_requires_air ?? !0) || e.elements.AIR >= 1) && !f.attempted.includes(e.id));
    for (const e of candidates) {
      const intended = e.id === f.targetEntityId, kind = intended ? "air" : "fire";
      if (limited && !attempt(state, e, tick, kind))
        continue;
      f.attempted.push(e.id);
      const stat = !intended && cfg.ball.interception_uses_fire_stat ? e.stats.agility : e.stats.precision, base = cfg.simulation.catch_base + stat * cfg.simulation.catch_stat, bonus = intended ? e.elements.AIR * cfg.simulation.catch_air : e.elements.FEU * cfg.simulation.catch_feu, chance = clamp(cfg, limited ? base + bonus : base + e.elements.FEU * cfg.simulation.catch_feu + e.elements.AIR * cfg.simulation.catch_air);
      if (rng.chance(chance)) {
        e.status.carrying_ball = !0;
        state.ball.holder_entity_id = e.id;
        state.ball.in_flight = !1;
        state.ball.position = { ...e.position };
        events.push({
          tick,
          type: "catch",
          actor: e.id,
          params: { position: { ...e.position }, catch_chance: chance, ...limited ? { interception: !intended, attempt: usedAttempts(state, e.id)[kind], action: kind } : {} }
        });
        return events;
      }
      events.push({
        tick,
        type: "catch_fail",
        actor: e.id,
        params: { catch_chance: chance, ...limited ? { interception: !intended, attempt: usedAttempts(state, e.id)[kind], action: kind } : {} }
      });
    }
  }
  if (tick === f.landTick) {
    state.ball.in_flight = !1;
    state.ball.position = { ...f.target };
    events.push({
      tick,
      type: "ball_land",
      params: { position: { ...f.target } }
    });
  }
  return events;
}
function resolvePickups(cfg, state, tick, onBlockedPickup, rng) {
  if (state.ball.in_flight || state.ball.holder_entity_id !== null)
    return [];
  const candidates = state.entities.filter((e) => {
    if (!active(e) || !withinRadius(point(e), fixed(state.ball.position), cfg.ball.pickup_range))
      return !1;
    if (!canPickup(cfg, e.elements)) {
      onBlockedPickup?.(e.id);
      return !1;
    }
    return !0;
  }).sort((a, b) => distanceSquared(point(a), fixed(state.ball.position)) - distanceSquared(point(b), fixed(state.ball.position)) || a.id - b.id);
  if (actionLimited(cfg)) {
    const events = [];
    for (const e of candidates) {
      const kind = remaining(state, e, "fire") > 0 ? "fire" : "air";
      if (!attempt(state, e, tick, kind))
        continue;
      const chance = clamp(cfg, cfg.simulation.catch_base + e.stats.precision * cfg.simulation.catch_stat + e.elements.AIR * cfg.simulation.catch_air + e.elements.FEU * cfg.simulation.catch_feu);
      if (!rng)
        throw Error("Pickup attempts require the turn RNG");
      const success = rng.chance(chance);
      events.push({
        tick,
        type: success ? "pickup" : "pickup_fail",
        actor: e.id,
        params: { position: { ...e.position }, pickup_chance: chance, attempt: usedAttempts(state, e.id).air + usedAttempts(state, e.id).fire, action: kind }
      });
      if (success) {
        e.status.carrying_ball = !0;
        state.ball.holder_entity_id = e.id;
        state.ball.position = { ...e.position };
        break;
      }
    }
    return events;
  }
  const e = candidates[0];
  if (!e)
    return [];
  e.status.carrying_ball = !0;
  state.ball.holder_entity_id = e.id;
  state.ball.position = { ...e.position };
  return [
    {
      tick,
      type: "pickup",
      actor: e.id,
      params: { position: { ...e.position } }
    }
  ];
}
function resolveGoals(cfg, state, tick) {
  const e = state.entities.find((e) => e.id === state.ball.holder_entity_id);
  if (!e || !active(e))
    return [];
  const p = point(e), x = 2 * p.q + p.r, goalLine = (cfg.ball.goal_line_half_width ?? 15.5) * 2 * SCALE, cellX = (2 * e.position.q + e.position.r) * SCALE;
  if (e.team_id === 0 !== (state.sides_swapped ?? !1) ? x > goalLine && cellX > goalLine : x < -goalLine && cellX < -goalLine) {
    e.status.carrying_ball = !1;
    state.ball.holder_entity_id = null;
    state.ball.in_flight = !1;
    state.ball.position = { ...e.position };
    return [
      {
        tick,
        type: "goal",
        actor: e.id,
        params: { team: e.team_id, position: { ...e.position } }
      }
    ];
  }
  return [];
}

// ../../boufbowl_server/src/simulator/turnTick.ts
function executeTick(context, tick) {
  const { cfg, state, actions, rng, events, consumedThrows, flights } = context;
  state.tick = tick;
  restoreStandingPlayers(context, tick);
  const pausedThisTick = new Set([...context.movements].filter(([, movement]) => movement.pause > 0).map(([id]) => id));
  const steps = movePlayers(context, tick);
  resolveMovementRisk(context, tick);
  const carrierBeforeContact = state.ball.holder_entity_id;
  const contactEventsStart = events.length;
  fightPlayers(context, tick);
  // M05: contact interrupts an unlaunched throwing action. No draw or flight
  // occurs; a pass already airborne remains independent of later contacts.
  if (cfg.ball.contact_cancels_pending_throw && carrierBeforeContact !== null &&
      !consumedThrows.has(carrierBeforeContact) && context.actions.some(action =>
        action.entity_id === carrierBeforeContact && action.action_type === "throw") &&
      events.slice(contactEventsStart).some(event =>
        (event.type === "duel" || event.type === "dodge") &&
        (event.actor === carrierBeforeContact || event.params.defender === carrierBeforeContact))) {
    consumedThrows.add(carrierBeforeContact);
    events.push({tick, type: "throw_cancelled", actor: carrierBeforeContact, params: {reason: "contact"}});
  }
  const thrown = (context.throwResolver ?? resolveThrows)(cfg, state, actions, rng, tick, consumedThrows, context.movements);
  events.push(...thrown.events);
  flights.push(...thrown.flights);
  events.push(...resolveReceptions(cfg, state, rng, tick, flights, context.onBlockedReception));
  events.push(...resolvePickups(cfg, state, tick, context.onBlockedPickup, rng));
  const goals = resolveGoals(cfg, state, tick);
  events.push(...goals);
  if (goals.length > 0)
    return { goalScored: true, workRemains: false };
  return {
    goalScored: false,
    workRemains: hasPendingWork(context, tick, steps, pausedThisTick)
  };
}
function restoreStandingPlayers(context, tick) {
  const { cfg, state, events, knockedAtStart } = context;
  if (tick === cfg.simulation.stand_up_ticks)
    for (const e of state.entities) {
      if (knockedAtStart.has(e.id) && e.hp > 0 && e.status.knocked_down && canRevive(cfg, e.elements)) {
        e.status.knocked_down = false;
        e.elements.EAU -= cfg.combat.revive.required_eau_actions_to_get_up;
        events.push({ tick, type: "stand_up", actor: e.id, params: {} });
      }
    }
}
function movePlayers(context, tick) {
  const { cfg, state, seed, events, movements } = context;
  const steps = stepMovements(state, movements, cfg.pitch.hex_size, cfg, tick, seed);
  for (const s of steps)
    events.push({
      tick,
      type: "move",
      actor: s.entityId,
      params: {
        position: s.hex,
        precise_position: { ...s.to, scale: SCALE },
        start_position: s.from,
        end_position: s.to
      }
    });
  return steps;
}
function fightPlayers(context, tick) {
  const { cfg, state, actions, rng, events, movements, dueledPairs } = context;
  const duelEvents = resolveDuels(cfg, state, actions, rng, tick, dueledPairs);
  events.push(...duelEvents);
  for (const ev of duelEvents.filter((event) => event.type === "duel"))
    for (const id of [ev.actor, ev.params.defender]) {
      const m = movements.get(id);
      if (m)
        m.pause += Math.ceil(cfg.combat.fight_duration_penalty_cells * SCALE / m.speed);
    }
}
function hasPendingWork(context, tick, steps, pausedThisTick) {
  const { cfg, state, actions, movements, knockedAtStart, consumedThrows } = context;
  const pendingMove = [...movements.entries()].some(([id, m]) => {
    const e = state.entities.find((entity) => entity.id === id);
    return !m.done && e.hp > 0 && !e.status.knocked_down && !e.status.stunned && (m.pause > 0 || pausedThisTick.has(id) || steps.length > 0);
  });
  const pendingThrow = actions.some((a) => {
    const e = state.entities.find((entity) => entity.id === a.entity_id);
    if (a.action_type !== "throw" || consumedThrows.has(a.entity_id) || !e || e.hp <= 0 || e.status.knocked_down || e.status.stunned || state.ball.holder_entity_id !== e.id || !canThrow(e.elements))
      return false;
    const targetEntity = state.entities.find((entity) => entity.id === a.params.target_entity_id);
    const modernTargeting = !context.throwResolver || context.throwResolver === resolveThrows;
    const start = fractional(e.precise_position);
    const target = targetEntity ? modernTargeting ? targetedThrow(cfg, start, targetEntity, context.movements.get(targetEntity.id)).target : fractional(targetEntity.precise_position) : a.params.target_position;
    const inRange = !!target && throwInRange(cfg, start, target, e.elements);
    return inRange;
  });
  const pendingRevive = state.entities.some((e) => knockedAtStart.has(e.id) && e.hp > 0 && e.status.knocked_down && canRevive(cfg, e.elements) && tick < cfg.simulation.stand_up_ticks);
  return pendingMove || pendingThrow || pendingRevive || state.ball.in_flight || hasPendingPickups(cfg, state);
}

// ../../boufbowl_server/src/simulator/abilities.ts
function resolveAbilities(cfg, state, actions, rng) {
  const activations = actions.filter((a) => a.action_type === "ability").map((action) => {
    const caster = state.entities.find((e) => e.id === action.entity_id), rule = caster && cfg.abilities?.[caster.class_name];
    return caster && rule && caster.hp > 0 && !caster.status.knocked_down && !caster.status.stunned && (caster.ability_uses_remaining ?? 0) > 0 ? { caster, rule, action } : null;
  }).filter((a) => a !== null), living = new Set(state.entities.filter((e) => e.hp > 0).map((e) => e.id)), redirectors = activations.filter(({ rule }) => rule.redirect_enemy_heal), events = [], teams = new Set;
  for (const { caster, rule, action } of activations) {
    if (rule.target && teams.has(caster.team_id))
      throw Error("Only one class power per team per turn");
    teams.add(caster.team_id);
    caster.ability_uses_remaining--;
    const targets = [];
    if (!rule.target) {
      for (const target of state.entities) {
        if (target.team_id !== caster.team_id || target.hp <= 0)
          continue;
        target.hp = Math.min(target.max_hp, target.hp + rule.heal);
        if (rule.element)
          target.elements[rule.element] += rule.bonus;
        targets.push(target.id);
      }
      events.push({ tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name,
        targets,
        heal: rule.heal,
        element: rule.element ?? null,
        bonus: rule.bonus,
        uses_remaining: caster.ability_uses_remaining
      } });
      continue;
    }
    caster.power_locked = !0;
    if (rule.redirect_enemy_heal) {
      events.push({ tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name,
        targets: [],
        redirected_healers: activations.filter((a) => a.caster.team_id !== caster.team_id && a.caster.class_name === "Eniripsa" && a.rule.hp > 0).map((a) => a.caster.id),
        uses_remaining: caster.ability_uses_remaining
      } });
      continue;
    }
    if (rule.change_mask) {
      caster.zobal_mask = action.params.zobal_mask;
      events.push({ tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name,
        targets: [],
        zobal_mask: caster.zobal_mask,
        uses_remaining: caster.ability_uses_remaining
      } });
      continue;
    }
    const enemyRoll = rule.enemy_chance !== void 0 ? rng.nextFloat() : void 0, enemy = enemyRoll !== void 0 ? enemyRoll < rule.enemy_chance : rule.target === "enemies", bonus = enemyRoll !== void 0 && enemy ? rule.enemy_elements : rule.elements, hpDeltas = {}, redirector = caster.class_name === "Eniripsa" && rule.hp > 0 ? redirectors.find((a) => a.caster.team_id !== caster.team_id) : void 0;
    for (const target of state.entities) {
      if (!living.has(target.id) || (redirector ? target.team_id !== redirector.caster.team_id : target.team_id !== caster.team_id !== enemy))
        continue;
      targets.push(target.id);
      const before = target.hp;
      target.hp = Math.max(0, Math.min(target.max_hp, target.hp + (rule.hp ?? 0)));
      hpDeltas[target.id] = target.hp - before;
      const fields = { TERRE: "strength", FEU: "agility", AIR: "precision", EAU: "endurance" };
      for (const [element, value] of Object.entries(bonus ?? {})) {
        const field = fields[element];
        target.stats[field] = Math.max(0, target.stats[field] + Number(value));
      }
      target.range_bonus = (target.range_bonus ?? 0) + (rule.range ?? 0);
      target.attack_bonus = (target.attack_bonus ?? 0) + (rule.attack ?? 0);
    }
    events.push({ tick: 0, type: "ability", actor: caster.id, params: {
      name: rule.name,
      targets,
      hp_deltas: hpDeltas,
      elements: bonus ?? {},
      range: rule.range ?? 0,
      attack: rule.attack ?? 0,
      target: enemy ? "enemies" : "allies",
      ...enemyRoll !== void 0 ? { random_draw: enemyRoll } : {},
      uses_remaining: caster.ability_uses_remaining,
      ...redirector ? { redirected_by: redirector.caster.id } : {}
    } });
  }
  return events;
}

// ../../boufbowl_server/src/validator.ts
class OrderValidator {
  config;
  constructor(config) {
    this.config = config;
  }
  validateOrder(order, playerId, turn, state, team) {
    const errors = [];
    const warnings = [];
    const ignored = new Set;
    const warn = (code, index) => {
      if (ignored.has(index))
        return;
      warnings.push({
        code,
        entity_id: order.actions[index].entity_id,
        action_index: index
      });
      ignored.add(index);
    };
    const fail = (message) => ({
      valid: false,
      errors: [message]
    });
    if (!order || typeof order !== "object" || !Array.isArray(order.actions) || order.actions.length > 15 || typeof order.nonce !== "string" || order.nonce.length > 128)
      return fail("Invalid order format");
    if (order.player_id !== playerId || order.turn_number !== turn)
      return fail("Player or turn mismatch");
    const powers = order.actions.filter((a) => a?.action_type === "ability");
    const modern = Object.values(this.config.abilities ?? {}).some((r) => r.target);
    if (modern) {
      if (powers.length > 1)
        return fail("Only one class power per team per turn");
      for (const power of powers) {
        if (order.actions.some((a) => a !== power && a.entity_id === power.entity_id))
          return fail("A class power cannot be combined with any other action");
        const caster = state.entities.find((e) => e.id === power.entity_id && e.team_id === team);
        if (!caster || caster.hp <= 0 || caster.status.stunned || caster.status.knocked_down || (caster.ability_uses_remaining ?? 0) <= 0 || !this.config.abilities?.[caster.class_name])
          return fail("Class power unavailable");
        if (Object.values(power.params?.elements ?? {}).some((v) => v !== 0))
          return fail("A class power cannot assign elements");
        if (Object.keys(power.params ?? {}).some((k) => !["elements", "zobal_mask"].includes(k)))
          return fail("A class power cannot target a movement or ball action");
        if (caster.class_name === "Zobal" && (![1, 2, 3].includes(power.params?.zobal_mask) || power.params.zobal_mask === (caster.zobal_mask ?? 1)))
          return fail("Choose a different Zobal mask");
        if (caster.class_name !== "Zobal" && power.params?.zobal_mask !== undefined)
          return fail("Only Zobal can select a mask");
      }
    }
    const allocations = new Map, seen = new Set;
    for (const [index, a] of order.actions.entries()) {
      if (!a || !Number.isSafeInteger(a.entity_id) || !a.params || typeof a.params !== "object" || Array.isArray(a.params))
        return fail("Malformed action");
      const e = state.entities.find((e) => e.id === a.entity_id && e.team_id === team);
      if (!e)
        return fail("Entity not owned by team");
      const elements = a.params.elements ?? EMPTY_ELEMENTS;
      if (!elements || typeof elements !== "object" || Object.keys(elements).some((k) => !["TERRE", "FEU", "AIR", "EAU"].includes(k)))
        return fail("Invalid elements");
      const values = ["TERRE", "FEU", "AIR", "EAU"].map((k) => elements[k]);
      if (values.some((v) => !Number.isSafeInteger(v) || v < 0))
        return fail("Element budget exceeded or invalid");
      if (values.reduce((a, b) => a + b, 0) > this.config.general.actions_per_character)
        warn("ELEMENT_BUDGET_EXCEEDED", index);
      const allocation = canonicalJSON(elements);
      if (allocations.has(e.id) && allocations.get(e.id) !== allocation)
        warn("CONFLICTING_ELEMENTS", index);
      const key = `${e.id}:${a.action_type}`;
      if (a.action_type === "ability" && order.actions.some((other) => other !== a && other?.entity_id === e.id))
        warn("ABILITY_EXCLUSIVE", index);
      if (seen.has(key))
        warn("DUPLICATE_COMMAND", index);
      if (e.hp <= 0 && a.action_type !== "wait")
        warn("ENTITY_ELIMINATED", index);
      if (e.status.knocked_down && a.action_type !== "wait" && !canRevive(this.config, elements))
        warn("REVIVE_REQUIRES_EAU", index);
      const target = a.params.target_position;
      if (target && (!Number.isSafeInteger(target.q) || !Number.isSafeInteger(target.r)))
        return fail("Invalid target coordinates");
      if (target && !isInBounds(target, this.config.pitch))
        warn("TARGET_OUTSIDE_PITCH", index);
      switch (a.action_type) {
        case "ability":
          if (!this.config.abilities?.[e.class_name] || (e.ability_uses_remaining ?? 0) <= 0 || e.status.knocked_down || e.status.stunned || e.hp <= 0)
            warn("ABILITY_UNAVAILABLE", index);
          if (values.some((v) => v !== 0))
            warn("ABILITY_ELEMENTS", index);
          break;
        case "follow":
          if (seen.has(`${e.id}:move`))
            warn("MOVEMENT_CONFLICT", index);
          if (a.params.follow_ball !== true && (!Number.isSafeInteger(a.params.target_entity_id) || a.params.target_entity_id === e.id || !state.entities.some((other) => other.id === a.params.target_entity_id)))
            warn("FOLLOW_TARGET_INVALID", index);
          break;
        case "move":
          if (seen.has(`${e.id}:follow`))
            warn("MOVEMENT_CONFLICT", index);
          if (!target || hexDistance(e.position, target) > maxMovementDistance(this.config, elements) + (modern ? Math.max(0, ...state.entities.filter((p) => p.team_id === team && p.hp > 0 && (p.ability_uses_remaining ?? 0) > 0).map((p) => this.config.abilities?.[p.class_name]?.range ?? 0)) : 0))
            warn("MOVE_OUT_OF_RANGE", index);
          break;
        case "throw":
          if (!canThrow(elements))
            warn("THROW_REQUIRES_AIR", index);
          if (a.params.target_entity_id !== undefined && (!Number.isSafeInteger(a.params.target_entity_id) || !state.entities.some((e) => e.id === a.params.target_entity_id)))
            warn("RECEIVER_INVALID", index);
          if (!target && a.params.target_entity_id === undefined)
            warn("THROW_TARGET_MISSING", index);
          break;
        case "pickup":
        case "wait":
          break;
        default:
          return fail("Unknown command");
      }
      if (!ignored.has(index)) {
        allocations.set(e.id, allocation);
        seen.add(key);
      }
    }
    const executable_order = structuredClone(order);
    executable_order.actions = executable_order.actions.filter((_, index) => !ignored.has(index));
    for (const action of order.actions) {
      if (executable_order.actions.some((a) => a.entity_id === action.entity_id))
        continue;
      const elements = action.params.elements ?? EMPTY_ELEMENTS;
      if (Object.values(elements).reduce((sum, value) => sum + value, 0) > this.config.general.actions_per_character)
        continue;
      executable_order.actions.push({
        entity_id: action.entity_id,
        action_type: "wait",
        params: { elements: { ...elements } }
      });
    }
    return {
      valid: true,
      errors,
      ...warnings.length ? { warnings, executable_order } : {}
    };
  }
}

// ../../boufbowl_server/src/simulator/engine.ts
function simulateTurn4(cfg, initialState, orderA, orderB, turnNumber, seed, onWarning, behavior = { version: VERSION.SIMULATION, throwResolver: resolveThrows }) {
  const state = structuredClone(initialState);
  state.entities.sort((a, b) => a.id - b.id);
  const initialHash = hashWorldState(state), rng = new DeterministicRNG(seed);
  const validator = new OrderValidator(cfg);
  const executable = [orderA, orderB].map((order) => {
    const team = order.team_index ?? state.entities.find((e) => e.id === order.actions[0]?.entity_id)?.team_id ?? 0;
    const reviewed = validator.validateOrder(order, order.player_id, turnNumber, state, team);
    if (!reviewed.valid)
      throw new Error(`Invalid simulation order: ${reviewed.errors.join(", ")}`);
    return reviewed.executable_order ?? order;
  });
  const actions = executable.flatMap((order) => order.actions).sort((a, b) => a.entity_id - b.entity_id || (a.action_type < b.action_type ? -1 : a.action_type > b.action_type ? 1 : 0));
  for (const e of state.entities)
    e.elements = {
      ...actions.find((a) => a.entity_id === e.id)?.params.elements ?? EMPTY_ELEMENTS
    };
  const originalStats = new Map(state.entities.map((e) => [e.id, { ...e.stats }]));
  const events = resolveAbilities(cfg, state, actions, rng), dueledPairs = new Set, consumedThrows = new Set;
  const flights = [];
  const knockedAtStart = new Set(state.entities.filter((e) => e.status.knocked_down).map((e) => e.id));
  const carrier = state.entities.find((e) => e.id === state.ball.holder_entity_id);
  if (carrier && (carrier.hp <= 0 || carrier.status.knocked_down)) {
    carrier.status.carrying_ball = false;
    state.ball = {
      position: { ...carrier.position },
      holder_entity_id: null,
      in_flight: false
    };
    events.push({
      tick: 0,
      type: "ball_drop",
      actor: carrier.id,
      params: { position: { ...carrier.position } }
    });
  }
  const movements = setupMovements(cfg, state, actions, cfg.pitch.hex_size);
  const warnedReceptionTeams = new Set;
  const warnedPickups = new Set;
  const context = {
    throwResolver: behavior.throwResolver,
    cfg,
    state,
    actions,
    rng,
    seed,
    events,
    movements,
    knockedAtStart,
    dueledPairs,
    consumedThrows,
    flights,
    onBlockedReception: onWarning ? (entityId) => {
      const team = state.entities.find((e) => e.id === entityId).team_id;
      if (warnedReceptionTeams.has(team))
        return;
      warnedReceptionTeams.add(team);
      onWarning({ code: "RECEPTION_REQUIRES_FEU", entity_id: entityId });
    } : undefined,
    onBlockedPickup: onWarning ? (entityId) => {
      if (!movements.has(entityId) || warnedPickups.has(entityId))
        return;
      warnedPickups.add(entityId);
      onWarning({ code: "PICKUP_REQUIRES_FEU", entity_id: entityId });
    } : undefined
  };
  for (let tick = 0;tick < cfg.tick_system.max_ticks_per_turn; tick++) {
    const outcome = executeTick(context, tick);
    if (outcome.goalScored || !outcome.workRemains)
      break;
  }
  publishMovementTests(context);
  if (state.ball.in_flight) {
    const f = flights.at(-1);
    state.ball.position = { ...f.target };
    state.ball.in_flight = false;
    events.push({
      tick: state.tick,
      type: "ball_land",
      params: { position: { ...f.target } }
    });
  }
  const preciseBeforeSettlement = new Map(state.entities.map((e) => [e.id, { ...e.precise_position }]));
  finalizePositions(state, movements, cfg.pitch.hex_size);
  const settling = state.entities.filter((e) => {
    const from = preciseBeforeSettlement.get(e.id);
    return from.q !== e.position.q * SCALE || from.r !== e.position.r * SCALE;
  });
  if (settling.length) {
    state.tick++;
    for (const e of settling)
      events.push({
        tick: state.tick,
        type: "move",
        actor: e.id,
        params: {
          position: { ...e.position },
          precise_position: {
            q: e.position.q * SCALE,
            r: e.position.r * SCALE,
            scale: SCALE
          },
          start_position: preciseBeforeSettlement.get(e.id),
          end_position: { q: e.position.q * SCALE, r: e.position.r * SCALE },
          settlement: true
        }
      });
  }
  for (const e of state.entities) {
    e.stats = originalStats.get(e.id);
    delete e.range_bonus;
    delete e.attack_bonus;
    delete e.power_locked;
  }
  const final_entity_states = state.entities.map((e) => ({
    ...e.ability_uses_remaining !== undefined ? { ability_uses_remaining: e.ability_uses_remaining } : {},
    ...e.zobal_mask !== undefined ? { zobal_mask: e.zobal_mask } : {},
    entity_id: e.id,
    position: { ...e.position },
    hp: e.hp,
    max_hp: e.max_hp,
    status: { ...e.status },
    is_ko: e.status.knocked_down,
    is_eliminated: e.hp <= 0
  }));
  const final_ball_state = structuredClone(state.ball);
  events.push({
    tick: state.tick,
    type: "final_state",
    actor: -1,
    params: { final_entity_states, final_ball_state }
  });
  const score = [0, 0];
  for (const e of events)
    if (e.type === "goal")
      score[e.params.team]++;
  return {
    turn_number: turnNumber,
    seed,
    tick_duration: cfg.tick_system.tick_dt_seconds,
    initial_state_hash: initialHash,
    events,
    final_state_hash: hashWorldState(state),
    protocol_version: VERSION.PROTOCOL,
    simulation_version: behavior.version,
    timestamp: 0,
    final_entity_states,
    final_ball_state,
    final_world_state: state,
    score
  };
}

// ../../boufbowl_server/src/ai.ts
var DEFAULT_AI = {
  default_personality: "balanced",
  default_level: "normal",
  personalities: {
    balanced: { progress: 20, risk: 18, aggression: 16, spacing: 30, passing: 24, defense: 15 },
    bruiser: { progress: 16, risk: 5, aggression: 32, spacing: 20, passing: 8, defense: 8 },
    playmaker: { progress: 18, risk: 22, aggression: 8, spacing: 35, passing: 40, defense: 12 },
    guardian: { progress: 12, risk: 28, aggression: 16, spacing: 30, passing: 20, defense: 30 }
  },
  levels: {
    beginner: { search_radius: 5, threat_radius: 1, pass_min_gain: 4, passes: false, abilities: false },
    normal: { search_radius: 10, threat_radius: 2, pass_min_gain: 2, passes: true, abilities: false },
    expert: { search_radius: 14, threat_radius: 3, pass_min_gain: 1, passes: true, abilities: true }
  }
};
function resolveAISettings(config, value = {}) {
  const rules = config.ai ?? DEFAULT_AI;
  const personality = value.personality ?? rules.default_personality;
  const level = value.level ?? rules.default_level;
  if (!Object.hasOwn(rules.personalities, personality) || !Object.hasOwn(rules.levels, level))
    throw new Error("Unknown CPU personality or level");
  return { personality, level };
}
var active2 = (e) => e.hp > 0 && !e.status.knocked_down && !e.status.stunned;
var column = (p) => p.q + Math.floor(p.r / 2);

class OpponentAI {
  config;
  settings;
  constructor(config, settings = {}) {
    this.config = config;
    this.settings = resolveAISettings(config, settings);
  }
  buildOrder(playerId, turnNumber, teamIndex, world) {
    const cfg = this.config, ai = cfg.ai ?? DEFAULT_AI;
    const bounds = pitchBounds(cfg.pitch);
    const personality = ai.personalities[this.settings.personality], level = ai.levels[this.settings.level];
    const team = world.entities.filter((e) => e.team_id === teamIndex).sort((a, b) => a.id - b.id);
    const enemies = world.entities.filter((e) => e.team_id !== teamIndex && active2(e)).sort((a, b) => a.id - b.id);
    const available = team.filter(active2), direction = teamIndex === 0 !== (world.sides_swapped ?? false) ? 1 : -1;
    const ownCarrier = available.find((e) => e.id === world.ball.holder_entity_id);
    const enemyCarrier = enemies.find((e) => e.id === world.ball.holder_entity_id);
    const nearest = [...available].sort((a, b) => hexDistance(a.position, world.ball.position) - hexDistance(b.position, world.ball.position) || a.id - b.id);
    const defenders = [...available].sort((a, b) => hexDistance(a.position, enemyCarrier?.position ?? world.ball.position) - hexDistance(b.position, enemyCarrier?.position ?? world.ball.position) || a.id - b.id).slice(0, personality.aggression >= 25 ? 2 : 1);
    const threat = (point) => enemies.reduce((n, e) => n + Math.max(0, level.threat_radius + 1 - hexDistance(point, e.position)) * (e.stats.strength + 5), 0);
    let receiver;
    if (ownCarrier && level.passes) {
      const allocation = { TERRE: 0, FEU: 1, AIR: 1, EAU: 1 };
      let best = 0;
      for (const candidate of available) {
        const distance = hexDistance(ownCarrier.position, candidate.position);
        const gain = direction * (column(candidate.position) - column(ownCarrier.position));
        if (candidate.id === ownCarrier.id || gain < level.pass_min_gain || distance > maxThrowRange(cfg, allocation))
          continue;
        const score = gain * personality.passing + candidate.stats.precision * 2 - distance * 8 - Math.trunc(threat(candidate.position) * personality.risk / 10);
        if (score > best) {
          best = score;
          receiver = candidate;
        }
      }
    }
    const actions = [], reserved = [];
    for (const entity of team) {
      if (!active2(entity)) {
        actions.push({ entity_id: entity.id, action_type: "wait", params: { elements: defaultElements() } });
        continue;
      }
      const ability = cfg.abilities?.[entity.class_name];
      if (level.abilities && ability && ability.heal > 0 && entity.hp * 2 <= entity.max_hp && (entity.ability_uses_remaining ?? 0) > 0) {
        actions.push({ entity_id: entity.id, action_type: "ability", params: { elements: { TERRE: 0, FEU: 0, AIR: 0, EAU: 0 } } });
        continue;
      }
      if (receiver?.id === entity.id) {
        actions.push({ entity_id: entity.id, action_type: "wait", params: { elements: { TERRE: 0, FEU: 2, AIR: 0, EAU: 1 } } });
        reserved.push(entity.position);
        continue;
      }
      const isCarrier = entity.id === ownCarrier?.id, pursuer = enemyCarrier && defenders.some((e) => e.id === entity.id);
      const elements = pursuer ? { TERRE: 2, FEU: 0, AIR: 0, EAU: 1 } : isCarrier && receiver ? { TERRE: 0, FEU: 1, AIR: 1, EAU: 1 } : { TERRE: 0, FEU: 1, AIR: 0, EAU: 2 };
      if (pursuer) {
        actions.push({ entity_id: entity.id, action_type: "follow", params: { target_entity_id: enemyCarrier.id, elements } });
        continue;
      }
      const role = available.indexOf(entity);
      let target;
      if (isCarrier)
        target = { q: (direction > 0 ? bounds.maxColumn : bounds.minColumn) - Math.floor(entity.position.r / 2), r: entity.position.r };
      else if (!ownCarrier && nearest[0]?.id === entity.id)
        target = world.ball.position;
      else {
        const lane = Math.min(bounds.maxRow, 2 + role % 2 * 2) * (role % 2 ? 1 : -1);
        const focus = ownCarrier?.position ?? enemyCarrier?.position ?? world.ball.position;
        const forward = ownCarrier ? 4 : personality.defense >= 25 ? -4 : role % 3 === 2 ? -4 : 2;
        const col = Math.max(bounds.minColumn, Math.min(bounds.maxColumn, column(focus) + direction * forward));
        target = { q: col - Math.floor(lane / 2), r: lane };
      }
      let best = entity.position, bestScore = -Infinity;
      const budget = Math.min(level.search_radius, Math.floor(maxMovementDistance(cfg, elements)));
      for (let dq = -budget;dq <= budget; dq++)
        for (let dr = -budget;dr <= budget; dr++) {
          const point = { q: entity.position.q + dq, r: entity.position.r + dr };
          if (hexDistance(entity.position, point) > budget || !isInBounds(point, cfg.pitch))
            continue;
          const crowd = reserved.reduce((n, p) => n + Math.max(0, 3 - hexDistance(point, p)), 0);
          const score = -hexDistance(point, target) * personality.progress - crowd * personality.spacing - (isCarrier ? Math.trunc(threat(point) * personality.risk / 10) : 0) - hexDistance(entity.position, point);
          if (score > bestScore) {
            best = point;
            bestScore = score;
          }
        }
      reserved.push(best);
      actions.push({ entity_id: entity.id, action_type: "move", params: { target_position: best, elements } });
      if (isCarrier && receiver)
        actions.push({ entity_id: entity.id, action_type: "throw", params: { target_entity_id: receiver.id, elements } });
    }
    return { player_id: playerId, turn_number: turnNumber, team_index: teamIndex, nonce: `ai-${teamIndex}-${turnNumber}`, actions };
  }
}

// backend/cpu-orders.ts
const directions = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]], cpuDistance = (a, b) => Math.max(Math.abs(a.q - b.q), Math.abs(a.r - b.r), Math.abs(a.q + a.r - b.q - b.r)), cpuColumn = (p) => p.q + p.r / 2, cpuActive = (e) => e.hp > 0 && !e.status.knocked_down && !e.status.stunned, cpuCellKey = (p) => `${p.q},${p.r}`;
function cpuRound(p) {
  let q = Math.round(p.q), r = Math.round(p.r), s = Math.round(-p.q - p.r);
  const dq = Math.abs(q - p.q), dr = Math.abs(r - p.r), ds = Math.abs(s + p.q + p.r);
  if (dq > dr && dq > ds)
    q = -r - s;
  else if (dr > ds)
    r = -q - s;
  return { q, r };
}
function cpuPlanningConfig(cfg) {
  return cfg;
}
function prepareCPUOrder(cfg, world, order, settings = {}) {
  if (!cfg.client_ranges || cfg.movement.overextension === void 0) {
    const receivers = new Set(order.actions.filter((a) => a.action_type === "throw").map((a) => a.params.target_entity_id));
    for (const action of order.actions)
      if (action.action_type === "wait" && receivers.has(action.entity_id))
        action.params.elements = { TERRE: 0, FEU: 0, AIR: 2, EAU: 1 };
    return order;
  }
  const ai = cfg.ai, levelName = settings.level ?? ai.default_level, personalityName = settings.personality ?? ai.default_personality, level = ai.levels[levelName], personality = ai.personalities[personalityName], team = world.entities.filter((e) => e.team_id === order.team_index).sort((a, b) => a.id - b.id), available = team.filter(cpuActive), enemies = world.entities.filter((e) => e.team_id !== order.team_index && cpuActive(e)).sort((a, b) => a.id - b.id), direction = order.team_index === 0 !== Boolean(world.sides_swapped) ? 1 : -1, goal = cfg.ball.goal_line_half_width ?? 15.5, dt = cfg.tick_system.tick_dt_seconds, slots = cfg.general.actions_per_character, allocation = (names) => {
    const e = { TERRE: 0, FEU: 0, AIR: 0, EAU: 0 };
    for (let i = 0;i < slots; i++)
      e[names[Math.min(i, names.length - 1)]]++;
    return e;
  }, water = allocation(["EAU"]), runner = allocation(["FEU", "EAU", "EAU"]), receive = allocation(["AIR", "EAU", "EAU"]), accurate = allocation(["AIR", "AIR", "EAU"]), brute = allocation(["TERRE", "TERRE", "EAU"]), evade = allocation(["FEU", "FEU", "EAU"]), intercept = allocation(["FEU", "FEU", "EAU"]), width = cfg.pitch.width ?? 2 * cfg.pitch.width_half + 1, height = cfg.pitch.height ?? 2 * cfg.pitch.height_half + 1, minColumn = -Math.floor(width / 2), minRow = -Math.floor(height / 2), inBounds = (p) => p.r >= minRow && p.r < minRow + height && p.q + Math.floor(p.r / 2) >= minColumn && p.q + Math.floor(p.r / 2) < minColumn + width, at = (x, r) => cpuRound({ q: x - r / 2, r }), forward = (p) => direction * cpuColumn(p), safeRange = (e) => e.TERRE * cfg.client_ranges.earth_distance_bonus + e.FEU * cfg.client_ranges.fire_distance_bonus + e.AIR * cfg.client_ranges.air_distance_bonus + e.EAU * cfg.client_ranges.water_distance_bonus, speed = (actor, e) => Math.max(0.1, cfg.movement.base_speed_cells_per_sec + actor.stats.endurance * cfg.movement.speed_per_endurance + e.EAU * cfg.movement.eau_speed_bonus_per_action + e.AIR * cfg.movement.air_speed_bonus_per_action - e.TERRE * cfg.movement.terre_speed_penalty_per_action), probability = (p) => Math.max(cfg.simulation.probability_min, Math.min(cfg.simulation.probability_max, p)), used = new Map, roles = [], protectedIds = new Set, reserved = new Set, paths = new Map;
  function pathsFor(actor) {
    if (paths.has(actor.id))
      return paths.get(actor.id);
    const maximum = Math.floor(Math.max(safeRange(water), safeRange(receive), safeRange(brute), safeRange(evade)) * cfg.client_ranges.max_distance_factor), occupied = new Set(world.entities.filter((e) => e.hp > 0 && e.id !== actor.id).map((e) => cpuCellKey(e.position))), result = [];
    for (let dq = -maximum;dq <= maximum; dq++)
      for (let dr = -maximum;dr <= maximum; dr++) {
        const target = { q: actor.position.q + dq, r: actor.position.r + dr };
        if (!inBounds(target) || cpuDistance(actor.position, target) > maximum || occupied.has(cpuCellKey(target)))
          continue;
        const path = [actor.position];
        let current = actor.position;
        while (cpuDistance(current, target) > 0 && path.length <= maximum) {
          const next = directions.map(([q, r]) => ({ q: current.q + q, r: current.r + r })).find((p) => inBounds(p) && !occupied.has(cpuCellKey(p)) && cpuDistance(p, target) < cpuDistance(current, target));
          if (!next)
            break;
          path.push(next);
          current = next;
        }
        if (cpuDistance(current, target) === 0)
          result.push({ target, path });
      }
    paths.set(actor.id, result);
    return result;
  }
  function runs(actor, elements) {
    const safe = safeRange(elements), maximum = safe * cfg.client_ranges.max_distance_factor, budget = Math.min(Math.floor(maximum), levelName === "beginner" ? level.search_radius : Math.floor(maximum)), rule = cfg.movement.overextension;
    return pathsFor(actor).filter((p) => p.path.length - 1 <= budget).map((p) => {
      const d = Math.max(...p.path.map((c) => cpuDistance(actor.position, c))), ratio = maximum > safe ? Math.max(0, Math.min(1, (d - safe) / (maximum - safe))) : 0, risk = rule.enabled && d > safe && maximum > safe ? rule.fall_probability_at_max * Math.pow(ratio, rule.exponent) : 0;
      return { actor, target: p.target, elements, path: p.path, speed: speed(actor, elements), risk };
    });
  }
  function position(run, seconds) {
    const traveled = Math.max(0, Math.min(run.path.length - 1, seconds * run.speed)), index = Math.min(run.path.length - 1, Math.floor(traveled)), a = run.path[index], b = run.path[Math.min(index + 1, run.path.length - 1)];
    return { q: a.q + (b.q - a.q) * (traveled - index), r: a.r + (b.r - a.r) * (traveled - index) };
  }
  function stand(actor, elements) {
    return { actor, target: actor.position, path: [actor.position], elements, speed: speed(actor, elements), risk: 0 };
  }
  function combatLoss(actor, elements, enemy) {
    const own = actor.stats.strength + elements.TERRE * cfg.actions.element_effects.terre.attack_bonus_per, opposing = enemy.stats.strength + cfg.actions.element_effects.terre.attack_bonus_per, damage = cfg.combat.duel.damage_on_win + 1;
    if (own > opposing)
      return 0.025;
    if (own === opposing)
      return actor.hp <= cfg.combat.duel.damage_on_tie + 1 ? 0.95 : 0.06;
    if (elements.FEU > 1 && actor.stats.agility >= enemy.stats.agility)
      return 0.08;
    if (actor.hp <= damage)
      return 0.98;
    return Math.min(0.99, Math.min(0.95, cfg.simulation.fall_base + (opposing - own) * cfg.simulation.fall_per_power) + 0.08 * (1 - actor.hp / actor.max_hp));
  }
  function survival(run, fromSeconds = 0, toSeconds = 1 / 0) {
    let result = 1 - run.risk;
    for (const enemy of enemies)
      if (run.path.some((p, i) => i / run.speed >= fromSeconds && i / run.speed <= toSeconds && cpuDistance(i === 0 ? position(run, dt) : p, enemy.position) <= cfg.combat.trigger_distance_cells + 0.05))
        result *= 1 - combatLoss(run.actor, run.elements, enemy);
    return result;
  }
  function pressure(actor, elements, p) {
    return enemies.reduce((sum, e) => sum + Math.max(0, 4 - cpuDistance(e.position, p)) * (0.12 + combatLoss(actor, elements, e)), 0);
  }
  const crowd = (p) => [...used.values()].reduce((n, r) => n + Math.max(0, 3 - cpuDistance(p, r.target)), 0);
  function terminal(run, origin, fromSeconds = 0) {
    const gain = forward(run.target) - forward(origin), scoring = forward(run.target) > goal, value = 36 + gain * 3.5 * personality.progress / 20 + (scoring ? 100 : 0) - pressure(run.actor, run.elements, run.target) * 6;
    return survival(run, fromSeconds) * value - 36 - (run.path.length - 1) * 0.035 - run.risk * 12 * (personality.risk / 18 - 1);
  }
  function select(actor, allocations, score) {
    let best = stand(actor, allocations[0]), value = -1 / 0;
    for (const e of allocations)
      for (const run of runs(actor, e)) {
        if (reserved.has(cpuCellKey(run.target)))
          continue;
        const v = score(run);
        if (v > value + 0.00000001) {
          best = run;
          value = v;
        }
      }
    return best;
  }
  function assign(run, role, protect = !1) {
    used.set(run.actor.id, run);
    reserved.add(cpuCellKey(run.target));
    roles.push({ entity_id: run.actor.id, role, movement_risk: run.risk });
    if (protect)
      protectedIds.add(run.actor.id);
  }
  const carrier = available.find((e) => e.id === world.ball.holder_entity_id), enemyCarrier = enemies.find((e) => e.id === world.ball.holder_entity_id);
  let strategy = "recover", pass = null;
  function projectPass(thrower, receiver) {
    const range = cfg.ball.base_range + thrower.elements.AIR * cfg.actions.element_effects.air.range_modifier, ballStep = cfg.ball.throw_speed_cells_per_sec * dt;
    for (let release = cfg.simulation.throw_delay_ticks;release < cfg.tick_system.max_ticks_per_turn; release++) {
      const origin = position(thrower, (release + 1) * dt);
      if (forward(origin) > goal && forward(cpuRound(origin)) > goal)
        return null;
      let landing, duration = 0;
      const latest = Math.ceil((cpuDistance(origin, receiver.actor.position) + receiver.path.length + 1) / ballStep);
      for (let ticks = 1;ticks <= latest; ticks++) {
        const target = cpuRound(position(receiver, (release + ticks + 1) * dt));
        if (cpuDistance(origin, target) <= ballStep * ticks) {
          landing = target;
          duration = ticks;
          break;
        }
      }
      if (!landing || cpuDistance(origin, landing) > range)
        continue;
      if (release + duration >= cfg.tick_system.max_ticks_per_turn)
        return null;
      const d = cpuDistance(origin, landing), accuracy = probability(cfg.simulation.throw_base + thrower.actor.stats.precision * cfg.simulation.throw_stat + thrower.elements.AIR * cfg.probabilities.air_precision_per_action - d * cfg.simulation.distance_penalty);
      let windows = 0, laneSurvival = 1;
      const lowSamples = [];
      for (let t = 1;t <= duration; t++) {
        if (4 * cfg.ball.arc_height_cells * t * (duration - t) / (duration * duration) > cfg.ball.intercept_height_threshold)
          continue;
        const p = { q: origin.q + (landing.q - origin.q) * t / duration, r: origin.r + (landing.r - origin.r) * t / duration }, time = (release + t + 1) * dt;
        lowSamples.push({ p, time });
        if (cpuDistance(position(receiver, time), p) <= cfg.ball.catch_radius_cells)
          windows++;
      }
      for (const enemy of enemies) {
        let threat = 0;
        for (const { p, time } of lowSamples) {
          const distance = cpuDistance(enemy.position, p), reach = Math.min(safeRange(intercept), speed(enemy, intercept) * time);
          if (distance > reach + cfg.ball.intercept_radius_cells)
            continue;
          const confidence = distance <= cfg.ball.intercept_radius_cells ? 1 : 0.35 * Math.max(0, 1 - (distance - cfg.ball.intercept_radius_cells) / (reach + 0.01)), interceptionStat = cfg.ball.interception_uses_fire_stat ? enemy.stats.agility : enemy.stats.precision;
          threat = Math.max(threat, confidence * probability(cfg.simulation.catch_base + interceptionStat * cfg.simulation.catch_stat + cfg.simulation.catch_feu));
        }
        laneSurvival *= 1 - threat;
      }
      const catchChance = probability(cfg.simulation.catch_base + receiver.actor.stats.precision * cfg.simulation.catch_stat + receiver.elements.AIR * cfg.simulation.catch_air), catches = 1 - Math.pow(1 - catchChance, Math.min(receiver.elements.AIR, windows)), arrival = (release + duration + 1) * dt, chance = accuracy * catches * laneSurvival * survival(thrower, 0, (release + 1) * dt);
      return { release_tick: release, land_tick: release + duration, landing, chance, arrival };
    }
    return null;
  }
  if (carrier) {
    strategy = "carry";
    const carry = select(carrier, [water, brute, evade], (r) => terminal(r, carrier.position));
    let chosen = carry, best = terminal(carry, carrier.position), chosenReceiver = null;
    if (level.passes && slots > 0) {
      const launches = [receive, accurate].flatMap((e) => {
        const candidates = runs(carrier, e).sort((a, b) => terminal(b, carrier.position) - terminal(a, carrier.position));
        return [stand(carrier, e), ...candidates.slice(0, 3)];
      });
      for (const receiver of available.filter((e) => e.id !== carrier.id)) {
        const receptionRuns = [receive, accurate].flatMap((e) => runs(receiver, e).sort((a, b) => terminal(b, carrier.position) - terminal(a, carrier.position)).slice(0, 4));
        for (const e of [receive, accurate])
          for (const gain of [0, 3, 6]) {
            const anchor = at(cpuColumn(receiver.position) + direction * gain, receiver.position.r);
            receptionRuns.push(select(receiver, [e], (r) => -cpuDistance(r.target, anchor) * 4 - r.risk * 35 - pressure(receiver, e, r.target) * 4));
          }
        receptionRuns.push(stand(receiver, allocation(["AIR", "AIR", "AIR"])));
        const towardsReceiver = [receive, accurate].map((e) => select(carrier, [e], (r) => -cpuDistance(r.target, receiver.position) * 3 - pressure(carrier, e, r.target) * 6 - r.risk * 40));
        for (const r of receptionRuns)
          for (const launch of [...launches, ...towardsReceiver]) {
            if (cpuDistance(launch.target, r.target) < 1)
              continue;
            const flight = projectPass(launch, r);
            if (!flight)
              continue;
            const value = flight.chance * (terminal(r, carrier.position, flight.arrival) + 36) - 36 - 1.5 + Math.max(0, personality.passing - 24) * 0.08;
            if (value > best + 0.5) {
              best = value;
              chosen = launch;
              chosenReceiver = r;
              pass = { ...flight, thrower: carrier.id, receiver: receiver.id };
            }
          }
      }
    }
    assign(chosen, "carrier", !0);
    if (chosenReceiver) {
      assign(chosenReceiver, "receiver", !0);
      strategy = "pass";
    } else if (forward(chosen.target) < forward(carrier.position) - 0.5)
      strategy = "retreat";
    else if (chosen.elements.TERRE > 0)
      strategy = "breakthrough";
    const focus = chosenReceiver?.target ?? chosen.target, support = available.filter((e) => !used.has(e.id)), screen = [...support].sort((a, b) => b.stats.strength + b.hp * 0.25 - cpuDistance(b.position, focus) - (a.stats.strength + a.hp * 0.25 - cpuDistance(a.position, focus)) || a.id - b.id)[0];
    if (screen) {
      const anchor = at(cpuColumn(focus) + direction * 1.5, focus.r + (focus.r > 0 ? -2 : 2));
      assign(select(screen, [brute], (r) => -cpuDistance(r.target, anchor) * 3 - r.risk * 30 - crowd(r.target) * 5), "screen");
    }
    const rest = support.filter((e) => e.id !== screen?.id).sort((a, b) => b.stats.precision + b.stats.endurance - a.stats.precision - a.stats.endurance || a.id - b.id);
    for (const [i, actor] of rest.entries()) {
      const cover = i === rest.length - 1 && rest.length > 1, row = cover ? focus.r / 2 : Math.max(-8, Math.min(8, focus.r + (i % 2 === 0 ? -4 : 4))), anchor = at(cpuColumn(focus) + direction * (cover ? -5 : 1), row);
      assign(select(actor, [cover ? runner : receive], (r) => -cpuDistance(r.target, anchor) * 3 - r.risk * 30 - pressure(actor, r.elements, r.target) * 2 - crowd(r.target) * 6), cover ? "cover" : "parallel_support");
    }
  } else if (enemyCarrier) {
    strategy = "defend";
    const press = [...available].sort((a, b) => {
      const suitability = (e) => e.stats.strength * 0.9 + e.stats.agility * 0.1 + e.hp * 0.2 - e.stats.precision * 0.25 - cpuDistance(e.position, enemyCarrier.position) * 1.4;
      return suitability(b) - suitability(a) || a.id - b.id;
    })[0];
    if (press) {
      const enemyGoal = -direction * goal, anchor = at(cpuColumn(enemyCarrier.position) - direction * 2, enemyCarrier.position.r);
      assign(select(press, [allocation(["TERRE", "TERRE", "FEU"]), allocation(["TERRE", "FEU", "EAU"]), evade], (r) => -cpuDistance(r.target, anchor) * 3 + (cpuDistance(r.target, enemyCarrier.position) <= 1 ? 10 * (1 - combatLoss(press, r.elements, enemyCarrier)) : 0) - r.risk * 24 - (Math.abs(cpuColumn(enemyCarrier.position) - enemyGoal) < 4 ? r.risk * -15 : 0)), "pressure", !0);
    }
    const options = [];
    for (const receiver of enemies.filter((e) => e.id !== enemyCarrier.id)) {
      const gain = -direction * (cpuColumn(receiver.position) - cpuColumn(enemyCarrier.position)), d = cpuDistance(enemyCarrier.position, receiver.position);
      if (d > cfg.ball.base_range + 2 * cfg.actions.element_effects.air.range_modifier || d < 2)
        continue;
      const value = 6 + Math.max(0, gain) * 2 + receiver.stats.precision * 0.25, ticks = Math.max(1, Math.ceil(d / (cfg.ball.throw_speed_cells_per_sec * dt)));
      for (let t = 1;t <= ticks; t++) {
        if (4 * cfg.ball.arc_height_cells * t * (ticks - t) / (ticks * ticks) > cfg.ball.intercept_height_threshold)
          continue;
        const p = {
          q: enemyCarrier.position.q + (receiver.position.q - enemyCarrier.position.q) * t / ticks,
          r: enemyCarrier.position.r + (receiver.position.r - enemyCarrier.position.r) * t / ticks
        };
        options.push({ p, time: (cfg.simulation.throw_delay_ticks + t + 1) * dt, value, receiver: receiver.id });
      }
    }
    const remaining = available.filter((e) => !used.has(e.id));
    while (options.length && remaining.length > 1) {
      let best = null;
      for (const actor of remaining)
        for (const run of runs(actor, intercept)) {
          if (reserved.has(cpuCellKey(run.target)))
            continue;
          for (const option of options) {
            if (cpuDistance(position(run, option.time), option.p) > cfg.ball.intercept_radius_cells)
              continue;
            const catchChance = probability(cfg.simulation.catch_base + actor.stats.precision * cfg.simulation.catch_stat + intercept.FEU * cfg.simulation.catch_feu), score = option.value * catchChance - cpuDistance(run.target, option.p) * 2 - run.risk * 25 - crowd(run.target) * 5;
            if (!best || score > best.score)
              best = { actor, run, option, score };
          }
        }
      if (!best || best.score < 3)
        break;
      assign(best.run, "pass_interceptor", !0);
      remaining.splice(remaining.indexOf(best.actor), 1);
      for (let i = options.length - 1;i >= 0; i--)
        if (options[i].receiver === best.option.receiver)
          options.splice(i, 1);
    }
    for (const [i, actor] of remaining.entries()) {
      const anchor = at(cpuColumn(enemyCarrier.position) - direction * (4 + i * 2), i % 2 === 0 ? -3 : 3);
      assign(select(actor, [runner, intercept], (r) => -cpuDistance(r.target, anchor) * 3 - r.risk * 28 - crowd(r.target) * 6), "cover");
    }
  } else if (available.length) {
    let collection = null;
    for (const actor of available)
      for (const e of [runner, evade, receive])
        for (const run of runs(actor, e)) {
          const gap = cpuDistance(run.target, world.ball.position), attempts = e.FEU + e.AIR, chance = 1 - Math.pow(1 - probability(cfg.simulation.catch_base + actor.stats.precision * cfg.simulation.catch_stat + e.AIR * cfg.simulation.catch_air + e.FEU * cfg.simulation.catch_feu), attempts), value = (gap <= cfg.ball.pickup_range ? 40 * chance : 0) - gap * 4 - (run.path.length - 1) / run.speed * 2 - run.risk * 32 - pressure(actor, e, run.target) * 3;
          if (!collection || value > collection.value)
            collection = { run, value };
        }
    if (collection)
      assign(collection.run, "retriever", !0);
    const focus = world.ball.position, rest = available.filter((e) => !used.has(e.id)).sort((a, b) => b.stats.precision + b.stats.endurance - a.stats.precision - a.stats.endurance || a.id - b.id);
    for (const [i, actor] of rest.entries()) {
      const cover = i === rest.length - 1 && rest.length > 1, anchor = at(cpuColumn(focus) + direction * (cover ? -5 : i === 0 ? 5 : 3), cover ? 0 : i % 2 === 0 ? -3 : 4);
      assign(select(actor, i === 0 ? [water, receive] : [receive], (r) => -cpuDistance(r.target, anchor) * 3 - r.risk * 28 - crowd(r.target) * 6 - pressure(actor, r.elements, r.target) * 2 - (r.elements.AIR + r.elements.FEU === 0 && r.path.some((p) => cpuDistance(p, focus) <= cfg.ball.pickup_range) ? 25 : 0)), cover ? "cover" : i === 0 ? "forward_outlet" : "recovery_support");
    }
  }
  const actions = [];
  for (const actor of team) {
    const run = used.get(actor.id);
    if (!run) {
      actions.push({ entity_id: actor.id, action_type: "wait", params: { elements: { ...water } } });
      continue;
    }
    const moving = cpuDistance(actor.position, run.target) > 0;
    actions.push({ entity_id: actor.id, action_type: moving ? "move" : "wait", params: { elements: { ...run.elements }, ...moving ? { target_position: run.target } : {} } });
    if (pass?.thrower === actor.id)
      actions.push({ entity_id: actor.id, action_type: "throw", params: { elements: { ...run.elements }, target_entity_id: pass.receiver } });
  }
  return { ...order, actions, cpu_plan: {
    version: 2,
    strategy,
    roles,
    protected_ids: [...protectedIds],
    ...pass ? { pass: {
      thrower: pass.thrower,
      receiver: pass.receiver,
      release_tick: pass.release_tick,
      land_tick: pass.land_tick,
      landing: pass.landing,
      estimated_success: pass.chance
    } } : {}
  } };
}

// backend/cpu-powers.ts
function addCPUPower(cfg, world, order, level) {
  if (level === "beginner" || !Object.values(cfg.abilities ?? {}).some((r) => r.target))
    return order;
  const active = (e) => e.hp > 0 && !e.status.knocked_down && !e.status.stunned, allies = world.entities.filter((e) => e.team_id === order.team_index && active(e)), enemies = world.entities.filter((e) => e.team_id !== order.team_index && active(e)), receivers = new Set(order.actions.filter((a) => a.action_type === "throw").map((a) => a.params.target_entity_id)), nearest = [...allies].sort((a, b) => hexDistance(a.position, world.ball.position) - hexDistance(b.position, world.ball.position) || a.id - b.id)[0], movements = new Map(order.actions.filter((a) => ["move", "follow"].includes(a.action_type)).map((a) => [a.entity_id, a])), moving = (e) => {
    const a = movements.get(e.id);
    return a && (a.action_type === "follow" || hexDistance(e.position, a.params.target_position) > 0);
  }, threatened = (e) => enemies.some((other) => hexDistance(e.position, other.position) <= 3);
  function value(rule, targets, hostile) {
    let score = 0;
    for (const target of targets) {
      if (rule.hp > 0)
        score += Math.min(rule.hp, target.max_hp - target.hp) * 2;
      if (rule.hp < 0)
        score += hostile ? Math.min(-rule.hp, target.hp) * 2 + (target.hp <= -rule.hp ? 6 : 0) : rule.hp * 2;
      if (rule.range)
        score += (hostile ? -rule.range : rule.range) * (hostile || moving(target) ? 1.5 : 0);
      if (rule.attack)
        score += (hostile ? -rule.attack : rule.attack) * (threatened(target) || hostile ? 1.5 : 0.25);
      for (const [element, amount] of Object.entries(rule.elements ?? {})) {
        const weight = element === "EAU" ? moving(target) ? 1 : 0.15 : element === "AIR" ? receivers.has(target.id) || world.ball.holder_entity_id === target.id ? 1 : 0.25 : threatened(target) ? 1 : 0.25;
        score += Number(amount) * weight * (hostile ? -1 : 1);
      }
    }
    return score;
  }
  const choices = [], protectedIds = new Set(order.cpu_plan?.protected_ids ?? []);
  for (const caster of allies) {
    const rule = cfg.abilities?.[caster.class_name];
    if (!rule?.target || (caster.ability_uses_remaining ?? 0) <= 0 || caster.id === world.ball.holder_entity_id || receivers.has(caster.id) || protectedIds.has(caster.id))
      continue;
    if (rule.redirect_enemy_heal)
      continue;
    if (world.ball.holder_entity_id === null && caster.id === nearest?.id && hexDistance(caster.position, world.ball.position) <= 3)
      continue;
    if (rule.target === "allies" && rule.hp < 0 && allies.some((e) => e.hp <= -rule.hp))
      continue;
    let score = rule.enemy_chance !== void 0 ? (1 - rule.enemy_chance) * value(rule, allies, !1) + rule.enemy_chance * value({ elements: rule.enemy_elements }, enemies, !0) : value(rule, rule.target === "enemies" ? enemies : allies, rule.target === "enemies");
    const params = {};
    if (rule.change_mask) {
      if (moving(caster) || order.turn_number % 4 !== 0)
        continue;
      params.zobal_mask = (caster.zobal_mask ?? 1) % 3 + 1;
      score = 2;
    }
    if (rule.target === "allies" && !rule.change_mask) {
      const ownBenefit = value({ ...rule, hp: 0 }, [caster], !1);
      score -= Math.max(0, ownBenefit) * (rule.enemy_chance === void 0 ? 1 : 1 - rule.enemy_chance);
    }
    score -= moving(caster) ? 1.5 : 0;
    if (score >= 2)
      choices.push({ caster, score, params });
  }
  choices.sort((a, b) => b.score - a.score || a.caster.id - b.caster.id);
  const selected = choices[0];
  if (!selected)
    return order;
  return {
    ...order,
    ...order.cpu_plan ? { cpu_plan: { ...order.cpu_plan, roles: order.cpu_plan.roles.map((r) => r.entity_id === selected.caster.id ? { ...r, role: "class_power" } : r) } } : {},
    actions: [
      ...order.actions.filter((a) => a.entity_id !== selected.caster.id && a.action_type !== "ability"),
      { entity_id: selected.caster.id, action_type: "ability", params: selected.params }
    ]
  };
}

// backend/engine.ts
import { readFileSync } from "fs";
import { createInterface } from "readline";
var base = JSON.parse(readFileSync(new URL("./engine_base.json", import.meta.url), "utf8"));
function merge(a, b) {
  const out = structuredClone(a);
  for (const [key, value] of Object.entries(b))
    out[key] = value && typeof value === "object" && !Array.isArray(value) ? merge(out[key] ?? {}, value) : structuredClone(value);
  return out;
}
if (process.env.BOUFBOWL_WORKER_HANDSHAKE === "1")
  process.stdout.write(JSON.stringify({ ready: true }) + `
`);
for await (const line of createInterface({ input: process.stdin })) {
  try {
    const request = JSON.parse(line);
    const cfg = merge(base, request.rules?.simulation ?? {});
    if (request.rules?.client_ranges)
      cfg.client_ranges = request.rules.client_ranges;
    if (request.rules?.abilities)
      cfg.abilities = request.rules.abilities;
    cfg.pitch.width_half = Math.floor(cfg.pitch.width / 2);
    cfg.pitch.height_half = Math.floor(cfg.pitch.height / 2);
    const orders = request.orders.map((order, team) => order ?? (request.cpu?.[team] ? new OpponentAI(cpuPlanningConfig(cfg), request.ai ?? {}).buildOrder(`cpu-${team}`, request.turn, team, request.world) : defaultOrder(`player-${team}`, request.turn, team, request.world.entities.filter((entity) => entity.team_id === team))));
    for (let team = 0; team < orders.length; team++) {
      if (request.cpu?.[team] && request.orders[team] == null) {
        orders[team] = prepareCPUOrder(cfg, request.world, orders[team], request.ai ?? {});
        orders[team] = addCPUPower(cfg, request.world, orders[team], request.ai?.level ?? cfg.ai?.default_level ?? "normal");
      }
    }
    const warnings = [];
    const result = simulateTurn4(cfg, request.world, orders[0], orders[1], request.turn, request.seed, (warning) => warnings.push(warning.code === "RECEPTION_REQUIRES_FEU" ? { ...warning, code: "RECEPTION_REQUIRES_AIR" } : warning));
    result.simulation_version += "+client-ball-2";
    result.simulation_version += "+goal-zones-1";
    if (cfg.ball.action_limited_attempts)
      result.simulation_version += "+ball-attempts-1";
    if (Object.values(cfg.abilities ?? {}).some((r) => r.target))
      result.simulation_version += "+class-powers-1";
    if (cfg.movement.overextension?.enabled)
      result.simulation_version += "+movement-risk-1";
    if (cfg.ball.interception_uses_fire_stat || cfg.ball.require_arrival_before_turn_end || cfg.ball.contact_cancels_pending_throw ||
        Object.values(cfg.abilities ?? {}).some(r => r.redirect_enemy_heal)) result.simulation_version += "+forum-semantics-2012-1";
    process.stdout.write(JSON.stringify({ ok: true, result, orders, warnings }) + `
`);
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(error) }) + `
`);
  }
}
