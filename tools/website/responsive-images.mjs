import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

const exists = (name) => fs.access(name).then(() => true, () => false);
const recipes = [
  { name: "logo", sources: ["assets/site/logo.webp"], widths: [120, 200, 240, 400, 600, 630], yuv: "444" },
  { name: "tutorial-poster", sources: ["assets/videos/layout_tuto_01.flv", "assets/site/tutorial-poster.avif"], widths: [480, 768, 1024], yuv: "420" },
];

async function command(args) {
  const process = Bun.spawn(args, { stdout: "ignore", stderr: "pipe" });
  const stderr = await new Response(process.stderr).text();
  if (await process.exited !== 0) throw new Error(`Responsive image conversion failed: ${args[0]}\n${stderr}`);
}

// Cache generated media under .local; source images and templates stay untouched.
export async function responsiveImages(root, temporary) {
  const outputs = [];
  for (const recipe of recipes) {
    let source;
    for (const candidate of recipe.sources) {
      if (await exists(path.join(root, candidate))) { source = candidate; break; }
    }
    if (!source) continue;
    const key = createHash("sha256")
      .update(await fs.readFile(path.join(root, source)))
      .update(JSON.stringify({ ...recipe, quality: 80, alphaQuality: 80, speed: 4, revision: 1 }))
      .digest("hex");
    const cache = path.join(root, ".local/website/image-cache", key);
    await fs.mkdir(cache, { recursive: true });
    const missing = [];
    for (const width of recipe.widths) {
      const filename = `${recipe.name}-${width}.avif`;
      const cached = path.join(cache, filename);
      outputs.push([`assets/site/responsive/${filename}`, cached]);
      if (!await exists(cached)) missing.push([width, cached]);
    }
    if (!missing.length) continue;
    console.log(`Generating ${missing.length} responsive ${recipe.name} images (AVIF quality 80)`);
    const master = path.join(temporary, `${recipe.name}-master.png`);
    await command(["ffmpeg", "-y", "-v", "error", ...(source.endsWith(".flv") ? ["-ss", "1"] : []),
      "-i", path.join(root, source), "-frames:v", "1", master]);
    for (const [width, cached] of missing) {
      const png = path.join(temporary, `${recipe.name}-${width}.png`);
      const avif = path.join(temporary, `${recipe.name}-${width}.avif`);
      await command(["ffmpeg", "-y", "-v", "error", "-i", master,
        "-vf", `scale=${width}:-1:flags=lanczos`, "-frames:v", "1", png]);
      await command(["avifenc", "--qcolor", "80", "--qalpha", "80", "--speed", "4", "--jobs", "2",
        "--yuv", recipe.yuv, png, avif]);
      // A failed encoder never leaves a reusable partial cache entry.
      await fs.copyFile(avif, cached + ".building");
      await fs.rename(cached + ".building", cached);
    }
  }
  return outputs;
}
