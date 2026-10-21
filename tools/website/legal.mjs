import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import data from "./legal-data.json";

const directory = path.dirname(fileURLToPath(import.meta.url));
const escape = (text) => String(text).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" })[char]);

function inline(text) {
  return text.split(/(\[[^\]\n]+\]\([^\s)]+\))/).map((part) => {
    const match = part.match(/^\[([^\]\n]+)\]\(([^\s)]+)\)$/);
    if (!match) return escape(part).replaceAll("[]", '<span class="placeholder" title="Information à compléter">[]</span>');
    let [, label, url] = match;
    if (!url.startsWith("https://") && !/^[a-z-]+\.(html|md)$/.test(url)) throw new Error(`Unsupported legal-document link: ${url}`);
    url = url.replace(/\.md$/, ".html");
    return `<a href="${escape(url)}">${escape(label)}</a>`;
  }).join("");
}

function markdown(source) {
  const result = [], headings = [];
  for (const block of source.trim().split(/\n\s*\n/)) {
    if (block.startsWith("# ")) continue;
    if (block.startsWith("## ")) {
      const label = block.slice(3), anchor = `section-${headings.length + 1}`;
      headings.push([anchor, label]);
      result.push(`<h2 id="${anchor}">${inline(label)}</h2>`);
    } else if (block.split("\n").every((line) => line.startsWith("- "))) {
      result.push("<ul>" + block.split("\n").map((line) => `<li>${inline(line.slice(2))}</li>`).join("") + "</ul>");
    } else result.push(`<p>${inline(block.split("\n").map((line) => line.trim()).join(" "))}</p>`);
  }
  return [result.join("\n"), headings];
}

export async function legalPages(root) {
  try { await fs.access(path.join(root, "docs/legal")); } catch { return {}; }
  const template = await fs.readFile(path.join(directory, "legal.html"), "utf8");
  function page(slug, title, body, headings = []) {
    const values = {
      DESCRIPTION: escape(data.descriptions[slug] || data.descriptions.legal), TITLE: escape(title), BODY: body,
      LINKS: data.documents.map(([key, label]) => `<a href="${key}.html"${key === slug ? ' aria-current="page"' : ""}>${escape(label)}</a>`).join(""),
      TOC: headings.length ? '<aside aria-label="Sommaire"><strong>Dans ce document</strong>' + headings.map(([anchor, label]) => `<a href="#${anchor}">${escape(label)}</a>`).join("") + "</aside>" : "",
    };
    return template.replace(/\{\{([A-Z]+)\}\}/g, (_, key) => values[key]);
  }
  const pages = {}, cards = [];
  for (const [slug] of data.documents) {
    const source = await fs.readFile(path.join(root, "docs/legal", `${slug}.md`), "utf8");
    const title = source.split("\n")[0].replace(/^# /, "");
    const [body, headings] = markdown(source);
    pages[`${slug}.html`] = page(slug, title, body, headings);
    cards.push(`<li><a href="${slug}.html">${escape(title)} <span aria-hidden="true">→</span></a></li>`);
  }
  const introduction = '<p>Retrouvez les règles d’utilisation du service, les informations relatives à vos données et le cadre des échanges et des compétitions.</p>';
  pages["legal.html"] = page("legal", "Informations juridiques", introduction + '<ul class="documents">' + cards.join("") + "</ul>");
  return pages;
}

if (import.meta.main) console.log(JSON.stringify(await legalPages(path.resolve(directory, "../.."))));
