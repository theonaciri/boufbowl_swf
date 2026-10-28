import { test, expect } from "bun:test";
import { chromium } from "playwright";

test("automatic refresh starts disabled, honors the chosen interval and stops", async () => {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  try {
    const page = await browser.newPage();
    await page.route("https://admin.test/", route => route.fulfill({ contentType: "text/html", body: '<div id="control"></div>' }));
    await page.goto("https://admin.test/");
    await page.evaluate(() => {
      window.calls = []; window.setInterval = (fn, ms) => { window.calls.push(ms); window.tick = fn; return 123; };
      window.clearInterval = id => { if (id) window.calls.push(-id); };
    });
    await page.addScriptTag({ path: "admin.js" });
    await page.evaluate(() => { window.refreshes = 0; AdminConsole.autoRefresh(document.getElementById("control"), () => window.refreshes++); });
    const select = page.locator("#control select");
    expect(await select.inputValue()).toBe("0");
    expect(await page.evaluate(() => window.calls)).toEqual([]);
    await select.selectOption("30");
    expect(await page.evaluate(() => window.calls)).toEqual([30000]);
    await page.evaluate(() => window.tick());
    expect(await page.evaluate(() => window.refreshes)).toBe(1);
    await select.selectOption("0");
    expect(await page.evaluate(() => window.calls)).toEqual([30000, -123]);
  } finally { await browser.close(); }
}, 30000);
