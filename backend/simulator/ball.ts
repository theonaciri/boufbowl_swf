import type {
  WorldState,
  Action,
  GameConfig,
  Event,
  BallFlight,
} from "../types";
import { hexDistance, hexRound } from "../hex";
import { canThrow, canPickup, throwInRange } from "../rules";
import type { DeterministicRNG } from "../rng";
import { fixed, fractional, withinRadius, distanceSquared, SCALE } from "./movement";
import type { MovementTable } from "./movement";
import { targetedThrow } from "./throwTarget";
import {rulebookPickupPenalty,rulebookThrowSpeed,rulebookOnFlightSegment,rulebookScatter,
  rollRulebookManeuver,failRulebookManeuver} from "boufbowl-rulebook";
const active = (e: WorldState["entities"][number]) =>
  e.hp > 0 && !e.status.knocked_down && !e.status.stunned && !(e as any).power_locked;
const point = (e: WorldState["entities"][number]) =>
  e.precise_position ?? fixed(e.position);
const clamp = (cfg: GameConfig, p: number) =>
  Math.max(
    cfg.simulation.probability_min,
    Math.min(cfg.simulation.probability_max, p),
  );
// Per-turn bookkeeping stays outside the persisted world/replay state.
interface Attempts { air: number; fire: number; lastTick: number }
const attemptBooks = new WeakMap<WorldState, Map<number, Attempts>>();
const throwDistances = new WeakMap<WorldState, Map<number, number>>();
const actionLimited = (cfg: GameConfig) => (cfg.ball as any).action_limited_attempts === true;
function usedAttempts(state: WorldState, id: number): Attempts {
  let book = attemptBooks.get(state);
  if (!book) { book = new Map(); attemptBooks.set(state, book); }
  let used = book.get(id);
  if (!used) { used = {air: 0, fire: 0, lastTick: -1}; book.set(id, used); }
  return used;
}
function remaining(state: WorldState, e: WorldState["entities"][number], kind: "air" | "fire"): number {
  return Math.max(0, (kind === "air" ? e.elements.AIR : e.elements.FEU) - usedAttempts(state,e.id)[kind]);
}
function attempt(state: WorldState, e: WorldState["entities"][number], tick: number, kind: "air" | "fire"): boolean {
  const used = usedAttempts(state,e.id);
  if (used.lastTick === tick || remaining(state,e,kind) <= 0) return false;
  used[kind]++; used.lastTick = tick;
  return true;
}
function groundCandidate(cfg: GameConfig, state: WorldState, e: WorldState["entities"][number]): boolean {
  return active(e) && withinRadius(point(e),fixed(state.ball.position),cfg.ball.pickup_range) &&
    (remaining(state,e,"air") > 0 || remaining(state,e,"fire") > 0);
}
export function hasPendingPickups(cfg: GameConfig, state: WorldState): boolean {
  return actionLimited(cfg) && !state.ball.in_flight && state.ball.holder_entity_id === null &&
    state.entities.some(e => groundCandidate(cfg,state,e));
}

