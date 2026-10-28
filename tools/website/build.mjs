import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { legalPages } from "./legal.mjs";
import { releaseManifest } from "./updates.mjs";
import { rulesPage } from "./rules.mjs";
import { responsiveImages } from "./responsive-images.mjs";
import { socialCards, socialMetadata } from "./social-cards.mjs";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const PAGES = ["index.html", "ladder.html", "play.html", "browser.html", "admin.html", "website-activity.html", "moderation.html", "tournaments.html", "assets-admin.html"];
const DOWNLOADS = {
  android: ["android/build/Boufbowl Fan.apk", "downloads/Boufbowl Fan.apk"],
  desktop: ["linux/build/Boufbowl Fan.run", "downloads/Boufbowl Fan.run"],
  windows: ["windows/build/Boufbowl Fan.exe", "downloads/Boufbowl Fan.exe"],
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

function pageMetadata(html, name, origin) {
  return html.replace(/<head\b[^>]*>[\s\S]*?<\/head>/i, (head) => {
    head = head.replace(/https:\/\/(?:boufbowl-fan\.fr|[a-z0-9-]+\.trycloudflare\.com)(?=[/:#?"'<>\s]|$)/gi, origin);
    const canonical = /<link\b(?=[^>]*\brel=["']canonical["'])[^>]*>/gi;
    if (canonical.test(head)) {
      return head.replace(canonical, (tag) => tag.replace(/\bhref=(["'])([^"']+)\1/i, (_, quote, value) => {
        const url = new URL(value, origin + "/");
        return `href=${quote}${origin}${url.pathname}${url.search}${url.hash}${quote}`;
      }));
    }
    const route = name === "index.html" ? "/" : `/${name}`;
    return head.replace(/<\/head>/i, `<link rel="canonical" href="${origin}${route}">\n</head>`);
  });
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
  const settingsPath = path.join(root, "resources/site.json");
  const settings = await exists(settingsPath) ? JSON.parse(await fs.readFile(settingsPath, "utf8")) : {};
  const siteUrl = settings.site_url ?? "https://boufbowl-fan.fr";
  const url = URL.parse(siteUrl);
  if (!url || url.protocol !== "https:" || url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
    throw new Error("site_url must be an HTTPS origin without credentials, a path, query, or fragment");
  }
  const origin = url.origin;
  const publicUrls = {};
  for (const key of ["android_download_url", "desktop_download_url", "windows_download_url", "contact_url", "tot_quote_source_url"]) {
    const value = settings[key];
    const parsed = URL.parse(value);
    publicUrls[key] = parsed?.protocol === "https:" && !parsed.username && !parsed.password ? value : null;
  }
  const release = JSON.parse(await fs.readFile(path.join(root, "resources/release.json"), "utf8"));
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
    if (!clientFile) throw new Error("Missing " + client + ". Run bun run build for the game, then bun run build:website for the website.");
    await record(client, await fs.readFile(clientFile));
    for (const [source, name] of Object.values(DOWNLOADS)) {
      const filename = await downloadFile(root, source);
      if (filename) await record(name, await fs.readFile(filename));
    }
    const pages = new Map(await Promise.all(PAGES.map(async (name) => [name, await fs.readFile(path.join(root, name), "utf8")])));
    for (const [name, html] of Object.entries(await legalPages(root))) pages.set(name, html);
    pages.set("regles.html", await rulesPage(root));
    // Keep bookmarks working when the output is served by a generic static host.
    for (const legacy of ["website-tracking.html", "website-analytics.html"]) pages.set(legacy, '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url=website-activity.html"><link rel="canonical" href="website-activity.html"><title>Website activity</title></head><body><a href="website-activity.html">Open website activity</a></body></html>');
    const cards = await socialCards(root, pages);
    for (const card of cards.values()) await record(card.path, await fs.readFile(card.filename));
    const media = [...files].filter(([name]) => /^(assets|vendor|bin)\//.test(name) && !name.endsWith(".json") && !name.startsWith("assets/site/social/"));
    const revision = digest(JSON.stringify(media.sort(([a], [b]) => a.localeCompare(b)).map(([name, entry]) => [name, entry.sha256]))).slice(0, 16);
    const version = (url) => {
      if (/^\/?(?:assets|vendor|bin)\//.test(url) && !files.has(url.split("?")[0].replace(/^\//, ""))) {
        throw new Error(`Missing public asset: ${url}`);
      }
      return versionUrl(url, revision);
    };
    const downloads = {};
    for (const [platform, [, target]] of Object.entries(DOWNLOADS)) {
      const artifact = files.get(target), external = publicUrls[`${platform}_download_url`];
      downloads[platform] = {
        url: external || (artifact ? `${encodeURI("/" + target)}?v=${artifact.sha256.slice(0, 16)}` : null), local: Boolean(artifact && !external),
        size: artifact && !external ? artifact.bytes : null,
        description: platform === "android" ? "APK · Android 6+ · ARM64" : platform === "windows" ? "Windows" : external ? "Desktop · client Flash" : "Linux x86-64",
      };
    }
    const manifest = { ok: true, downloads, contact_url: publicUrls.contact_url, tot_quote_source_url: publicUrls.tot_quote_source_url };
    const scripts = new Map();
    const buildScript = async (source, module) => {
      const key = `${source}:${module}`;
      if (scripts.has(key)) return scripts.get(key);
      const build = await Bun.build({
        entrypoints: [path.join(root, source)], minify: true, target: "browser",
        format: module ? "esm" : "iife", naming: "js/[name].[hash].[ext]",
        define: { __SITE_ASSET_VERSION__: JSON.stringify(revision), __CLIENT_VERSION__: JSON.stringify(release.version) },
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
    const sitemapUrls = new Set();
    for (const [name, source] of pages) {
      let html = socialMetadata(pageMetadata(source, name, origin), name, origin, cards.get(name));
      html = await new HTMLRewriter().on("[data-source-only]", {
        element(element) { element.remove(); },
      }).transform(new Response(html)).text();
      if (name === "index.html") {
        const escape = (text) => text.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
        for (const [platform, item] of Object.entries(manifest.downloads)) {
          if (!item.url) continue;
          const link = new RegExp(`(<a\\b(?=[^>]*\\bid=["']download-${platform}["'])[^>]*\\bhref=["'])[^"']+`, "i");
          html = html.replace(link, (_, prefix) => prefix + escape(item.url));
          const detail = new RegExp(`(<small\\b(?=[^>]*\\bid=["']${platform}-detail["'])[^>]*>)[\\s\\S]*?(</small\\s*>)`, "i");
          const size = item.size ? " · " + (item.size / 1048576).toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + " Mo" : "";
          html = html.replace(detail, (_, opening, closing) => opening + escape(item.description + size) + closing);
        }
      }
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
      const head = html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1] || "";
      const meta = [...head.matchAll(/<meta\b[^>]*>/gi)].map((match) => match[0]);
      const noindex = meta.some((tag) => /\bname=["'](?:robots|googlebot)["']/i.test(tag) && /\bcontent=["'][^"']*\bnoindex\b/i.test(tag));
      const redirect = meta.some((tag) => /\bhttp-equiv=["']refresh["']/i.test(tag));
      const canonical = head.match(/<link\b(?=[^>]*\brel=["']canonical["'])[^>]*\bhref=["']([^"']+)["']/i)?.[1];
      if (!noindex && !redirect && canonical) sitemapUrls.add(canonical);
    }
    const xmlEscape = (value) => value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[char]);
    await record("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      [...sitemapUrls].sort().map((url) => `  <url><loc>${xmlEscape(url)}</loc></url>`).join("\n") + "\n</urlset>\n");
    await record("robots.txt", `User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: ${origin}/sitemap.xml\n`);
    const configPath = path.join(stage, "resources/config.json");
    if (await exists(configPath)) {
      const config = JSON.parse(await fs.readFile(configPath, "utf8"));
      config["3dActivated"] = "true";
      await record("resources/config.json", JSON.stringify(config, null, 2) + "\n");
    }
    await record("resources/site-manifest.json", JSON.stringify(manifest, null, 2) + "\n");
    await record("updates.json", await releaseManifest(root,files,origin,revision,release));
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
