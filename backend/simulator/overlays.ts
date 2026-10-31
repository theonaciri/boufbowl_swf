/** Narrow source overlays keep the archived simulator source untouched. */
export function passRangeOverlay(name: string, source: string): string {
  const before = name === 'rules'
    ? 'return cfg.ball.base_range + elements.AIR * cfg.actions.element_effects.air.range_modifier;'
    : 'const inRange = !!target && throwInRange(cfg, start, target, e.elements);';
  const after = name === 'rules'
    ? 'return (cfg.ball.base_range + elements.AIR * cfg.actions.element_effects.air.range_modifier) * (cfg.ball.range_multiplier ?? 1);'
    : 'const inRange = !!target && (cfg.ball.attempt_out_of_range || throwInRange(cfg, start, target, e.elements));';
  if (source.includes(after)) return source;
  if (source.split(before).length !== 2) throw new Error(`Simulator ${name} pass range boundary changed`);
  return source.replace(before,after);
}

export function guardContactThrows(source: string): string {
  const before = "fightPlayers(context, tick);";
  if (source.split(before).length !== 2) throw new Error("Expected one combat call before throws");
  const replacement = `const carrierBeforeContact = state.ball.holder_entity_id;
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
  }`;
  const start = source.indexOf("const carrierBeforeContact =");
  if (start >= 0) {
    const end = source.indexOf("const thrown =", start);
    if (end < 0 || source.indexOf("const carrierBeforeContact =", start + 1) >= 0)
      throw new Error("Retained contact guard boundary changed");
    return source.slice(0, start) + replacement + "\n  " + source.slice(end);
  }
  return source.replace(before, replacement);
}

export function overlay(name: string, source: string): string {
  if (name === 'rules' || name === 'turnTick') source = passRangeOverlay(name,source);
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
    replace("? elements.FEU >= 1\n    : true;", "? elements.FEU >= 1 || ((cfg.actions.element_effects.air as any).used_for_pickup === true && elements.AIR >= 1)\n    : true;");
    source = 'import {referenceDistance} from "boufbowl-movement-risk";\n' + source;
    replace("// max distance = base", `if ((cfg.movement as any).overextension !== undefined && (cfg as any).client_ranges)
    return referenceDistance(cfg,elements) * (cfg as any).client_ranges.max_distance_factor;
  // max distance = base`);
  }
  if (name === "turnTick") {
    source = guardContactThrows(source);
    source = 'import {resolveMovementRisk} from "boufbowl-movement-risk";\n' + source;
    replace("  resolvePickups,", "  resolvePickups,\n  hasPendingPickups,");
    replace("resolvePickups(cfg, state, tick, context.onBlockedPickup)", "resolvePickups(cfg, state, tick, context.onBlockedPickup, rng)");
    replace("return pendingMove || pendingThrow || pendingRevive || state.ball.in_flight;", "return pendingMove || pendingThrow || pendingRevive || state.ball.in_flight || hasPendingPickups(cfg,state);");
    replace("const steps = movePlayers(context, tick);", "const steps = movePlayers(context, tick);\n  resolveMovementRisk(context,tick);");
  }
  if (name === "movement") {
    replace("target: { ...target },", "risk_origin: {...e.position},\n      target: { ...target },");
    replace("budget: maxMovementDistance(cfg, e.elements),", "budget: Math.max(0, Math.floor(maxMovementDistance(cfg, e.elements) + ((e as any).range_bonus ?? 0))),");
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
  if (name === "engine" || name === "turnTick") source = rulebookOverlay(name,source);
  return source;
}

/** Shared by a full archive build and the retained-worker refresh. */
export function rulebookOverlay(name: string, source: string): string {
  function replaceOne(before: string,after: string) {
    if (source.split(before).length !== 2) throw new Error(`Rulebook ${name} boundary changed: ${before}`);
    source=source.replace(before,after);
  }
  if (name === "engine") {
    if (!source.includes("prepareRulebookTurn(cfg, state);")) {
      const loop = /for \(let tick = 0;\s*tick < cfg.tick_system.max_ticks_per_turn; tick\+\+\) \{/;
      if (!loop.test(source)) throw new Error("Simulation turn-loop boundary changed");
      source = source.replace(loop, `prepareRulebookTurn(cfg, state);
  if (cfg.rulebook) resolveMovementRisk(context, -1);
  $&`);
    }
    if (!source.includes("finishRulebookTurn(cfg, state, events);"))
      replaceOne("const final_entity_states =", "finishRulebookTurn(cfg, state, events);\n  const final_entity_states =");
    if (source.startsWith("import") && !source.includes('import {prepareRulebookTurn,finishRulebookTurn}')) source = 'import {prepareRulebookTurn,finishRulebookTurn} from "boufbowl-rulebook";\nimport {resolveMovementRisk} from "boufbowl-movement-risk";\n'+source;
  } else if (name === "turnTick") {
    if (!source.includes("tickRulebook(context, tick);")) replaceOne("restoreStandingPlayers(context, tick);", "tickRulebook(context, tick);\n  restoreStandingPlayers(context, tick);");
    if (!source.includes("const pendingStun =")) replaceOne("return pendingMove ||", "const pendingStun = !!cfg.rulebook && state.entities.some(e => e.hp > 0 && e.status.stunned);\n  return pendingStun || pendingMove ||");
    if (source.startsWith("import") && !source.includes('import {tickRulebook}')) source = 'import {tickRulebook} from "boufbowl-rulebook";\n'+source;
  }
  return source;
}
