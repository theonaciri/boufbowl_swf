import {attackPower, dodgeSucceeds, duelDamage} from "../rules";
import {fixed, withinRadius} from "./movement";
import {applyRulebookDamage, recordRulebookLoss, rulebookConsequences, rulebookStunDuration, rulebookCombatNoise, takeRulebookActionBonus} from "boufbowl-rulebook";

export function resolveDuels(cfg, state, actions, rng, tick, dueledPairs) {
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
        const outcome = performDuel(cfg, a, b, ea, eb, rng, actions, state, tick);
        dueledPairs.add(pairKey);
        events.push({
          tick,
          type: outcome.defenderDodged ? "dodge" : "duel",
          actor: outcome.attacker.id,
          params: { defender: outcome.defender.id, ...(outcome.audit ?? {}) }
        });
        events.push(...duelEvents(outcome, tick));
        if (outcome.ballDropped) {
          state.ball = {
            holder_entity_id: null,
            in_flight: false,
            position: { ...(outcome.dropper ?? outcome.defender).position }
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
function legacyPerformDuel(cfg, a, b, ea, eb, rng) {
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
    attacker.hp = Math.max(0, attacker.hp - tieDamage - (attacker.combat_damage_bonus ?? 0));
    defender.hp = Math.max(0, defender.hp - tieDamage - (defender.combat_damage_bonus ?? 0));
    return {
      attacker,
      defender,
      damage: tieDamage,
      tieDamage: {attacker:tieDamage+(attacker.combat_damage_bonus ?? 0),defender:tieDamage+(defender.combat_damage_bonus ?? 0)},
      defenderDodged: false,
      defenderKO: false,
      ballDropped: false,
      tie: true
    };
  }
  const damage = duelDamage(cfg, atk.TERRE) + (defender.combat_damage_bonus ?? 0);
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
  if (outcome.audit) {
    const loser = outcome.loser;
    events.push({tick,type:"damage",actor:loser.id,params:{...outcome.applied}});
    if (loser.status.knocked_down) events.push({tick,type:"ko",actor:loser.id,params:{}});
    else if (loser.status.stunned) events.push({tick,type:"stun",actor:loser.id,params:{until_tick:loser.stun_until_tick}});
    if (outcome.ballDropped) events.push({tick,type:"ball_drop",actor:loser.id,params:{position:{...loser.position}}});
    return events;
  }
  if (outcome.tie) {
    events.push({
      tick,
      type: "damage",
      actor: outcome.attacker.id,
      params: { damage: outcome.tieDamage?.attacker ?? outcome.damage, hp: outcome.attacker.hp }
    });
    events.push({
      tick,
      type: "damage",
      actor: outcome.defender.id,
      params: { damage: outcome.tieDamage?.defender ?? outcome.damage, hp: outcome.defender.hp }
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
        params: { position: { ...(outcome.dropper ?? outcome.defender).position } }
      });
    }
  }
  return events;
}


function performDuel(cfg: any, a: any, b: any, ea: any, eb: any, rng: any, actions: any[], state: any, tick: number): any {
  const policy = cfg.rulebook?.combat;
  if (!policy?.official_effects) return legacyPerformDuel(cfg,a,b,ea,eb,rng);
  // Retain the recreation's pre-existing score proxy, NOT formula1/formula2.
  const movementA=takeRulebookActionBonus(a),movementB=takeRulebookActionBonus(b);
  const bonusA=(a.next_combat_bonus ?? 0)+movementA,bonusB=(b.next_combat_bonus ?? 0)+movementB;
  const powerA = attackPower(cfg,a.stats.strength,ea.TERRE)+(a.attack_bonus ?? 0)+bonusA;
  const powerB = attackPower(cfg,b.stats.strength,eb.TERRE)+(b.attack_bonus ?? 0)+bonusB;
  delete a.next_combat_bonus; delete b.next_combat_bonus;
  const aAttacks = a.power_locked ? false : b.power_locked ? true : powerA >= powerB;
  const attacker = aAttacks ? a : b, defender = aAttacks ? b : a;
  const atk = aAttacks ? ea : eb, def = aAttacks ? eb : ea;
  let dodged = dodgeSucceeds({attacker_terre:atk.TERRE,defender_feu:def.FEU,
    attacker_agility:attacker.stats.agility,defender_agility:defender.stats.agility});
  let defenderWins = dodged;
  let fireDefense = dodged;
  let scoreValues = dodged
    ? {[attacker.id]:aAttacks ? powerA : powerB,[defender.id]:attackPower(cfg,defender.stats.agility,def.FEU)+(defender.attack_bonus ?? 0)+(aAttacks ? bonusB : bonusA)}
    : {[a.id]:powerA,[b.id]:powerB};
  let margin = dodged ? Math.max(0,scoreValues[defender.id]-scoreValues[attacker.id]) : Math.abs(powerA-powerB);
  const random = rulebookCombatNoise(cfg,rng);
  if (policy.random_score) {
    fireDefense = def.FEU > 0 && !def.TERRE;
    const attack = aAttacks ? powerA : powerB;
    const defense = fireDefense
      ? attackPower(cfg,defender.stats.agility,def.FEU)+(defender.attack_bonus ?? 0)+(aAttacks ? bonusB : bonusA)
      : aAttacks ? powerB : powerA;
    const noisyAttack = attack + random.noise;
    const delta = noisyAttack - defense;
    defenderWins = delta < 0;
    dodged = defenderWins && fireDefense;
    margin = Math.abs(delta);
    // Original score fields are unsigned. A common shift preserves the margin
    // when a rare negative draw puts one displayed score below zero.
    const shift = Math.max(0,-Math.min(noisyAttack,defense));
    scoreValues = {[attacker.id]:noisyAttack+shift,[defender.id]:defense+shift};
  }
  const winner = defenderWins ? defender : attacker, loser = defenderWins ? attacker : defender;
  const targeted = actions.some(order => order.entity_id === winner.id && order.action_type === "follow" && order.params.target_entity_id === loser.id);
  const branch = dodged ? "dodge" : targeted ? "targeted" : "incidental";
  const upper = policy.boundary === "upper";
  const tier = (upper ? margin >= 30 : margin > 30) ? "critical" : (upper ? margin >= 15 : margin > 15) ? "wide" : "normal";
  const effect = rulebookConsequences(tier,branch,policy.critical_dodge_down);
  const applied = applyRulebookDamage(loser,effect.damage+(loser.combat_damage_bonus ?? 0));
  if (effect.down || loser.hp <= 0) {loser.status.knocked_down=true;loser.status.stunned=false;delete loser.stun_until_tick;}
  else {loser.status.stunned=true;loser.stun_until_tick=tick+rulebookStunDuration(cfg,loser);}
  recordRulebookLoss(state,loser.id);
  if (effect.next_bonus) winner.next_combat_bonus = policy.next_bonus;
  const ballDropped = loser.status.carrying_ball && loser.status.knocked_down;
  if (ballDropped) loser.status.carrying_ball=false;
  return {attacker,defender,loser,dropper:loser,damage:applied.damage,applied,defenderDodged:dodged,ballDropped,
    audit:{winner:winner.id,loser:loser.id,tier,branch,margin,granted_bonus:effect.next_bonus ? policy.next_bonus : 0,
      ...(cfg.rulebook?.maneuvers ? {movement_bonuses:{[a.id]:movementA,[b.id]:movementB}} : {}),
      score_model:policy.random_score ? 'proxy-intrinsic+logistic-approximation' : "legacy-proxy-unverified",score_values:scoreValues,
      ...(policy.random_score ? {random_draw:random.draw,random_score:random.noise,random_model:policy.random_score.model} : {}),
      stat_fields:{[attacker.id]:"strength",[defender.id]:fireDefense ? "agility" : "strength"}}};
}
