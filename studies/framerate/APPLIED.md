# Applied high-refresh policy

The baseline study is commit `a4b1762`. After reviewing it, the user authorized
applying useful findings to the game. This change remains on
`study/animation-framerate-interpolation`; nothing was merged, deployed, restarted
or written to the main checkout. Generated game/probe builds are local artifacts.

## Behavior

- Native desktop and Android: an explicit saved 25–240 FPS target now applies
  both during resolution and afterward. Previously a selected 144 became 50 on
  resolution entry and 25 on exit. With no explicit setting those 50/25 defaults
  remain; the legacy 25 FPS cap remains 25.
- Web: loader `webFps`, live display settings and the in-game slider accept
  25–240 instead of stopping at 60. Existing performance/balanced/quality presets
  stay 25/30/60. A high-refresh choice is optional, not a new automatic default.
- Root policy is shared through `ClientRuntime.as.inc`; Android retains its
  platform input/layout and does not enable browser-specific behavior.

Existing absolute-time trajectories provide the additional movement positions.
Authored pose rate, time providers, scripts, collisions, ball ownership, frame
completion events and backend simulation were not modified. No runtime busy loop,
Ruffle forced-rate option, new body poses or asset interpolation was added.
Requesting a higher rate is not a guarantee of receiving or displaying it.

## Reproducible checks

```sh
python3 -m tools.verify_client --area shared
python3 -m tools.verify_client --area web
python3 -m tools.verify_client --area compile
bun test studies/framerate/interpolation.test.js
python3 studies/framerate/validate_results.py
python3 studies/framerate/validate_applied.py
```

The applied browser server is built with `--production-policy`: it instruments
counters but does **not** replace `sceneFrameRate`. It uses a locally rebuilt
SWF containing the maintained patches, including OptionsView. Run it on port
9914 as described in [README.md](README.md). For replay, use:

```js
// /study.html?applied=1&replay=1&fps=144
await studyReady;
await sample(144, 0, 0, true);
await save();
```

Repeat with targets 25 and 240; use `runtime=flash&fps=60` for the native settings
branch in Ruffle. Each trial needs an empty per-rate trace to avoid reading an
old MATCH_END. Results are retained separately under `applied/`; baseline timing
matrices and replay evidence are unchanged.

The bare control starts at `?applied=1&bare=1&fps=144`. It records loader acceptance,
then exercises `studySetRate`/`studySettings` at 25,30,50,60,90,120,144,240.
`studyWebDisplay` rejects 24,241,NaN,+Infinity,-Infinity and unsupported qualities
without changing the stage setting. `studySynthetic` rechecks actual controller
and trajectory classes. `probeShared` is run on the normal page (the bare page
returns before installing that callback); its result is attached to the control
JSON. The validator checks every captured assertion rather than treating a
non-empty result as a pass.

## Runtime boundary

The test browser uses SwiftShader software rendering and is not a physical
high-refresh display. Replay counters must show the chosen **stage setting**
throughout the scene, equal scene/UI update counts, position writes, and exactly
one ResolutionDone followed by MATCH_END. This verifies policy and a saved
pass/catch scenario, not 144/240 FPS gameplay or all animation transitions.

Both native diagnostic roots compile. Native execution remains unverified: the
baseline attempt was blocked by AIR's developer license requirement before
application code ran; no native runtime pass is claimed for this change. Real
Windows/Linux/Android rendering, high-refresh display timing, power/temperature
and longer mixed-action matches remain the next validation step before publishing.

## Recorded result

Shared tooling and web verification passed. The local game rebuilt successfully;
both desktop and Android diagnostic roots compiled against that rebuild. Actual
AS3 shared smoke passed in both browser and native policy branches inside Ruffle.
Eight accepted settings, seven rejected inputs, unchanged authored frame-index
sequences, interpolation endpoints and single completion callbacks passed.

| Requested target | Policy branch in Ruffle | Scene updates | UI updates | Observed scene setting |
| --- | --- | --- | --- | --- |
| 25 | ruffle | 129 | 129 | 25 |
| 60 | flash | 128 | 128 | 60 |
| 144 | ruffle | 128 | 128 | 144 |
| 240 | ruffle | 128 | 128 | 240 |

All four reached 3D playback, exactly one ResolutionDone and MATCH_END in that
order. The table records requested/retained settings, **not achieved display FPS**.
`applied/validation.json` fingerprints the patched sources, local rebuilt SWF and
diagnostic SWF and preserves focused verification status. Raw timing/ordered
events remain in `applied/results-*.json`.
