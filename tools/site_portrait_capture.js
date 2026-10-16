// Export-only helpers. Never loaded by the public website or the playable client.
const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function createPortraitPlayer(mount, captureSWF) {
  const original = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, attributes) {
    return original.call(this, type, /webgl/.test(type)
      ? { ...attributes, preserveDrawingBuffer: true } : attributes);
  };
  try {
    const player = window.RufflePlayer.newest().createPlayer();
    player.style.cssText = "display:block;width:2048px;height:1200px";
    mount.append(player);
    await player.load({
      url: captureSWF,
      wmode: "transparent",
      allowScriptAccess: true,
      autoplay: "on",
      unmuteOverlay: "hidden",
      parameters: { lang: "fr", server: "0", mock: "0", tuto: "0" },
    });
    return player;
  } finally {
    HTMLCanvasElement.prototype.getContext = original;
  }
}

export async function capturePortrait(player, task) {
  const api = player.ruffle();
  api.resume();
  const request = task.id + ":" + crypto.randomUUID();
  const deadline = performance.now() + 60000;
  async function until(check, message) {
    while (performance.now() < deadline) {
      try { if (check()) return; } catch (error) {
        if (String(error).includes("ERROR:")) throw error;
      }
      await wait(20);
    }
    throw Error(message + ": " + task.id);
  }
  await until(() => {
    const ready = api.callExternalInterface("siteRender", task.cls, task.gender, task.hero, task.symbol,
      parseInt(task.colors.hair, 16), parseInt(task.colors.skin, 16), parseInt(task.colors.eyes, 16), request);
    if (String(ready).startsWith("ERROR:")) throw Error(ready);
    return ready === "READY";
  }, "Original illustration libraries did not load");
  const expectedLabel = "cg_" + (task.hero || task.cls * 10 + task.gender);
  const rendered = (frames) => {
    const status = String(api.callExternalInterface("siteStatus")).split("|");
    return status[0] === request && Number(status[1]) >= frames && status[2] === expectedLabel && status[3]?.split("::").pop() === task.native_group;
  };
  await until(() => rendered(1), "Requested native character frame did not initialize");
  const bounds = api.callExternalInterface("sitePreview");
  await until(() => rendered(2), "Requested pose did not finish rendering");
  await new Promise(requestAnimationFrame);
  await new Promise(requestAnimationFrame);
  const match = bounds.match(/w=([\d.]+), h=([\d.]+)/);
  if (!match) throw Error("Missing native pose bounds: " + bounds);
  const logicalWidth = Number(match[1]) * 500 / Number(match[2]);
  const output = document.createElement("canvas");
  output.width = Math.ceil(logicalWidth * 2) + 80;
  output.height = 1080;
  const source = player.shadowRoot.querySelector("canvas");
  const sourceScale = source.height / 600;
  async function webp() {
    const blob = await new Promise((resolve) => output.toBlob(resolve, "image/webp", 0.92));
    if (!blob || blob.type !== "image/webp") throw Error("WebP encoding unavailable");
    return {id: task.id, blob, width: output.width, height: output.height};
  }
  async function nativeFallback() {
    api.suspend();
    const png = api.callExternalInterface("sitePNG");
    if (!png || png.startsWith("ERROR")) throw Error(png);
    const bytes = Uint8Array.from(atob(png), (c) => c.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], {type: "image/png"}));
    output.width = bitmap.width; output.height = bitmap.height;
    output.getContext("2d").drawImage(bitmap, 0, 0);
    bitmap.close();
    const pixels = output.getContext("2d").getImageData(0, 0, output.width, output.height).data;
    let visible = 0;
    for (let i = 3; i < pixels.length; i += 4) if (pixels[i]) visible++;
    if (visible < 1000) throw Error("Empty native bitmap: " + task.id);
    return webp();
  }
  if (logicalWidth + 40 > source.width / sourceScale) return nativeFallback();
  const context = output.getContext("2d");
  context.drawImage(source,
    (512 - logicalWidth / 2 - 20) * sourceScale, 15 * sourceScale,
    output.width / 2 * sourceScale, 540 * sourceScale,
    0, 0, output.width, output.height);
  // The next pose resumes the isolated player. Encoding and HTTP uploads need no game frames.
  api.suspend();
  const pixels = context.getImageData(0, 0, output.width, output.height).data;
  let visiblePixels = 0;
  for (let i = 3; i < pixels.length; i += 4) if (pixels[i]) visiblePixels++;
  if (visiblePixels < 1000) return nativeFallback();
  return webp();
}
