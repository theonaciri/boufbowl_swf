/* Shared navigation, tab-scoped authentication and safe DOM helpers. */
window.AdminConsole = (() => {
  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const date = (value) =>
    value
      ? new Date(value * 1000).toLocaleString([], {
          dateStyle: "medium",
          timeStyle: "short",
        })
      : "Indefinite";
  const number = (value) => new Intl.NumberFormat().format(value ?? 0);
  let token = sessionStorage.getItem("boufbowl-admin-session") || "";
  async function api(action, fields = {}) {
    const response = await fetch("api/admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session: token, action, ...fields }),
      cache: "no-store",
    });
    if (!response.ok) throw Error("Server returned HTTP " + response.status);
    const data = await response.json();
    if (!data.ok) throw Error(data.error || "Request failed");
    return data;
  }
  const nav = el("header", null, "admin-nav");
  const brand = el("a", null, "brand");
  brand.href = "admin.html";
  brand.append(el("span", "B", "brand-mark"), el("span", "BOUFBOWL"));
  const links = el("nav");
  links.setAttribute("aria-label", "Pages d’administration");
  for (const [href, label] of [
    ["admin.html", "Vue d’ensemble"],
    ["website-activity.html", "Site web"],
    ["moderation.html", "Modération"],
    ["tournaments.html", "Tournois"],
    ["assets-admin.html", "Assets"],
  ]) {
    const link = el("a", label);
    link.href = href;
    if (location.pathname.endsWith("/" + href))
      link.setAttribute("aria-current", "page");
    links.append(link);
  }
  const right = el("div", null, "nav-right");
  right.append(el("span", "ADMIN CONSOLE", "eyebrow"));
  const signout = el("button", "Déconnexion", "secondary small");
  signout.hidden = !token;
  window.addEventListener("admin-session-changed", () => {
    token = sessionStorage.getItem("boufbowl-admin-session") || "";
    signout.hidden = !token;
  });
  signout.onclick = () => {
    sessionStorage.removeItem("boufbowl-admin-session");
    location.reload();
  };
  right.append(signout);
  nav.append(brand, links, right);
  document.body.prepend(nav);
  const legalFooter = el("footer", null, "admin-legal-footer");
  for (const [href, label] of [["legal.html", "Informations juridiques"], ["confidentialite.html", "Confidentialité"], ["conditions-utilisation.html", "CGU"]]) {
    const link = el("a", label); link.href = href; legalFooter.append(link);
  }
  document.body.append(legalFooter);
  let onReady;
  async function connect() {
    try {
      const data = await api(
        document.body.dataset.console === "activity" ? "website_activity" : document.body.dataset.console === "assets" ? "assets" : document.body.dataset.console === "tournaments"
          ? "tournaments"
          : "moderation",
      );
      $("console-login").hidden = true;
      $("console-main").hidden = false;
      signout.hidden = false;
      sessionStorage.setItem("boufbowl-admin-session", token);
      $("console-error").textContent = "";
      await onReady(data);
    } catch (error) {
      $("console-error").textContent = error.message;
    }
  }
  function init(callback) {
    onReady = callback;
    $("console-account").onsubmit = async (event) => {
      event.preventDefault();
      const button = event.submitter;
      button.disabled = true;
      $("console-error").textContent = "Signing in…";
      try {
        const r = await fetch("api/account", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "login",
            username: $("console-username").value,
            password: $("console-password").value,
          }),
        });
        const data = await r.json();
        if (!data.ok) throw Error(data.error);
        token = data.session;
        $("console-password").value = "";
        await connect();
      } catch (error) {
        $("console-error").textContent = error.message;
      } finally {
        button.disabled = false;
      }
    };
    $("console-device").onsubmit = async (event) => {
      event.preventDefault();
      token = $("console-session").value.trim();
      $("console-session").value = "";
      await connect();
    };
    if (token) connect();
  }
  function stats(node, items) {
    node.replaceChildren(
      ...items.map(([label, value, sub]) => {
        const card = el("div", null, "stat");
        card.append(
          el("small", label),
          el("strong", number(value)),
          el("div", sub, "sub"),
        );
        return card;
      }),
    );
  }
  function chart(node, activity) {
    node.replaceChildren();
    const buckets = Array.from({ length: 24 }, (_, i) => ({
      hour: Math.floor(Date.now() / 3600000) * 3600 - (23 - i) * 3600,
      count: 0,
    }));
    for (const bucket of buckets)
      bucket.count = activity.find((r) => r.hour === bucket.hour)?.count || 0;
    const max = Math.max(1, ...buckets.map((r) => r.count));
    for (const row of buckets) {
      const bar = el("div", null, "bar");
      bar.style.height = Math.max(3, (row.count / max) * 100) + "%";
      bar.title = date(row.hour) + " · " + number(row.count) + " messages";
      node.append(bar);
    }
  }
  function status(error) {
    $("page-status").textContent = error?.message || error || "";
  }
  function autoRefresh(container, callback) {
    const label = el("label", "Actualisation automatique ");
    const select = el("select");
    select.setAttribute("aria-label", "Intervalle d’actualisation automatique");
    for (const [value, text] of [[0,"Désactivée"],[5,"5 secondes"],[10,"10 secondes"],[30,"30 secondes"],[60,"1 minute"],[300,"5 minutes"]]) {
      const option = el("option", text); option.value = value; select.append(option);
    }
    let timer = null;
    select.onchange = () => {
      clearInterval(timer); timer = null;
      const seconds = Number(select.value);
      if (seconds) timer = setInterval(() => { if (!document.hidden) callback(); }, seconds * 1000);
    };
    label.append(select); container.append(label);
  }
  return { $, el, date, number, api, init, stats, chart, status, autoRefresh };
})();
