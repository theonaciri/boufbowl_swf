(() => {
  const $ = (id) => document.getElementById(id), section = $("classement");
  if (!section) return;
  const refreshEvery = 30 * 60 * 1000;
  const players = $("ladder-players"), board = $("ladder-board"), status = $("ladder-status");
  let page = 1, pages = 1, loaded = false, busy = false, refreshTimer;
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  function controls() {
    $("ladder-prev").disabled = busy || !loaded || page === 1;
    $("ladder-next").disabled = busy || !loaded || page >= pages;
    $("ladder-refresh").disabled = busy;
  }
  function render(result) {
    page = result.page; pages = result.pages;
    players.replaceChildren(...result.players.map((player) => {
      const row = el("tr"), name = el("td"), rank = el("th", `#${player.rank}`, "ladder-rank");
      row.dataset.rank = player.rank; rank.scope = "row";
      name.append(el("strong", player.nickname), el("span", player.club, "ladder-club"), el("small", player.qualified ? `Ligue ${player.league}` : "En qualification", "ladder-league"));
      row.append(rank, name, el("td", player.rating.toLocaleString("fr-FR"), "ladder-rating"));
      for (const key of ["wins", "draws", "losses"]) row.append(el("td", player[key].toLocaleString("fr-FR"), "ladder-record"));
      return row;
    }));
    $("ladder-empty").hidden = result.total > 0;
    $("ladder-page").textContent = result.total ? `${(page - 1) * 10 + 1}–${(page - 1) * 10 + result.players.length} sur ${result.total} joueurs · Page ${page} / ${pages}` : "0 joueur · Page 1 / 1";
    loaded = true;
    const time = new Date(result.generated_at * 1000).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" });
    status.textContent = `Mis à jour à ${time} (heure de Paris).`;
  }
  async function load(target = page) {
    if (busy) return;
    busy = true; board.setAttribute("aria-busy", "true"); controls();
    try {
      const response = await fetch(`api/ladder?page=${target}`, { cache: "no-store", signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw Error();
      const result = await response.json();
      if (!result.ok) throw Error();
      render(result);
    } catch {
      status.textContent = loaded ? "Actualisation interrompue. Le dernier classement reste affiché. Réessayez avec « Actualiser »." : "Le classement est indisponible. Réessayez avec « Actualiser » dans un instant.";
    } finally {
      busy = false; board.setAttribute("aria-busy", "false"); controls();
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => load(), refreshEvery);
    }
  }
  $("ladder-prev").onclick = () => load(page - 1);
  $("ladder-next").onclick = () => load(page + 1);
  $("ladder-refresh").onclick = () => load();
  const observer = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return;
    observer.unobserve(section);
    if (!loaded) load();
  }, { rootMargin: "300px" });
  observer.observe(section);
})();
