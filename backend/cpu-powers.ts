/** Choose one power from public field state; never inspect the opponent's orders or seed. */
import { hexDistance } from "../../boufbowl_server/src/hex";

export function addCPUPower(cfg: any, world: any, order: any, level: string): any {
  if (level === "beginner" || !Object.values(cfg.abilities ?? {}).some((r: any) => r.target)) return order;
  const active = (e: any) => e.hp > 0 && !e.status.knocked_down && !e.status.stunned;
  const allies = world.entities.filter((e: any) => e.team_id === order.team_index && active(e));
  const enemies = world.entities.filter((e: any) => e.team_id !== order.team_index && active(e));
  const receivers = new Set(order.actions.filter((a: any) => a.action_type === "throw").map((a: any) => a.params.target_entity_id));
  const nearest = [...allies].sort((a: any,b: any) => hexDistance(a.position,world.ball.position)-hexDistance(b.position,world.ball.position) || a.id-b.id)[0];
  const movements = new Map(order.actions.filter((a: any) => ["move", "follow"].includes(a.action_type)).map((a: any) => [a.entity_id,a]));
  const moving = (e: any) => {
    const a: any = movements.get(e.id);
    return a && (a.action_type === "follow" || hexDistance(e.position,a.params.target_position) > 0);
  };
  const threatened = (e: any) => enemies.some((other: any) => hexDistance(e.position,other.position) <= 3);
  function value(rule: any, targets: any[], hostile: boolean): number {
    let score = 0;
    for (const target of targets) {
      if (rule.hp > 0) score += Math.min(rule.hp,target.max_hp-target.hp) * 2;
      if (rule.hp < 0) score += hostile ? Math.min(-rule.hp,target.hp) * 2 + (target.hp <= -rule.hp ? 6 : 0) : rule.hp * 2;
      if (rule.range) score += (hostile ? -rule.range : rule.range) * (hostile || moving(target) ? 1.5 : 0);
      if (rule.attack) score += (hostile ? -rule.attack : rule.attack) * (threatened(target) || hostile ? 1.5 : .25);
      for (const [element, amount] of Object.entries(rule.elements ?? {})) {
        const weight = element === "EAU" ? (moving(target) ? 1 : .15) : element === "AIR" ? (receivers.has(target.id) || world.ball.holder_entity_id === target.id ? 1 : .25) : (threatened(target) ? 1 : .25);
        score += Number(amount) * weight * (hostile ? -1 : 1);
      }
    }
    return score;
  }
  const choices: any[] = [];
  const protectedIds = new Set(order.cpu_plan?.protected_ids ?? []);
  for (const caster of allies) {
    const rule = cfg.abilities?.[caster.class_name];
    if (!rule?.target || (caster.ability_uses_remaining ?? 0) <= 0 || caster.id === world.ball.holder_entity_id || receivers.has(caster.id) || protectedIds.has(caster.id)) continue;
    // Preserve the immediate ball pickup rather than freezing the designated retriever.
    if (world.ball.holder_entity_id === null && caster.id === nearest?.id && hexDistance(caster.position,world.ball.position) <= 3) continue;
    if (rule.target === "allies" && rule.hp < 0 && allies.some((e: any) => e.hp <= -rule.hp)) continue;
    let score = rule.enemy_chance !== undefined
      ? (1-rule.enemy_chance) * value(rule,allies,false) + rule.enemy_chance * value({elements:rule.enemy_elements},enemies,true)
      : value(rule,rule.target === "enemies" ? enemies : allies,rule.target === "enemies");
    const params: any = {};
    if (rule.change_mask) {
      // Current masks have no stat effects: change only while idle, occasionally.
      if (moving(caster) || order.turn_number % 4 !== 0) continue;
      params.zobal_mask = (caster.zobal_mask ?? 1) % 3 + 1;
      score = 2;
    }
    // Freeze the caster, so its own movement/stat bonuses provide no tactical value.
    if (rule.target === "allies" && !rule.change_mask) {
      const ownBenefit = value({...rule,hp:0},[caster],false);
      score -= Math.max(0,ownBenefit) * (rule.enemy_chance === undefined ? 1 : 1-rule.enemy_chance);
    }
    score -= moving(caster) ? 1.5 : 0;
    if (score >= 2) choices.push({caster,score,params});
  }
  choices.sort((a,b) => b.score-a.score || a.caster.id-b.caster.id);
  const selected = choices[0];
  if (!selected) return order;
  return {...order, ...(order.cpu_plan ? {cpu_plan: {...order.cpu_plan, roles: order.cpu_plan.roles.map((r: any) =>
    r.entity_id === selected.caster.id ? {...r, role:"class_power"} : r)}} : {}),
    actions: [...order.actions.filter((a: any) => a.entity_id !== selected.caster.id && a.action_type !== "ability"),
    {entity_id:selected.caster.id,action_type:"ability",params:selected.params}]};
}
