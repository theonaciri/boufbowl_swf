import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import legalData from "./legal-data.json";
import SOCIAL_PAGES from "./social-data.json";

const WIDTH = 1200, HEIGHT = 630;
const escape = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const digest = (value) => createHash("sha256").update(value).digest("hex");
const exists = (name) => fs.access(name).then(() => true, () => false);

// Deliberate page-specific original client captures, never generated game artwork.
// Add new public pages in social-data.json before publication. Each recipe fingerprints
// independently, so changing one page does not regenerate the other cards.
export { SOCIAL_PAGES };

export function indexablePage(html) {
  const head = html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1] || "";
  const meta = [...head.matchAll(/<meta\b[^>]*>/gi)].map(([tag]) => tag);
  return !meta.some((tag) => /\bname=["'](?:robots|googlebot)["']/i.test(tag) && /\bcontent=["'][^"']*\bnoindex\b/i.test(tag)) &&
    !meta.some((tag) => /\bhttp-equiv=["']refresh["']/i.test(tag));
}

// Legal documents are public and shareable even while excluded from search indexes.
const PUBLIC_LEGAL_PAGES = new Set(["legal.html", ...legalData.documents.map(([slug]) => `${slug}.html`)]);

export function publicSocialPages(pages) {
  const result = [];
  for (const [name, html] of pages) {
    if (/<meta\b(?=[^>]*\bhttp-equiv=["']refresh["'])[^>]*>/i.test(html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1] || "")) continue;
    if (!indexablePage(html) && !PUBLIC_LEGAL_PAGES.has(name)) continue;
    if (!SOCIAL_PAGES[name]) throw new Error(`Missing page-specific social card: ${name}`);
    result.push([name, SOCIAL_PAGES[name]]);
  }
  return result;
}

// All content is embedded; generation needs no server, network, SWF export or media rebuild.
export function socialCardHtml(recipe, { image, heading, body }) {
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>
@font-face{font-family:Heading;src:url(data:font/woff2;base64,${heading})}
@font-face{font-family:Body;src:url(data:font/woff2;base64,${body})}
*{box-sizing:border-box}html,body{margin:0;width:${WIDTH}px;height:${HEIGHT}px;overflow:hidden}
body{background:#f4f0e5;color:#193e32;font-family:Body,sans-serif}
.copy{position:absolute;left:58px;top:49px;width:510px;z-index:2}
.brand{font:32px Heading;letter-spacing:2px}.label{margin-top:42px;color:#995019;font-size:16px;letter-spacing:1.2px}
h1{font:76px/1 Heading;margin:20px 0 25px;max-width:510px;overflow-wrap:break-word}
.note{font-size:22px;line-height:1.4;max-width:450px}.picture{position:absolute;left:610px;top:0;width:590px;height:550px;background:#193e32;display:flex;align-items:center}
.picture img{width:100%;height:auto;max-height:100%;object-fit:contain}
.rule{position:absolute;left:58px;top:541px;width:80px;height:5px;background:#bd601f}
footer{position:absolute;bottom:0;left:0;width:100%;height:80px;background:#193e32;color:#fff;padding:22px 58px;display:flex;justify-content:space-between;align-items:center;font-size:16px}
</style></head><body><div class="copy"><div class="brand">BOUFBOWL FAN</div>
<div class="label">${escape(recipe.label)}</div><h1>${escape(recipe.title)}</h1>
<div class="note">Un projet de préservation bénévole et non commercial.</div></div>
<div class="picture"><img src="data:${recipe.image.endsWith('.png') ? 'image/png' : 'image/webp'};base64,${image}" alt=""></div>
<div class="rule"></div><footer><span>Images du jeu original · © Ankama</span><span>Projet non affilié à Ankama</span></footer></body></html>`;
}

export async function socialCards(root, pages) {
  const recipes = publicSocialPages(pages);
  if (!recipes.length) return new Map();
  const fonts = await Promise.all(["BarlowCondensed-ExtraBold.woff2", "Barlow-Regular.woff2"].map((name) => fs.readFile(path.join(root, "assets/site", name))));
  const generator = await fs.readFile(new URL(import.meta.url));
  // Include renderer version as well as recipe, source imagery, fonts and code.
  const renderer = JSON.parse(await fs.readFile(new URL("./node_modules/playwright-core/package.json", import.meta.url), "utf8")).version;
  const cards = new Map();
  let browser;
  try {
    for (const [name, recipe] of recipes) {
      const source = await fs.readFile(path.join(root, recipe.image));
      const key = digest(Buffer.concat([generator, Buffer.from(JSON.stringify({ recipe, renderer })), source, ...fonts]));
      const filename = `${name.replace(/\.html$/, "")}.${key.slice(0, 20)}.png`;
      const cached = path.join(root, ".local/website/social-cache", filename);
      if (!await exists(cached)) {
        console.log(`Generating social card: ${name}`);
        browser ||= await chromium.launch({ headless: true, args: ["--no-sandbox"] });
        const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
        try {
          await page.setContent(socialCardHtml(recipe, { image: source.toString("base64"), heading: fonts[0].toString("base64"), body: fonts[1].toString("base64") }));
          await page.evaluate(async () => {
            await document.fonts.ready;
            await Promise.all([...document.images].map((image) => image.decode()));
            const title = document.querySelector("h1"), note = document.querySelector(".note");
            while (note.getBoundingClientRect().bottom > 520 && parseFloat(getComputedStyle(title).fontSize) > 45) {
              title.style.fontSize = `${parseFloat(getComputedStyle(title).fontSize) - 1}px`;
            }
            if (note.getBoundingClientRect().bottom > 520) throw new Error("Social card text overflows");
          });
          const bytes = await page.screenshot({ type: "png" });
          await fs.mkdir(path.dirname(cached), { recursive: true });
          const temporary = `${cached}.building.${process.pid}`;
          await fs.writeFile(temporary, bytes);
          await fs.rename(temporary, cached);
        } finally { await page.close(); }
      }
      cards.set(name, { ...recipe, path: `assets/site/social/${filename}`, filename: cached });
    }
  } finally { await browser?.close(); }
  return cards;
}

export function socialMetadata(html, name, origin, card) {
  if (!card) return html;
  const route = name === "index.html" ? "/" : `/${name}`;
  // Preserve source editorial metadata except for the social fields owned here.
  const description = html.match(/<meta\b(?=[^>]*\bname=["']description["'])[^>]*\bcontent=["']([^"']*)["']/i)?.[1] || "";
  const title = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1] || escape(card.title);
  const values = {
    "og:type": "website", "og:site_name": "Boufbowl Fan", "og:locale": "fr_FR", "og:url": escape(origin + route),
    "og:title": title, "og:description": description, "og:image": escape(`${origin}/${card.path}`),
    "og:image:type": "image/png", "og:image:width": "1200", "og:image:height": "630", "og:image:alt": escape(card.alt),
    "twitter:card": "summary_large_image", "twitter:title": title, "twitter:description": description,
    "twitter:image": escape(`${origin}/${card.path}`), "twitter:image:alt": escape(card.alt),
  };
  return html.replace(/<head\b[^>]*>[\s\S]*?<\/head>/i, (head) => {
    head = head.replace(/<meta\b(?=[^>]*\b(?:property|name)=["'](?:og:|twitter:)[^"']*["'])[^>]*>\s*/gi, "");
    return head.replace(/<\/head>/i, Object.entries(values).map(([key, value]) => `<meta ${key.startsWith("og:") ? "property" : "name"}="${key}" content="${value}" />`).join("\n") + "\n</head>");
  });
}
