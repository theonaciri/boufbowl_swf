# Shared client performance work

The five optimization cycles target code shared by Ruffle, desktop Flash, and
Android AIR. Preserve action timing, coordinate mapping, explicit redraws and
completion callbacks. Renderer-specific popup skins remain scoped to Ruffle.

## Cycle 1: batch sprite vertex writes

Moving sprites formerly wrote three temporary extreme coordinates, then the
three actual coordinates. Each Sprite3D setter also read the vertex, potentially
recomputing its position repeatedly. Use the existing shared vertex's setValue
method to update all axes and invalidate geometry once. Explicit redraws use the
same method without allocating a temporary Point3. Reject NaN before mutation.

The focused benchmark in tools/shared_client_bench.as.inc compares 3,000 changing
positions using identical, preallocated points. Under this host's Ruffle runtime,
three samples were 25–26 ms for the former setter sequence and 8 ms for the
batched presenter path. These are microbenchmark results, not measured gameplay
FPS gains or native runtime results.

The shared smoke checks cover unchanged/moving positions, axis mapping, explicit
redraws, replacement sprites, rejected NaN coordinates, and chat scroll state.
Run `python3 -m tools.smoke_shared_client` on a host with a compatible, licensed
AIR runtime. Native AIR application execution on this development host is
license gated; browser probes exercise both runtime branches in Ruffle.

## Cycle 2: retire completed frame controllers

A finished FrameController now returns immediately and reports completion once.
Unobserved frame/completion events no longer allocate Event objects. The smoke
test sends 1,000 updates past the end and requires exactly one completion, while
also checking scheduled starts, timed loops and incremental non-skipping frames.

## Cycle 3: compose text only when dirty

TextZone tracks pending content/layout work, registers its frame listener once
per batch and makes unchanged updateNow calls cheap. Size/padding changes still
invalidate layout; a failed composition can be retried explicitly. The smoke
test requires no extra change notifications for 500 unchanged refreshes, and
requires composition after resizing or changing padding. Identical dimensions
no longer update the TLF controller or recreate a browser clipping rectangle.

## Cycle 4: advance the scene UI once

SceneController updated the UI explicitly and again through its updatable list.
Remove the duplicate registration, retaining the explicit update before scripts
and models and the same behavior after reset. Instrumented playback measured
47 scene updates and 94 UI updates before this change; the corrected path must
produce one UI update per scene update and still finish the resolution. The
corrected replay completed with 143 scene updates and 143 UI updates, emitted
ResolutionDoneMessage, and reached MATCH_END at the selected 30 FPS stage cap.

## Cycle 5: cache equivalent character ids

Keep the existing identity lookup and roster iteration order, but remember the
original map key after matching a decoded Int64 by value. Repeated equivalent-id
lookups then avoid allocating an iterator and scanning the roster. Add/remove
operations invalidate the relevant cache entry; reset clears it. Cache keys keep
both integer words separated, avoiding ambiguous Int64.toString values and
Number precision loss. Cached keys are checked for equality before use.

The smoke test covers fresh equivalent objects, high/low word collisions,
negative/high-bit ids, removal and re-adding. With ten characters and 3,000
preallocated decoded ids, three Ruffle samples took 27–28 ms on the former scan
path and 6–7 ms with the cache. This remains a microbenchmark, not a claim of
native or whole-game speedup. The benchmark sources are included in the native
smoke harness for reproduction on supported hosts.

## Combined validation

The final combined browser replay reached ResolutionDoneMessage and MATCH_END
with a 30 FPS stage limit and 141 scene/UI updates each. The shared smoke checks
passed with both the native and Ruffle runtime branches selected in Ruffle.
The Python suite passed 314 tests with one skipped; both browser-preset tests
passed. Native application execution remains unverified on this host because
its ARM64 AIR runtime requires a commercial developer license.

## Optional high-refresh settings

The [frame-rate study](../studies/framerate/REPORT.md) separates authored 25 Hz
poses, scene update frequency and browser presentation. Explicit native FPS
preferences now take precedence over both 50 FPS resolution entry and 25 FPS
scene exit defaults. With no saved preference those defaults remain unchanged;
legacy `limitFrameRate25` still resolves to 25. Both roots use the shared policy.

The browser loader, live display callback and in-game slider now accept the same
25–240 range. Existing web presets remain 25/30/60, so high-refresh use is opt-in.
This permits additional samples of existing elapsed-time movement trajectories;
it does not synthesize limb poses or change authored frame constants. Raising
the request on a 60 Hz or overloaded display can add work without visible benefit.
Applied regression evidence and runtime boundaries are recorded in
[APPLIED.md](../studies/framerate/APPLIED.md).

