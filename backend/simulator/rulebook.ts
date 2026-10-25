/** Explicit restoration policies. None of these functions recovers the missing
 * intrinsic-score table or combat random CDF. See resources/rulebook.json.
 */
const rulebookLosses = new WeakMap<object, Map<number, number>>();
const bounded = (p: number) => Math.max(Number.EPSILON,Math.min(1-Number.EPSILON,p));
export function rulebookQuality(cfg: any, probability: number, draw: number): any {
  const policy = cfg.rulebook.maneuvers;
  const scale = cfg.rulebook.combat.random_score?.scale ?? 6/Math.log(17/3);
  const logit = (p: number) => Math.log(bounded(p)/(1-bounded(p)));
  const margin = scale*(logit(probability)-logit(draw));
  const magnitude = Math.abs(margin);
  return {quality_margin:margin,tier:magnitude>policy.critical_margin ? 'critical' : magnitude>policy.wide_margin ? 'wide' : 'normal'};
}
export function takeRulebookActionBonus(actor: any): number {
  const bonus = actor.next_action_bonus ?? 0;
  delete actor.next_action_bonus;
  return bonus;
}
export function rollRulebookManeuver(cfg: any, actor: any, chance: number, rng: any, kind: string): any {
  if (!cfg.rulebook?.maneuvers) return {success:rng.chance(chance)};
  let bonus = takeRulebookActionBonus(actor);
  if (kind === 'throw') {bonus += actor.next_throw_bonus ?? 0;delete actor.next_throw_bonus;}
  if (bonus && chance>0 && chance<1) {
    const scale = cfg.rulebook.combat.random_score?.scale ?? 6/Math.log(17/3);
    chance = 1/(1+Math.exp(-(Math.log(chance/(1-chance))+bonus/scale)));
    chance = Math.max(cfg.simulation.probability_min,Math.min(cfg.simulation.probability_max,chance));
  }
  const draw = rng.nextFloat();
  const quality = rulebookQuality(cfg,chance,draw);
  const inherent = ['interception','pickup_fire'].includes(kind) ? actor.stats.agility : actor.stats.precision;
  if (draw>=chance && quality.tier==='critical' && !cfg.rulebook.maneuvers.critical_failures) quality.tier='wide';
  return {success:draw<chance,probability:chance,random_draw:draw,...quality,
    consumed_bonus:bonus,maneuver_bonus_malus:bonus,
    inherent_score:inherent,final_score:Math.max(0,inherent+bonus),
    difficulty:Math.round(chance*100)};
}
export function failRulebookManeuver(cfg: any, actor: any, result: any, kind: string, tick: number, events: any[]): void {
  if (result.success || result.tier!=='critical' || !cfg.rulebook?.maneuvers?.critical_failures) return;
  if (kind==='throw') {
    actor.status.stunned=true;actor.stun_until_tick=tick+rulebookStunDuration(cfg,actor);
    events.push({tick,type:'stun',actor:actor.id,params:{until_tick:actor.stun_until_tick,reason:'critical_throw'}});
  } else {
    actor.status.knocked_down=true;actor.status.stunned=false;delete actor.stun_until_tick;
    events.push({tick,type:'ko',actor:actor.id,params:{reason:'critical_'+kind}});
  }
}
export function rulebookCombatNoise(cfg: any, rng: any): any {
  const policy = cfg.rulebook?.combat?.random_score;
  if (!policy) return {noise:0};
  if (policy.model !== 'logistic-approximation' || !(policy.scale > 0)) throw new Error('Invalid score distribution');
  const draw = rng.nextFloat();
  const u = Math.max(Number.EPSILON,Math.min(1-Number.EPSILON,draw));
  return {draw,noise:policy.scale*Math.log(u/(1-u))};
}
export function rulebookMovementProbability(cfg: any, base: number, water: number, orders: number): number {
  const policy=cfg.rulebook?.movement;
  return policy ? Math.min(1,(policy.safe_failure+base)/(1+Math.max(0,water)*policy.water_stat+orders*policy.water_order)) : base;
}
export function rulebookThrowSpeed(cfg: any, elements: any): number {
  return cfg.ball.throw_speed_cells_per_sec*(1+(cfg.rulebook?.passing?.air_speed_bonus ?? 0)*elements.AIR);
}
export function rulebookOnFlightSegment(start: any, target: any, point: any): boolean {
  const dx=target.q-start.q+(target.r-start.r)/2,dy=(target.r-start.r)*Math.sqrt(3)/2;
  const px=point.q-start.q+(point.r-start.r)/2,py=(point.r-start.r)*Math.sqrt(3)/2;
  const projection=px*dx+py*dy,length=dx*dx+dy*dy;
  return length>0 && projection>=0 && projection<=length;
}
export function rulebookScatter(start: any, target: any, draw: number): any {
  return {q:start.q+(target.q-start.q)*draw,r:start.r+(target.r-start.r)*draw};
}
export function recordRulebookLoss(state: any, id: number): void {
  let losses = rulebookLosses.get(state);
  if (!losses) { losses = new Map(); rulebookLosses.set(state, losses); }
  losses.set(id, (losses.get(id) ?? 0) + 1);
}
export function rulebookPickupPenalty(cfg: any, state: any, actor: any): any {
  const policy = cfg.rulebook?.pickup;
  if (!policy) return {penalty: 0, nearby: 0, lost_combats: 0};
  const nearby = state.entities.filter((other: any) => {
    const dq = actor.position.q-other.position.q;
    const dr = actor.position.r-other.position.r;
    return other.id !== actor.id && other.hp > 0 && Math.max(Math.abs(dq),Math.abs(dr),Math.abs(dq+dr)) <= policy.radius;
  }).length;
  const lost_combats = rulebookLosses.get(state)?.get(actor.id) ?? 0;
  return {nearby, lost_combats, penalty: nearby*policy.nearby_penalty + lost_combats*policy.loss_penalty};
}
export function rulebookStunDuration(cfg: any, actor: any): number {
  const policy = cfg.rulebook.status;
  return Math.max(policy.minimum_ticks, Math.ceil(policy.base_ticks - Math.max(0,actor.stats.endurance)*policy.water_reduction));
}
export function prepareRulebookTurn(cfg: any, state: any): void {
  if (!cfg.rulebook) return;
  for (const actor of state.entities) {
    if (actor.status.stunned && actor.hp > 0)
      actor.stun_until_tick = actor.stun_ticks_remaining ?? rulebookStunDuration(cfg,actor);
    delete actor.stun_ticks_remaining;
  }
}
export function tickRulebook(context: any, tick: number): void {
  if (!context.cfg.rulebook) return;
  for (const actor of context.state.entities) {
    if (actor.status.stunned && actor.hp > 0 && actor.stun_until_tick <= tick) {
      actor.status.stunned = false;
      delete actor.stun_until_tick;
      context.events.push({tick,type:"stun_end",actor:actor.id,params:{}});
    }
  }
}
export function finishRulebookTurn(cfg: any, state: any, events: any[]): void {
  if (!cfg.rulebook) return;
  for (const actor of state.entities) {
    if (actor.status.stunned && actor.hp > 0) actor.stun_ticks_remaining = Math.max(1,actor.stun_until_tick-state.tick-1);
    delete actor.stun_until_tick;
    delete actor.next_combat_bonus;
    delete actor.next_action_bonus;delete actor.next_throw_bonus;
    if (actor.shield_hp || actor.temporary_hp) events.push({tick:state.tick,type:"protection_expired",actor:actor.id,
      params:{shield_hp:actor.shield_hp ?? 0,temporary_hp:actor.temporary_hp ?? 0}});
    delete actor.shield_hp; delete actor.temporary_hp; delete actor.combat_damage_bonus;
  }
}
export function applyRulebookDamage(actor: any, amount: number): any {
  let remaining = Math.max(0, amount);
  const shield = Math.min(actor.shield_hp ?? 0,remaining); remaining -= shield;
  const temporary = Math.min(actor.temporary_hp ?? 0,remaining); remaining -= temporary;
  actor.shield_hp = Math.max(0,(actor.shield_hp ?? 0)-shield);
  actor.temporary_hp = Math.max(0,(actor.temporary_hp ?? 0)-temporary);
  const hp_loss = Math.min(actor.hp,remaining);
  actor.hp = Math.max(0,actor.hp-remaining);
  return {damage:hp_loss,absorbed_shield:shield,absorbed_temporary:temporary,hp:actor.hp};
}
export function rulebookConsequences(tier: string, branch: string, criticalDodgeDown=false): any {
  const index = ["normal","wide","critical"].indexOf(tier);
  if (index < 0 || !["targeted","incidental","dodge"].includes(branch)) throw new Error("Unknown combat tier/branch");
  const down = branch === "targeted" ? index > 0 : branch === "dodge" && index === 2 && criticalDodgeDown;
  return {damage:(branch === "targeted" ? [1,3,5] : [0,2,4])[index],down,stun:!down,next_bonus:index>0};
}
