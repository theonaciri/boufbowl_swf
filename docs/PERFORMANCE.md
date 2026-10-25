# Client performance

## Render FPS setting

The in-game slider (25–240 FPS) controls the render target through 3D entry/exit;
native default is 60. Removed the scene's old 50/25 caps and browser slider's 60
cap. Authored animation clocks remain separate. Benchmarks below used the older
50 FPS scene target; they do not measure high-FPS capability.

Game rebuilt; both roots compiled and Windows/Linux/Android downloads packaged.
Actual high-FPS rendering remains unverified on hardware.

3D-entry crash: FFDec26.3 compiled `Boufbowler._uid = _nextUid++` into
constructor bytecode that reused/killed local0 (`this`) and local1 (sprite).
Native Flash debug traced Error1009 to that constructor; Android reported1010.
Allocate the ID after `super()` with separate read/add assignments. Avoid side
effects in field initializers when introducing decompiled overrides.
Fixed native Flash32 debug probe retained a 90FPS target, rendered the CPU turn
and sent `RESOLUTION_DONE`, reaching turn2. This verifies the constructor repair,
not sustained90FPS or Android hardware. Android error overlay now distinguishes
game runtime from synchronous startup failures.

## Running cadence

Ordinary travel uses `min(scheduledMs, floor(pathDistance * 40 / (30 * 0.7)))`
(positive paths: at least1ms). Runs slow by at most30%; remaining time becomes
an idle wait at the route's end, not at every hex. Full movement-node duration
is retained, so interaction joins keep their existing schedule. Combat/pass
choreography and the server simulation are unchanged. Footstep counts exclude
the new idle portion, at the existing sound timeline's tick granularity.
`presentationItems` groups adjacent moving wire entries into a continuous route;
stationary waits, gaps and interactions break the group. Consumers use copies:
the received protocol message is unchanged. Track information, movement nodes
and footsteps use the same grouping.
Grouped-route native Flash32 debug probe at target90FPS completed two CPU turns,
including five fights in turn2, and reached orders/turn3 with both real client
acknowledgements. Seeds3435174131 / 618410282; Android device check pending.

Field markers use `getTimer()` at25FPS, independently of stage FPS: possession's
24-frame loop lasts960ms; the red power indicator's 14-frame loop lasts560ms.
Possession loss stops its callback; stage detachment removes both listeners.
Native Flash32 debug at a 90FPS target completed a CPU turn and displayed the
possession marker. Cross-FPS timing comparison and Android confirmation pending.
The transient Android black ground could not be reproduced by the user; retain
original texture loading. Packaged grass PNG matches its source.

`Boufbowler` derives cadence from segment distance/duration:
`rate = min(1, distance * 40 / (duration * 30))`, using the retained
`Physics.DEFAULT_VELOCITY` (30 units/40ms). Velocity moves use the factory's rounded
duration; timed moves use their supplied duration. Faster moves retain rate1.

`FpsControler` accumulates fractional frame credit without skipping authored
markers or restarting phase. Reapply after sprite/direction changes. Scale normal,
Water and circle-free runs during movement; other animations use rate1. Global
replay speed/pause applies separately; clip cleanup removes rate entries.

Game/downloads rebuilt; desktop/Android roots compiled. Visual/gameplay validation
remains pending. Recordings below predate this change.

## Shared optimizations

| Path | Change / invariant | Evidence |
| --- | --- | --- |
| `MovieClipSpritePresenter` | One vertex `setValue`; preserve explicit redraw, axis mapping and NaN rejection | 3,000 updates: 25–26ms → 8ms |
| `FrameController` | Finished controllers return; completion once; allocate events only when observed | 1,000 post-end updates, one completion |
| `TextZone` | Compose only when dirty; resize/padding invalidate; retry failures | 500 unchanged updates, no notifications |
| `SceneController` | UI once before scripts/models | Before: 47 scene/94 UI; after: 143/143, resolution completed |
| `SceneModel` | Cache equivalent Int64 keys; invalidate on add/remove/reset; retain full IDs | 3,000 lookups: 27–28ms → 6–7ms |

Timings are Ruffle microbenchmarks, not whole-game/native FPS. Sources:
`tools/shared_client_{smoke,bench}.as.inc`. Combined browser replay reached
`ResolutionDoneMessage`/`MATCH_END` at 30FPS; both runtime branches passed in
Ruffle. Historical Python run: 314 passed, one skipped; browser presets: two
passed. AIR execution was license-blocked then; later native trials follow.

## Same-host runtime comparison — 2026-10-24

Four-core ARM64 Neoverse-N1 Ubuntu26.04 server, software graphics, approximately
640×375 game content, 50FPS target:

| Runtime | Recording OFF | Recording ON |
| --- | ---: | ---: |
| Native ARM64 Android AIR / Redroid15 | 43.68 FPS | 42.29 FPS |
| Windows i386 Flash32 / Hangover11.16 FEX | 11.82 FPS | 12.03 FPS |

Android: API35, ANGLE/SwiftShader, 640×376 at 60Hz, density160. Desktop:
Xvfb/llvmpipe, `HODLL=libwow64fex.dll`; default Box64 stalled. Each of five measured
passes completed two CPU turns (3+6 fights), with identical authoritative result
hashes, fixed roster/seeds, and real client acknowledgements. Android warm-up
excluded; production APK/SWF unchanged.

Android OFF/ON/OFF: 43.67/42.29/43.70FPS → observed recording slowdown **3.20%**.
Desktop showed no resolved slowdown; turn2 alone: 11.75/11.73FPS. Its slight
aggregate improvement may reflect cache/timing variation. Android was **3.69×**
desktop here; native ARM versus x86 emulation/software graphics does not predict
physical-phone or native-x86 GPU performance. These are frame-event rates,
not video/GPU presentation FPS.

Capture paths differ: Android `screenrecord`, H.264 2Mbps, 640×376; desktop
15FPS X11 + x264 ultrafast, 640×394 including menu. Videos decoded/visually checked,
YUV420P; earlier YUV444P played black. Small samples do not establish universal
overhead or encoder efficiency.

Earlier desktop trials: 1024×600 movement-only 11.90FPS; 640×375 combat turns
11.81/11.65FPS, worst frames548/431ms, processCPU128% (100%=one CPU), peakRSS660/681MiB.
Main thread95% plus llvmpipe workers indicates a CPU limit on this host. Different
turns/cache states prevent a controlled resolution comparison.

## Evidence and reproduction

[Runtime recipes](NATIVE_TESTING.md); [telemetry](GAME_MEASUREMENTS.md).
External caches retain scripts, build hashes, SQLite, raw samples and recordings:

- `~/.cache/boufbowl-android-testing/performance/`: `METHOD.md`, `REPORT.md`,
  `comparison-results.json`, `android-recorded.mp4`.
- `~/.cache/boufbowl-desktop-testing/`: `comparison/desktop-recorded.mp4`,
  `cpu-turn/`, `cpu-small/`.

Test runtimes/backend stopped; disposable Android OS data/images removed.
Logs/DBs contain local sessions; redact before publishing.
