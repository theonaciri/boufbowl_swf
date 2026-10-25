import type { Action, Event, GameConfig, WorldState } from "../types";
import type { DeterministicRNG } from "../rng";

/** Legacy records keep their original provisional effects and random sequence. */
export function resolveAbilities(cfg: GameConfig, state: WorldState, actions: Action[], rng: DeterministicRNG): Event[] {
  const activations = actions.filter(a => a.action_type === "ability").map(action => {
    const caster = state.entities.find(e => e.id === action.entity_id) as any;
    const rule = caster && cfg.abilities?.[caster.class_name] as any;
    return caster && rule && caster.hp > 0 && !caster.status.knocked_down && !caster.status.stunned &&
      (caster.ability_uses_remaining ?? 0) > 0 ? {caster, rule, action} : null;
  }).filter(a => a !== null);
  // Exact mask numbers are missing. Reorder the existing stat pool using the
  // strong-element pairs from the original tooltip, without inventing points.
  // Base stats are restored at turn end; the saved mask reapplies next turn.
  for (const actor of state.entities as any[]) {
    const rule = cfg.abilities?.[actor.class_name] as any;
    if (!rule?.mask_order) continue;
    const selected = activations.find(a => a.caster.id === actor.id);
    const mask = selected?.rule.change_mask ? selected.action.params.zobal_mask : actor.zobal_mask ?? 1;
    const fields = rule.mask_order[String(mask)];
    const values = Object.values(actor.stats).map(Number).sort((a,b) => b-a);
    if (fields?.length !== 4 || new Set(fields).size !== 4) throw new Error('Invalid mask stat ordering');
    fields.forEach((field: string,index: number) => actor.stats[field] = values[index]);
  }
  const living = new Set(state.entities.filter(e => e.hp > 0).map(e => e.id));
  // Resolve target reversal from both submitted orders, before actor-ID order.
  // Old snapshots retain the narrower Eniripsa-only counterspell.
  const redirectors = activations.filter(({rule}) => rule.redirect_enemy_heal || rule.redirect_enemy_ability);
  const events: Event[] = [];
  const teams = new Set<number>();
  for (const {caster, rule, action} of activations) {
    if (rule.target && teams.has(caster.team_id)) throw new Error("Only one class power per team per turn");
    teams.add(caster.team_id);
    caster.ability_uses_remaining--;
    const targets: number[] = [];
    if (!rule.target) {
      for (const target of state.entities) {
        if (target.team_id !== caster.team_id || target.hp <= 0) continue;
        target.hp = Math.min(target.max_hp, target.hp + rule.heal);
        if (rule.element) target.elements[rule.element] += rule.bonus;
        targets.push(target.id);
      }
      events.push({tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name, targets, heal: rule.heal, element: rule.element ?? null,
        bonus: rule.bonus, uses_remaining: caster.ability_uses_remaining,
      }});
      continue;
    }
    caster.power_locked = true;
    if (rule.redirect_enemy_heal || rule.redirect_enemy_ability) {
      events.push({tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name, targets: [], redirected_healers: activations.filter(a =>
          a.caster.team_id !== caster.team_id && a.caster.class_name === "Eniripsa" && a.rule.hp > 0
        ).map(a => a.caster.id), uses_remaining: caster.ability_uses_remaining,
        redirected_casters: activations.filter(a => a.caster.team_id !== caster.team_id &&
          !a.rule.change_mask && ['allies','enemies'].includes(a.rule.target) &&
          (rule.redirect_enemy_ability || a.caster.class_name === 'Eniripsa' && a.rule.hp > 0) &&
          !a.rule.redirect_enemy_ability && !a.rule.redirect_enemy_heal).map(a => a.caster.id),
      }});
      continue;
    }
    if (rule.change_mask) {
      caster.zobal_mask = action.params.zobal_mask;
      events.push({tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name, targets: [], zobal_mask: caster.zobal_mask, uses_remaining: caster.ability_uses_remaining,
      }});
      continue;
    }
    const enemyRoll = rule.enemy_chance !== undefined ? rng.nextFloat() : undefined;
    const originalEnemy = enemyRoll !== undefined ? enemyRoll < rule.enemy_chance : rule.target === "enemies";
    const bonus = enemyRoll !== undefined && originalEnemy ? rule.enemy_elements : rule.elements;
    const hpDeltas: Record<number, number> = {};
    const redirector = rule.target !== 'all' ? redirectors.find(a => a.caster.team_id !== caster.team_id &&
      (a.rule.redirect_enemy_ability || caster.class_name === 'Eniripsa' && rule.hp > 0)) : undefined;
    const enemy = redirector ? !originalEnemy : originalEnemy;
    for (const target of state.entities as any[]) {
      if (!living.has(target.id) || rule.target !== 'all' && (target.team_id !== caster.team_id) !== enemy) continue;
      targets.push(target.id);
      const before = target.hp;
      target.hp = Math.max(0, Math.min(target.max_hp, target.hp + (rule.hp ?? 0)));
      hpDeltas[target.id] = target.hp - before;
      if ((cfg as any).rulebook) {
        target.shield_hp = (target.shield_hp ?? 0) + (rule.shield ?? 0);
        target.temporary_hp = (target.temporary_hp ?? 0) + (rule.temporary_hp ?? 0);
      }
      // Characteristics are separate from the three action slots.
      const fields = {TERRE: "strength", FEU: "agility", AIR: "precision", EAU: "endurance"};
      for (const [element, value] of Object.entries(bonus ?? {})) {
        const field = fields[element as keyof typeof fields];
        target.stats[field] = Math.max(0, target.stats[field] + Number(value));
      }
      target.range_bonus = (target.range_bonus ?? 0) + (rule.range ?? 0);
      target.attack_bonus = (target.attack_bonus ?? 0) + (rule.attack ?? 0);
      target.combat_damage_bonus = (target.combat_damage_bonus ?? 0) + (rule.combat_damage ?? 0);
    }
    events.push({tick: 0, type: "ability", actor: caster.id, params: {
      name: rule.name, targets, hp_deltas: hpDeltas, elements: bonus ?? {},
      range: rule.range ?? 0, attack: rule.attack ?? 0, combat_damage: rule.combat_damage ?? 0,
      target: rule.target === 'all' ? 'all' : enemy ? "enemies" : "allies",
      ...(enemyRoll !== undefined ? {random_draw: enemyRoll} : {}),
      uses_remaining: caster.ability_uses_remaining,
      ...(redirector ? {redirected_by: redirector.caster.id} : {}),
      ...((cfg as any).rulebook ? {shield:rule.shield ?? 0,temporary_hp:rule.temporary_hp ?? 0} : {}),
    }});
  }
  return events;
}
