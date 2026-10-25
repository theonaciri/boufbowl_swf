/** Overextension follows the original client's reference/max coloured ranges.
 * The wire contract is recovered; the configurable probability curve is a replacement.
 */
import {hexDistance} from "../../boufbowl_server/src/hex";
import {SIMULATION_SCALE} from "../../boufbowl_server/src/coordinates";
import {rulebookMovementProbability,rulebookQuality} from "boufbowl-rulebook";

export function referenceDistance(cfg: any, elements: any): number {
  const r = cfg.client_ranges;
  return elements.TERRE*r.earth_distance_bonus + elements.FEU*r.fire_distance_bonus +
    elements.AIR*r.air_distance_bonus + elements.EAU*r.water_distance_bonus;
}

export function resolveMovementRisk(context: any, tick: number): void {
  const {cfg,state,movements,rng,events} = context;
  const risk = cfg.movement.overextension;
  if (!risk?.enabled || !cfg.client_ranges) return;
  context.rangeRisk ??= new Map();
  for (const [id,m] of movements) {
    const e = state.entities.find((actor: any) => actor.id === id);
    if (!e || e.hp <= 0 || (tick >= 0 && (e.status.knocked_down || e.status.stunned))) continue;
    let test = context.rangeRisk.get(id);
    if (!test) {
      // Store the original allocation: recovery may consume EAU later in the turn.
      const action = context.actions.find((a: any) => a.entity_id === id && ['move','follow'].includes(a.action_type));
      const safe = Math.max(0,referenceDistance(cfg,action.params.elements ?? e.elements)+(e.range_bonus ?? 0));
      test = {safe,max:Math.max(safe,referenceDistance(cfg,action.params.elements ?? e.elements)*cfg.client_ranges.max_distance_factor+(e.range_bonus ?? 0)),
        origin:m.risk_origin,probability:0,success:true,score:e.stats.endurance,distance:0};
      context.rangeRisk.set(id,test);
      if (cfg.rulebook?.movement) test.draw = rng.nextFloat();
    }
    test.distance = hexDistance(test.origin,m.current);
    const policy = cfg.rulebook?.movement;
    if (!policy && (test.distance <= test.safe || test.max <= test.safe)) continue;
    test.draw ??= rng.nextFloat();
    const ratio = test.max > test.safe ? Math.max(0,Math.min(1,(test.distance-test.safe)/(test.max-test.safe))) : 0;
    test.probability = risk.fall_probability_at_max*Math.pow(ratio,risk.exponent);
    if (policy) {
      const allocation = context.actions.find((a: any) => a.entity_id === id && ['move','follow'].includes(a.action_type)).params.elements ?? e.elements;
      // Explicit replacement balance: not the missing original success formula.
      test.probability = rulebookMovementProbability(cfg,test.probability,e.stats.endurance,allocation.EAU);
      if (test.distance <= 0) continue;
    }
    if (test.draw >= test.probability) {
      if (cfg.rulebook?.maneuvers && m.done && test.distance>0 && !test.bonusGranted) {
        const quality=rulebookQuality(cfg,1-test.probability,1-test.draw);
        test.tier=quality.tier;
        if (quality.tier!=='normal') {
          test.bonusGranted=true;
          e.next_action_bonus=cfg.rulebook.maneuvers.movement_bonus;
          events.push({tick,type:'movement_bonus',actor:id,params:{bonus:e.next_action_bonus,...quality}});
        }
      }
      continue;
    }
    test.success = false;
    e.status.knocked_down = true;
    m.done = true;
    const landing = m.next && m.progress > SIMULATION_SCALE/2 ? m.next : m.current;
    e.position = {...landing};
    e.precise_position = {q:landing.q*SIMULATION_SCALE,r:landing.r*SIMULATION_SCALE};
    m.current = {...landing};m.next = undefined;m.progress = 0;
    const carried = state.ball.holder_entity_id === id;
    events.push({tick,type:'fall',actor:id,params:{position:{...e.position},has_ball:carried,
      probability:test.probability,random_draw:test.draw,distance:test.distance,safe_range:test.safe,max_range:test.max}});
    if (carried) {
      e.status.carrying_ball = false;
      state.ball = {position:{...e.position},holder_entity_id:null,in_flight:false};
      events.push({tick,type:'ball_drop',actor:id,params:{position:{...e.position}}});
    }
  }
}

export function publishMovementTests(context: any): void {
  for (const [id,test] of context.rangeRisk ?? []) context.events.push({tick:context.state.tick,type:'movement_test',actor:id,params:{
    success:test.success,probability:test.probability,random_draw:test.draw ?? null,
    distance:test.distance,safe_range:test.safe,max_range:test.max,inherent_score:test.score,
    ...(test.tier ? {tier:test.tier,granted_bonus:test.bonusGranted ? context.cfg.rulebook.maneuvers.movement_bonus : 0} : {}),
  }});
}
