(() => {
  const { $, api, init, date, number } = AdminConsole;
  const targets = {
    sections: ["Section", "Views", "Visible time"],
    classes: ["Class", "Selections"],
    characters: ["Character", "Selections"],
    downloads: ["Button", "Clicks"],
    web: ["Destination", "Clicks"],
    asset_requests: ["Asset path", "Requests"],
  };
  let busy = false;
  function seconds(value) {
    const n = Number(value || 0);
    return n < 60 ? `${n.toFixed(1)} s` : `${(n / 60).toFixed(1)} min`;
  }
  function table(node, rows, columns) {
    node.replaceChildren();
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    for (const label of columns) {
      const th = document.createElement("th");
      th.textContent = label;
      header.append(th);
    }
    head.append(header);
    table.append(head);
    const body = document.createElement("tbody");
    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = columns.length;
      td.textContent = "No activity recorded in this period.";
      tr.append(td);
      body.append(tr);
    }
    for (const row of rows) {
      const tr = document.createElement("tr");
      const values = [row.name, number(row.count)];
      if (row.views !== undefined) values.splice(1, 1, number(row.views), seconds(row.seconds));
      for (const value of values) {
        const td = document.createElement("td");
        td.textContent = String(value ?? "—");
        tr.append(td);
      }
      body.append(tr);
    }
    table.append(body);
    node.replaceChildren(table);
  }
  function render(data) {
    table($("website-sections"), data.sections, targets.sections);
    for (const key of ["classes", "characters", "downloads", "web", "asset_requests"])
      table($("website-" + key), data[key], targets[key]);
    $("website-updated").textContent = "Updated " + date(data.generated_at);
    $("website-coverage").textContent = data.coverage;
  }
  async function refresh() {
    if (busy) return;
    busy = true;
    $("website-refresh").disabled = true;
    $("website-status").textContent = "Loading…";
    try {
      const data = await api("website_tracking", { days: Number($("website-days").value) });
      render(data);
      $("website-status").textContent = "";
    } catch (error) {
      $("website-status").textContent = error.message;
    } finally {
      busy = false;
      $("website-refresh").disabled = false;
    }
  }
  init((data) => {
    render(data);
    $("website-refresh").onclick = refresh;
    $("website-days").onchange = refresh;
    setInterval(() => { if (!document.hidden) refresh(); }, 60000);
  });
})();
