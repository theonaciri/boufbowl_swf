(() => {
  const { $, el, date, number, api, init, stats, chart, status } = AdminConsole;
  let focus = null,
    busy = false,
    revision = 0,
    messages = new Map(),
    oldest = null,
    hasMore = false,
    metadataAt = 0,
    pending = null;
  function filters() {
    return {
      search: $("search").value,
      player: $("player-filter").value,
      kind: $("kind").value,
      language: $("language").value,
      ...(focus ? { focus } : {}),
    };
  }
  function clearFocus() {
    if (!focus) return;
    focus = null;
    $("conversation-focus").hidden = true;
    reset();
  }
  $("clear-focus").onclick = clearFocus;
  document.addEventListener("click", (event) => {
    if (
      focus &&
      !event.target.closest("#conversation-panel,dialog,#suspension-form")
    )
      clearFocus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("suspend-dialog").open) clearFocus();
  });
  $("refresh-feed").onclick = () => refresh(true);
  AdminConsole.autoRefresh($("auto-refresh"), () => refresh());
  let debounce;
  for (const id of ["search", "player-filter", "kind", "language"])
    $(id).addEventListener(
      id === "search" || id === "player-filter" ? "input" : "change",
      () => {
        clearTimeout(debounce);
        debounce = setTimeout(reset, 250);
      },
    );
  function reset() {
    revision++;
    messages.clear();
    oldest = null;
    hasMore = false;
    refresh(true);
  }
  function selectPlayer(name) {
    $("suspend-player").value = name;
    $("reason").focus();
  }
  function renderFeed() {
    const container = $("feed"),
      scroll = container.scrollTop;
    const rows = [...messages.values()].sort((a, b) => b.id - a.id);
    const nodes = rows.map((row) => {
      const card = el("article", null, "message"),
        time = el(
          "time",
          new Date(row.created * 1000).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        );
      time.title = date(row.created);
      time.dateTime = new Date(row.created * 1000).toISOString();
      const body = el("div"),
        meta = el("div", null, "meta");
      meta.append(el("span", row.sender_name, "name"));
      const kind = row.recipient
        ? "private"
        : row.match_id
          ? "match"
          : "public";
      meta.append(
        el(
          "span",
          kind === "private"
            ? "PRIVATE"
            : kind === "match"
              ? "MATCH #" + row.match_id
              : (row.language || "Public").toUpperCase(),
          "tag " + kind,
        ),
      );
      if (row.recipient)
        meta.append(el("span", "→ " + row.recipient_name, "muted"));
      body.append(meta, el("p", row.message));
      const button = el("button", "Suspend", "secondary small");
      button.setAttribute("aria-label", "Suspend " + row.sender_name);
      button.onclick = (event) => {
        event.stopPropagation();
        selectPlayer(row.sender_name);
      };
      card.append(time, body, button);
      if (kind !== "public") {
        card.dataset.focus = row.id;
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute(
          "aria-label",
          "View " +
            (kind === "private"
              ? row.sender_name + " and " + row.recipient_name + " conversation"
              : "match " + row.match_id + " conversation"),
        );
        const select = () => {
          focus = row.id;
          $("focus-label").textContent =
            kind === "private"
              ? row.sender_name + " ↔ " + row.recipient_name
              : "Match #" + row.match_id + " · all participants";
          $("conversation-focus").hidden = false;
          reset();
        };
        card.onclick = select;
        card.onkeydown = (event) => {
          if (
            event.target === card &&
            (event.key === "Enter" || event.key === " ")
          ) {
            event.preventDefault();
            select();
          }
        };
      }
      return card;
    });
    container.replaceChildren(
      ...(nodes.length
        ? nodes
        : [
            el(
              "div",
              "No messages match these filters. New messages will appear here.",
              "empty",
            ),
          ]),
    );
    container.scrollTop = scroll;
    $("older").hidden = !hasMore;
    oldest = rows.at(-1)?.id;
  }
  async function refresh(force = false, older = false) {
    if (busy) {
      if (force) setTimeout(() => refresh(true, older), 150);
      return;
    }
    busy = true;
    const requested = revision;
    try {
      const data = await api("messages", {
        ...filters(),
        ...(older && oldest ? { before: oldest } : {}),
      });
      if (requested !== revision) return;
      let changed = false;
      for (const row of data.messages) {
        if (!messages.has(row.id)) {
          messages.set(row.id, row);
          changed = true;
        }
      }
      if (!older && messages.size > 1500) {
        const keep = [...messages.values()]
          .sort((a, b) => b.id - a.id)
          .slice(0, 1500);
        messages = new Map(keep.map((r) => [r.id, r]));
        changed = true;
      }
      if (older || oldest === null) hasMore = data.has_more;
      if (changed || !messages.size) renderFeed();
      const c = data.counts;
      stats($("moderation-stats"), [
        ["Messages", c.total, "Last 24 hours"],
        ["Private messages", c.private, "Last 24 hours"],
        ["Match messages", c.match, "Last 24 hours"],
        ["Active senders", c.senders, "Last 24 hours"],
      ]);
      chart($("activity-chart"), data.activity);
      status("");
      if (Date.now() - metadataAt > 10000) {
        await metadata();
        metadataAt = Date.now();
      }
    } catch (error) {
      status(error);
    } finally {
      busy = false;
    }
  }
  async function metadata() {
    const data = await api("moderation");
    $("players").replaceChildren(
      ...data.players.map((p) => {
        const option = el("option");
        option.value = p.nickname;
        option.label = p.username
          ? p.nickname + " · @" + p.username
          : p.nickname;
        return option;
      }),
    );
    $("duration").querySelector('[value="0"]').disabled = data.role !== "admin";
    $("audit").replaceChildren(
      ...data.audit.map((row) => {
        const tr = el("tr");
        for (const value of [
          date(row.created),
          row.target_name,
          row.action === "ban"
            ? "Suspension"
            : row.action === "unban"
              ? "Reinstated"
              : row.action,
          row.actor_name || "Local operator",
          row.reason,
          row.action === "ban" ? date(row.expires) : "—",
        ])
          tr.append(el("td", value));
        return tr;
      }),
    );
    if (!data.audit.length) {
      const tr = el("tr"),
        td = el("td", "No moderation actions yet.");
      td.colSpan = 6;
      tr.append(td);
      $("audit").append(tr);
    }
    const sanctions = data.sanctions.filter((row) => row.kind === "ban");
    $("sanctions").replaceChildren(
      ...(sanctions.length
        ? sanctions.map((row) => {
            const entry = el("div", null, "side-entry");
            entry.append(
              el("strong", row.nickname),
              el("p", row.reason),
              el("p", "Until: " + date(row.expires)),
            );
            const button = el("button", "Lift suspension", "secondary small");
            button.onclick = async () => {
              button.disabled = true;
              try {
                await api("unsuspend", {
                  nickname: row.nickname,
                  reason: "Suspension lifted through admin console",
                });
                await metadata();
                status("Suspension lifted for " + row.nickname);
              } catch (error) {
                status(error);
              } finally {
                button.disabled = false;
              }
            };
            entry.append(button);
            return entry;
          })
        : [el("p", "No active suspensions.")]),
    );
    $("reports").replaceChildren(
      ...(data.reports.length
        ? data.reports.slice(0, 8).map((row) => {
            const entry = el("div", null, "side-entry");
            entry.append(
              el("strong", row.target),
              el("p", row.reason),
              el(
                "p",
                "Reported by " + row.reporter + " · " + date(row.created),
              ),
            );
            const button = el("button", "Review player", "secondary small");
            button.onclick = () => {
              $("player-filter").value = row.target;
              selectPlayer(row.target);
              reset();
            };
            entry.append(button);
            return entry;
          })
        : [el("p", "No player reports.")]),
    );
  }
  $("older").onclick = () => refresh(true, true);
  $("suspension-form").onsubmit = (event) => {
    event.preventDefault();
    pending = {
      nickname: $("suspend-player").value.trim(),
      duration: Number($("duration").value),
      reason: $("reason").value.trim(),
    };
    $("suspend-summary").textContent =
      pending.nickname +
      " will be suspended " +
      (pending.duration === 0
        ? "indefinitely"
        : pending.duration === 86400
          ? "for 1 day"
          : "for 7 days") +
      ". Active matches will be forfeited.";
    $("suspend-reason").textContent = "Reason: " + pending.reason;
    $("suspend-error").textContent = "";
    $("suspend-dialog").showModal();
  };
  $("cancel-suspend").onclick = () => $("suspend-dialog").close();
  $("confirm-suspend").onclick = async () => {
    const button = $("confirm-suspend");
    button.disabled = true;
    try {
      await api("suspend", pending);
      $("suspend-dialog").close();
      $("reason").value = "";
      await metadata();
      status("Suspended " + pending.nickname + ".");
    } catch (error) {
      $("suspend-error").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
  init(async () => {
    await metadata();
    await refresh(true);
  });
})();
