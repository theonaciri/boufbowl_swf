# Isolated frame-rate study

Read [REPORT.md](REPORT.md) for findings, evidence, alternatives and limitations.
This folder contains diagnostic tooling and saved measurements. Nothing here is
imported by the application or website build. Baseline observations were committed
as `a4b1762`; the later authorized game policy changes are in [APPLIED.md](APPLIED.md).

## Inputs and isolation

Base commit: `6855365`; baseline study snapshot: `a4b1762`. Use that snapshot
to reproduce the original caps; current source includes the authorized fix. The study used a read-only copy of main's already built
`bin/boufbowl-client-1.9.6.swf`; its SHA-256 is recorded in `provenance.json`.
If that generated file is absent in a fresh study worktree, copy the exact input
from an existing build or build it **inside this worktree** with
`python3 patches/rebuild.py`. Do not rebuild or deploy main to run this study.
The saved reception record is a read-only copy from the main checkout, identified
by its SHA-256. The server generates its client fixture and ignored stadium models
locally. Java 17/FFDec use the repository's normal build-tool cache.

`study.py` expands the root in memory, adds the separate `probe.as.inc`, and
instruments scene/UI/position counters in temporary class copies. The single
study-only FPS override bypasses scene entry caps. Maintained AS3 files are never
written. All generated SWFs and class replacements stay under
`.local/client-probes`; failures/logs/generated inputs live in
`.local/framerate-study`. It serves localhost on port **9913**, not the live ports.

## Run tests and timing experiments

```sh
python3 -m tools.verify_client --area shared
bun test studies/framerate/interpolation.test.js
python3 studies/framerate/study.py --serve
```

Keep the diagnostic tab foreground and use the same viewport/device pixel ratio
for comparisons. Open `http://127.0.0.1:9913/study.html?bare=1` and run:

```js
await studyReady;
await runMatrix(); // 8 rates × 3 repeats, 3 s/window, alternating order
```

Open `/study.html` without `bare` and repeat for the normal game UI. The matrices
are saved as `results-bare.json` and `results-game-ui.json`; each save contains
actual intervals, not just a rounded FPS number. `studySynthetic` uses the actual
AS3 controller/trajectory classes with controlled timestamps independently of
runtime scheduling. Avoid `probeShared` during a matrix: the existing shared smoke
callback intentionally resets the stage to 30 FPS.

For a full reception replay at each of 25, 60, 144 and 240, first remove only that
rate's old `.local/framerate-study/replay-RATE.jsonl` (or use a fresh worktree), then
open `/study.html?replay=1&fps=RATE` and run, replacing RATE with a number:

```js
await studyReady;
await sample(RATE, 0, 0, true);
await save();
```

This polls until the mock reaches MATCH_END, with a 90-second timeout. Saved files
are `results-replay-RATE.json`. The trace records the originating page URL and
checks 3D playback → exactly one ResolutionDone → MATCH_END, plus equal scene/UI
update counts. This fixture never connects to a real account or server.

To check Ruffle's force-rate behavior, open
`/study.html?bare=1&forced=30&fps=144` and call `sample(144)` then `save()`: the stage
should still report 30 because the frontend has locked it. Results are saved as
`results-forced.json`.

Validate saved observations:

```sh
python3 studies/framerate/validate_results.py
```

Fresh replay traces are local diagnostic logs; the durable result JSON files
also retain their ordered mock events. Use them to inspect past evidence when
local logs are no longer present. Rerunning a matrix overwrites that matrix's
saved result file, so retain copies when comparing machines.

The optional existing native check is:

```sh
python3 -m tools.build_mock_fixture
python3 -m tools.verify_client --area native
```

Provide the documented native dependencies/`LD_LIBRARY_PATH` and a licensed
runtime. This host compiled both diagnostic roots but was blocked by AIR's
commercial developer-license requirement; it did not run native game code.
`native-validation.json` preserves the status, independently of browser passes.

## Files

- `REPORT.md`: source trace, measured results, recommendation and safety boundary.
- `study.py`, `probe.as.inc`, `study.html`: reproducible diagnostic build/server,
  real AS3 tests and browser collector.
- `interpolation.test.js`: separate render-only feasibility tests.
- `results-*.json`: raw browser observations, controller results and replay events.
- `provenance.json`, `sources.json`, `asset-rates.json`: input/runtime identities.
- `summary.json`, `report.html`: compact data and interactive study report.
- `validate_results.py`, `build_report.py`: checks and regeneration of the report.

Do not merge the diagnostic FPS bypass into game roots. To test the applied
policy without this bypass, rebuild locally then run:

```sh
python3 patches/rebuild.py
python3 studies/framerate/study.py --production-policy --serve --port 9914
```

Use `?applied=1&replay=1&fps=RATE` on port 9914. Results and traces are saved
separately under `studies/framerate/applied/` and `.local/framerate-study/applied/`.
Use a fresh trace for each replay. `runtime=flash` exercises the native policy
branch inside Ruffle; it is not a native-runtime test. These probes count the
actual stage rates seen by SceneController, not just the requested rate. Native
hardware and high-refresh display validation remain necessary before publication.

The running-player follow-up and blank Wine runtime probe are documented in
[RENDERING.md](RENDERING.md); its artifacts are under `rendering/`.
