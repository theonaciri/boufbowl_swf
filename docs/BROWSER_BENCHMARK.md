# Browser rendering benchmark

```sh
bun run benchmark:browser
# Open http://127.0.0.1:9927/
# For another machine/phone on your network:
bun run benchmark:browser --host 0.0.0.0 --port 9927
```

The command builds a cached diagnostic SWF under `.local/client-probes` and serves
an isolated, read-only asset server. It does not modify production SWFs, website
output, accounts, packages or databases. Existing compiled game client and normal
Java/FFDec discovery are required. AS3 changes are compiled into the probe directly.

Choose variants, duration, warmup and repetitions; click **Lancer le benchmark**.
Defaults compare baseline/retained layers at60FPS, high quality, original
perspective accuracy. Other existing experiments can be selected without reducing
quality. Resetting or selecting lower quality on the normal player has no effect
here. Keep the tab visible and viewport unchanged. Allow audio if prompted.

## Fixed workload

- Current match-setup menu, then tactical orders on the actual field.
- Cania3D; ten maleIop actors follow identical zigzag routes for800 game ticks (40s of game time).
  A one-time per-actor movement notice gates sampling; frame observations verify
  that all ten actually move, without endpoint aliasing on repeated routes.
  This is a rendering fixture, not an authoritative simulation/combat benchmark.
- Original fullscreen brawl, throw and reception illustrations, using the real
  cutscene controller while the game clock is paused; music continues.
  Tactic/resolution music is pinned to loop01 in a diagnostic-only override.
- Accelerate only the unmeasured remainder, then require the actual `ResolutionDoneMessage` and next field.

The preliminary unmeasured run warms common assets. Every case creates a fresh
Ruffle instance, then each menu/orders/3D phase warms up again. Repetitions reverse
case order on alternate rounds. This reduces first-run bias; it cannot remove
thermal throttling, browser JIT variation or all cache effects.

JSON includes fixture/client SHA256, Ruffle version, requested backend and actual
renderer log, viewport/DPR, audio state/music requests, scene notices, per-phase
render counters and raw intervals. No measurements are claimed for a failed run.
Completed runs are retained in localStorage and exportable as JSON/CSV.

## Reading results

Game samples are AS3 `ENTER_FRAME` intervals measured with `getTimer` (1ms
resolution). FPS =1000/mean interval. P50/P95/P99 use nearest rank; P95 is a frame-time
percentile, **not a95% confidence interval**. Lower times are better. Long frames
above50/100ms, maximum and1%low FPS are in JSON. Aggregation pools raw intervals,
not average FPS values. Browser `requestAnimationFrame` intervals are separate:
neither counter directly measures GPU-presented frames. Long loading phases,
user-paused audio setup and per-case total duration remain distinguishable.

Fullscreen results include all three animation sequences, with keys preserved in
the raw data. Audio verification requires a loaded game music resource and a
running WebAudio context; it does not prove loudspeaker output. No audio-disabled
run should be presented as fulfilling the music workload.

## Retained layers (`retainLayers=1`)

Ruffle retained fills did not reflect live bitmap mutation in the pixel test.
Exact BitmapData comparisons detect changes once per texture/session frame; shared
snapshots have a64MiB budget. This adds CPU work and memory, measured in the test.

Projection/culling upstream still runs; this experiment avoids clearing and
reissuing unchanged drawing commands, rather than caching the whole scene.

Only graphics consisting exclusively of bitmap triangles are retained. Compare
the complete ordered sequence of texture identities, UVT, projected coordinates,
size and sampling policy. If unchanged, keep the existing Graphics commands and
avoid clearing/reissuing them. Any changed/reordered/removed triangle redraws the
layer. Mixed vector/fog/mask/sprite operations flush pending triangles and use the
original path. Display-object ordering, filters, alpha, camera and resolution are
unchanged; no rasterization, reduced resolution or reduced animation cadence.

The probe checks exact pixels, live texture mutation, camera-coordinate changes,
mixed-operation fallback and empty-layer clearing before each measured variant.
`layersReused`/`layersRedrawn` quantify whether a scene benefits. A zero reuse count
means this optimization did not engage; higher FPS alone is insufficient evidence.

Results from this ARM server use SwiftShader software graphics and are diagnostic;
repeat on a normal hardware-accelerated browser before choosing a default.

Additional options: **Grille en un calque** caches the complete cells layer while
keeping the original per-cell caches; **Grille vectorielle** disables per-cell
caches. They use separate diagnostic SWFs and leave production `FieldView` intact.
The3D-reuse counter does not count native grid bitmap caches.
[CPU/GPU profiles, grid comparisons and profiling commands](BROWSER_BOTTLENECKS.md).

Runtime data is copied out of its iframe before unloading. Audio contexts are
closed and the player removed between cases; iframe navigation is generation-gated
so readiness from the previous run cannot satisfy the next run. Visibility or
viewport/DPR changes stop the comparison. Unsupported/failed cases are listed,
excluded from aggregates, and do not silently become successful measurements.
The production100ms slow-frame clock clamp remains enabled: under severe load,
scene progression can slow down. Sampling windows use wall time and the fixed
route/position evidence is retained; results are not a pixel-identical timedemo.

## Host measurement —2026-10-31

ARM64, four cores, Chromium156, wgpu-webgl/SwiftShader,638×373 CSS pixels, DPR1; high quality,60FPS target. One preliminary pass; two repetitions per option, A–B–B–A;5s menu/orders/3D sampling and1s warmup. Three original fullscreen sequences sampled in full.

| Scene | Option | Event FPS | Mean ms | P95 ms | P99 ms | N |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| menu | baseline | 11.51 | 86.9 | 257 | 531 | 114 |
| orders | baseline | 4.68 | 213.6 | 388 | 394 | 45 |
| stadium | baseline | 10.06 | 99.4 | 186 | 237 | 99 |
| cinematics | baseline | 6.79 | 147.2 | 269 | 394 | 149 |
| menu | layers | 11.47 | 87.2 | 405 | 441 | 113 |
| orders | layers | 4.63 | 215.9 | 406 | 514 | 45 |
| stadium | layers | 9.80 | 102.1 | 183 | 234 | 97 |
| cinematics | layers | 6.93 | 144.3 | 212 | 367 | 148 |

All four measured runs passed texture/pixel checks, ten-actor movement evidence, audio verification, original cutscene completion, ResolutionDone and next field. Retention reused198 layers during3D sampling and4 during cutscenes. It avoided the repeated affine draws, but did not demonstrate an average FPS gain. Leave disabled. Two repetitions and software graphics do not establish hardware-browser performance or statistical significance. No screenshot/video capture occurred during sampled phases. One screenshot was taken during unmeasured completion of the preliminary pass.
