# Browser rendering experiments

Branch: `experiment/browser-rendering`. No default renderer/quality change.
Native Android/desktop policies remain unchanged. No production deployment.

Build the game, then the website. The experiment controls are in **Affichage →
Expériences de rendu navigateur**. Applying them reloads the player; URLs preserve
settings. Reset removes only experiment parameters.

```sh
bun run build
bun tools/website/build.mjs --output .local/website/render-experiments
```

Use the normal website/backend hosting arrangement with this output directory.
The standalone static server does not implement `/api/client` or game APIs.

| Experiment | URL parameters | Purpose |
| --- | --- | --- |
| Renderer | `renderBackend=webgpu`, `wgpu-webgl`, `webgl` or `auto` | Compare Ruffle backends. Selection is a preference: inspect Ruffle's console for the actual backend/fallback. Direct WebGL may lose effects. |
| Subdivision | `triangleDetail=low`, `medium`, `high`, `quality` or `original` | Low: error threshold24/depth3; medium12/4; high and original6/5. `quality` follows stage quality. These are existing heuristic screen-space units, not guaranteed pixel-error bounds. |
| Projected geometry cache | `geometryCache=1` | Reuse subdivision and affine matrices for exactly identical projected triangles. Does not cache whole stadium bitmaps or reduce draw calls. |
| Original perspective path (control) | `perspective=native` | Bypass subdivision and send original `GraphicsTrianglePath.uvtData`. **Incorrect on the bundled nightly**; illustrates the cost of the workaround. Not an upstream perspective-support implementation or an equal-quality speed comparison. |

`renderDiagnostics=1` shows cumulative calls, cache hits, newly calculated affine
triangles and native-UVT calls. Counters default off. They are not FPS or GPU frame
counts. Applying settings starts a new run. Browser FPS/quality presets remain
independent; hold them constant for comparisons.

## Cache contract

Per-session exact keys include texture identity/dimensions, projected vertices,
UVT, quality and smoothing/repeat flags. Moving camera/geometry and quality changes
miss; cached fills reference live BitmapData, so palette/pixel updates remain live.
Each session clears its cache at128 entries or32768 drawing commands. Old command
sets are released on eviction/session collection. Cache-on can be slower for
constantly moving views because lookup/allocation work may exceed reuse.

## Suggested phone/desktop checks

1. Baseline: no experiment parameters; record actual renderer, viewport, DPR,
   FPS target, quality and measured game FPS.
2. Same match/replay, one option at a time. Test renderer choices, low/medium
   subdivision and cache off/on. Include camera movement, zoom and a full3D turn.
3. Check stadium perspective, seams, character depth, chat, progress bars and
   popup skins. Return to2D and resize. Inspect console for runtime errors.
4. NativeUVT is a known-broken visual control. Do not pick it as a release default
   based on higher FPS. True upstream support still requires a separate Ruffle
   renderer implementation and build; no custom runtime is shipped here.

No performance improvement is claimed before device measurements. Headless
SwiftShader timings on this server are not representative of hardware browsers.

## Verification performed

- Bun:9 tests passed (presets, experiment URL validation, cursor zoom).
- Actual Ruffle/SwiftShader probe: repeated geometry hit the cache with identical
  pixels; live texture mutation remained visible; moved vertices and changed UVT
  missed; reduced detail emitted fewer pieces; native control bypassed subdivision.
 140 distinct geometries crossed the eviction limit without a runtime error.
- Reusable probe: `python3 -m tools.client_probe --serve --port 9926`, then
  `player.ruffle().callExternalInterface("probeRenderingCache")` in the page console.
  This diagnostic intentionally changes experiment settings; reload afterward.
- Both application roots compiled successfully. Isolated website build/check passed.
- NativeUVT support in Ruffle remains unimplemented. No upstream fix claimed.
