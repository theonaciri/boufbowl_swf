import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { legalPages } from "./legal.mjs";
import { responsiveImages } from "./responsive-images.mjs";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const PAGES = ["index.html", "play.html", "browser.html", "admin.html", "website-activity.html", "moderation.html", "tournaments.html", "assets-admin.html"];
const DOWNLOADS = {
  android: ["android/build/BoufbowlOffline.apk", "downloads/BoufbowlOffline.apk"],
  desktop: ["linux/build/Boufbowl-linux.tar.gz", "downloads/Boufbowl-linux.tar.gz"],
  windows: ["windows/build/Boufbowl-windows.zip", "downloads/Boufbowl-windows.zip"],
};
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const exists = async (name) => fs.access(name).then(() => true, () => false);

async function canonicalPath(name) {
  try { return await fs.realpath(name); }
  catch (error) {
    if (error.code !== "ENOENT") throw error;
    return path.join(await canonicalPath(path.dirname(name)), path.basename(name));
  }
}

async function downloadFile(root, source) {
  const filename = path.join(root, source);
  const resolved = await fs.realpath(filename).catch(() => null);
  if (!resolved || !resolved.startsWith(path.join(root, path.dirname(source)) + path.sep)) return null;
  return (await fs.stat(resolved)).isFile() ? resolved : null;
}

