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
  const living = new Set(state.entities.filter(e => e.hp > 0).map(e => e.id));
  // Resolve the documented Ecaflip/Eniripsa pairing from both submitted orders,
  // before processing actors by ID. Other inversion combinations are unknown.
  const redirectors = activations.filter(({rule}) => rule.redirect_enemy_heal);
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
    if (rule.redirect_enemy_heal) {
      events.push({tick: 0, type: "ability", actor: caster.id, params: {
        name: rule.name, targets: [], redirected_healers: activations.filter(a =>
          a.caster.team_id !== caster.team_id && a.caster.class_name === "Eniripsa" && a.rule.hp > 0
        ).map(a => a.caster.id), uses_remaining: caster.ability_uses_remaining,
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
    const enemy = enemyRoll !== undefined ? enemyRoll < rule.enemy_chance : rule.target === "enemies";
    const bonus = enemyRoll !== undefined && enemy ? rule.enemy_elements : rule.elements;
    const hpDeltas: Record<number, number> = {};
    const redirector = caster.class_name === "Eniripsa" && rule.hp > 0
      ? redirectors.find(a => a.caster.team_id !== caster.team_id) : undefined;
    for (const target of state.entities as any[]) {
      if (!living.has(target.id) || (redirector
        ? target.team_id !== redirector.caster.team_id
        : (target.team_id !== caster.team_id) !== enemy)) continue;
      targets.push(target.id);
      const before = target.hp;
      target.hp = Math.max(0, Math.min(target.max_hp, target.hp + (rule.hp ?? 0)));
      hpDeltas[target.id] = target.hp - before;
      // Characteristics are separate from the three action slots.
      const fields = {TERRE: "strength", FEU: "agility", AIR: "precision", EAU: "endurance"};
      for (const [element, value] of Object.entries(bonus ?? {})) {
        const field = fields[element as keyof typeof fields];
        target.stats[field] = Math.max(0, target.stats[field] + Number(value));
      }
      target.range_bonus = (target.range_bonus ?? 0) + (rule.range ?? 0);
      target.attack_bonus = (target.attack_bonus ?? 0) + (rule.attack ?? 0);
    }
    events.push({tick: 0, type: "ability", actor: caster.id, params: {
      name: rule.name, targets, hp_deltas: hpDeltas, elements: bonus ?? {},
      range: rule.range ?? 0, attack: rule.attack ?? 0, target: enemy ? "enemies" : "allies",
      ...(enemyRoll !== undefined ? {random_draw: enemyRoll} : {}),
      uses_remaining: caster.ability_uses_remaining,
      ...(redirector ? {redirected_by: redirector.caster.id} : {}),
    }});
  }
  return events;
}
