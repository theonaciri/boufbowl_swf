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
const active = (e: WorldState["entities"][number]) =>
  e.hp > 0 && !e.status.knocked_down && !e.status.stunned && !(e as any).power_locked;
const point = (e: WorldState["entities"][number]) =>
  e.precise_position ?? fixed(e.position);
const clamp = (cfg: GameConfig, p: number) =>
  Math.max(
    cfg.simulation.probability_min,
    Math.min(cfg.simulation.probability_max, p),
  );
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
      consumed.has(action.entity_id) ||
      tick < cfg.simulation.throw_delay_ticks
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
    const predicted = targetEntity ? targetedThrow(cfg, start, targetEntity, movements?.get(targetEntity.id)) : undefined;
    const target = predicted?.target ?? action.params.target_position;
    if (!target || !throwInRange({...cfg, ball: {...cfg.ball, base_range: cfg.ball.base_range + ((e as any).range_bonus ?? 0)}}, start, target, e.elements)) continue;
    consumed.add(e.id);
    e.status.carrying_ball = false;
    state.ball.holder_entity_id = null;
    state.ball.in_flight = true;
    const distance = hexDistance(start, target);
    const precision = clamp(
      cfg,
      cfg.simulation.throw_base +
        e.stats.precision * cfg.simulation.throw_stat +
        e.elements.AIR * cfg.probabilities.air_precision_per_action -
        distance * cfg.simulation.distance_penalty,
    );
    const success = rng.chance(precision);
    const landTick =
      tick +
      (predicted?.flightTicks ?? Math.max(
        1,
        Math.ceil(
          distance /
            cfg.ball.throw_speed_cells_per_sec /
            cfg.tick_system.tick_dt_seconds,
        ),
      ));
    const landing = hexRound(target);
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
        arc_height: cfg.ball.arc_height_cells,
      },
    });
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
    f.success
  ) {
    const thrower = state.entities.find((e) => e.id === f.thrower)!;
    const reachable = state.entities
      .filter(
        (e) =>
          active(e) &&
          e.id !== f.thrower &&
          withinRadius(
            point(e),
            pos,
            e.team_id === thrower.team_id
              ? cfg.ball.catch_radius_cells
              : cfg.ball.intercept_radius_cells,
          ),
      )
      .sort(
        (a, b) =>
          distanceSquared(point(a), pos) - distanceSquared(point(b), pos) || a.id - b.id,
      );
    if (onBlockedReception && ((cfg.ball as any).reception_requires_air ?? true)) {
      // Check the whole reachable team, including previous failed attempts:
      // a missed random catch is not an element assignment mistake.
      const teams = new Set(reachable.map((e) => e.team_id));
      for (const team of teams) {
        const teammates = reachable.filter((e) => e.team_id === team);
        if (!teammates.some((e) => e.elements.AIR >= 1))
          onBlockedReception(teammates[0]!.id);
      }
    }
    const candidates = reachable.filter((e) =>
      (!((cfg.ball as any).reception_requires_air ?? true) || e.elements.AIR >= 1) &&
      !f.attempted.includes(e.id),
    );
    for (const e of candidates) {
      f.attempted.push(e.id);
      const chance = clamp(
        cfg,
        cfg.simulation.catch_base +
          e.stats.precision * cfg.simulation.catch_stat +
          e.elements.FEU * cfg.simulation.catch_feu +
          e.elements.AIR * cfg.simulation.catch_air,
      );
      if (rng.chance(chance)) {
        e.status.carrying_ball = true;
        state.ball.holder_entity_id = e.id;
        state.ball.in_flight = false;
        state.ball.position = { ...e.position };
        events.push({
          tick,
          type: "catch",
          actor: e.id,
          params: { position: { ...e.position }, catch_chance: chance },
        });
        return events;
      }
      events.push({
        tick,
        type: "catch_fail",
        actor: e.id,
        params: { catch_chance: chance },
      });
    }
  }
  if (tick === f.landTick) {
    state.ball.in_flight = false;
    state.ball.position = { ...f.target };
    events.push({
      tick,
      type: "ball_land",
      params: { position: { ...f.target } },
    });
  }
  return events;
}
export function resolvePickups(
  cfg: GameConfig,
  state: WorldState,
  tick: number,
  onBlockedPickup?: (entityId: number) => void,
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
  // Client spacePoint.x = q + r/2: goal lines are fixed vertical lines,
  // inside the reserve columns, independent of row parity.
  const goalLine = ((cfg.ball as any).goal_line_half_width ?? 12.5) * 2 * SCALE;
  const attacksRight = (e.team_id === 0) !== (state.sides_swapped ?? false);
  if (attacksRight ? x >= goalLine : x <= -goalLine) {
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