async function walk(directory, base = directory) {
  const result = [];
  if (!await exists(directory)) return result;
  if ((await fs.lstat(directory)).isSymbolicLink()) throw new Error(`Public folders must not be symlinks: ${directory}`);
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const name = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Public files must not be symlinks: ${name}`);
    if (entry.isDirectory()) result.push(...await walk(name, base));
    else if (entry.isFile() && !entry.name.includes(".building.")) result.push(path.relative(base, name));
  }
  return result.sort();
}

function versionUrl(value, revision) {
  if (!/^(?:\/?assets|\/?vendor|\/?bin)\//.test(value)) return value;
  const [pathname, query = ""] = value.split("?", 2);
  const params = new URLSearchParams(query.replace(/&amp;/g, "&"));
  params.set("v", revision);
  return `${pathname}?${params}`;
}

async function siteManifest(root) {
  const settingsPath = path.join(root, "resources/site.json");
  const settings = await exists(settingsPath) ? JSON.parse(await fs.readFile(settingsPath, "utf8")) : {};
  function publicUrl(key) {
    try {
      const url = new URL(settings[key]);
      return url.protocol === "https:" && !url.username && !url.password ? settings[key] : null;
    } catch { return null; }
  }
  const downloads = {};
  for (const [platform, [source, target]] of Object.entries(DOWNLOADS)) {
    const local = await downloadFile(root, source);
    const external = publicUrl(`${platform}_download_url`);
    downloads[platform] = {
      url: external || (local ? `/${target}` : null), local: Boolean(local && !external),
      size: local && !external ? (await fs.stat(local)).size : null,
      description: platform === "android" ? "APK · Android 6+ · ARM64" : platform === "windows" ? "Windows · sans Wine ni Python" : external ? "Desktop · client Flash" : "Linux x86-64 · Wine requis · sans Python",
    };
  }
  return { ok: true, downloads, contact_url: publicUrl("contact_url"), tot_quote_source_url: publicUrl("tot_quote_source_url") };
}

export async function buildSite({ root = ROOT, output = path.join(root, ".local/website/dist"), check = false } = {}) {
  root = await fs.realpath(path.resolve(root));
  output = await canonicalPath(path.resolve(output));
  const relative = path.relative(root, output);
  const sourceFromOutput = path.relative(output, root);
  const isInside = (value) => value === "" || !value.startsWith(".." + path.sep) && !path.isAbsolute(value);
  if (isInside(sourceFromOutput) || isInside(relative) && !relative.startsWith(".local" + path.sep)) {
    throw new Error("Use an output directory under .local, or a separate directory outside the source tree");
  }
  if (await exists(output) && (await fs.readdir(output)).length && !await exists(path.join(output, "delivery.json"))) {
    throw new Error("Refusing to replace an output folder without delivery.json");
  }
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "boufbowl-web-"));
  await fs.mkdir(path.dirname(output), { recursive: true });
  const stage = await fs.mkdtemp(path.join(path.dirname(output), ".website-stage-"));
  // mkdtemp defaults to 0700; the static web server needs directory access.
  await fs.chmod(stage, 0o755);
  const files = new Map();
  const record = async (name, bytes) => {
    if (path.isAbsolute(name) || name.split(/[\\/]/).includes("..")) throw new Error(`Unsafe output path: ${name}`);
    const target = path.join(stage, name);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, bytes);
    files.set(name, { bytes: Buffer.byteLength(bytes), sha256: digest(bytes) });
  };
  try {
    for (const folder of ["assets", "resources", "vendor"]) {
      for (const relative of await walk(path.join(root, folder))) {
        const name = `${folder}/${relative}`;
        await record(name, await fs.readFile(path.join(root, name)));
      }
    }
    for (const [name, filename] of await responsiveImages(root, temporary)) {
      await record(name, await fs.readFile(filename));
    }
    const client = "bin/boufbowl-client-1.9.6.swf";
    const clientFile = await downloadFile(root, client);
    if (!clientFile) throw new Error("Build the game client before building the website: " + client);
    await record(client, await fs.readFile(clientFile));
    for (const [source, name] of Object.values(DOWNLOADS)) {
      const filename = await downloadFile(root, source);
      if (filename) await record(name, await fs.readFile(filename));
    }
    const media = [...files].filter(([name]) => /^(assets|vendor|bin)\//.test(name) && !name.endsWith(".json"));
    const revision = digest(JSON.stringify(media.sort(([a], [b]) => a.localeCompare(b)).map(([name, entry]) => [name, entry.sha256]))).slice(0, 16);
    const version = (url) => {
      if (/^\/?(?:assets|vendor|bin)\//.test(url) && !files.has(url.split("?")[0].replace(/^\//, ""))) {
        throw new Error(`Missing public asset: ${url}`);
      }
      return versionUrl(url, revision);
    };
    const pages = new Map(await Promise.all(PAGES.map(async (name) => [name, await fs.readFile(path.join(root, name), "utf8")])));
    for (const [name, html] of Object.entries(await legalPages(root))) pages.set(name, html);
    // Keep bookmarks working when the output is served by a generic static host.
    for (const legacy of ["website-tracking.html", "website-analytics.html"]) pages.set(legacy, '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url=website-activity.html"><link rel="canonical" href="website-activity.html"><title>Website activity</title></head><body><a href="website-activity.html">Open website activity</a></body></html>');
    const scripts = new Map();
    const buildScript = async (source, module) => {
      const key = `${source}:${module}`;
      if (scripts.has(key)) return scripts.get(key);
      const build = await Bun.build({
        entrypoints: [path.join(root, source)], minify: true, target: "browser",
        format: module ? "esm" : "iife", naming: "js/[name].[hash].[ext]",
        define: { __SITE_ASSET_VERSION__: JSON.stringify(revision) },
      });
      if (!build.success) throw new AggregateError(build.logs, `Cannot bundle ${source}`);
      let entry;
      for (const artifact of build.outputs) {
        const name = artifact.path.replace(/^\.\//, "");
        if (artifact.kind === "entry-point") entry = name;
        await record(name, Buffer.from(await artifact.arrayBuffer()));
      }
      if (!entry) throw new Error(`Missing entry point for ${source}`);
      scripts.set(key, entry);
      return entry;
    };
    for (const [name, source] of pages) {
      let html = source;
      // Preserve stylesheet/inline-style order, then inline Bun's combined CSS.
      const cssTags = [...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>|<link\b(?=[^>]*\brel=["']stylesheet["'])[^>]*>/gi)];
      if (cssTags.length) {
        const imports = [];
        for (let index = 0; index < cssTags.length; index++) {
          const tag = cssTags[index];
          let cssSource;
          if (tag[1] !== undefined) {
            cssSource = path.join(temporary, `${name}-${index}.css`);
            await fs.writeFile(cssSource, tag[1]);
          } else {
            const href = tag[0].match(/\bhref=["']([^"']+)["']/i)?.[1];
            if (!href || /^(https?:)?\/\//.test(href)) throw new Error(`Local CSS expected in ${name}`);
            cssSource = path.join(root, href.split("?")[0]);
          }
          imports.push(`import ${JSON.stringify(cssSource)};`);
        }
        const entry = path.join(temporary, `${name}.js`);
        await fs.writeFile(entry, imports.join("\n"));
        const build = await Bun.build({ entrypoints: [entry], minify: true, target: "browser", external: ["assets/*", "/assets/*"] });
        if (!build.success) throw new AggregateError(build.logs, `Cannot bundle CSS in ${name}`);
        const css = build.outputs.find((artifact) => artifact.path.endsWith(".css"));
        if (!css) throw new Error(`Missing CSS bundle for ${name}`);
        let bundled = await css.text();
        bundled = bundled.replace(/url\(\s*(["']?)([^"')]+)\1\s*\)/g, (_, quote, url) => `url(${quote}${version(url)}${quote})`);
        bundled = bundled.replace(/<\/style/gi, "<\\/style");
        // A callback preserves literal dollar signs in generated CSS.
        let first = true;
        html = html.replace(/<style\b[^>]*>[\s\S]*?<\/style>|<link\b(?=[^>]*\brel=["']stylesheet["'])[^>]*>/gi, () => {
          if (!first) return "";
          first = false;
          return `<style>${bundled}</style>`;
        });
      }
      const scriptTags = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>\s*<\/script>/gi)];
      for (const match of scriptTags) {
        const source = match[1].split("?")[0];
        if (/^(https?:)?\/\//.test(source) || source.startsWith("vendor/")) continue;
        const entry = await buildScript(source, /\btype=["']module["']/.test(match[0]));
        html = html.replace(match[0], match[0].replace(match[1], entry));
      }
      html = html.replace(/\b(src|href|poster|data-puppet-src)=(['"])([^'"\s]+)\2/g, (_, attr, quote, value) => `${attr}=${quote}${version(value)}${quote}`);
      html = html.replace(/\bsrcset=(["'])(.*?)\1/gs, (_, quote, value) => {
        const candidates = value.split(",").map((candidate) => {
          const [url, descriptor] = candidate.trim().split(/\s+/);
          return `${version(url)}${descriptor ? " " + descriptor : ""}`;
        });
        return `srcset=${quote}${candidates.join(", ")}${quote}`;
      });
      await record(name, html);
    }
    const configPath = path.join(stage, "resources/config.json");
    if (await exists(configPath)) {
      const config = JSON.parse(await fs.readFile(configPath, "utf8"));
      config["3dActivated"] = "true";
      await record("resources/config.json", JSON.stringify(config, null, 2) + "\n");
    }
    const manifest = await siteManifest(root);
    await record("resources/site-manifest.json", JSON.stringify(manifest, null, 2) + "\n");
    await record("crossdomain.xml", '<cross-domain-policy><allow-access-from domain="*" secure="false"/><allow-http-request-headers-from domain="*" headers="Content-Type" secure="false"/></cross-domain-policy>');
    const entries = Object.fromEntries([...files].sort(([a], [b]) => a.localeCompare(b)));
    const report = { version: 2, asset_revision: revision, files: entries, file_count: files.size, bytes: [...files.values()].reduce((total, entry) => total + entry.bytes, 0), downloads: manifest.downloads };
    await fs.writeFile(path.join(stage, "delivery.json"), JSON.stringify(report, null, 2) + "\n");
    if (check) {
      const actual = await walk(output);
      if (JSON.stringify(actual) !== JSON.stringify([...Object.keys(entries), "delivery.json"].sort())) throw new Error("Static output contains missing or unexpected files; rebuild with Bun");
      for (const [name, entry] of Object.entries(entries)) {
        if (digest(await fs.readFile(path.join(output, name))) !== entry.sha256) throw new Error(`Static output is stale: ${name}`);
      }
      if (await fs.readFile(path.join(output, "delivery.json"), "utf8") !== await fs.readFile(path.join(stage, "delivery.json"), "utf8")) throw new Error("Static output manifest is stale");
    } else {
      const backup = output + ".previous";
      if (await exists(backup)) throw new Error(`Previous build backup already exists: ${backup}`);
      if (await exists(output)) await fs.rename(output, backup);
      try { await fs.rename(stage, output); }
      catch (error) { if (await exists(backup)) await fs.rename(backup, output); throw error; }
      await fs.rm(backup, { recursive: true, force: true });
    }
    return report;
  } finally {
    await fs.rm(temporary, { recursive: true, force: true });
    await fs.rm(stage, { recursive: true, force: true });
  }
}

if (import.meta.main) {
  let output, root = ROOT, check = false;
  for (let index = 2; index < Bun.argv.length; index++) {
    if (Bun.argv[index] === "--output") output = Bun.argv[++index];
    else if (Bun.argv[index] === "--root") root = Bun.argv[++index];
    else if (Bun.argv[index] === "--check") check = true;
    else throw new Error(`Unknown argument: ${Bun.argv[index]}`);
  }
  const report = await buildSite({ root, output, check });
  console.log(`${check ? "Verified" : "Built"} ${report.file_count} static files; asset revision ${report.asset_revision}`);
  console.log(output || path.join(root, ".local/website/dist"));
}