export function resolveThrows(
  cfg: GameConfig,
  state: WorldState,
  actions: Action[],
  rng: DeterministicRNG,
  tick: number,
  consumed = new Set<number>(),
  movements?: MovementTable,
): { events: Event[]; flights: BallFlight[] } {
  const events: Event[] = [],
    flights: BallFlight[] = [];
  for (const action of actions) {
    if (
      action.action_type !== "throw" ||
      consumed.has(action.entity_id)
    )
      continue;
    const e = state.entities.find((e) => e.id === action.entity_id);
    if (
      !e ||
      !active(e) ||
      state.ball.holder_entity_id !== e.id ||
      !canThrow(e.elements)
    )
      continue;
    const targetEntity = state.entities.find(
      (e) => e.id === action.params.target_entity_id,
    );
    const start = fractional(point(e));
    const throwingCfg = {...cfg,ball:{...cfg.ball,throw_speed_cells_per_sec:rulebookThrowSpeed(cfg,e.elements)}};
    const predicted = targetEntity ? targetedThrow(throwingCfg, start, targetEntity, movements?.get(targetEntity.id)) : undefined;
    const target = predicted?.target ?? action.params.target_position;
    if (!target || !throwInRange({...cfg, ball: {...cfg.ball, base_range: cfg.ball.base_range + ((e as any).range_bonus ?? 0)}}, start, target, e.elements)) continue;
    const distance = hexDistance(start, target);
    const landTick = tick + (predicted?.flightTicks ?? Math.max(1, Math.ceil(
      distance / throwingCfg.ball.throw_speed_cells_per_sec / cfg.tick_system.tick_dt_seconds,
    )));
    let distances=throwDistances.get(state);
    if (!distances) {distances=new Map();throwDistances.set(state,distances);}
    const timingDistance=targetEntity ? hexDistance(start,fractional(point(targetEntity))) : distance;
    const previous=distances.get(e.id);distances.set(e.id,timingDistance);
    if (tick < cfg.simulation.throw_delay_ticks) continue;
    if ((cfg as any).rulebook?.passing?.favorable_timing && previous !== undefined && timingDistance < previous &&
        landTick+1 < cfg.tick_system.max_ticks_per_turn) continue;
    // M05: test scheduling before changing possession, consuming the order or
    // drawing randomness. The last executable tick is max_ticks_per_turn - 1.
    if ((cfg.ball as any).require_arrival_before_turn_end && landTick >= cfg.tick_system.max_ticks_per_turn) continue;
    consumed.add(e.id);
    e.status.carrying_ball = false;
    state.ball.holder_entity_id = null;
    state.ball.in_flight = true;
    const precision = clamp(
      cfg,
      cfg.simulation.throw_base +
        e.stats.precision * cfg.simulation.throw_stat +
        e.elements.AIR * cfg.probabilities.air_precision_per_action -
        distance * cfg.simulation.distance_penalty,
    );
    const test = rollRulebookManeuver(cfg,e,precision,rng,'throw');
    const success = test.success;
    const landing = hexRound(!success && (cfg as any).rulebook?.passing?.scatter_failures
      ? rulebookScatter(start,target,rng.nextFloat()) : target);
    events.push({
      tick,
      type: "throw",
      actor: e.id,
      params: {
        start_position: start,
        target_position: landing,
        target_entity_id: targetEntity?.id ?? null,
        success,
        precision:test.probability ?? precision,
        ...((cfg as any).rulebook?.maneuvers ? test : {}),
        land_tick: landTick,
        arc_height: cfg.ball.arc_height_cells,
      },
    });
    failRulebookManeuver(cfg,e,test,'throw',tick,events);
    flights.push({
      start: fixed(start),
      startTick: tick,
      thrower: e.id,
      success,
      attempted: [],
      target: landing,
      targetEntityId: targetEntity?.id ?? null,
      landTick,
    });
  }
  return { events, flights };
}
export function resolveReceptions(
  cfg: GameConfig,
  state: WorldState,
  rng: DeterministicRNG,
  tick: number,
  flights: BallFlight[],
  onBlockedReception?: (entityId: number) => void,
): Event[] {
  const events: Event[] = [];
  if (!state.ball.in_flight) return events;
  const f = flights.at(-1);
  if (!f || tick < f.startTick || tick > f.landTick) return events;
  const duration = f.landTick - f.startTick,
    elapsed = tick - f.startTick;
  const end = fixed(f.target);
  const pos = {
    q: f.start.q + Math.trunc(((end.q - f.start.q) * elapsed) / duration),
    r: f.start.r + Math.trunc(((end.r - f.start.r) * elapsed) / duration),
  };
  const height = Math.trunc(
    (4 *
      Math.round(cfg.ball.arc_height_cells * SCALE) *
      elapsed *
      (duration - elapsed)) /
      (duration * duration),
  );
  state.ball.position = hexRound(fractional(pos));
  events.push({
    tick,
    type: "ball_move",
    params: { position: fractional(pos), height: height / SCALE },
  });
  if (
    elapsed > 0 &&
    height <= Math.round(cfg.ball.intercept_height_threshold * SCALE) &&
    (f.success || actionLimited(cfg))
  ) {
    const thrower = state.entities.find((e) => e.id === f.thrower)!;
    const limited = actionLimited(cfg);
    const reachable = state.entities
      .filter(
        (e) =>
          active(e) &&
          e.id !== f.thrower &&
          (!(cfg as any).rulebook?.passing?.path_interception || e.id === f.targetEntityId ||
            rulebookOnFlightSegment(fractional(f.start),f.target,fractional(point(e)))) &&
          (!limited || e.id === f.targetEntityId || e.team_id !== thrower.team_id) &&
          withinRadius(
            point(e),
            pos,
            (limited ? e.id === f.targetEntityId : e.team_id === thrower.team_id)
              ? cfg.ball.catch_radius_cells
              : cfg.ball.intercept_radius_cells,
          ),
      )
      .sort(
        (a, b) =>
          distanceSquared(point(a), pos) - distanceSquared(point(b), pos) || a.id - b.id,
      );
    if (!limited && onBlockedReception && ((cfg.ball as any).reception_requires_air ?? true)) {
      // Check the whole reachable team, including previous failed attempts:
      // a missed random catch is not an element assignment mistake.
      const teams = new Set(reachable.map((e) => e.team_id));
      for (const team of teams) {
        const teammates = reachable.filter((e) => e.team_id === team);
        if (!teammates.some((e) => e.elements.AIR >= 1))
          onBlockedReception(teammates[0]!.id);
      }
    }
    const candidates = reachable.filter((e) => limited
      ? (e.id === f.targetEntityId ? f.success && remaining(state,e,"air") > 0 : remaining(state,e,"fire") > 0)
      : (!((cfg.ball as any).reception_requires_air ?? true) || e.elements.AIR >= 1) && !f.attempted.includes(e.id),
    );
    for (const e of candidates) {
      const intended = e.id === f.targetEntityId;
      const kind = intended ? "air" : "fire";
      if (limited && !attempt(state,e,tick,kind)) continue;
      f.attempted.push(e.id);
      // M05: Fire interception and Air reception use different characteristics.
      // Coefficients remain the recreation's provisional balance parameters.
      const stat = !intended && (cfg.ball as any).interception_uses_fire_stat ? e.stats.agility : e.stats.precision;
      const base = cfg.simulation.catch_base + stat * cfg.simulation.catch_stat;
      const bonus = intended ? e.elements.AIR * cfg.simulation.catch_air : e.elements.FEU * cfg.simulation.catch_feu;
      const chance = clamp(cfg, limited ? base + bonus
        : base + e.elements.FEU * cfg.simulation.catch_feu + e.elements.AIR * cfg.simulation.catch_air);
      const test = rollRulebookManeuver(cfg,e,chance,rng,intended ? 'reception' : 'interception');
      if (test.success) {
        e.status.carrying_ball = true;
        state.ball.holder_entity_id = e.id;
        state.ball.in_flight = false;
        state.ball.position = { ...e.position };
        let granted = 0;
        if (intended && (cfg as any).rulebook?.maneuvers) {
          granted = (cfg as any).rulebook.maneuvers.reception_throw_bonus *
            ({normal:1,wide:2,critical:3}[test.tier] ?? 1);
          (e as any).next_throw_bonus = granted;
        }
        events.push({
          tick,
          type: "catch",
          actor: e.id,
          params: { position: { ...e.position }, catch_chance: test.probability ?? chance,
            ...((cfg as any).rulebook?.maneuvers ? {...test,granted_throw_bonus:granted,maneuver_bonus_malus:granted || test.maneuver_bonus_malus} : {}),
            ...(limited ? {interception: !intended, attempt: usedAttempts(state,e.id)[kind], action: kind} : {}) },
        });
        return events;
      }
      events.push({
        tick,
        type: "catch_fail",
        actor: e.id,
        params: { position:{...e.position},catch_chance: test.probability ?? chance,
          ...((cfg as any).rulebook?.maneuvers ? test : {}),
          ...(limited ? {interception: !intended, attempt: usedAttempts(state,e.id)[kind], action: kind} : {}) },
      });
      failRulebookManeuver(cfg,e,test,intended ? 'reception' : 'interception',tick,events);
      if (intended && test.tier==='critical' && (cfg as any).rulebook?.maneuvers?.critical_failures) {
        // The original critical reception is a hit/fumble, not a retry with
        // possession. End this flight and publish its separate ground rebound.
        state.ball.in_flight=false;state.ball.holder_entity_id=null;
        state.ball.position=hexRound(rulebookScatter(e.position,f.target,rng.nextFloat()));
        events.push({tick,type:'ball_land',params:{position:{...state.ball.position},reason:'critical_reception'}});
        return events;
      }
    }
  }
  if (tick === f.landTick) {
    state.ball.in_flight = false;
    state.ball.position = (cfg as any).rulebook?.passing?.scatter_failures && f.attempted.includes(f.targetEntityId as number)
      ? hexRound(rulebookScatter(fractional(f.start),f.target,rng.nextFloat())) : {...f.target};
    events.push({
      tick,
      type: "ball_land",
      params: { position: { ...state.ball.position } },
    });
  }
  return events;
}
export function resolvePickups(
  cfg: GameConfig,
  state: WorldState,
  tick: number,
  onBlockedPickup?: (entityId: number) => void,
  rng?: DeterministicRNG,
): Event[] {
  if (state.ball.in_flight || state.ball.holder_entity_id !== null) return [];
  const candidates = state.entities
    .filter((e) => {
      if (!active(e) || !withinRadius(point(e), fixed(state.ball.position), cfg.ball.pickup_range))
        return false;
      if (!canPickup(cfg, e.elements)) {
        onBlockedPickup?.(e.id);
        return false;
      }
      return true;
    })
    .sort(
      (a, b) =>
        distanceSquared(point(a), fixed(state.ball.position)) -
          distanceSquared(point(b), fixed(state.ball.position)) || a.id - b.id,
    );
  if (actionLimited(cfg)) {
    const events: Event[] = [];
    for (const e of candidates) {
      // Use fire first on the ground, preserving air for an intended reception.
      const kind = remaining(state,e,"fire") > 0 ? "fire" : "air";
      if (!attempt(state,e,tick,kind)) continue;
      const pressure = rulebookPickupPenalty(cfg,state,e);
      const stat = (cfg as any).rulebook?.maneuvers && kind==='fire' ? e.stats.agility : e.stats.precision;
      const chance = clamp(cfg,cfg.simulation.catch_base + stat * cfg.simulation.catch_stat +
        e.elements.AIR * cfg.simulation.catch_air + e.elements.FEU * cfg.simulation.catch_feu - pressure.penalty);
      if (!rng) throw new Error("Pickup attempts require the turn RNG");
      const test = rollRulebookManeuver(cfg,e,chance,rng,kind==='fire' ? 'pickup_fire' : 'pickup');
      const success = test.success;
      events.push({tick, type: success ? "pickup" : "pickup_fail" as any, actor:e.id,
        params:{position:{...e.position}, pickup_chance:test.probability ?? chance, attempt:usedAttempts(state,e.id).air+usedAttempts(state,e.id).fire, action:kind,
          // Original FX uses the sign only. Report actual applied pressure,
          // expressed in percentage points, without adding a gameplay malus.
          maneuver_bonus_malus: test.maneuver_bonus_malus || (pressure.penalty > 0 ? -Math.ceil(pressure.penalty * 100) : 0),
          ...((cfg as any).rulebook?.maneuvers ? {...test,maneuver_bonus_malus:test.maneuver_bonus_malus || (pressure.penalty>0 ? -Math.ceil(pressure.penalty*100) : 0)} : {}),
          ...((cfg as any).rulebook ? {nearby_players:pressure.nearby,lost_combats:pressure.lost_combats} : {})}});
      failRulebookManeuver(cfg,e,test,'pickup',tick,events);
      if (success) {
        e.status.carrying_ball = true; state.ball.holder_entity_id = e.id;
        state.ball.position = {...e.position}; break;
      }
    }
    return events;
  }
  const e = candidates[0];
  if (!e) return [];
  e.status.carrying_ball = true;
  state.ball.holder_entity_id = e.id;
  state.ball.position = { ...e.position };
  return [
    {
      tick,
      type: "pickup",
      actor: e.id,
      params: { position: { ...e.position } },
    },
  ];
}
export function resolveGoals(
  cfg: GameConfig,
  state: WorldState,
  tick: number,
): Event[] {
  const e = state.entities.find((e) => e.id === state.ball.holder_entity_id);
  if (!e || !active(e)) return [];
  const p = point(e), x = 2 * p.q + p.r;
  // Client spacePoint.x = q + r/2. Its outer edge is +/-17.5;
  // crossing +/-15.5 enters the two-column end zone on either row parity.
  const goalLine = ((cfg.ball as any).goal_line_half_width ?? 15.5) * 2 * SCALE;
  // The replay settles onto a hex center. Do not score while its rounded
  // position is still on the line, even if the continuous position is past it.
  const cellX = (2 * e.position.q + e.position.r) * SCALE;
  const attacksRight = (e.team_id === 0) !== (state.sides_swapped ?? false);
  if (attacksRight ? x > goalLine && cellX > goalLine : x < -goalLine && cellX < -goalLine) {
    e.status.carrying_ball = false;
    state.ball.holder_entity_id = null;
    state.ball.in_flight = false;
    state.ball.position = { ...e.position };
    return [
      {
        tick,
        type: "goal",
        actor: e.id,
        params: { team: e.team_id, position: { ...e.position } },
      },
    ];
  }
  return [];
}
