# Browser performance

```sh
bun run build                     # Rebuild after client changes
bun run benchmark:browser         # Open http://127.0.0.1:9927/
# Phone / another machine:
bun run benchmark:browser --host 0.0.0.0
# Separate terminal, optional CPU profiling:
bun run benchmark:profile --headed
bun run benchmark:profile --software --trace  # Large GPU trace files
```

The benchmark compares current browser rendering (whole-grid caching) against a
reference with only that cache disabled. Both use Ruffle's default backend, HIGH
quality, original perspective subdivision and the same resolution/FPS target.
Native clients retain their original per-cell caches without a parent cache.
Child changes invalidate the browser's parent cache. The cache covers cells only;
players, ball and order arrows remain in separate layers.

## Workload and interpretation

The command compiles cached diagnostic SWFs under `.local/client-probes`, then
serves a local read-only asset server. No real accounts, backend or production
packages are involved. Requirements: existing compiled client, Java/FFDec, assets.

Each fresh player runs match setup, orders, ten Iop actors following fixed zigzags
in Cania3D with music, and the original brawl/throw/reception fullscreen animations.
It requires actual movement of all ten actors, cutscene completion, real
`ResolutionDoneMessage` and the next field. This is a rendering fixture, not a
combat/simulator benchmark. Tactic/resolution music is fixed to loop01.
The orders phase verifies that the actual grid-cache flag matches its variant.

Use three repetitions with warmup. Alternate rounds reverse option order.
Keep viewport, DPR and tab visibility unchanged; changes invalidate the comparison.
Unloading closes audio contexts and removes the old player. Errors remain failures,
not measurements; music needs loaded resources and an active WebAudio context.

FPS =1000/mean AS3 `ENTER_FRAME` interval. P95/P99 use nearest ranks, not confidence
intervals. Aggregation pools raw intervals; rAF callbacks are recorded separately.
Neither counter measures GPU-presented frames. Compare slow-frame percentages,
not raw counts when sample sizes differ. The production100ms game-clock clamp
remains active, so severe stalls can slow scene progression.

JSON/CSV exports and localStorage preserve results. JSON also records fixture and
client hashes, actual renderer logs, audio, positions and completion notices.
CSV alone cannot establish renderer fallback or per-run variance.

## Experiments retained and removed — October 2026

Two user hardware comparisons, three runs per variant:

| Orders screen | First comparison FPS | Second comparison FPS | Decision |
| --- | ---: | ---: | --- |
| Reference | 38.78 | 35.87 | Control |
| Whole-grid cache | 45.30 | 45.61 | Keep:17–27% higher mean cadence |
| Requested WebGPU | 40.73 | 36.64 | Remove override: inconsistent benefit |

Grid caching's rare stalls remain a limitation: second comparison P95 improved
32→28ms, but P99 worsened44→51ms; frames over50ms rose0.23→1.27%.
3D/cinematic gains were small. Normal, DPR2 and4×/8× diagnostic screenshots
retained similar grid detail, with minor rasterization differences.

Removed experiments and associated controls, callbacks and probe-only checks:

- Projected-geometry cache: slower, around56→42FPS in one hardware3D comparison.
- Retained triangle layers:198 layer redraws skipped in the server fixture, but
  average3D cadence10.06→9.80FPS. Texture snapshots/comparison added overhead.
- Vector grid without per-cell caches: slower on server and hardware.
- Explicit WebGPU/WGPU/WebGL selection: no reliable overall win; default Ruffle
  selection remains. This server's WebGPU also failed mapped-buffer allocation.
- Reduced subdivision and native UVT bypass: rejected quality compromises. Original
  fixed subdivision remains essential; see [Ruffle audit](RUFFLE_RENDERING.md).

The benchmark and optional profiler remain; rejected algorithms are not shipped.
Historical variants can be recovered from experiment commits13dccf4/00a9d24.

## Profile findings

ARM64 four-core server, Chromium156/SwiftShader,638×373/DPR1: GPU-process CPU
accounted for85–94% of measured Chrome CPU across scenes. This is software graphics
CPU, not physical GPU utilization. Menu traces showed990 command-buffer waits
(2.60s in5.39s). Native-call wall samples can include blocking; nested traces overlap.
Timeline processing was a secondary candidate (22.5% of renderer wall samples
in3D,28.2% in cutscenes), not a demonstrated safe optimization.

Profiler outputs `.cpuprofile`, optional `.trace.json`, `profiles.json` and
`benchmark.json` under `.local/browser-profiling`. `cpuWallSeconds` excludes trace
file IO; multithreaded CPU seconds may exceed wall time. Tracing changes execution
cost: use separate unprofiled runs for performance comparisons. Software results
must not be extrapolated to hardware GPUs. Raw local captures remain ignored.
