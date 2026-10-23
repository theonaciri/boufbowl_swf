# Animation rate and interpolation study

Study branch: `study/animation-framerate-interpolation`, based on `6855365`.
Date: 2026-10-23. Baseline study committed as `a4b1762` before changing game
source. Measurements below describe that baseline. The subsequently authorized
policy fix is documented in [APPLIED.md](APPLIED.md). All edits/builds remain in
this worktree; no main checkout, live service, published site or download changed.

## Answer

There is no universal 60 FPS limit in the game's animation machinery. There are
several application-selected rates, a 25 Hz authored-pose timeline, and the host's
ability to render/present frames. The study-only diagnostic successfully requests
144 and 240 Flash updates per second in Ruffle. It does **not** demonstrate a
144/240 Hz display: this browser supplies about 60 repaint callbacks per second.

The existing movement trajectories already interpolate positions with time.
Higher display frequency can sample more positions without speeding up the run.
It cannot create new limb poses merely by repeating a 25 FPS MovieClip frame.
Interpolation can be evaluated on demand for any supported timestamp; an
unbounded number of visible frames is neither possible nor useful. The present
AS3 trajectory API takes integer milliseconds, so even 10,000 requests over one
second produce only 1,001 distinct position samples. A fractional-time prototype
produces 10,001 samples, but that is a mathematical sampling test, not 10,000
rendered game frames or a practical target.

The safest next experiment is a bounded 120/144 Hz presentation option, preserving
authored pose timing, server simulation and action callbacks. Do not globally
change the animation constant or run the whole game in an unlimited busy loop.

## Traced rates and their owners

| Layer | Baseline behavior | Evidence |
| --- | --- | --- |
| SWF/library metadata | Copied runnable SWF, all seven available body/movement library headers and the sampled ball asset declare 25 FPS | `provenance.json`, `asset-rates.json`; header reads |
| App startup | Root restores native preference or defaults to 60 | `patches/BoufbowlClient.as`, `ClientRuntime.as.inc` |
| Browser launch/display controls | `webFps` and `setWebDisplay` accept 25–60; browser options clamp to 60 | same root/policy, `OptionsView.as` |
| Saved native preference | accepts 25–240 | `readFrameRatePreference`, options slider |
| Scene entry/exit | defaults to 50 in resolution and 25 afterward; native uses `min(default, preference)` | `ResolutionMediator.as`, `sceneFrameRate` |
| Live option changes | setter writes `stage.frameRate` directly; later scene entry can cap it again | `OptionsView.setFrameRateFromPointer` |
| Model/scene updates | per `ENTER_FRAME`; game/real time read before scripts/models | `ResolutionView.enterFrameHandler` → `SceneController.update` |
| 3D draw | another `ENTER_FRAME` listener calls Away3D `View3D.render` | `SceneContainer.onEnterFrame` |
| Motion | absolute-time trajectory sampling, not one-hex-per-frame | `MoveBoufbowlerToWithDurationAction` → `Boufbowler.moveToDuration/updatePosition` → `SegmentTrajectory.getPosition` |
| MovieClip effects/cutscenes | `elapsedMs * .025`, rounded to an integer timeline frame | `FrameController` → `ControlledMovieClip.gotoAndStop` |
| Character animations | library frame rate feeds controlled clips | `TiphonSprite` → `FpsControler` → `EnterFrameDispatcher` |
| Server simulation | configured independently; base tick is 0.1 seconds | `backend/engine_base.json` |

The apparent 60 limit can therefore have different causes. In the browser it is
an explicit control limit. Native scene entry actually asks for 50, while startup
or a live options change can ask for 60 or more. The 25 FPS authoring rate is not
the server's simulation rate, and raising a stage setting does not necessarily
raise displayed FPS.

`AsvmTimeProvider` and the slower time-provider wrapper use elapsed time. The
browser path clamps a long clock advance to 100 ms. This intentionally slows
presentation under severe stalls; wall-clock replay durations measured on the
software renderer below should not be read as deterministic scene durations.

## Runtime sources checked

The bundled Ruffle JS contains commit
`46fec3f1b2e625fae7035bb3b00d6d5c0ec0d413`, matching tag
`nightly-2026-10-13`. Conclusions about that scheduler were checked against this
exact revision, not just today's master:

