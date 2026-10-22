export const WEB_PRESETS = Object.freeze({
  balanced: Object.freeze({ fps: 30, quality: "medium" }),
  quality: Object.freeze({ fps: 60, quality: "high" }),
  performance: Object.freeze({ fps: 25, quality: "low" }),
});

export function displayPreset(name) {
  return Object.hasOwn(WEB_PRESETS, name) ? WEB_PRESETS[name] : WEB_PRESETS.balanced;
}

if (typeof document !== "undefined") (async () => {
  const status = document.getElementById("status");
  const game = document.getElementById("game");
  const fullscreenButton = document.getElementById("fullscreen");
  const launchOptions = new URLSearchParams(location.search);
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
