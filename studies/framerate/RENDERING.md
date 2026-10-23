# Running-character rendering follow-up

The user reports `60 / 240` in menus and around `12 / 240` when all characters
run, on a 240 Hz display with an RTX 4070 Mobile and a Wayland session. Reducing
the window size does not help. CPU model and the actual Wine/driver/compositor
configuration are unknown. Main and the live backend remain untouched.

## What this establishes

The requested stage rate is active. The former application-selected 50/25 scene
limits no longer explain the result. There are two questions: why a light scene
stays near 60, and why running players add enough work to fall below it.

The lack of improvement at smaller window sizes makes pixel fill less likely
as the main cause. It does not prove which function dominates the user's CPU.
This renderer uses Away3D's Flash display-list path: CPU-side projection, sorting
and display-tree manipulation, with character MovieClips added as display objects.
It is not the later Stage3D mesh renderer. A fast GPU cannot automatically make
those ActionScript operations parallel. Final drawing/presentation still depends
on the host runtime; no claim is made that all rasterization happens on the CPU.

`play.py` explicitly selects Wine's `x11` driver. On the reported Wayland session,
the game therefore uses the XWayland path, not Wine's native Wayland driver.
That is a relevant runtime boundary, not proof that XWayland causes the 60 limit.

## Traced path and applied optimization

`SceneContainer.onEnterFrame` calls `View3D.render`, which projects the scene,
clears sessions and draws sorted primitives. `Renderer.renderPrimitive` positions
and scales each MovieClip display object and passes it to `SpriteSession`.
The former session cleared its graphics **and removed every display child** on
an update, then added them back during drawing. Stage lifecycle events propagated
through nested character objects; `TiphonSprite.onAdded` recalculated animation
scales. This also happened while a character merely changed world position.

The new shared `patches/SpriteSession.as` preserves attached children and
reconciles painter order using indexed insertion/reordering. It removes stale
children after drawing. It retains the existing material/shape pools, clipping,
alpha, blend modes, cache policy and renderer sorting. Duplicate display-object
draws retain last-draw-wins order. Genuine removal/reappearance still generates
stage events. No pose, action clock, collision or backend outcome was changed.
The patch registry includes this override in desktop/web and Android builds.

We did not enable the old rasterized-animation path globally. It has different
label/event and subentity behavior, and attached ball/effect slots need dedicated
validation before using it for running-pose caches.

## Controlled evidence

These measurements are from Chromium/Ruffle with SwiftShader, not the user's
Wine runtime or RTX GPU. Absolute times and gains must not be transferred to it.

| Probe | Former session | Retained session | Scope |
| --- | --- | --- | --- |
| 300 redraws, 10 synthetic actors, 30 children each; three samples | 329, 327, 327 ms | 82, 82, 82 ms | Session-loop benchmark; about 75% less time |
| Stage additions in each loop sample | 90,000 | 300 | Initial attachment remains |
| Stage removals in each loop sample | 89,700 | 0 | Excludes final teardown after timing |
| Ten-runner replay: total instrumented `View3D.render` time | 1,017 ms over 70 calls | 720 ms over 70 calls | One capture per variant; about 29% less AS3 render-call time |
| `TiphonSprite.onAdded` calls in that replay | 446 | 96 | Necessary initialization/change events remain |
| Whole probe window, Flash frame-event rate | 5.33/s | 5.53/s | Includes startup and fixture delays; not a gameplay benchmark |

The end-to-end difference is small. Much of this host's frame cost remains outside
the instrumented render call: animation execution, Flash rendering/composition,
and runtime scheduling. This optimization does **not** establish a fix for the
user's 12 FPS, or a fourfold improvement to gameplay FPS.

The ten-runner fixture issues ten move orders to the existing engine with a fixed
seed, on separated lanes without combat. Its authoritative result contains 260
move events covering all ten actors. Rules, engine and input hashes are recorded
in `rendering/provenance.json`. No server/simulator source was modified.

The baseline and optimized ten-runner replays at target 60, optimized ten-runner
replay at target 240, and optimized pass/catch replay at target 240 all reached
3D playback → exactly one ResolutionDone → MATCH_END, with one UI update per
scene update. The chosen stage rates were retained. The 240 correctness runs
were not used for comparative timing; background compilation could affect them.