- [Stage setter](https://github.com/ruffle-rs/ruffle/blob/46fec3f1b2e625fae7035bb3b00d6d5c0ec0d413/core/src/avm2/globals/flash/display/stage.rs): accepts/clamps 0.01–1000, unless the frontend locks the rate.
- [Web loop](https://github.com/ruffle-rs/ruffle/blob/46fec3f1b2e625fae7035bb3b00d6d5c0ec0d413/web/src/lib.rs): browser animation callback ticks the core, then renders once when needed.
- [Core scheduler](https://github.com/ruffle-rs/ruffle/blob/46fec3f1b2e625fae7035bb3b00d6d5c0ec0d413/core/src/player.rs): can catch up multiple frame updates in one browser callback, with a load-dependent maximum of five.
- [Ruffle load option](https://ruffle.rs/js-docs/master/interfaces/Config.URLLoadOptions.html#frameRate): `frameRate` locks the player rate and overrides movie changes. It is a diagnostic alternative, not a good transparent replacement for working in-game FPS controls.
- [AIR Stage reference](https://airsdk.dev/reference/actionscript/3.0/flash/display/Stage.html#frameRate): documents 0.01–1000 and warns actual rate depends on hardware, platform policy and vsync.
- [Browser scheduling](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame): callbacks usually follow display refresh. Their count does not prove GPU presentation or distinct displayed content.

## Experiments and interpretation

### Actual AS3 controllers and trajectories, controlled timestamps

`studySynthetic` runs the game's unmodified `FrameController` and
`SegmentTrajectory` at timestamp sequences corresponding to 25, 30, 50, 60, 90,
120, 144, 240, 1,000 and 10,000 updates per second. This runs inside the diagnostic
SWF in Ruffle, not a Python reimplementation.

Every rate produced the same frame-index sequence (0 through 25), exactly one
completion callback, the same final x=100 position, and interpolation error below
1.5e-14 world units. The sequence includes the initial controller index 0; this
is **25 changes after the initial index**, not 26 newly authored character poses.

| Sampling requests in one second | Distinct positions including start | Largest x step over 100-unit travel | Authored frame-index changes after start |
| --- | --- | --- | --- |
| 25 | 26 | 4.0 | 25 |
| 60 | 61 | 1.7 | 25 |
| 144 | 145 | 0.7 | 25 |
| 240 | 241 | 0.5 | 25 |
| 1,000 | 1,001 | 0.1 | 25 |
| 10,000 | 1,001 | 0.1 | 25 |

This explains why 25→60 can look smoother: world movement/camera have additional
positions available while limbs/effects keep their authored cadence. 60→144 can
likewise help on a host that actually draws and displays those samples. It does
not require changing match speed.

### Measured browser timing

Two matrices each cover eight requested rates, three repeats, 3-second windows,
350 ms settling, and alternating order. The first suppresses startup UI in the
study root to isolate scheduling; the second uses the normal game menu. The
probe is still the actual game's SWF. Counters distinguish Flash `ENTER_FRAME`,
zero-millisecond duplicate timestamps and browser animation callbacks.

Environment: Chromium 154 Linux x86_64, four reported hardware threads, DPR 2,
640×375 CSS player / 1280×750 backing canvas, ANGLE/Vulkan **SwiftShader software
GPU**, foreground document. No physical high-refresh display was available.

| Requested | Bare Flash events/s median | Browser callbacks/s median | Same-ms event fraction | Normal menu Flash events/s median |
| --- | --- | --- | --- | --- |
| 25 | 25.0 | 59.7 | 0.0% | 22.8 |
| 30 | 30.0 | 59.7 | 0.0% | 22.9 |
| 50 | 50.0 | 59.7 | 0.0% | 22.5 |
| 60 | 60.0 | 59.6 | 0.2% | 22.8 |
| 90 | 90.0 | 59.6 | 31.7% | 22.5 |
| 120 | 120.0 | 59.7 | 47.2% | 22.8 |
| 144 | 143.9 | 59.6 | 55.4% | 11.0 |
| 240 | 240.3 | 59.7 | 72.8% | 3.9 |

Three repeats are descriptive, not a confidence interval. Raw samples and
interval arrays are retained. The menu at 240 varied from 2.6–17.7 frame events/s;
its median browser callback rate was 2.2/s. This demonstrates a renderer/load
bottleneck on **this host**, not a general player's expected performance.
No claim of a production FPS gain follows from these measurements.

At 240 in the bare control, about 73% of frame events have the same integer timer
value as their predecessor. Scheduling more Flash updates between redraws is
therefore not equivalent to presenting more frames. A native 120/144 Hz device
and hardware-accelerated browser must be tested before judging the visible gain.

### Rendering-only interpolation feasibility

`interpolation.test.js` is an explicitly separate mathematical presentation
prototype. Four tests (53 assertions) cover multiple display samples per logical
update, stable callback order/counts, preserved endpoints, paused game time,
instant teleport boundaries, no mutation of possession, and fractional versus
integer milliseconds. It uses a known replay path, not guesses about future
live simulation. This supports the architecture, not a claim that a new
interpolator has been integrated into the game.

### Full 3D reception replay

The same saved authoritative reception record is rendered at several requested
rates. Instrumentation counts scene/UI updates and sprite-position setter calls.
Validation requires a 3D playback marker, exactly one `ResolutionDoneMessage`,
and `MATCH_END` in order, plus one UI update per scene update. See saved replay
results and `summary.json` for completed rates. The fixture's content is unchanged
between requests; only the diagnostic root's stage policy differs. This is a
Ruffle regression probe, not a native or physical high-refresh display test.

| Requested stage rate | Scene updates | UI updates | ResolutionDone count | Result |
| --- | --- | --- | --- | --- |
| 25 | 128 | 128 | 1 | MATCH_END |
| 60 | 128 | 128 | 1 | MATCH_END |
| 144 | 128 | 128 | 1 | MATCH_END |
| 240 | 128 | 128 | 1 | MATCH_END |

These similar update counts reflect this renderer-limited run, not identical
presented frame counts on faster hardware. A separate forced-rate check set the
frontend to 30 and requested 144 from AS3: the getter remained 30 and observed
frame events were about 29.9/s, confirming that this option locks the rate.


## What interpolation can and cannot improve

1. **Movement/camera/ball trajectories:** strongest first target. These already
   have time-based paths. Sample them per displayed frame, preserve segment
   boundaries and do not run authoritative logic again. For known replays,
   sample the current segment directly without adding an interpolation delay.
2. **Character body poses:** raising stage FPS alone repeats existing MovieClip
   poses. Transform interpolation is possible only where adjacent frames retain
   compatible display-object identities, hierarchy, masks and ordering. Prove
   that on one running animation before attempting all characters and powers.
3. **Two-frame crossfade:** can be prototyped, but blends two silhouettes and may
   ghost feet, equipment and ball edges. It is not a correct intermediate pose.
   Sampling both frames with `gotoAndStop` can execute frame scripts; isolated
   pose snapshots must not trigger gameplay/animation events twice.
4. **Offline optical flow or resampled atlases:** potentially useful for selected
   animations, but need visual review for occlusions, direction changes, alpha
   edges and recoloring. Generating every character/equipment/direction variant
   multiplies storage. This study does not implement or quality-test optical flow.
5. **True skeletal/mesh interpolation:** offers the most control, but requires
   compatible underlying rig data or conversion work. The runtime has MovieClip
   animation libraries; the presence of a file named `bones` is not evidence of
   an exposed interpolatable mesh rig. This study does not claim that conversion
   is automatic.

## Proposed next step, not applied

First make a diagnostic high-refresh build available on a **real 120/144 Hz**
Windows/Linux/Android device, with vsync retained and a bounded target. Unify
root startup, scene entry/exit and options behavior in one FPS policy. Keep the
25 FPS effect/library rate, server tick configuration, callback scheduling and
authoritative outcomes unchanged. Measure displayed/presented cadence separately
from frame-event counters, along with CPU/GPU cost and frame-time tails.

For scale, the per-frame budgets are 40 ms at 25 FPS, 16.7 ms at 60,
8.3 ms at 120, 6.9 ms at 144 and 4.2 ms at 240. These are arithmetic budgets,
not measured costs. Generating intermediate samples does not remove drawing,
texture upload, UI composition or vsync costs.

If movement is smooth but character poses remain visibly stepped, test one
presentation-only running-pose interpolator. It must not advance labels, fire
frame scripts, change collision tests, alter ball ownership, smear a fall/teleport,
or delay the next ordered action. Check loops, pause/speed changes, failure
clouds, pass/reception and touchdown animations in both native and web clients.
Only then decide whether to extend it or convert selected assets offline.

Do not change `.025` to `.06` or `.144` to obtain more frames: that retimes authored
animation and completion events. Do not ship Ruffle's force-rate option silently:
it locks out movie-side changes and may multiply expensive scene/UI/render work.

## Validation boundaries

- Shared tooling verification passed in the study worktree.
- Actual AS3 synthetic interpolation/callback checks and the separate feasibility
  tests passed. Browser timing samples are observations, not a promised target.
- Both native diagnostic roots compiled through the existing native harness.
  Execution is **blocked** by the AIR developer license gate. No native animation
  ran, and no native >60 Hz result is claimed.
- Initial worktree attempts found missing generated fixture/model inputs. The
  reception record was copied read-only from main and fingerprinted, a fixture
  was generated locally, and the stadium model was copied into this worktree.
  The final harness prepares that ignored stadium input itself. Failed setup
  attempts are not counted as runtime passes.
- Missing pre-existing music assets can log 404s. They are not evidence of a
  successful animation path; replay completion markers are checked separately.

Reproduction commands and file ownership are in [README.md](README.md).
