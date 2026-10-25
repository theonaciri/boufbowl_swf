import { test, expect } from "bun:test";
import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import { ROOT, PAGES } from "./build.mjs";
import { legalPages } from "./legal.mjs";
import { rulesPage } from "./rules.mjs";
import { SOCIAL_PAGES, indexablePage, publicSocialPages, socialCards, socialMetadata } from "./social-cards.mjs";

const page = (head = "") => `<html><head><title>Sport &amp; tactique</title><meta name="description" content="Planifier &amp; jouer">${head}</head><body>Un match</body></html>`;

test("public generated pages have deliberate, distinct cards; legal pages are included, private pages and redirects stay excluded", async () => {
  const pages = new Map(await Promise.all(PAGES.map(async (name) => [name, await fs.readFile(path.join(ROOT, name), "utf8")])));
  for (const [name, html] of Object.entries(await legalPages(ROOT))) pages.set(name, html);
  pages.set("regles.html", await rulesPage(ROOT));
  const publicPages = publicSocialPages(pages);
  expect(publicPages.map(([name]) => name).sort()).toEqual(["charte-communaute.html", "conditions-utilisation.html", "confidentialite.html", "cookies.html", "index.html", "ladder.html", "legal.html", "mentions-legales.html", "play.html", "reglement-tournois.html", "regles.html"]);
  expect(new Set(publicPages.map(([, recipe]) => recipe.image)).size).toBe(publicPages.length);
  expect(new Set(publicPages.map(([, recipe]) => recipe.title)).size).toBe(publicPages.length);
  expect(indexablePage(page('<meta content="noindex,follow" name="robots">'))).toBe(false);
  expect(indexablePage(page('<meta http-equiv="refresh" content="0;url=play.html">'))).toBe(false);
  expect(publicSocialPages(new Map([["legal.html", page('<meta name="robots" content="noindex,follow">')]]))).toHaveLength(1);
  expect(publicSocialPages(new Map([["legal.html", page('<meta http-equiv="refresh" content="0;url=index.html">')]]))).toHaveLength(0);
  expect(() => publicSocialPages(new Map([["new-public.html", page()]]))).toThrow("Missing page-specific social card: new-public.html");
});

test("social metadata uses one absolute PNG card with dimensions, accessible alt and escaped editorial text", () => {
  const source = page('<meta property="og:image" content="old.avif"><meta name="twitter:card" content="summary">');
  const card = { ...SOCIAL_PAGES["regles.html"], path: "assets/site/social/regles.abc.png" };
  const html = socialMetadata(source, "regles.html", "https://example.org", card);
  expect(html.match(/property="og:image"/g)).toHaveLength(1);
  expect(html).toContain('content="https://example.org/assets/site/social/regles.abc.png"');
  expect(html).toContain('property="og:url" content="https://example.org/regles.html"');
  expect(html).toContain('property="og:image:width" content="1200"');
  expect(html).toContain('property="og:image:height" content="630"');
  expect(html).toContain('name="twitter:image:alt"');
  expect(html).toContain('content="Sport &amp; tactique"');
  expect(html).not.toContain("&amp;amp;");
  expect(socialMetadata(source, "admin.html", "https://example.org", undefined)).toBe(source);
});

test("native raster generation is 1200×630, cached, and invalidated by changed original imagery", async () => {
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "boufbowl-social-test-"));
  try {
    const images = ["game-resolution.webp", "game-orders.webp", "BarlowCondensed-ExtraBold.woff2", "Barlow-Regular.woff2"];
    await fs.mkdir(path.join(temporary, "assets/site"), { recursive: true });
    for (const image of images) await fs.copyFile(path.join(ROOT, "assets/site", image), path.join(temporary, "assets/site", image));
    const pages = new Map([["index.html", page()]]);
    const first = (await socialCards(temporary, pages)).get("index.html");
    const bytes = await fs.readFile(first.filename);
    expect(bytes.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
    expect([bytes.readUInt32BE(16), bytes.readUInt32BE(20)]).toEqual([1200, 630]);
    const before = await fs.stat(first.filename);
    const cached = (await socialCards(temporary, pages)).get("index.html");
    expect(cached.path).toBe(first.path);
    expect((await fs.stat(cached.filename)).mtimeMs).toBe(before.mtimeMs);
    await fs.copyFile(path.join(temporary, "assets/site/game-orders.webp"), path.join(temporary, "assets/site/game-resolution.webp"));
    const changed = (await socialCards(temporary, pages)).get("index.html");
    expect(changed.path).not.toBe(first.path);
    expect(await fs.readFile(changed.filename)).not.toEqual(bytes);
  } finally { await fs.rm(temporary, { recursive: true, force: true }); }
}, 30000);
