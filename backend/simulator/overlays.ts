/** Narrow source overlays keep the archived simulator source untouched. */
export function overlay(name: string, source: string): string {
  function replace(before: string, after: string) {
    if (!source.includes(before)) throw new Error(`Simulator ${name} changed: missing ${before}`);
    source = source.replace(before, after);
  }
  if (name === "engine") {
    source = 'import {publishMovementTests} from "boufbowl-movement-risk";\n' + source;
    replace("// A bounded turn always settles", "publishMovementTests(context);\n  // A bounded turn always settles");
    replace("const events: Event[] = resolveAbilities(cfg, state, actions),", `const originalStats = new Map(state.entities.map(e => [e.id, {...e.stats}]));
  const events: Event[] = resolveAbilities(cfg, state, actions, rng),`);
    replace("const final_entity_states = state.entities.map", `// Expire temporary bonuses before persisting or hashing the next turn.
  for (const e of state.entities as any[]) {
    e.stats = originalStats.get(e.id)!;
    delete e.range_bonus; delete e.attack_bonus; delete e.power_locked;
  }
  const final_entity_states = state.entities.map`);
    replace("entity_id: e.id,", "...((e as any).zobal_mask !== undefined ? {zobal_mask: (e as any).zobal_mask} : {}),\n    entity_id: e.id,");
  }
  if (name === "rules") {
    source = 'import {referenceDistance} from "boufbowl-movement-risk";\n' + source;
    replace("// max distance = base", `if ((cfg.movement as any).overextension !== undefined && (cfg as any).client_ranges)
    return referenceDistance(cfg,elements) * (cfg as any).client_ranges.max_distance_factor;
  // max distance = base`);
  }
  if (name === "turnTick") {
    source = 'import {resolveMovementRisk} from "boufbowl-movement-risk";\n' + source;
    replace("const steps = movePlayers(context, tick);", "const steps = movePlayers(context, tick);\n  resolveMovementRisk(context,tick);");
  }
  if (name === "movement") {
    replace("target: { ...target },", "risk_origin: {...e.position},\n      target: { ...target },");
    replace("budget: maxMovementDistance(cfg, e.elements),", "budget: Math.max(0, Math.floor(maxMovementDistance(cfg, e.elements) + ((e as any).range_bonus ?? 0))),");
  }
  if (name === "combat") {
    replace("if (a.team_id === b.team_id) continue;", "if (a.team_id === b.team_id || ((a as any).power_locked && (b as any).power_locked)) continue;");
    replace("const powerA = attackPower(cfg, a.stats.strength, ea.TERRE);", "const powerA = attackPower(cfg, a.stats.strength, ea.TERRE) + ((a as any).attack_bonus ?? 0);");
    replace("const powerB = attackPower(cfg, b.stats.strength, eb.TERRE);", "const powerB = attackPower(cfg, b.stats.strength, eb.TERRE) + ((b as any).attack_bonus ?? 0);");
    replace("const aAttacks = powerA >= powerB;", "const aAttacks = (a as any).power_locked ? false : (b as any).power_locked ? true : powerA >= powerB;");
    replace("if (powerA === powerB) {", "if (powerA === powerB && !(a as any).power_locked && !(b as any).power_locked) {");
  }
  if (name === "validator") {
    replace('const allocations = new Map<number, string>(),', `const powers = order.actions.filter(a => a?.action_type === "ability");
    const modern = Object.values(this.config.abilities ?? {}).some((r: any) => r.target);
    if (modern) {
      if (powers.length > 1) return fail("Only one class power per team per turn");
      for (const power of powers) {
        if (order.actions.some(a => a !== power && a.entity_id === power.entity_id))
          return fail("A class power cannot be combined with any other action");
        const caster = state.entities.find(e => e.id === power.entity_id && e.team_id === team) as any;
        if (!caster || caster.hp <= 0 || caster.status.stunned || caster.status.knocked_down ||
            (caster.ability_uses_remaining ?? 0) <= 0 || !this.config.abilities?.[caster.class_name])
          return fail("Class power unavailable");
        if (Object.values(power.params?.elements ?? {}).some(v => v !== 0))
          return fail("A class power cannot assign elements");
        if (Object.keys(power.params ?? {}).some(k => !["elements", "zobal_mask"].includes(k)))
          return fail("A class power cannot target a movement or ball action");
        if (caster.class_name === "Zobal" && (![1,2,3].includes(power.params?.zobal_mask as number) ||
            power.params.zobal_mask === (caster.zobal_mask ?? 1))) return fail("Choose a different Zobal mask");
        if (caster.class_name !== "Zobal" && power.params?.zobal_mask !== undefined)
          return fail("Only Zobal can select a mask");
      }
    }
    const allocations = new Map<number, string>(),`);
    // Powers can extend a valid target beyond its ordinary budget. Execution still clamps to the actual budget.
    replace("hexDistance(e.position, target) >\n              maxMovementDistance(this.config, elements)", `hexDistance(e.position, target) >
              maxMovementDistance(this.config, elements) + (modern ? Math.max(0, ...state.entities.filter(p => p.team_id === team && p.hp > 0 && (p.ability_uses_remaining ?? 0) > 0).map(p => (this.config.abilities?.[p.class_name] as any)?.range ?? 0)) : 0)`);
  }
  return source;
}