Shared smoke now checks stable attachment, depth reorder, removal, reappearance,
duplicate draws, mixed pooled shape layers, empty scenes and unchanged cached
frames. It passed in both runtime-policy branches in Ruffle. The game rebuilt
and both diagnostic roots compiled. Wine is absent on this host; no Wine runtime
pass or physical high-refresh presentation is claimed. AIR license blocking in
the earlier study is a separate boundary and does not explain the user's Wine FPS.

An initial profiler-only failure omitted an explicit `getTimer` import required
by the replacement compiler. This was corrected before successful replay captures;
failed local traces are not counted as passes.

## Is 240 FPS possible?

The application permits 240. The target is an upper request, not a guarantee.
At 12 FPS a frame takes about 83.3 ms; 60 FPS needs 16.7 ms and 240 needs 4.17 ms
for **all** work and presentation. Authored poses remain 25 Hz while world
trajectories can be sampled more often. Neither the powerful GPU nor the setting
alone guarantees that the current Flash/Wine renderer can meet 4.17 ms.

The [Stage API documentation](https://airsdk.dev/reference/actionscript/3.0/flash/display/Stage.html#frameRate)
distinguishes requested cadence from platform capability. Its `vsyncEnabled`
control is documented for AIR; it must not be treated as a portable Flash Player
switch. The [pinned Ruffle scheduler](https://github.com/ruffle-rs/ruffle/blob/46fec3f1b2e625fae7035bb3b00d6d5c0ec0d413/web/src/lib.rs)
uses browser redraw opportunities, so multiple frame events do not establish
multiple displayed frames.

To isolate the user's actual runtime, close the game, keep the probe foreground,
and run on the updated study branch:

```sh
./play.sh --fps-probe 240
```

The launcher builds a cached diagnostic SWF under `.local/client-probes`, uses the
same standalone Flash/Wine prefix/driver path, and forces menus mode so no local
backend service starts. The replacement document class contains only a counter
and a text label: no MainApp, game scene or animations. It does not change saved
game preferences. Normal `--fps-experiment` behavior remains available separately.

- Blank probe near `60 / 240`: investigate the Flash/Wine scheduling and
  presentation path separately; game animation code cannot account for the cap.
- Blank probe above 60, but game UI near 60: investigate game UI work and runtime
  behavior with that workload.
- Blank probe fast, running scene slow: continue profiling character animation
  execution, sprite bounds/projection, vector drawing and composition. Bitmap
  pose caching or a renderer migration may be justified, with event/FX checks.

The minimal counter was compiled and tested in Ruffle: three 3-second windows
produced about 192–194 frame events/s and 47–48 browser callbacks/s on this host.
This proves the probe functions, not 240 Hz presentation or the user's Wine limit.
Ruffle reports a compatible Flash version through `Capabilities.version`; that
string is not evidence that Adobe Flash Player was used.

## Reproduce the rendering experiment

```sh
python3 studies/framerate/render_cost.py --baseline --serve --port 9915
python3 studies/framerate/render_cost.py --serve --port 9916
```

The harness selectively exports the original three classes from the preserved
base; its export cache is tied to that input hash. It builds disposable SWFs
with explicit timer imports and counters. It does not replace FPS policy.

On each server open `/study.html?applied=1&bare=1&fps=60`, then run:

```js
await studyReady;
result.benchmarks = [];
call('studySessionBench', 20, 30); // warm-up
for (let i = 0; i < 3; i++) result.benchmarks.push(call('studySessionBench', 300, 30));
// On the optimized server:
result.sessionCheck = call('studySessionCheck');
await save();
```

For replays use `/study.html?applied=1&replay=1&fps=60`, then:

```js
await studyReady;
call('studyRenderProfile', true);
await sample(60, 0, 0, true);
result.renderProfile = call('studyRenderProfile');
await save();
```

Use a fresh per-rate trace. Repeat the optimized replay at 240. To use pass/catch,
start the optimized harness with `--reception --port 9917`; its results go to a
separate `retained-reception` folder. `validate_rendering.py` checks saved evidence
without asserting hardware speed gains. Shared validation commands are in the
code map. A browser wrapper for the blank SWF is `runtime_probe.html?swf=PATH`;
`runRuntimeProbe()` records frame events and browser callbacks independently.
