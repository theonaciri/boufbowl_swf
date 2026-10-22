import { test, expect } from "bun:test";
import "../admin-game.js";

test("runtime comparison weights frame intervals and uses worst platform p95 bound", () => {
  const rows = [{ day: "2026-10-22", runtime: "ruffle", frames: 30, elapsed_ms: 1000, slow_frames: 0, samples: 1, p95_frame_ms: 34 },
    { day: "2026-10-22", runtime: "ruffle", frames: 30, elapsed_ms: 3000, slow_frames: 10, samples: 1, p95_frame_ms: 100 }];
  const [result] = globalThis.AdminGameMeasurements.combineFrames(rows);
  expect(result.fps).toBe(15);
  expect(result.p95_frame_ms).toBe(100);
  expect(result.samples).toBe(2);
  expect(result.slow_percent).toBeCloseTo(100 / 6);
});

test("gameplay rates use attempts as denominators and missing attempts stay unknown", () => {
  const base = { controller: "cpu", team_turns: 1, moves: 3, risk_tests: 0, falls: 0, passes: 0, completed_passes: 0, interceptions: 0, goals: 0 };
  const [empty] = globalThis.AdminGameMeasurements.gameplayTotals([base]);
  expect(empty.fall_percent).toBeNull();
  expect(empty.pass_percent).toBeNull();
  const [result] = globalThis.AdminGameMeasurements.gameplayTotals([
    { ...base, risk_tests: 1, falls: 1, passes: 1, completed_passes: 1 },
    { ...base, risk_tests: 9, falls: 1, passes: 9, completed_passes: 1 },
  ]);
  expect(result.fall_percent).toBe(20);
  expect(result.pass_percent).toBe(20);
});
