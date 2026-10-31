import { watchWebUpdates } from "./client-updates.js";
export const WEB_PRESETS = Object.freeze({
  balanced: Object.freeze({ fps: 30, quality: "medium" }),
  quality: Object.freeze({ fps: 60, quality: "high" }),
  performance: Object.freeze({ fps: 25, quality: "low" }),
});

export function displayPreset(name) {
  return Object.hasOwn(WEB_PRESETS, name) ? WEB_PRESETS[name] : WEB_PRESETS.balanced;
}

// URL is the experiment boundary; defaults preserve the normal player.
export function renderingExperiments(params) {
  const pick = (key, choices, fallback) => choices.includes(params.get(key)) ? params.get(key) : fallback;
  return {
    renderer: pick("renderBackend", ["auto", "webgpu", "wgpu-webgl", "webgl"], "auto"),
    detail: pick("triangleDetail", ["original", "quality", "low", "medium", "high"], "original"),
    cache: params.get("geometryCache") === "1",
    perspective: pick("perspective", ["subdivide", "native"], "subdivide"),
    diagnostics: params.get("renderDiagnostics") === "1",
  };
}

if (typeof document !== "undefined") (async () => {
  const status = document.getElementById("status");
  const game = document.getElementById("game");
  const fullscreenButton = document.getElementById("fullscreen");
  watchWebUpdates({version: typeof __CLIENT_VERSION__ === "undefined" ? "0.0.0" : __CLIENT_VERSION__,container:document.body});
  const launchOptions = new URLSearchParams(location.search);
  const experiment = renderingExperiments(launchOptions);
  const experimentForm = document.getElementById("render-experiments");
  for (const [name, value] of Object.entries({renderBackend:experiment.renderer,
    triangleDetail:experiment.detail,geometryCache:experiment.cache ? "1" : "0",
    perspective:experiment.perspective,renderDiagnostics:experiment.diagnostics ? "1" : "0"})) {
    experimentForm.elements.namedItem(name).value = value;
  }
  experimentForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const url = new URL(location.href);
    for (const [name, value] of new FormData(experimentForm)) url.searchParams.set(name, value);
    location.assign(url);
  });
  document.getElementById("reset-render-experiments").addEventListener("click", () => {
    const url = new URL(location.href);
    for (const name of ["renderBackend","triangleDetail","geometryCache","perspective","renderDiagnostics"])
      url.searchParams.delete(name);
    location.assign(url);
  });
  document.getElementById("display-options").hidden = false;
  const qualityChoice = document.getElementById("web-quality");
  let storedQuality;
  try { storedQuality = localStorage.getItem("boufbowl.webQuality"); } catch {}
  qualityChoice.value = Object.hasOwn(WEB_PRESETS, storedQuality) ? storedQuality : "balanced";
  const preset = displayPreset(qualityChoice.value);
  let drag = null;
  let suppressClickUntil = 0;
  fullscreenButton.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const rect = fullscreenButton.getBoundingClientRect();
    drag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      left: rect.left,
      top: rect.top,
      moved: false,
    };
    fullscreenButton.setPointerCapture(event.pointerId);
  });
  fullscreenButton.addEventListener("pointermove", (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 6) return;
    drag.moved = true;
    fullscreenButton.classList.add("is-dragging");
    fullscreenButton.style.left = `${Math.max(0, Math.min(innerWidth - fullscreenButton.offsetWidth, drag.left + dx))}px`;
    fullscreenButton.style.top = `${Math.max(0, Math.min(innerHeight - fullscreenButton.offsetHeight, drag.top + dy))}px`;
    fullscreenButton.style.right = "auto";
  });
  const finishDrag = (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (drag.moved) suppressClickUntil = Date.now() + 400;
    drag = null;
    fullscreenButton.classList.remove("is-dragging");
  };
  fullscreenButton.addEventListener("pointerup", finishDrag);
  fullscreenButton.addEventListener("pointercancel", finishDrag);
  fullscreenButton.addEventListener("click", async (event) => {
    if (Date.now() < suppressClickUntil) {
      event.preventDefault();
      return;
    }
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      } else if (game.requestFullscreen) {
        await game.requestFullscreen();
      } else {
        status.hidden = false;
        status.textContent =
          "Le plein écran n’est pas disponible dans ce navigateur. Sur iPhone, ouvrez cette page depuis l’écran d’accueil pour masquer les barres du navigateur.";
      }
    } catch (error) {
      status.hidden = false;
      status.textContent =
        "Le plein écran n’a pas pu être activé. Sur iPhone, ajoutez cette page à l’écran d’accueil pour une expérience sans barres du navigateur.";
      console.error(error);
    }
  });
  try {
    if (!window.RufflePlayer) {
      throw new Error(
        "Ruffle is missing. Install its self-hosted release in vendor/ruffle/.",
      );
    }
    const response = await fetch("api/client", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(
        "Restart the updated backend server, then reload this page.",
      );
    }
    const client = await response.json();
    const player = window.RufflePlayer.newest().createPlayer();
    game.appendChild(player);
    await player.load({
      url: client.url,
      allowScriptAccess: true,
      quality: preset.quality,
      ...(experiment.renderer === "auto" ? {} : {preferredRenderer: experiment.renderer}),
      backgroundExecutionMode: "none",
      scale: "showAll",
      forceScale: true,
      parameters: {
        lang: "fr",
        tuto: launchOptions.get("tuto") === "1" ? "1" : "0",
        mock: launchOptions.get("mock") === "1" ? "1" : "0",
        server: launchOptions.get("server") === "0" ? "0" : "1",
        scene3d: launchOptions.get("scene3d") === "0" ? "0" : "1",
        backend: location.origin,
        clientPlatform: "browser",
        clientRuntime: "ruffle",
        webFps: String(preset.fps),
        triangleDetail: experiment.detail,
        geometryCache: experiment.cache ? "1" : "0",
        perspective: experiment.perspective,
        renderDiagnostics: experiment.diagnostics ? "1" : "0",
        clientOS:
          navigator.userAgentData?.platform || navigator.platform || "",
        clientBrowser: (() => {
          for (const [token, name] of [
            ["Edg", "Edge"],
            ["OPR", "Opera"],
            ["Firefox", "Firefox"],
            ["Chrome", "Chrome"],
            ["Version", "Safari"],
          ]) {
            const match = navigator.userAgent.match(
              new RegExp(token + "/([\\d.]+)"),
            );
            if (match) return name + " " + match[1];
          }
          return "unknown";
        })(),
      },
    });
    status.hidden = true;
    const diagnostics = document.getElementById("render-diagnostics");
    if (experiment.perspective === "native") {
      document.getElementById("native-perspective-warning").hidden = false;
    }
    if (experiment.diagnostics) {
      diagnostics.hidden = false;
      const updateDiagnostics = () => {
        // Runtime initialization and older clients are an external boundary.
        let stats;
        try { stats = player.ruffle().callExternalInterface("browserRenderStats"); }
        catch { diagnostics.textContent = "Compteurs en attente du client expérimental…"; return; }
        diagnostics.textContent = stats ?
          `Demandé : ${experiment.renderer} · appels ${stats.calls} · cache ${stats.cacheHits} · triangles calculés ${stats.affineTriangles} · UVT natif ${stats.nativeCalls}` :
          "Compteurs indisponibles : reconstruire le client expérimental.";
      };
      updateDiagnostics();
      const timer = setInterval(updateDiagnostics, 2000);
      window.addEventListener("pagehide", () => clearInterval(timer), {once:true});
    }
    const reportVisibility = () => {
      try { player.ruffle().callExternalInterface("setMeasurementActive", !document.hidden); } catch {}
    };
    document.addEventListener("visibilitychange", reportVisibility);
    reportVisibility();
    fullscreenButton.hidden = false;
    document.getElementById("display-options").hidden = false;
    qualityChoice.addEventListener("change", () => {
      const next = displayPreset(qualityChoice.value);
      player.ruffle().callExternalInterface("setWebDisplay", next.fps, next.quality);
      try { localStorage.setItem("boufbowl.webQuality", qualityChoice.value); } catch {}
      player.focus();
    });
  } catch (error) {
    status.textContent = "Unable to load Boufbowl: " + error.message;
    console.error(error);
  }
})();
