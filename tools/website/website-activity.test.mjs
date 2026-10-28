import { test, expect } from "bun:test";
import { chromium } from "playwright";
import { readFile } from "node:fs/promises";

test("website activity keeps aggregate metrics distinct and charts accessible", async () => {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  try {
    const page = await browser.newPage({ viewport: { width: 360, height: 800 } });
    const html = (await readFile("website-activity.html", "utf8")).replace(/<script[^>]*src=[^>]+><\/script>/g, "");
    await page.setContent(html);
    await page.addStyleTag({ path: "admin.css" });
    await page.evaluate(() => {
      const fixture = {
        generated_at: 1700000000,
        sections: [{ name: "Jouer", views: 12, seconds: 500 }, { name: "Règles", views: 3, seconds: 60 }],
        classes: [{ name: "Crâ", count: 7 }], characters: [{ name: "Aria", count: 4 }],
        downloads: [{ name: "Android", count: 5 }], web: [{ name: "Navigateur", count: 2 }], asset_requests: [],
      };
      window.AdminConsole = { $: id => document.getElementById(id), api: async () => fixture, autoRefresh: () => {}, init: callback => { document.getElementById("console-main").hidden = false; callback(fixture); } };
    });
    await page.addScriptTag({ path: "website-activity.js" });
    expect(await page.locator("#website-stats strong").allTextContents()).toEqual(["15", "5", "2"]);
    const bar = page.getByRole("button", { name: "Jouer : 12 vues, 8 min de temps visible cumulé." });
    await bar.click();
    expect(await bar.getAttribute("aria-pressed")).toBe("true");
    expect(await page.locator("#website-section-selection").textContent()).toContain("12 vues");
    await page.selectOption("#website-section-metric", "seconds");
    expect(await page.locator("#website-section-bars strong").first().textContent()).toBe("8 min");
    await page.selectOption("#website-interest-kind", "characters");
    expect(await page.locator("#website-interest-bars").textContent()).toContain("Aria");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator("#website-refresh").click();
    expect(await page.locator("#website-status").textContent()).toBe("");
  } finally { await browser.close(); }
}, 30000);
