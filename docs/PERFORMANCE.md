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
