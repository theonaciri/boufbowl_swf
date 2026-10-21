/* Aggregate-only public-site activity; no visitor identifier is sent. */
(() => {
  const endpoint = "api/site-events";
  const pending = [];
  const visible = new Map();
  const countedSections = new Set();
  let timer = 0;

  function flush() {
    clearTimeout(timer);
    timer = 0;
    if (!pending.length) return;
    const events = pending.splice(0, 40);
    const body = JSON.stringify({ events });
    const payload = new Blob([body], { type: "application/json" });
    if (!navigator.sendBeacon?.(endpoint, payload)) {
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
        credentials: "same-origin",
      }).catch(() => {});
    }
    if (pending.length) timer = setTimeout(flush, 0);
  }

  function record(kind, name, duration_ms) {
    if (typeof name !== "string" || !name) return;
    pending.push({ kind, name, ...(duration_ms == null ? {} : { duration_ms }) });
    if (pending.length >= 20) flush();
    else if (!timer) timer = setTimeout(flush, 1200);
  }

  window.SiteActivity = {
    classInterest(name) { record("class_interest", name); },
    characterInterest(name) { record("character_interest", name); },
  };

  const sections = [...document.querySelectorAll("main > section")];
  const sectionName = (section) => {
    if (section.id) return section.id;
    if (section.classList.contains("hero")) return "hero";
    if (section.classList.contains("manifesto-section")) return "manifesto";
    if (section.classList.contains("final-cta")) return "final-cta";
    return "";
  };
  const observer = new IntersectionObserver((entries) => {
    const now = performance.now();
    for (const entry of entries) {
      const name = sectionName(entry.target);
      if (!name) continue;
      // Measure intersection with the viewport. A fixed fraction of a very
      // tall section may never fit on screen, even while the visitor scrolls it.
      if (entry.isIntersecting) {
        if (!visible.has(name)) visible.set(name, now);
        if (!countedSections.has(name)) {
          countedSections.add(name);
          record("section_view", name);
        }
      } else if (visible.has(name)) {
        const elapsed = Math.round(now - visible.get(name));
        visible.delete(name);
        if (elapsed >= 800) record("section_time", name, elapsed);
      }
    }
  }, { threshold: [0, 0.25] });
  for (const section of sections) observer.observe(section);

  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a") : null;
    if (!link) return;
    const downloads = {
      "download-desktop": "desktop",
      "download-windows": "windows",
      "download-android": "android",
    };
    if (downloads[link.id]) {
      record("download_click", downloads[link.id]);
      flush();
      return;
    }
    try {
      const destination = new URL(link.href, location.href);
      if (destination.origin === location.origin && destination.pathname.endsWith("/play.html")) {
        record("web_click", "play");
        flush();
      }
    } catch (_) {}
  }, true);

  window.addEventListener("pagehide", () => {
    const now = performance.now();
    for (const [name, started] of visible) {
      const elapsed = Math.round(now - started);
      if (elapsed >= 800) record("section_time", name, elapsed);
    }
    visible.clear();
    flush();
  });
})();
