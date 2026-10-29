import { test, expect } from "bun:test";
import { chromium } from "playwright";
import { readFile } from "node:fs/promises";

test("game charts show values and sample sizes without hover, with metric definitions", async () => {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  try {
    const page = await browser.newPage();
    const html = (await readFile("admin.html", "utf8")).replace(/<script[^>]*src=[^>]+><\/script>/g, "");
    await page.setContent(html);
    await page.addScriptTag({ path: "admin-game.js" });
    await page.evaluate(() => {
      document.getElementById("dashboard").hidden = false;
      document.getElementById("technical").open = true;
      const day = "2026-10-28";
      AdminGameMeasurements.render({ daily: [{ day, matches_started: 2, matches_completed: 1 }], performance: [], game: {
        frames: [{ day, runtime: "air", platform: "android", phase: "3d", frames: 30, elapsed_ms: 1000, slow_frames: 3, samples: 1, fps: 30, target_fps: 60, p95_frame_ms: 67, max_frame_ms: 70 }],
        gameplay: [{ day, controller: "human", team_turns: 2, moves: 5, risk_tests: 4, falls: 1, passes: 2, completed_passes: 1, interceptions: 0, goals: 1, fall_percent: 25, pass_percent: 50 }],
      } });
    });
    expect(await page.locator("#game-frames-chart").textContent()).toContain("30 FPS");
    expect(await page.locator("#game-frames-chart").textContent()).toContain("1 échantillon(s), 30 événements d’image");
    await page.selectOption("#game-frame-metric", "slow_percent");
    expect(await page.locator("#game-frames-chart").textContent()).toContain("10 %");
    await page.selectOption("#game-play-metric", "pass_percent");
    expect(await page.locator("#game-play-chart").textContent()).toContain("50 %");
    expect(await page.locator("#game-play-help").textContent()).toContain("coéquipier");
    expect(await page.locator("body").textContent()).toContain("33,3 ms");
  } finally { await browser.close(); }
}, 30000);
