(() => {
  const { $, api, init } = AdminConsole;
  const number = value => new Intl.NumberFormat("fr-FR").format(value);
  const seconds = value => value < 60 ? `${number(Math.round(value))} s` : `${number(Math.round(value / 60))} min`;
  const labels = { hero: "Accueil", telecharger: "Télécharger", "le-jeu": "Le jeu", "le-chantier": "Restauration", vestiaires: "Vestiaires", benevoles: "Bénévoles", manifesto: "Le projet", "final-cta": "Invitation à jouer", desktop: "Linux", windows: "Windows", android: "Android", play: "Jeu web" };
  const name = value => labels[value] || value;
  const columns = {
    sections: ["Section", "Vues", "Temps visible cumulé"],
    classes: ["Classe", "Sélections"], characters: ["Personnage", "Sélections"],
    downloads: ["Bouton", "Clics"], web: ["Destination", "Clics"], asset_requests: ["Ressource", "Requêtes"],
  };
  let busy = false, latest = null;
  function table(node, rows, headings, section = false) {
    node.replaceChildren();
    if (!rows.length) { node.textContent = "Aucune activité enregistrée pour cette période."; return; }
    const table = document.createElement("table"), head = table.createTHead().insertRow();
    for (const label of headings) { const th = document.createElement("th"); th.scope = "col"; th.textContent = label; head.append(th); }
    const body = table.createTBody();
    for (const row of rows) {
      const tr = body.insertRow();
      const values = section ? [name(row.name), number(row.views), seconds(row.seconds)] : [name(row.name), number(row.count)];
      for (const value of values) tr.insertCell().textContent = value;
    }
    node.append(table);
  }
  function bars(node, selection, rows, value, describe, format) {
    node.replaceChildren();
    selection.textContent = "Sélectionnez une barre pour afficher son détail.";
    const visible = [...rows].sort((a, b) => value(b) - value(a)).slice(0, 10);
    if (!visible.length) { node.textContent = "Aucune activité enregistrée pour cette période."; selection.textContent = ""; return; }
    const max = Math.max(...visible.map(value), 1);
    for (const row of visible) {
      const button = document.createElement("button"), label = document.createElement("span"), track = document.createElement("span"), fill = document.createElement("span"), count = document.createElement("strong");
      button.type = "button"; button.className = "website-bar"; button.setAttribute("aria-pressed", "false");
      label.textContent = name(row.name); track.className = "website-track"; fill.className = "website-fill";
      fill.style.width = `${100 * value(row) / max}%`; count.textContent = format(value(row));
      track.append(fill); button.append(label, track, count);
      button.setAttribute("aria-label", describe(row));
      button.onclick = () => {
        for (const item of node.querySelectorAll("button")) item.setAttribute("aria-pressed", String(item === button));
        selection.textContent = describe(row);
      };
      node.append(button);
    }
  }
  function charts() {
    const metric = $("website-section-metric").value;
    bars($("website-section-bars"), $("website-section-selection"), latest.sections, row => row[metric],
      row => `${name(row.name)} : ${number(row.views)} vues, ${seconds(row.seconds)} de temps visible cumulé.`,
      metric === "views" ? number : seconds);
    const kind = $("website-interest-kind").value;
    bars($("website-interest-bars"), $("website-interest-selection"), latest[kind], row => row.count,
      row => `${name(row.name)} : ${number(row.count)} sélections.`, number);
  }
  function render(data) {
    latest = data;
    const stats = [
      ["Vues de sections", data.sections.reduce((sum, row) => sum + row.views, 0), "Affichages, pas visiteurs"],
      ["Clics de téléchargement", data.downloads.reduce((sum, row) => sum + row.count, 0), "Installations non mesurées"],
      ["Clics vers le jeu web", data.web.reduce((sum, row) => sum + row.count, 0), "Parties non mesurées"],
    ];
    $("website-stats").replaceChildren(...stats.map(([label, count, hint]) => {
      const card = document.createElement("div"), heading = document.createElement("small"), value = document.createElement("strong"), detail = document.createElement("div");
      card.className = "stat"; heading.textContent = label; value.textContent = number(count); detail.className = "sub"; detail.textContent = hint;
      card.append(heading, value, detail); return card;
    }));
    table($("website-sections"), data.sections, columns.sections, true);
    for (const key of ["classes", "characters", "downloads", "web", "asset_requests"]) table($("website-" + key), data[key], columns[key]);
    charts();
    $("website-updated").textContent = "Actualisé le " + new Date(data.generated_at * 1000).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC";
  }
  async function refresh() {
    if (busy) return;
    busy = true; $("website-refresh").disabled = true; $("website-status").textContent = "Chargement…";
    try {
      render(await api("website_activity", { days: Number($("website-days").value) }));
      $("website-status").textContent = "";
    } catch (error) {
      $("website-status").textContent = "Actualisation impossible. " + (latest ? "Les dernières données restent affichées. " : "") + error.message;
    } finally { busy = false; $("website-refresh").disabled = false; }
  }
  $("website-refresh").onclick = refresh;
  $("website-days").onchange = refresh;
  $("website-section-metric").onchange = charts;
  $("website-interest-kind").onchange = charts;
  init(data => { render(data); setInterval(() => { if (!document.hidden) refresh(); }, 60000); });
})();