## Diagnosing a low FPS report after packaging

The Linux developer launcher reads `bin/boufbowl-client-1.9.6.swf` and runs it
in the standalone Windows Flash player through Wine. `--show-fps` enables a
frame-event counter; it does not raise the frame-rate setting. The overlay now
includes the requested stage rate: `FPS: measured / target`. This separates a
scene policy reverting to 50/25 from a renderer failing to reach a higher target.

Before this follow-up, `build:players` prepared an existing SWF without checking
whether ActionScript had changed. The packager now uses the game receipt's SWF
hash and logic fingerprint to rebuild stale/missing/unrecognized game code,
while retaining incremental reuse when inputs match. Direct `play.sh` launches
still do not compile; `bun run build` explicitly rebuilds the local game.

After rebuilding, select and release the FPS slider at 120 or higher, then check
the overlay in both UI and resolution. A retained target of 120 with an actual
rate of 12–50 needs runtime profiling; unlocking a setting does not remove the
cost of scene updates, sprite generation and drawing. Browser/native-branch
probes and compilation do not establish performance of the user's Wine runtime.

## Retain the 3D display list

Away3D SpriteSession formerly removed all display children on each update, then
reattached them during drawing. The shared override retains existing children,
reconciles painter order and removes stale children after rendering. Shape pools,
clipping, filters, alpha and the unchanged-frame cache policy remain in place.
Shared smoke covers ordering, duplicate draws, shape interleaving, visibility
changes and cached frames. Ten-runner and pass/catch replays preserve ordered
completion and scene/UI update counts at the requested targets.

The isolated benchmark reduced session-loop time from a median 327 ms to 82 ms
for 300 draws of ten synthetic trees. One real replay reduced instrumented AS3
View3D.render time from 1,017 ms to 720 ms over 70 calls, but whole-probe frame
events changed only 5.33/s to 5.53/s on the software browser host. These are not
Wine/GPU measurements or a promise to fix 12 FPS on a player's machine. See the
[focused renderer study](../studies/framerate/RENDERING.md) for evidence, source
trace, limitations and reproduction. `play.sh --fps-probe 240` now isolates a
blank counter through the user's standalone Flash/Wine path without game/backend
startup, allowing its steady 60 FPS ceiling to be investigated separately.

## 2D possession animation speed

`BoufbowlerFieldRepresentationMediator.boufbowlerUpdated` passes the model to
`BoufbowlerFieldRepresentationView.updateBoufbowler`, which sets `hasBall`.
Previously every true assignment called `gotoAndPlay(1)`. The embedded field
sprite therefore advanced at the stage rate and restarted on unrelated character
updates. Its 24-frame timeline took 960 ms at the authored 25 FPS, but only
400 ms at 60 FPS and 100 ms at 240 FPS. The front/back ball children each have
one frame; the parent timeline supplies the animation.

The shared view override stops automatic playback and selects the authored frame
from elapsed milliseconds. Its loop remains 960 ms at every requested display
rate. Repeated possession assignments preserve phase; possession loss hides both
halves and removes the frame listener. Removal from the stage pauses the clock,
and reattachment resumes it. Offstage assignments wait for attachment to start.
Both desktop/web and Android select this same override. Match state and
resolution clocks remain owned by their existing paths.

Run `python3 -m tools.smoke_possession_client --serve --port 9919`, open the
printed `/probe.html?replay=1` URL, and call
`document.querySelector('ruffle-player').ruffle().callExternalInterface('probePossession')`.
This tests the real tactical view and embedded asset with a temporary controlled
clock, checking two loops at 25/30/50/60/90/120/144/240 Hz, the 39/40 ms frame
boundary, repeated assignments, possession loss and stage removal/reattachment.
The test hooks exist only in disposable diagnostic SWFs under `.local/client-probes`.
`probePossessionLive(rate)` resets the real-time marker and requests that stage
rate asynchronously; subsequent calls with zero return elapsed time and the
current frame. After the field loads, run
`await import('/tools/possession_client_timing.js').then(m => m.checkPossessionTiming())`
in the browser console for live-clock checks at 25/60/120/240 FPS. All 12 recorded
samples selected the correct frame for their last update time. The software
browser host left samples 291–308 ms behind that update, so these are
clock correctness checks, not achieved display-rate measurements. The live
probe schedules stage changes outside ExternalInterface; changing it directly
inside the callback caused a recursive Ruffle core-lock error during diagnosis.
Browser execution is Ruffle validation, not native Wine/Flash or Android device
validation. Timing results are recorded in
[`studies/framerate/possession-results.json`](../studies/framerate/possession-results.json).
