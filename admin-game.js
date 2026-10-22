/* Dependency-free game charts. All labels use text nodes, including reports. */
(() => {
  const colors = ["#75ddc6", "#f0cd87", "#a8baff", "#ee93b5", "#88c7ff"];
  const metrics = {
    fps: ["Measured frame-event FPS", "FPS"],
    p95_frame_ms: ["p95 frame interval upper bound", "ms"],
    slow_percent: ["Slow frames", "%"],
    fall_percent: ["Falls / risky movement tests", "%"],
    pass_percent: ["Completed / attempted passes", "%"],
    falls: ["Falls", "events"], goals: ["Goals", "events"],
    interceptions: ["Interceptions", "events"], passes: ["Pass attempts", "events"],
  };
  const number = value => value == null ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
  const element = (name, text) => { const node = document.createElement(name); if (text != null) node.textContent = text; return node; };
  function svgElement(name, attrs = {}, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text != null) node.textContent = text;
    return node;
  }
  function chart(id, days, series, label, unit) {
    const svg = document.getElementById(id);
    svg.replaceChildren();
    svg.setAttribute("aria-label", label);
    const values = series.flatMap(s => s.values.filter(v => v != null && Number.isFinite(v)));
    if (!values.length) { svg.append(svgElement("text", { x: 40, y: 105, fill: "#aebdc3" }, "No measured data in this period.")); return; }
    const maximum = Math.max(1, ...values) * 1.1;
    const x = i => 65 + i * 825 / Math.max(1, days.length - 1);
    const y = value => 190 - value * 145 / maximum;
    for (let i = 0; i <= 4; i++) {
      const value = maximum * i / 4;
      svg.append(svgElement("line", { x1: 65, x2: 890, y1: y(value), y2: y(value), stroke: "#35434b" }));
      svg.append(svgElement("text", { x: 58, y: y(value) + 4, "text-anchor": "end", fill: "#aebdc3", "font-size": 12 }, number(value)));
    }
    svg.append(svgElement("text", { x: 65, y: 20, fill: "#aebdc3" }, unit));
    series.forEach((s, index) => {
      const color = colors[index % colors.length];
      let path = "", previous = false;
      s.values.forEach((value, i) => {
        if (value == null) { previous = false; return; }
        path += `${previous ? "L" : "M"}${x(i)},${y(value)} `; previous = true;
        const dot = svgElement("circle", { cx: x(i), cy: y(value), r: 3, fill: color, tabindex: 0 });
        dot.append(svgElement("title", {}, `${days[i]} · ${s.name}: ${number(value)} ${unit}${s.notes?.[i] ? " · " + s.notes[i] : ""}`));
        svg.append(dot);
      });
      svg.prepend(svgElement("path", { d: path, fill: "none", stroke: color, "stroke-width": 2 }));
      svg.append(svgElement("text", { x: 65 + index * 185, y: 248, fill: color, "font-size": 12 }, s.name));
    });
    for (const index of new Set([0, Math.floor((days.length - 1) / 2), days.length - 1])) {
      svg.append(svgElement("text", { x: x(index), y: 217, "text-anchor": index ? "end" : "start", fill: "#aebdc3", "font-size": 12 }, days[index]));
    }
  }
  function table(id, headings, rows) {
    const target = document.getElementById(id); target.replaceChildren();
    if (!rows.length) { target.textContent = "No measured data in this period."; return; }
    const node = element("table"), header = element("tr");
    headings.forEach(heading => header.append(element("th", heading)));
    const head = element("thead"); head.append(header); node.append(head);
    const body = element("tbody");
    rows.forEach(values => { const row = element("tr"); values.forEach(value => row.append(element("td", value))); body.append(row); });
    node.append(body); target.append(node);
  }
  function combineFrames(rows) {
    const result = new Map();
    for (const row of rows) {
      const key = row.day + ":" + row.runtime;
      const item = result.get(key) || { day: row.day, runtime: row.runtime, frames: 0, elapsed_ms: 0, slow_frames: 0, samples: 0, p95_frame_ms: null };
      for (const name of ["frames", "elapsed_ms", "slow_frames", "samples"]) item[name] += row[name];
      // Histograms are not exposed here: use the worst platform p95 bound, not an average of percentiles.
      item.p95_frame_ms = Math.max(item.p95_frame_ms || 0, row.p95_frame_ms || 0);
      result.set(key, item);
    }
    return [...result.values()].map(row => ({ ...row, fps: row.frames * 1000 / row.elapsed_ms, slow_percent: row.slow_frames * 100 / row.frames }));
  }
  function gameplayTotals(rows) {
    return ["cpu", "human"].map(controller => {
      const item = { controller, team_turns: 0, moves: 0, risk_tests: 0, falls: 0, passes: 0, completed_passes: 0, interceptions: 0, goals: 0 };
      for (const row of rows.filter(r => r.controller === controller)) for (const key of Object.keys(item)) if (key !== "controller") item[key] += row[key];
      return { ...item, fall_percent: item.risk_tests ? item.falls * 100 / item.risk_tests : null, pass_percent: item.passes ? item.completed_passes * 100 / item.passes : null };
    }).filter(row => row.team_turns);
  }
  function render(data) {
    const game = data.game || { frames: [], gameplay: [], coverage: "Game measurement collection is unavailable on this server version." };
    const days = data.daily.map(row => row.day);
    document.getElementById("game-coverage").textContent = game.coverage + (game.started_at ? " Collection started " + new Date(game.started_at * 1000).toLocaleString() + "." : "");
    const phase = document.getElementById("game-phase").value;
    const metric = document.getElementById("game-frame-metric").value;
    const frames = combineFrames(game.frames.filter(row => row.phase === phase));
    const frameSeries = [...new Set(frames.map(row => row.runtime))].map(runtime => {
      const byDay = new Map(frames.filter(row => row.runtime === runtime).map(row => [row.day, row]));
      return { name: runtime, values: days.map(day => byDay.get(day)?.[metric] ?? null), notes: days.map(day => byDay.has(day) ? `${byDay.get(day).samples} windows, ${byDay.get(day).frames} frames` : "") };
    });
    const [frameLabel, frameUnit] = metrics[metric];
    chart("game-frames-chart", days, frameSeries, frameLabel + (metric === "p95_frame_ms" ? " (worst platform bound)" : ""), frameUnit);
    table("game-frame-details", ["UTC day", "Runtime / platform", "Phase", "Windows / frames", "Measured / target FPS", "p95 ≤ ms", "Slow %", "Max gap ms", "Peak runtime MB"],
      game.frames.map(row => [row.day, row.runtime + " / " + row.platform, row.phase, `${row.samples} / ${row.frames}`, `${number(row.fps)} / ${number(row.target_fps)}`, number(row.p95_frame_ms), number(row.slow_percent), number(row.max_frame_ms), number(row.memory_max_mb)]));
    const gameplayMetric = document.getElementById("game-play-metric").value;
    const [gameLabel, gameUnit] = metrics[gameplayMetric];
    chart("game-play-chart", days, ["cpu", "human"].map(controller => {
      const byDay = new Map(game.gameplay.filter(row => row.controller === controller).map(row => [row.day, row]));
      return { name: controller === "cpu" ? "CPU teams" : "Human teams", values: days.map(day => byDay.get(day)?.[gameplayMetric] ?? null), notes: days.map(day => byDay.has(day) ? `${byDay.get(day).team_turns} team-turns` : "") };
    }), gameLabel, gameUnit);
    table("game-play-details", ["Controller", "Team-turns", "Move steps", "Risk tests", "Falls", "Fall %", "Passes", "Completed", "Pass %", "Interceptions", "Goals"],
      gameplayTotals(game.gameplay).map(row => [row.controller, row.team_turns, row.moves, row.risk_tests, row.falls, number(row.fall_percent), row.passes, row.completed_passes, number(row.pass_percent), row.interceptions, row.goals]));
    chart("game-matches-chart", days, [["matches_started", "Started"], ["matches_completed", "Ended (includes surrender)"]].map(([key, name]) => ({ name, values: data.daily.map(row => row[key]) })), "Daily match starts and endings", "matches");
    const startup = data.performance.filter(row => row.kind === "game_startup");
    table("game-startup", ["SWF start → first server connection", "Samples", "Mean ms", "p95 ≤ ms"], startup.map(row => [row.name, row.count, number(row.mean_ms), number(row.p95_bucket_ms)]));
  }
  let latest;
  globalThis.AdminGameMeasurements = { combineFrames, gameplayTotals, render(data) {
    latest = data; render(data);
    for (const id of ["game-phase", "game-frame-metric", "game-play-metric"]) document.getElementById(id).onchange = () => render(latest);
  } };
})();
