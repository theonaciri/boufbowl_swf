import { assetUrl } from "./tools/website/asset-url.js";

(() => {
  const $ = (id) => document.getElementById(id);
  const section = $("tournois");
  if (!section) return;
  const events = $("tournament-events"), status = $("tournament-status"), dialog = $("tournament-login");
  const sessionKey = "boufbowl-tournament-session";
  let token = "", data = null, fingerprint = "", busy = false, pending = null, inventory;
  try { token = sessionStorage.getItem(sessionKey) || ""; } catch {}
  const saveToken = (value) => {
    token = value;
    try { value ? sessionStorage.setItem(sessionKey, value) : sessionStorage.removeItem(sessionKey); } catch {}
  };
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const date = (seconds) => new Date(seconds * 1000).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" });
  const phase = { open: "EN DIRECT", closing: "DERNIERS MATCHS", upcoming: "À VENIR" };
  async function request(url, body) {
    const response = await fetch(url, {
      method: body ? "POST" : "GET", cache: "no-store", signal: AbortSignal.timeout(15000),
      ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw Error("Le serveur des tournois est indisponible. Réessayez dans un instant.");
    const result = await response.json();
    if (!result.ok) {
      const error = Error(result.error || "La demande a échoué.");
      error.code = result.code;
      throw error;
    }
    return result;
  }
  function scheduleDate(label, seconds) {
    const line = el("div"), time = el("time", date(seconds));
    time.dateTime = new Date(seconds * 1000).toISOString();
    line.append(el("dt", label), el("dd"));
    line.lastChild.append(time);
    return line;
  }
  function rules(event) {
    const details = el("details", null, "tournament-rules"), summary = el("summary", "RÈGLES DU TOURNOI +");
    const list = el("ul"), m = event.match_rules;
    const lines = [
      event.format === "elimination" ? `Qualifications de ${Math.round(event.qualification_seconds / 60)} min, puis élimination directe. Les ${event.qualifying_top} meilleurs se qualifient.` : "Championnat : cumulez des points pendant toute la durée du tournoi.",
      `Victoire : ${event.points.win} pts · Nul : ${event.points.draw} pts · Défaite : ${event.points.loss} pts.`,
      event.min_rating === 0 && event.max_rating === 100000 ? "Ouvert à toutes les cotes. Entrée gratuite." : `Cote requise : ${event.min_rating} à ${event.max_rating}. Entrée gratuite.`,
      `${m.turns_per_match} tours par match · ${m.turns_per_period} par période.`,
      `Placement : ${m.placement_seconds} s · Préparation des ordres : ${m.planning_seconds} s.`,
      `${m.class_ability_uses} utilisation(s) de pouvoir de classe · Régénération entre les tours : ${m.regenerate_between_turns ? "oui" : "non"}.`,
    ];
    if (event.format === "elimination") lines.push("En cas d’égalité en phase finale, le classement des qualifications départage les joueurs.");
    list.append(...lines.map((text) => el("li", text)));
    details.append(summary, list);
    if (event.rounds.length) {
      const rounds = el("dl", null, "tournament-rounds");
      for (const [i, round] of event.rounds.entries()) {
        rounds.append(el("dt", i === 0 ? "Qualifications" : `Tour ${i}`), el("dd", `${date(round.startTime / 1000)} → ${date(round.endTime / 1000)}`));
      }
      details.append(rounds);
    }
    return details;
  }
  function standings(event) {
    const board = el("div", null, "tournament-leaderboard");
    board.append(el("h4", "LE TOP 10"), el("p", "Le top 5 à l’affiche. Les trois premières places sur le podium.", "tournament-small"));
    if (!event.standings.length) {
      board.append(el("p", "Le classement s’affichera dès l’arrivée des premiers participants. À vous d’ouvrir le score !", "tournament-empty"));
      return board;
    }
    const list = el("ol", null, "tournament-ranking");
    for (const player of event.standings) {
      const item = el("li", null, `tournament-rank rank-${player.rank}`), name = el("div", null, "tournament-player");
      item.value = player.rank;
      name.append(el("strong", player.nickname), el("span", player.club));
      if (player.eliminated) name.append(el("small", "Éliminé"));
      const points = el("span", `${player.points} pts`, "tournament-points");
      item.append(el("span", `#${player.rank}`, "tournament-place"), name, points);
      list.append(item);
    }
    board.append(list);
    return board;
  }
  function card(event) {
    const live = event.phase !== "upcoming", stadium = inventory.stadiums.find((s) => s.id === event.stadium);
    const article = el("article", null, `tournament-card${live ? " is-live" : ""}`);
    article.dataset.tournament = event.id;
    const information = el("div", null, "tournament-information");
    const map = el("figure", null, "tournament-map"), image = el("img");
    if (stadium) {
      image.src = assetUrl(stadium.image); image.alt = `Terrain du stade ${stadium.name}`;
      image.loading = "lazy"; image.width = 1015; image.height = 595;
      map.append(image, el("figcaption", stadium.name));
    } else map.append(el("figcaption", event.stadium));
    const body = el("div", null, "tournament-body"), title = el("div", null, "tournament-card-heading");
    title.append(el("span", phase[event.phase], "tournament-phase"), el("span", live ? `${event.participants} joueur(s)` : `${event.interested} présence(s) annoncée(s)`, "tournament-small"));
    const dates = el("dl", null, "tournament-dates");
    dates.append(scheduleDate("DÉBUT", event.start_time), scheduleDate("FIN", event.end_time));
    const action = el("button", event.participating ? "JE PARTICIPE ✓" : "JE PARTICIPE ↗", "button tournament-join");
    action.type = "button"; action.dataset.join = event.id;
    action.setAttribute("aria-pressed", String(event.participating));
    action.setAttribute("aria-label", `${event.participating ? "Annuler ma participation à" : "Annoncer ma participation à"} ${event.name}, ${date(event.start_time)}`);
    action.disabled = event.phase === "closing";
    if (action.disabled) action.textContent = "INSCRIPTIONS CLOSES";
    action.onclick = () => {
      if (!token) { pending = event.id; openLogin(); }
      else participate(event.id, !event.participating);
    };
    body.append(title, el("h3", event.name), el("p", event.format === "elimination" ? "QUALIFICATIONS + ÉLIMINATION DIRECTE" : "CHAMPIONNAT AUX POINTS", "tournament-format"), dates, rules(event), action);
    if (live) body.append(el("p", `${event.interested} présence(s) annoncée(s)`, "tournament-small"));
    information.append(map, body); article.append(information);
    if (live) article.append(standings(event));
    return article;
  }
  function render(result) {
    data = result;
    $("tournament-viewer").textContent = result.viewer ? `Bonjour ${result.viewer.nickname}` : "";
    $("tournament-signin").hidden = Boolean(result.viewer);
    $("tournament-signout").hidden = !result.viewer;
    const nextFingerprint = JSON.stringify([result.tournaments, result.viewer]);
    if (nextFingerprint === fingerprint) return;
    fingerprint = nextFingerprint;
    const openRules = new Set([...events.querySelectorAll("article:has(details[open])")].map((article) => article.dataset.tournament));
    const focused = document.activeElement?.dataset.join;
    const fragments = [];
    for (const [label, matches] of [
      ["LE TOURNOI EN COURS", result.tournaments.filter((e) => e.phase !== "upcoming").slice(0, 1)],
      ["LE PROCHAIN RENDEZ-VOUS", result.tournaments.filter((e) => e.phase === "upcoming").slice(0, 1)],
    ]) {
      if (!matches.length) continue;
      const group = el("div", null, "tournament-group"), cards = el("div", null, "tournament-cards");
      group.append(el("h3", label, "tournament-group-title"), cards);
      cards.append(...matches.map(card)); fragments.push(group);
    }
    if (!fragments.length) fragments.push(el("p", "Aucun tournoi annoncé pour le moment. Revenez bientôt pour le prochain coup d’envoi.", "tournament-empty"));
    events.replaceChildren(...fragments);
    for (const article of events.querySelectorAll("article")) if (openRules.has(article.dataset.tournament)) article.querySelector("details").open = true;
    if (focused) events.querySelector(`[data-join="${CSS.escape(focused)}"]`)?.focus({ preventScroll: true });
  }
  async function refresh() {
    if (busy) return;
    busy = true; $("tournament-refresh").disabled = true;
    try {
      inventory ||= await fetch(assetUrl("assets/site/restoration/inventory.json"), { signal: AbortSignal.timeout(15000) }).then((r) => {
        if (!r.ok) throw Error("Les terrains ne sont pas disponibles. Réessayez dans un instant.");
        return r.json();
      });
      let result;
      try { result = await request("api/tournaments", token ? { action: "list", session: token } : null); }
      catch (error) {
        if (!["SESSION_INVALID", "PLAYER_BANNED", "PLAYER_KICKED"].includes(error.code)) throw error;
        saveToken(""); result = await request("api/tournaments");
      }
      render(result);
      status.textContent = `Mis à jour à ${new Date(result.generated_at * 1000).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" })} · Horaires en heure de Paris (Europe/Paris).`;
    } catch (error) {
      status.textContent = data ? "Actualisation interrompue. Le dernier classement reste affiché ; réessayez dans un instant." : error.message;
    } finally { busy = false; events.setAttribute("aria-busy", "false"); $("tournament-refresh").disabled = false; }
  }
  async function participate(id, participating) {
    if (busy) return;
    busy = true;
    const button = events.querySelector(`[data-join="${CSS.escape(id)}"]`);
    if (button) button.disabled = true;
    try {
      render(await request("api/tournaments", { action: "participate", session: token, tournament_id: id, participating }));
      status.textContent = participating ? "Votre présence est annoncée ! Retrouvez ce tournoi dans le jeu au coup d’envoi." : "Votre annonce de participation est annulée.";
    } catch (error) {
      if (error.code === "SESSION_INVALID") { saveToken(""); pending = id; openLogin(); }
      status.textContent = error.message;
    } finally { busy = false; if (button?.isConnected) button.disabled = false; }
  }
  function openLogin() {
    $("tournament-login-status").textContent = "";
    dialog.showModal(); $("tournament-username").focus();
  }
  $("tournament-signin").onclick = () => { pending = null; openLogin(); };
  $("tournament-login-close").onclick = () => dialog.close();
  $("tournament-get-client").onclick = () => dialog.close();
  $("tournament-signout").onclick = async () => {
    if (busy) return;
    busy = true;
    try {
      render(await request("api/tournaments", { action: "logout", session: token }));
      saveToken(""); pending = null; status.textContent = "Vous êtes déconnecté de cette page.";
    } catch (error) { status.textContent = error.message; }
    finally { busy = false; }
  };
  $("tournament-login-form").onsubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget, submit = form.querySelector('[type="submit"]'); submit.disabled = true;
    $("tournament-login-status").textContent = "Connexion…";
    try {
      const result = await request("api/account", { action: "login", username: form.elements.username.value.trim(), password: form.elements.password.value, client: "website" });
      saveToken(result.session); form.elements.password.value = ""; dialog.close();
      const id = pending; pending = null;
      if (id) await participate(id, true); else await refresh();
    } catch (error) { $("tournament-login-status").textContent = error.code === "ACCOUNT_AUTH" ? "Nom de compte ou mot de passe incorrect." : error.message; }
    finally { submit.disabled = false; }
  };
  $("tournament-refresh").onclick = refresh;
  const observer = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return;
    observer.unobserve(section);
    if (!data) refresh();
  }, { rootMargin: "300px" });
  observer.observe(section);
})();
