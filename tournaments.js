(() => {
  const { $, el, date, number, api, init, stats, status } = AdminConsole;
  let data = null,
    tab = "current",
    selected = null,
    pending = null,
    busy = false;
  const form = $("schedule-form"),
    field = (name) => form.elements.namedItem(name);
  const phaseLabel = (phase) =>
    ({
      open: "Running",
      upcoming: "Upcoming",
      closing: "Finishing matches",
      ended: "Completed",
    })[phase] || phase;
  const stadiumName = (id) =>
    data?.stadiums.find((s) => s.id === id)?.name.replaceAll("_", " ") ||
    "Stadium " + id;
  const duration = (seconds) => {
    for (const [size, unit] of [
      [86400, "day"],
      [3600, "hour"],
      [60, "minute"],
    ]) {
      if (seconds >= size || size === 60) {
        const count = Math.max(1, Math.floor(seconds / size));
        return count + " " + unit + (count === 1 ? "" : "s");
      }
    }
  };
  function summary(cfg) {
    const box = el("div");
    for (const text of [
      cfg.name || "Tournament #" + cfg.id,
      date(cfg.start_time) + " → " + date(cfg.end_time),
      cfg.repeat_seconds
        ? "Repeats every " + duration(cfg.repeat_seconds)
        : "One-time event",
      stadiumName(cfg.stadium) + " · " + cfg.format,
      number(cfg.min_rating || 0) +
        "–" +
        number(cfg.max_rating ?? 100000) +
        " rating",
      cfg.prizes
        ? "Champion: " +
          number(cfg.prizes.glory) +
          " glory · " +
          number(cfg.prizes.influence) +
          " influence · " +
          number(cfg.prizes.coins) +
          " coins"
        : "Standard reward bands",
    ])
      box.append(el("p", text));
    return box;
  }
  function render() {
    const events = data.tournaments,
      current = events.filter((e) => ["open", "closing"].includes(e.phase)),
      next = events
        .filter((e) => e.phase === "upcoming")
        .sort((a, b) => a.settings.start_time - b.settings.start_time),
      past = events.filter((e) => e.phase === "ended");
    stats($("tournament-stats"), [
      ["Running", current.length, "Including matches finishing"],
      ["Upcoming", next.length, "Scheduled occurrences"],
      [
        "Participants",
        current.reduce((sum, e) => sum + e.participants, 0),
        "Across running tournaments",
      ],
      ["Completed", past.length, "Most recent 100 events"],
    ]);
    const rows = tab === "current" ? current : tab === "upcoming" ? next : past;
    if (!rows.some((e) => e.id === selected)) selected = rows[0]?.id || null;
    $("events").replaceChildren(
      ...(rows.length
        ? rows.map((event) => {
            const cfg = event.settings,
              card = el(
                "article",
                null,
                "event-card" + (event.id === selected ? " selected" : ""),
              );
            card.tabIndex = 0;
            card.setAttribute("role", "button");
            card.setAttribute(
              "aria-label",
              "View " + (cfg.name || "Tournament #" + event.id),
            );
            card.setAttribute("aria-pressed", String(selected === event.id));
            const head = el("div", null, "event-head");
            head.append(
              el("h3", cfg.name || "Tournament #" + event.id),
              el("span", phaseLabel(event.phase), "tag " + event.phase),
            );
            card.append(
              head,
              el("p", date(cfg.start_time) + " → " + date(cfg.end_time)),
            );
            const info = el("div", null, "event-info");
            for (const text of [
              stadiumName(cfg.stadium),
              cfg.format === "elimination" ? "Knockout" : "League",
              number(event.participants) + " players",
              number(cfg.min_rating || 0) +
                "–" +
                number(cfg.max_rating ?? 100000) +
                " rating",
            ])
              info.append(el("span", text));
            card.append(info);
            const progress = el("div", null, "timeline"),
              fill = el("span");
            fill.style.width =
              Math.max(
                0,
                Math.min(
                  100,
                  ((data.generated_at - cfg.start_time) /
                    (cfg.end_time - cfg.start_time)) *
                    100,
                ),
              ) + "%";
            progress.append(fill);
            card.append(
              progress,
              el(
                "small",
                event.phase === "upcoming"
                  ? "Starts in " +
                      duration(Math.max(60, cfg.start_time - data.generated_at))
                  : event.phase === "open"
                    ? "Entry closes in " +
                      duration(Math.max(60, cfg.end_time - data.generated_at))
                    : event.phase === "closing"
                      ? "Waiting for active matches to finish"
                      : "Results finalized",
              ),
            );
            const select = () => {
              selected = event.id;
              render();
            };
            card.onclick = select;
            card.onkeydown = (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                select();
              }
            };
            return card;
          })
        : [
            el(
              "div",
              "No " +
                tab +
                " tournaments. Use the schedule builder to plan the next event.",
              "panel empty",
            ),
          ]),
    );
    $("event-detail").hidden = !selected;
    if (selected) details(events.find((e) => e.id === selected));
    $("published").replaceChildren(summary(data.schedule));
  }
  function details(event) {
    const cfg = event.settings;
    $("edit-event").hidden = !["upcoming", "open"].includes(event.phase);
    $("edit-event-form").hidden = true;
    $("detail-title").textContent = cfg.name || "Tournament #" + event.id;
    $("detail-phase").textContent = phaseLabel(event.phase);
    const rules = summary(cfg);
    if (cfg.match_rules) {
      const m = cfg.match_rules;
      rules.append(
        el(
          "p",
          `${m.turns_per_match} turns · ${m.turns_per_period} per period · ${m.planning_seconds}s planning · ${m.placement_seconds}s placement · ${m.class_ability_uses} class ability uses · regeneration ${m.regenerate_between_turns ? "on" : "off"}`,
        ),
      );
    }
    $("detail-rules").replaceChildren(rules);
    $("rounds").replaceChildren(
      ...(event.rounds.length
        ? event.rounds.map((r, i) =>
            el(
              "p",
              (r.label || "Round " + (i + 1)) +
                " · " +
                date(r.startTime / 1000) +
                " → " +
                date(r.endTime / 1000),
            ),
          )
        : [
            el(
              "p",
              "League format: matches count throughout the entry window.",
            ),
          ]),
    );
    $("matches").replaceChildren(
      ...(event.active_matches.length
        ? event.active_matches.map((m) =>
            el(
              "p",
              "#" +
                m.id +
                " · " +
                m.players.join(" vs ") +
                " · " +
                m.score.join(" : "),
            ),
          )
        : [el("p", "No matches currently in progress.")]),
    );
    $("standings").replaceChildren(
      ...event.standings.map((entry) => {
        const row = el("tr");
        for (const value of [
          entry.currentRank,
          entry.player.nickname,
          entry.tournamentPoints,
          entry.eliminated
            ? "Eliminated"
            : event.phase === "ended"
              ? "Final"
              : "In contention",
        ])
          row.append(el("td", value));
        return row;
      }),
    );
    if (!event.standings.length) {
      const row = el("tr"),
        cell = el("td", "No entrants yet.");
      cell.colSpan = 4;
      row.append(cell);
      $("standings").append(row);
    }
  }
  const editForm = $("edit-event-form");
  const localTime = seconds => {
    const d = new Date(seconds * 1000);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
  };
  $("edit-event").onclick = () => {
    const event = data.tournaments.find(item => item.id === selected), cfg = event.settings;
    editForm.elements.name.value = cfg.name || "";
    editForm.elements.start.value = localTime(cfg.start_time);
    editForm.elements.end.value = localTime(cfg.end_time);
    editForm.elements.stadium.replaceChildren(...data.stadiums.map(item => { const option = el("option", item.name); option.value = item.id; return option; }));
    editForm.elements.stadium.value = cfg.stadium;
    editForm.elements.start.disabled = editForm.elements.stadium.disabled = event.phase === "open";
    $("edit-event-error").textContent = ""; editForm.hidden = false;
  };
  $("cancel-edit-event").onclick = () => { editForm.hidden = true; };
  editForm.onsubmit = async event => {
    event.preventDefault();
    const submit = editForm.querySelector('[type="submit"]'); submit.disabled = true;
    try {
      data = await api("edit_tournament", { tournament_id: selected, settings: {
        name: editForm.elements.name.value, start_time: Math.floor(new Date(editForm.elements.start.value).getTime()/1000),
        end_time: Math.floor(new Date(editForm.elements.end.value).getTime()/1000), stadium: Number(editForm.elements.stadium.value)
      }});
      render(); status("Tournament updated.");
    } catch (error) { $("edit-event-error").textContent = error.message; }
    finally { submit.disabled = false; }
  };
  for (const button of document.querySelectorAll("[data-tab]"))
    button.onclick = () => {
      tab = button.dataset.tab;
      for (const b of document.querySelectorAll("[data-tab]"))
        b.setAttribute("aria-selected", String(b === button));
      render();
    };
  $("format").onchange = () =>
    ($("knockout").hidden = field("format").value !== "elimination");
  function settings() {
    const n = (name) => Number(field(name).value),
      start = new Date(field("start").value).getTime() / 1000;
    return {
      name: field("name").value.trim(),
      start_time: start,
      duration_seconds: n("minutes") * 60,
      repeat_seconds: n("repeat"),
      stadium: n("stadium"),
      format: field("format").value,
      min_rating: n("min_rating"),
      max_rating: n("max_rating"),
      qualification_seconds: n("qualification") * 60,
      qualifying_top: n("qualifying_top"),
      round_count: n("round_count"),
      round_seconds: n("round_minutes") * 60,
      win_points: n("win_points"),
      draw_points: n("draw_points"),
      loss_points: n("loss_points"),
      match_rules: {
        turns_per_match: n("turns_per_match"),
        turns_per_period: n("turns_per_period"),
        planning_seconds: n("planning_seconds"),
        placement_seconds: n("placement_seconds"),
        class_ability_uses: n("class_ability_uses"),
        regenerate_between_turns:
          field("regenerate_between_turns").value === "true",
      },
      prizes: {
        glory: n("glory"),
        influence: n("influence"),
        coins: n("coins"),
      },
    };
  }
  form.oninput = () => {
    const cfg = settings();
    $("schedule-preview").textContent = cfg.start_time
      ? "Preview: " +
        date(cfg.start_time) +
        " → " +
        date(cfg.start_time + cfg.duration_seconds) +
        (cfg.repeat_seconds
          ? " · every " + duration(cfg.repeat_seconds)
          : " · one-time")
      : "";
  };
  form.onsubmit = (event) => {
    event.preventDefault();
    pending = settings();
    pending.end_time = pending.start_time + pending.duration_seconds;
    const error =
      pending.start_time <= Date.now() / 1000
        ? "Choose a future start time."
        : pending.min_rating > pending.max_rating
          ? "Minimum rating must not exceed maximum rating."
          : pending.repeat_seconds &&
              pending.repeat_seconds < pending.duration_seconds
            ? "Recurrence must be at least the event duration."
            : pending.format === "elimination" &&
                (pending.qualification_seconds +
                  pending.round_count * pending.round_seconds >
                  pending.duration_seconds ||
                  pending.qualifying_top > 2 ** pending.round_count)
              ? "Qualification and knockout rounds must fit the duration and bracket capacity."
              : null;
    if (error) {
      status(error);
      return;
    }
    $("schedule-summary").replaceChildren(summary(pending));
    $("schedule-error").textContent = "";
    $("schedule-dialog").showModal();
  };
  $("cancel-schedule").onclick = () => $("schedule-dialog").close();
  $("confirm-schedule").onclick = async () => {
    const button = $("confirm-schedule");
    button.disabled = true;
    try {
      data = await api("schedule", { settings: pending });
      $("schedule-dialog").close();
      tab = "upcoming";
      for (const b of document.querySelectorAll("[data-tab]"))
        b.setAttribute("aria-selected", String(b.dataset.tab === tab));
      selected = null;
      render();
      status("Schedule published. Upcoming events now use these settings.");
    } catch (error) {
      $("schedule-error").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
  init(async (result) => {
    data = result;
    $("stadium").replaceChildren(
      ...data.stadiums.map((s) => {
        const option = el("option", stadiumName(s.id));
        option.value = s.id;
        return option;
      }),
    );
    const active = data.tournaments.filter((e) =>
      ["open", "closing"].includes(e.phase),
    );
    const next = Math.max(
      Date.now() / 1000 + 3600,
      ...active.map((e) => e.settings.end_time + 60),
    );
    const local = new Date(next * 1000);
    local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
    field("start").value = local.toISOString().slice(0, 16);
    form.oninput();
    render();
  });
  async function refreshTournaments() {
      if (busy || !data) return;
      busy = true;
      try {
        data = await api("tournaments");
        render();
      } catch (error) {
        status(error);
      } finally {
        busy = false;
      }
  }
  $("refresh-tournaments").onclick = refreshTournaments;
  AdminConsole.autoRefresh($("auto-refresh"), () => {
    if (editForm.hidden && !$("schedule-dialog").open) refreshTournaments();
  });
})();
