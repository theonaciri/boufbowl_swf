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
  let ready;
  for (let attempt = 0; attempt < 40; attempt++) {
    ready = api.callExternalInterface("siteRender", task.cls, task.gender, task.hero, task.symbol,
      parseInt(task.colors.hair, 16), parseInt(task.colors.skin, 16), parseInt(task.colors.eyes, 16));
    if (ready === "READY") break;
    if (ready !== "LOADING") throw Error(ready);
    await wait(200);
  }
  if (ready !== "READY") throw Error("Original illustration libraries did not load");
  await wait(160);
  const bounds = api.callExternalInterface("sitePreview");
  await wait(90);
  const match = bounds.match(/w=([\d.]+), h=([\d.]+)/);
  if (!match) throw Error("Missing native pose bounds: " + bounds);
  const logicalWidth = Number(match[1]) * 500 / Number(match[2]);
  const output = document.createElement("canvas");
  output.width = Math.ceil(logicalWidth * 2) + 80;
  output.height = 1080;
  const source = player.shadowRoot.querySelector("canvas");
  const sourceScale = source.height / 600;
  if (logicalWidth + 40 > source.width / sourceScale) {
    // Some cinematic effects extend beyond the stage; export them without clipping.
    const png = api.callExternalInterface("sitePNG");
    if (!png || png.startsWith("ERROR")) throw Error(png);
    return { id: task.id, png, width: output.width, height: output.height };
  }
  const context = output.getContext("2d");
  context.drawImage(source,
    (512 - logicalWidth / 2 - 20) * sourceScale, 15 * sourceScale,
    output.width / 2 * sourceScale, 540 * sourceScale,
    0, 0, output.width, output.height);
  const pixels = context.getImageData(0, 0, output.width, output.height).data;
  let visiblePixels = 0;
  for (let i = 3; i < pixels.length; i += 4) if (pixels[i]) visiblePixels++;
  if (visiblePixels < 1000) {
    const png = api.callExternalInterface("sitePNG");
    if (!png || png.startsWith("ERROR")) throw Error("Empty native portrait: " + task.id);
    return { id: task.id, png, width: output.width, height: output.height };
  }
  return { id: task.id, png: output.toDataURL("image/png").split(",")[1],
    width: output.width, height: output.height };
}
