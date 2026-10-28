(() => {
  const $ = id => document.getElementById(id);
  const number = value => value == null ? "—" : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(value);
  const date = value => value ? new Date(value * 1000).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC" : "—";
  const duration = value => value == null ? "—" : value < 60 ? `${number(value)} s` : `${number(value / 60)} min`;
  const el = (tag, text, className) => { const node = document.createElement(tag); if (text != null) node.textContent = text; if (className) node.className = className; return node; };
  let session = sessionStorage.getItem("boufbowl-admin-session") || "", latest = null, busy = false, selected = null;
  const series = { active_users: { label: "Profils actifs", color: "#97e7c2", on: true }, peak_online: { label: "Pic en ligne", color: "#efd194", on: true } };
  async function api(route, body) {
    const response = await fetch("api/" + route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), cache: "no-store" });
    if (!response.ok) throw Error("Le serveur a répondu HTTP " + response.status);
    const result = await response.json();
    if (!result.ok) throw Error(result.error || "La demande a échoué.");
    return result;
  }
  function table(id, columns, rows) {
    const target = $(id); target.replaceChildren();
    if (!rows.length) { target.textContent = "Aucune donnée pour cette période."; return; }
    const node = el("table"), head = el("thead"), header = el("tr"), body = el("tbody");
    for (const [label] of columns) { const th = el("th", label); th.scope = "col"; header.append(th); }
    head.append(header); node.append(head);
    for (const item of rows) { const row = el("tr"); for (const [, value] of columns) row.append(el("td", String(value(item) ?? "—"))); body.append(row); }
    node.append(body); target.append(node);
  }
  function card(container, label, value, explanation, href) {
    const node = el("div", null, "overview-card"); node.append(el("span", label, "card-label"), el("strong", number(value)), el("small", explanation));
    if (href) { const link = el("a", "Voir le détail →", "card-link"); link.href = href; node.append(link); }
    container.append(node);
  }
  function comparison(current, previous, start, end) {
    if (previous == null) return "Période précédente indisponible";
    const change = current - previous;
    return `${change > 0 ? "+" : ""}${number(change)} vs période précédente (${start} au ${end}, fin exclue)`;
  }
  function svg(name, attributes, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text != null) node.textContent = text;
    return node;
  }
  function activityChart(rows) {
    const graph = $("chart"); graph.replaceChildren();
    if (!rows.length) { graph.append(svg("text", { x: 40, y: 100, fill: "#91a7ac" }, "Aucune donnée pour cette période.")); return; }
    const enabled = Object.keys(series).filter(key => series[key].on);
    const max = Math.max(1, ...rows.flatMap(row => enabled.map(key => row[key] ?? 0)));
    const x = index => 55 + index * 900 / Math.max(1, rows.length - 1), y = value => 190 - value * 150 / max;
    for (let i = 0; i <= 4; i++) {
      const value = max * i / 4;
      graph.append(svg("line", { x1: 55, x2: 955, y1: y(value), y2: y(value), stroke: "#2b3b3f" }), svg("text", { x: 45, y: y(value) + 4, "text-anchor": "end", fill: "#91a7ac", "font-size": 12 }, number(value)));
    }
    for (const key of enabled) {
      let path = "", previous = false;
      rows.forEach((row, i) => {
        if (row[key] == null) { previous = false; return; }
        path += `${previous ? "L" : "M"}${x(i)},${y(row[key])} `; previous = true;
      });
      graph.append(svg("path", { d: path, fill: "none", stroke: series[key].color, "stroke-width": 2.5, "stroke-linejoin": "round" }));
      if (rows.length <= 90) rows.forEach((row, i) => { if (row[key] != null) graph.append(svg("circle", { cx: x(i), cy: y(row[key]), r: 3, fill: series[key].color, class: "chart-dot" })); });
    }
    graph.append(svg("text", { x: 55, y: 220, fill: "#91a7ac", "font-size": 12 }, rows[0].day), svg("text", { x: 955, y: 220, "text-anchor": "end", fill: "#91a7ac", "font-size": 12 }, rows.at(-1).day));
    graph.setAttribute("tabindex", "0"); graph.setAttribute("aria-describedby", "chart-readout");
    const show = index => {
      selected = Math.max(0, Math.min(rows.length - 1, index));
      const row = rows[selected];
      $("chart-readout").textContent = `${row.day} · ${enabled.map(key => `${series[key].label} : ${number(row[key])}`).join(" · ") || "Aucune courbe sélectionnée"}`;
    };
    graph.onpointermove = event => { const box = graph.getBoundingClientRect(); show(Math.round(((event.clientX - box.left) / box.width * 1000 - 55) / 900 * (rows.length - 1))); };
    graph.onpointerdown = graph.onpointermove;
    graph.onfocus = () => show(selected ?? rows.length - 1);
    graph.onkeydown = event => { if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return; event.preventDefault(); show((selected ?? rows.length - 1) + (event.key === "ArrowLeft" ? -1 : 1)); };
  }
  function summaryValues(target, entries) {
    target.replaceChildren(); const numbers = el("div", null, "summary-numbers");
    for (const [label, value] of entries) { const item = el("div"); item.append(el("span", label), el("strong", value)); numbers.append(item); }
    target.append(numbers);
  }
  function render(data) {
    latest = data; $("login").hidden = true; $("dashboard").hidden = false;
    $("updated").textContent = "Actualisé le " + date(data.generated_at);
    const live = $("live-cards"), period = $("period-cards"); live.replaceChildren(); period.replaceChildren();
    card(live, "Profils en ligne", data.online, "Présence récente", "#engagement");
    card(live, "Matchs en cours", data.active_matches, "Tous modes confondus", "#matches");
    card(live, "En recherche", data.queued, "File de matchmaking", "#matches");
    card(live, "Erreurs signalées", data.errors.reduce((sum, error) => sum + error.count, 0), "Occurrences de la période · 50 groupes récents au maximum", "#technical");
    $("live-note").textContent = "Les erreurs couvrent la période sélectionnée ; les autres indicateurs montrent l’état actuel.";
    const cmp = data.comparison;
    card(period, "Profils actifs", data.usage.active_users, cmp?.activity_complete ? comparison(data.usage.active_users, cmp.active_profiles, cmp.start, cmp.end_exclusive) : "Comparaison indisponible : historique incomplet");
    card(period, "Profils de retour", data.usage.returning_users, "Actifs après leur premier jour observé");
    card(period, "Matchs commencés", data.matches.started, cmp ? comparison(data.matches.started, cmp.matches_started, cmp.start, cmp.end_exclusive) : "Sur la période", "#matches");
    card(period, "Pic en ligne", data.peak_online, "Présence maximale échantillonnée");
    activityChart(data.daily);
    table("activity-table", [["Jour UTC", r => r.day], ["Profils actifs", r => number(r.active_users)], ["Pic en ligne", r => number(r.peak_online)]], data.daily);
    $("history").textContent = "Avant le début de la collecte, l’historique est partiel. Collecte commencée le " + date(data.coverage.started_at) + ".";
    summaryValues($("match-summary"), [["Commencés", number(data.matches.started)], ["Contre l’ordinateur", number(data.matches.cpu)], ["Entre joueurs", number(data.matches.human)], ["Durée moyenne des matchs terminés", duration(data.matches.mean_duration_seconds)]]);
    const cohort = data.match_cohort;
    $("match-cohort").textContent = cohort ? `${number(cohort.started)} matchs commencés sur la période : ${number(cohort.completed_without_surrender)} terminés sans forfait, ${number(cohort.surrendered)} avec forfait, ${number(cohort.ongoing)} en cours. Proportion terminée, forfaits inclus : ${cohort.completion_rate == null ? "—" : number(cohort.completion_rate) + " %"}. Les matchs en cours peuvent encore se terminer ; une fin sans forfait peut inclure une interruption.` : "Détail des matchs de la période indisponible.";
    table("stadiums", [["Terrain", r => r.name || r.stadium], ["Matchs commencés", r => number(r.matches)]], data.matches.stadiums);
    const queueKinds = { regular: "Match libre", tournament: "Tournoi" }, outcomes = { matched: "Adversaire trouvé", cancelled: "Annulée", expired: "Expirée", tournament_closed: "Tournoi fermé", replaced: "Remplacée", other: "Autre" };
    table("queue-waits", [["Jour UTC", r => r.day], ["Type", r => queueKinds[r.kind] || r.kind], ["Résultat", r => outcomes[r.outcome] || r.outcome], ["Recherches", r => number(r.count)], ["Moyenne", r => duration(r.mean_seconds)], ["p50 ≤", r => duration(r.p50_upper_seconds)], ["p95 ≤", r => duration(r.p95_upper_seconds)]], data.queue_waits?.rows || []);
    $("queue-coverage").textContent = data.queue_waits ? `Collecte commencée le ${date(data.queue_waits.coverage_started_at)} ; pas d’historique avant cette date.` : "Les mesures de recherche ne sont pas disponibles.";
    const retention = $("retention"); retention.replaceChildren();
    for (const item of data.retention?.days || []) { const box = el("div", null, "retention-item"); box.append(el("span", `Jour ${item.day}`), el("strong", item.rate == null ? "—" : number(item.rate) + " %"), el("small", `${number(item.returned)} sur ${number(item.eligible)} profils éligibles`)); retention.append(box); }
    const cohortDates = data.retention?.cohort_start && data.retention.cohort_start <= data.retention.cohort_end ? `Cohorte : ${data.retention.cohort_start} au ${data.retention.cohort_end}.` : "Aucune journée de cohorte entièrement couverte.";
    $("retention-note").textContent = data.retention ? `${cohortDates} Collecte depuis ${date(data.retention.coverage_started_at)}. Le premier jour partiel et les jours de retour incomplets sont exclus. L’historique reconstitué n’est pas utilisé ; les suppressions et pertes d’activité peuvent rendre les comptes incomplets.` : "Données de retour indisponibles.";
    table("platforms", [["Plateforme", r => r.platform], ["Profils", r => number(r.users)], ["Clients", r => number(r.clients)]], data.platforms);
    table("versions", [["Jeu", r => r.game_version || "inconnu"], ["Moteur", r => r.runtime || "inconnu"], ["Version déclarée", r => r.runtime_version || "inconnue"], ["Profils", r => number(r.users)]], data.versions);
    const resources = data.resources;
    $("resources").textContent = resources ? `Serveur actif depuis ${duration(resources.uptime_seconds)} · mémoire Python ${number(resources.python_rss_mb)} Mo · simulateur ${number(resources.simulator_rss_mb)} Mo.` : "Aucune mesure récente du serveur.";
    $("error-summary").textContent = data.errors.length ? `${number(data.errors.length)} groupes d’erreurs récents dans la période. Consultez les diagnostics pour le détail.` : "Aucune erreur rapportée sur la période.";
    table("performance", [["Type", r => r.kind], ["Opération", r => r.name], ["Échantillons", r => number(r.count)], ["Erreurs", r => number(r.errors)], ["Moyenne ms", r => number(r.mean_ms)], ["p95 ≤ ms", r => number(r.p95_bucket_ms)], ["Maximum ms", r => number(r.max_ms)]], data.performance);
    table("daily", [["Jour", r => r.day], ["Actifs", r => number(r.active_users)], ["De retour", r => number(r.returning_users)], ["Nouveaux profils", r => number(r.new_profiles)], ["Nouveaux comptes", r => number(r.new_accounts)], ["Pic", r => number(r.peak_online)], ["Connexions", r => number(r.logins)], ["Requêtes", r => number(r.requests)], ["Reconnexions", r => number(r.reconnects)], ["Coupures", r => number(r.connection_gaps)], ["Temps estimé", r => duration(r.online_seconds)], ["Matchs commencés", r => number(r.matches_started)], ["Terminés", r => number(r.matches_completed)], ["Messages", r => number(r.chat_messages)]], data.daily);
    table("diagnostics", [["Joueur", r => r.nickname], ["Plateforme", r => r.platform], ["Moteur", r => r.runtime], ["Jeu", r => r.game_version], ["Version", r => r.runtime_version], ["OS hôte", r => r.host_os], ["OS déclaré", r => r.reported_os], ["Navigateur", r => r.browser], ["CPU", r => r.cpu], ["Écran", r => r.screen_width == null ? "—" : `${r.screen_width} × ${r.screen_height}`], ["GPU", r => r.gpu], ["Débogueur", r => r.debugger], ["Actualisé", r => date(r.updated)]], data.diagnostics);
    $("errors").replaceChildren(); if (!data.errors.length) $("errors").textContent = "Aucune erreur sur cette période.";
    for (const error of data.errors) { const details = el("details"), summary = el("summary", `${error.origin} · ${error.code} · ${number(error.count)} occurrences · ${date(error.last_seen)}`), pre = el("pre", [error.message, error.stack].filter(Boolean).join("\n")); details.append(summary, pre); $("errors").append(details); }
    $("online-note").textContent = "En ligne : présence avec une marge de 90 secondes. Les pics sont échantillonnés chaque seconde.";
    $("duration-note").textContent = "Le temps en ligne est estimé à partir des requêtes et ne mesure pas le jeu au premier plan.";
    $("latency").textContent = "La latence des longues requêtes inclut l’attente volontaire. Les p95 sont des bornes d’histogramme.";
    AdminGameMeasurements.render(data);
  }
  async function refresh() {
    if (busy || !session) return;
    busy = true; $("refresh").disabled = true; $("status").textContent = "Actualisation…";
    try {
      const data = await api("metrics", { session, days: Number($("days").value) }); render(data); $("status").textContent = "";
      try {
        const result = await api("admin", { session, action: "tournaments" });
        const next = result.tournaments.filter(t => (t.phase === "open" || t.phase === "upcoming") && t.settings.end_time * 1000 >= Date.now()).sort((a, b) => a.settings.start_time - b.settings.start_time)[0];
        $("next-tournament").textContent = next ? `${next.phase === "open" ? "Tournoi en cours" : "Prochain tournoi"} : ${next.settings.name || "Coupe du Boufbowl"} · ${date(next.settings.start_time)} · ${number(next.participants)} participants.` : "Aucun tournoi à venir.";
      } catch { $("next-tournament").textContent = "État des tournois indisponible."; }
    } catch (error) { $("status").textContent = latest ? `Actualisation interrompue : ${error.message}. Les dernières données restent affichées.` : error.message; }
    finally { busy = false; $("refresh").disabled = false; }
  }
  $("account").onsubmit = async event => {
    event.preventDefault(); $("status").textContent = "Connexion…";
    try { const result = await api("account", { action: "login", username: $("username").value, password: $("password").value }); session = result.session; sessionStorage.setItem("boufbowl-admin-session", session); window.dispatchEvent(new Event("admin-session-changed")); $("password").value = ""; await refresh(); }
    catch (error) { $("status").textContent = error.message; }
  };
  $("device").onsubmit = event => { event.preventDefault(); session = $("session").value.trim(); sessionStorage.setItem("boufbowl-admin-session", session); window.dispatchEvent(new Event("admin-session-changed")); $("session").value = ""; refresh(); };
  $("refresh").onclick = refresh; $("days").onchange = refresh;
  $("download").onclick = () => { if (!latest) return; const url = URL.createObjectURL(new Blob([JSON.stringify(latest, null, 2)], { type: "application/json" })), link = el("a"); link.href = url; link.download = `boufbowl-activite-${new Date().toISOString().slice(0, 10)}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
  for (const button of document.querySelectorAll("[data-series]")) button.onclick = () => { const item = series[button.dataset.series]; item.on = !item.on; button.setAttribute("aria-pressed", String(item.on)); if (latest) activityChart(latest.daily); };
  setInterval(() => { if ($("auto").checked && !document.hidden) refresh(); }, 60000);
  if (session) refresh();
})();
