# Browser bottlenecks — 2026-10-31

Measured on ARM64, four cores, Chromium156, SwiftShader software graphics,
638×373 CSS pixels, DPR1, HIGH quality and original perspective accuracy.
These are host-specific findings, not predictions for a hardware GPU.

## Dominant cost: graphics submission and software rasterization

Five-second Chrome CPU profiles, process CPU counters and GPU traces were captured
in each fixed benchmark scene, with music. The complete baseline replay passed
ten-actor movement, original cutscenes and the real next-turn acknowledgment.

| Scene | GPU-process CPU seconds | Renderer CPU seconds | GPU share of measured Chrome CPU |
| --- | ---: | ---: | ---: |
| Menu | 19.67 | 1.06 | 94.4% |
| Orders | 17.68 | 1.10 | 93.7% |
| Moving Cania3D | 16.14 | 2.78 | 84.7% |
| Fullscreen animations | 15.09 | 2.27 | 86.4% |

The GPU process runs software graphics here. These are **CPU shares, not physical
GPU utilization**. Multithreaded CPU seconds can exceed wall time. Audio consumed
0.03–0.04 CPU seconds per window. Trace writing is outside the CPU counter window;
do not divide old captures' IO-inclusive `wallSeconds` into CPU time.

The menu trace contains990 `CommandBufferProxyImpl::WaitForGetOffset` waits,
totaling2.60s during a5.39s profile, versus22 canvas mailbox submissions.
Native WebGL submission/state calls dominate sampled menu activity. Nested trace
events overlap: their durations cannot be added. CPU-profile native-call samples
can include blocking; they are not pure computation time.

Secondary cost is Flash timeline processing: MovieClip enter/construct/frame-script
functions account for22.5% of renderer wall samples in3D and28.2% in cutscenes.
AVM2 execution accounts for18.2% and4.5%; GC1.2% and approximately0% respectively.
This supports investigating unchanged display-list/timeline work next, but does
not identify a particular game method safe to stop. Keep callbacks, animation
progress and script completion intact. The fixture does not measure the backend.

## Two grid experiments

Each comparison uses its own baseline; do not combine their results. Original
artwork, resolution and animation policy remain unchanged. Both diagnostic SWFs
are compiled from the current `FieldView` override; production sources are untouched.

| Experiment | Baseline event FPS | Variant event FPS | Conclusion |
| --- | ---: | ---: | --- |
| Disable per-cell bitmap caches | 4.52 | 3.66 | About19% slower; reject |
| Cache the whole cells layer, retaining per-cell caches | 4.50 | 5.23 | About16% faster; hardware retest |

The vector trial completed four full replays (A–B–B–A). The whole-layer trial
used a separate orders-only harness, one warmup followed by two5s samples per
variant, also A–B–B–A. P95 interval:280→277ms; P99:413→419ms. Only44/51
intervals were collected: the mean improvement is exploratory, not a proven
statistical or tail-latency improvement. No profiling/video during those samples.

Screenshots at normal scale, DPR2 and explicit4×/8× diagnostic zoom show similar
grid detail, with small rasterization differences; pixels are not identical.
The parent cache can use more memory and may invalidate on interaction. Hover,
selection, pan/zoom during play and hardware GPUs still need testing. It remains
a **benchmark-only option**, not a production default or guaranteed quality win.

Native WebGPU was also attempted. On this host Ruffle/wgpu panics in
`BufferBuilder.finish` / `register_shape_internal`: `GPUDevice.createBuffer`
rejects a2856-byte mapped allocation. Adapter availability alone does not make
the backend usable. Both attempts failed; neither contributes successful results.

## Reproduce

```sh
bun run benchmark:browser
# Open http://127.0.0.1:9927/
# Select Référence + Grille en un calque; increase duration/repetitions.

# Separate terminal; hardware/default backend, visible browser:
bun run benchmark:profile --headed --output .local/browser-profile-hardware
# Reproduce this host's software attribution (large trace files):
bun run benchmark:profile --software --trace
```

Profiling is separate from timing comparisons: tracing changes execution cost.
Outputs include per-scene `.cpuprofile`, optional `.trace.json`, `profiles.json`
and a complete `benchmark.json`. Load profiles/traces in Chrome DevTools.
`cpuWallSeconds` measures the process-counter window, excluding trace file IO.
The sampling browser is automated, not the user's active browser.

Original artifacts are in `.local/browser-profiling/`: `profiles.json`,
`hotspot-summary.json`, `vector-grid-results.json`, `grid-layer-results.json`,
`backend-results.json`, quality PNGs and `report.html`. These are ignored local
results. [Benchmark workload and metric definitions](BROWSER_BENCHMARK.md).
