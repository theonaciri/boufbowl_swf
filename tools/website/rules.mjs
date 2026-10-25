import { promises as fs } from "node:fs";
import path from "node:path";
import copy from "./rules-data.json";

const escape = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const number = (value) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 4 }).format(value);
const statuses = { implemented: "Principe documenté", provisional: "Fidélité incertaine", custom: "Règle de la restauration", pending: "À vérifier" };
const names = { CRA: "Crâ", ECAFLIP: "Écaflip", ENIRIPSA: "Eniripsa", ENUTROF: "Enutrof", FECA: "Féca", IOP: "Iop", OSAMODAS: "Osamodas", PANDAWA: "Pandawa", ROUBLARD: "Roublard", ROGUE: "Roublard", SACRIEUR: "Sacrieur", SACRIER: "Sacrieur", SADIDA: "Sadida", SRAM: "Sram", XELOR: "Xélor", ZOBAL: "Zobal" };
const roles = { 1: "Bloqueur", 2: "Esquiveur", 3: "Coureur", 4: "Lanceur" };
const elements = { TERRE: "Terre", FEU: "Feu", AIR: "Air", EAU: "Eau" };
const signed = (value) => `${value > 0 ? "+" : ""}${number(value)}`;
const badge = (status) => {
  if (!statuses[status]) throw new Error(`Unknown rulebook status: ${status}`);
  return `<span class="rule-badge ${status}">${escape(statuses[status])}</span>`;
};
function table(caption, headings, rows) {
  return `<div class="rules-table-wrap" role="region" aria-label="${escape(caption)}" tabindex="0"><table><caption>${escape(caption)}</caption><thead><tr>${headings.map((h) => `<th scope="col">${escape(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell, i) => `<${i ? "td" : 'th scope="row"'}>${escape(cell)}</${i ? "td" : "th"}>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function merge(base, overrides) {
  const result = structuredClone(base);
  for (const [key, value] of Object.entries(overrides)) result[key] = value && typeof value === "object" && !Array.isArray(value) ? merge(result[key] || {}, value) : value;
  return result;
}
function effect(ability) {
  const parts = [];
  for (const [element, value] of Object.entries(ability.elements || {})) {
    if (!elements[element]) throw new Error(`Untranslated ability element: ${element}`);
    parts.push(`${signed(value)} à la caractéristique ${elements[element]}`);
  }
  if (ability.hp) parts.push(`${signed(ability.hp)} PV`);
  if (ability.heal) parts.push(`soin de ${number(ability.heal)} PV`);
  if (ability.range) parts.push(`${signed(ability.range)} à la portée`);
  if (ability.attack) parts.push(`${signed(ability.attack)} au score d’attaque`);
  if (ability.shield) parts.push(`${number(ability.shield)} PV de bouclier`);
  if (ability.temporary_hp) parts.push(`${number(ability.temporary_hp)} PV temporaires`);
  if (ability.combat_damage) parts.push(`${signed(ability.combat_damage)} PV de dégâts dans tous les combats du tour`);
  if (ability.redirect_enemy_ability) parts.push("inverse les équipes ciblées par le pouvoir adverse");
  if (ability.redirect_enemy_heal) parts.push("détourne vers son équipe le soin d’un Eniripsa adverse");
  if (ability.change_mask) parts.push("choisit un autre masque parmi les trois disponibles");
  if (ability.mask_order) parts.push("réorganise ses caractéristiques selon le masque ; valeurs exactes d’origine inconnues");
  if (!parts.length || ability.enemy_chance !== undefined) throw new Error(`Translate the configured class effect: ${ability.name}`);
  return parts.join(" ; ");
}

export async function rulesPage(root) {
  const read = async (name) => JSON.parse(await fs.readFile(path.join(root, name), "utf8"));
  const [registry, config, inventory, template] = await Promise.all([
    read("resources/rulebook.json"), read("resources/game_config.json"), read("assets/site/restoration/inventory.json"),
    fs.readFile(path.join(root, "regles.html"), "utf8"),
  ]);
  const rules = config.rules, match = rules.match, sim = rules.simulation, policy = sim.rulebook;
  if (!policy || policy.id !== registry.id) throw new Error("The French rules page requires the active registered rulebook");
  const indexed = new Map(registry.rules.map((rule) => [rule.id, rule]));
  const covered = copy.groups.flatMap(([, , ids]) => ids);
  if (new Set(covered).size !== covered.length || covered.length !== indexed.size || covered.some((id) => !indexed.has(id))) throw new Error("Translate and group every rulebook case exactly once");
  const tick = sim.tick_system.tick_dt_seconds;
  const tournament = config.general.tournament;
  const zone = tournament.timezone;
  const time = (seconds, options) => new Intl.DateTimeFormat("fr-FR", { timeZone: zone, ...options }).format(new Date(seconds * 1000));
  const context = {
    rosterLimit: match.roster_role_limit ?? match.max_players_per_role, fieldRoleLimit: match.max_players_per_role,
    placementSeconds: match.placement_seconds, planningSeconds: match.planning_seconds, matchTurns: match.turns_per_match, periodTurns: match.turns_per_period,
    standOrders: sim.combat.revive.required_eau_actions_to_get_up, standSeconds: number(sim.simulation.stand_up_ticks * tick),
    pickupRange: number(sim.ball.pickup_range), pressureRadius: number(policy.pickup.radius), nearbyPenalty: number(100 * policy.pickup.nearby_penalty), lossPenalty: number(100 * policy.pickup.loss_penalty),
    airSpeedBonus: number(100 * policy.passing.air_speed_bonus),
    revival: policy.recovery?.revive_rested_reserves ? "Choix de restauration : un joueur à zéro PV revient au maximum après une phase sur le banc. Un joueur du terrain ne ressuscite pas à la remise en place immédiate." : "Un joueur à zéro PV reste mort, même après un repos sur le banc.",
    movementQuality: policy.maneuvers ? `Un déplacement terminé avec une réussite large ou critique donne ${number(policy.maneuvers.movement_bonus)} point(s) au prochain test de ballon ou combat, sans cumul et avant la fin du tour.` : "Le profil ne donne pas de bonus de déplacement.",
    maneuverQuality: policy.maneuvers ? `Les seuils de qualité ${number(policy.maneuvers.wide_margin)} et ${number(policy.maneuvers.critical_margin)} utilisent une marge logistique reconstruite, distincte du score historique inconnu. ${policy.maneuvers.critical_failures ? 'Un échec critique étourdit le lanceur ou met au sol le ramasseur, le réceptionneur ou l’intercepteur, sans perte de PV ajoutée. Une interception manquée ne termine pas le vol.' : 'Les conséquences critiques sont désactivées.'}` : "Les tests de ballon ne produisent pas de grades critiques.",
    receptionBonus: policy.maneuvers ? `Une réception normale, large ou critique donne respectivement ${[1,2,3].map(n=>number(n*policy.maneuvers.reception_throw_bonus)).join(', ')} point(s) au prochain lancer du même tour. Ces valeurs sont provisoires.` : "Le profil ne donne pas de bonus au lancer suivant.",
    stunFormula: `max(${number(policy.status.minimum_ticks)}, plafond(${number(policy.status.base_ticks)} − Eau × ${number(policy.status.water_reduction)})) pas de ${number(tick)} seconde`,
    graceSeconds: policy.connection.grace_seconds, heartbeatSeconds: policy.connection.heartbeat_timeout,
    bothExpired: policy.connection.both_expired === "finish-current-score" ? "la partie est arrêtée au score courant" : (() => { throw new Error("Translate both-offline settlement"); })(),
    restartRecovery: match.restart_recovery === "reserves" ? "À une remise en place, les réservistes vivants retrouvent leurs PV maximum. Les joueurs qui étaient sur le terrain gardent leurs PV courants." : "À une remise en place, le profil actuel rétablit les PV des joueurs de terrain.",
    criticalDodge: policy.combat.critical_dodge_down ? "Le profil actuel met au sol après une esquive critique." : "Le profil actuel étourdit après une esquive critique, sans mise au sol automatique.",
    targetedEffects: policy.combat.official_effects ? "Quand le vainqueur poursuivait explicitement le perdant, les dégâts et conséquences suivent la branche « contact ciblé » du tableau ci-dessous." : "Le profil actuel désactive le tableau de conséquences documenté et utilise l’ancien modèle expérimental indiqué ci-dessous.",
    interceptionStat: sim.ball.interception_uses_fire_stat ? "Feu" : "Air",
    ecaflipBehavior: rules.abilities.Ecaflip?.redirect_enemy_ability ? "Écaflip inverse les équipes ciblées par le pouvoir adverse : un soin ou bonus allié passe à l’autre équipe, et un malus adverse change de destinataires. Aucun effet sans pouvoir adverse. Les masques personnels et les effets globaux ne sont pas redirigés." : rules.abilities.Ecaflip?.redirect_enemy_heal ? "Le pouvoir d’Écaflip redirige le soin d’un Eniripsa adverse vers sa propre équipe. Sans soin adverse, cette interaction n’a aucun effet." : "L’interaction documentée détourne un soin adverse vers l’équipe d’Écaflip, mais elle est désactivée dans le profil actuel. Son effet configuré figure dans le tableau des pouvoirs.",
    scatter: policy.passing.scatter_failures ? "En cas d’échec, la restauration tire un point le long du trajet prévu puis le ramène à une case." : "Le profil actuel désactive la déviation reconstruite le long du trajet.",
    passDeadline: sim.ball.require_arrival_before_turn_end ? "Une passe n’est pas lancée si son arrivée prévue dépasse la dernière étape jouable du tour." : "Le profil actuel n’impose pas la contrainte d’arrivée avant la fin du tour.",
    contactCancellation: sim.ball.contact_cancels_pending_throw ? "Un contact avec le porteur annule sa passe encore en préparation. Une passe déjà partie continue ; un joueur qui récupère le ballon plus tard n’est pas automatiquement privé de son ordre." : "L’annulation d’un lancer en préparation au contact est désactivée dans ce profil.",
    passingTiming: policy.passing.favorable_timing ? "Le lancer peut attendre lorsque les trajectoires se rapprochent, puis partir avant que la fenêtre d’arrivée se ferme. Des trajectoires qui s’écartent favorisent un départ plus tôt." : "L’attente reconstruite en fonction du rapprochement des trajectoires est désactivée.",
    pathInterception: policy.passing.path_interception ? "La restauration filtre actuellement les joueurs situés sur le segment de vol, devant le passeur." : "Le filtre supplémentaire sur le segment de vol est désactivé dans ce profil.",
    tournamentSchedule: tournament.enabled ? `${time(tournament.start_time, { weekday: "long" })}, de ${time(tournament.start_time, { hour: "2-digit", minute: "2-digit" })} à ${time(tournament.end_time, { hour: "2-digit", minute: "2-digit" })} (${zone}).` : "Les tournois sont actuellement désactivés.",
    tournamentFormat: tournament.format === "elimination" ? `Qualifications de ${number(tournament.qualification_seconds / 60)} minutes, puis ${tournament.qualifying_top} qualifiés en élimination directe, sur ${tournament.round_count} rondes de ${number(tournament.round_seconds / 60)} minutes.` : "Les participants cumulent des points pendant toute la durée de l’épreuve.",
    winPoints: tournament.win_points, drawPoints: tournament.draw_points, lossPoints: tournament.loss_points,
  };
  const prose = (text) => escape(text.replace(/\{(\w+)\}/g, (_, key) => {
    if (!(key in context)) throw new Error(`Unknown French rule value: ${key}`);
    return context[key];
  }));
  const cases = copy.groups.map(([anchor, title, ids]) => `<section class="rules-section" id="${anchor}" aria-labelledby="heading-${anchor}"><div class="rules-section-title"><span class="eyebrow">LE RÈGLEMENT</span><h2 id="heading-${anchor}">${escape(title)}</h2></div><div class="rule-grid">${ids.map((id) => {
    const rule = indexed.get(id), translation = copy.cases[id];
    if (!translation) throw new Error(`Missing French rule: ${id}`);
    return `<article class="rule-card"><div class="rule-card-top">${badge(rule.status)}<span class="rule-reference">${escape(id)}</span></div><h3>${prose(translation[0])}</h3><p>${prose(translation[1])}</p><p class="rule-note">${prose(translation[2])}</p><p class="rule-sources">Repères d’archives : ${rule.sources.map(escape).join(" · ")}</p></article>`;
  }).join("")}</div>${anchor === "combat" ? combatTable(policy, sim) : ""}${anchor === "pouvoirs" ? '<p class="rules-crosslink"><a href="#classes">Voir les caractéristiques et tous les pouvoirs ↓</a></p>' : ""}</section>`).join("\n");
  const attributes = Object.entries(rules.classes.overrides).map(([key, values]) => {
    const value = { ...rules.classes.defaults, ...values };
    if (!names[key] || !roles[value.role]) throw new Error(`Translate the configured class/role: ${key}`);
    return [names[key], roles[value.role], ...["earth", "fire", "air", "water", "health", "regeneration"].map((field) => number(value[field]))];
  });
  const abilities = Object.entries(rules.abilities).map(([key, ability]) => {
    const target = ability.change_mask ? "Le lanceur" : ability.target === 'all' ? 'Les deux équipes' : ability.target === "enemies" ? "Adversaires vivants" : "Alliés vivants";
    if (!names[key.toUpperCase()]) throw new Error(`Translate the configured class: ${key}`);
    return [names[key.toUpperCase()], target, effect(ability), ability.verified ? "Documenté pour ce profil" : "Fidélité historique incertaine"];
  });
  const stadiums = Object.entries(config.stadiums).filter(([, stadium]) => stadium.enabled).map(([key, stadium]) => {
    const resolved = merge(rules, stadium.overrides), m = resolved.match;
    const powersDiffer = JSON.stringify(resolved.abilities) !== JSON.stringify(rules.abilities);
    return [inventory.stadiums.find((s) => s.id === key)?.name || key, m.turns_per_match, m.turns_per_period, m.class_ability_uses, `${m.placement_seconds} s / ${m.planning_seconds} s`, m.regenerate_between_turns ? "Oui" : "Non", powersDiffer ? "Pouvoirs spécifiques à ce stade" : "Pouvoirs communs"];
  });
  const formulas = [
    ["Chute", `min(1 ; (${number(policy.movement.safe_failure)} + risque d’extension) / (1 + Eau × ${number(policy.movement.water_stat)} + ordres Eau × ${number(policy.movement.water_order)}))`],
    ["Pression au ramassage", `${number(policy.pickup.nearby_penalty)} × joueurs proches + ${number(policy.pickup.loss_penalty)} × combats perdus ce tour`],
    ["Étourdissement", context.stunFormula],
    ["Lancer", `${number(sim.simulation.throw_base)} + Air × ${number(sim.simulation.throw_stat)} + ordres Air × ${number(sim.probabilities.air_precision_per_action)} − distance × ${number(sim.simulation.distance_penalty)}`],
    ["Réception prévue", `${number(sim.simulation.catch_base)} + Air × ${number(sim.simulation.catch_stat)} + ordres Air × ${number(sim.simulation.catch_air)}${sim.ball.action_limited_attempts ? "" : ` + ordres Feu × ${number(sim.simulation.catch_feu)}`}`],
    ["Interception", `${number(sim.simulation.catch_base)} + ${sim.ball.interception_uses_fire_stat ? "Feu" : "Air"} × ${number(sim.simulation.catch_stat)} + ordres Feu × ${number(sim.simulation.catch_feu)}${sim.ball.action_limited_attempts ? "" : ` + ordres Air × ${number(sim.simulation.catch_air)}`}`],
    ["Ramassage", `${number(sim.simulation.catch_base)} + ${policy.maneuvers ? 'Feu avec un ordre Feu, sinon Air' : 'Air'} × ${number(sim.simulation.catch_stat)} + ordres Air × ${number(sim.simulation.catch_air)} + ordres Feu × ${number(sim.simulation.catch_feu)} − pression`],
    ["Bornes des tests de ballon", `${number(100 * sim.simulation.probability_min)} % à ${number(100 * sim.simulation.probability_max)} %`],
    ["Vitesse de passe", `${number(sim.ball.throw_speed_cells_per_sec)} cases/s × (1 + ordres Air × ${number(policy.passing.air_speed_bonus)})`],
  ];
  const values = {
    CASES: cases,
    TOC: copy.groups.map(([id, title]) => `<a href="#${id}">${escape(title)}</a>`).join("") + '<a href="#classes">Classes et pouvoirs</a><a href="#stades">Variantes des stades</a><a href="#incertitudes">Ce qui reste incertain</a>',
    COUNTS: `${registry.rules.length} règles expliquées · ${registry.rules.filter((r) => r.status === "provisional" || r.status === "pending").length} à fidélité incertaine`,
    MATCH_TURNS: match.turns_per_match, PLAN_SECONDS: match.planning_seconds,
    ATTRIBUTES: table("Caractéristiques de base configurées", ["Classe", "Rôle", "Terre", "Feu", "Air", "Eau", "PV", "Régén.¹"], attributes),
    ABILITIES: table("Effets des pouvoirs configurés", ["Classe", "Cible", "Effet actuel", "Fidélité"], abilities),
    STADIUMS: table("Règles des stades activés", ["Stade", "Tours", "Par période", "Charges / joueur", "Placement / ordres", "Régénération", "Pouvoirs"], stadiums),
    FORMULAS: table("Calculs de remplacement actuellement configurés", ["Mécanique", "Calcul"], formulas),
    UNRESOLVED: registry.unresolved.map((question) => {
      if (!copy.unresolved[question]) throw new Error(`Translate unresolved rule: ${question}`);
      return `<li>${escape(copy.unresolved[question])}</li>`;
    }).join(""),
    RULEBOOK_ID: escape(registry.id), EVIDENCE_REVISION: escape(registry.evidence_revision),
    REGENERATION: match.regenerate_between_turns ? "activée" : "désactivée",
    ORDERS: sim.ball.action_limited_attempts ? "Les tentatives de ramassage et de réception/interception sont limitées par les ordres Air ou Feu disponibles. Au sol, le Feu est utilisé en priorité pour préserver l’Air." : "Le profil actuel ne limite pas les tentatives par le budget d’ordres Air/Feu.",
  };
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (_, key) => {
    if (!(key in values)) throw new Error(`Unknown rules page placeholder: ${key}`);
    return values[key];
  });
}

function combatTable(policy, sim) {
  if (!policy.combat.official_effects) return `<p class="rules-notice">Le tableau de conséquences documenté est désactivé dans ce profil. Le modèle antérieur applique ${escape(sim.combat.duel.damage_on_win)} PV de base sur une victoire et ${escape(sim.combat.duel.damage_on_tie)} en cas d’égalité, avec ses modificateurs expérimentaux.</p>`;
  const thresholds = policy.combat.boundary === "lower" ? "À égalité, 15 reste dans le niveau normal et 30 dans le niveau large." : "À égalité, 15 passe dans le niveau large et 30 dans le niveau critique.";
  const random = policy.combat.random_score;
  const distribution = random ? `Le score intrinsèque reste un remplacement. Un tirage logistique reproductible d’échelle ${number(random.scale)} est ajouté à la différence des scores ; sa courbe approche les probabilités décrites dans les archives, mais l’image d’origine reste introuvable.` : 'Le score de victoire utilise le modèle déterministe de remplacement.';
  return `<p class="rules-notice">${escape(distribution)}</p>` + table("Conséquences des combats dans le profil actif", ["Victoire", "Normale", "Large", "Critique"], [
    ["Contact ciblé", "1 PV + étourdissement", "3 PV + au sol", "5 PV + au sol"],
    ["Contact incident", "0 PV + étourdissement", "2 PV + étourdissement", "4 PV + étourdissement"],
    ["Esquive", "0 PV + étourdissement", "2 PV + étourdissement", `4 PV + ${policy.combat.critical_dodge_down ? "au sol" : "étourdissement"}`],
  ]) + `<p class="rules-notice">Les dégâts sont documentés ; le score qui choisit la ligne est provisoire. ${escape(thresholds)} Ces égalités et le départage à zéro ne sont pas certifiés. Après une victoire large ou critique, le bonus de prochain combat vaut actuellement ${escape(policy.combat.next_bonus)} point(s) du score de remplacement ; il ne s’accumule pas indéfiniment et expire en fin de tour.</p>`;
}
