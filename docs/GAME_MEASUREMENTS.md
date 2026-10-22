# Game measurements

The private `admin.html` dashboard combines authenticated client timing reports
with authoritative counters from newly resolved turns. Historical matches are
not backfilled. The report exposes its collection start time and coverage notes;
empty series remain gaps rather than zero performance.

## Collection path

- Both application roots expand `patches/ClientRuntime.as.inc`. Once the server
  enables the existing diagnostic channel, it attaches one `ENTER_FRAME` listener.
  It accumulates counters and a fixed ten-bucket interval histogram, without
  allocating per-frame objects. Samples flush after 30 measured seconds or a
  phase/activation change; windows shorter than one second are discarded.
- `ResolutionMediator` brackets playback as `3d`; other time is `ui` (menus and
  tactics). Browser visibility and native activation suspend sampling. Intervals
  over 60 seconds and nonpositive intervals are excluded. Changing target FPS
  flushes the window so budgets do not mix.
- `ServerTracking.as.inc` uses the existing bounded diagnostic queue, retry IDs
  and session authentication. `backend/tracking.py` validates payloads before
  writing receipts, deduplicates retries and retains the existing 60 events per
  minute limit per profile/device. No per-frame network requests are made.
- `backend/game_measurements.py` stores timing totals by UTC day, runtime,
  platform and phase. Memory is a peak of reported runtime allocations.
- `Service.run_resolution` records gameplay in the same transaction as the turn.
  The `(match_id, turn, team)` key prevents duplicate counting. It distinguishes
  CPU teams by their absent profile, without changing orders, randomness or
  presentation. Rows expire after 400 days alongside timing aggregates.

## Interpretation

Frame-event FPS is `sum(frames) * 1000 / sum(elapsed_ms)`, not GPU presentation
FPS. Slow frames take more than twice the selected target-frame budget. p95 is
a histogram upper bound. The chart combines platforms by weighted timing totals;
its p95 view explicitly shows the worst platform bound instead of averaging
percentiles. The detail table preserves platform-level measurements and counts.
`System.totalMemory` is runtime allocation, not OS process or GPU memory.

Startup measures SWF construction to the first server response enabling
diagnostics. It excludes page download and Ruffle initialization before SWF
construction and may include user interaction or connection delays.

Moves count simulation steps. Risk tests count nonzero-probability movement tests;
falls count movement `fall` events. A completed pass is a teammate catching a
throw's flight; an opponent catch is an interception. Rates divide summed event
counts, not averages of percentages. Zero attempts produce no rate. Counts
compare observed play, not equivalent opponents or a controlled balance test.
Daily match starts/endings can involve different matches and are not a cohort
completion rate. Endings include surrender.

## Verification and boundaries

Run `python3 -m tools.verify_client --area all` for backend and chart aggregation
tests and `--area compile` for both AS3 roots. Tests cover invalid payloads,
receipt deduplication, persistence, transaction rollback, CPU/human attribution,
pass/interception counters and weighted aggregation. Admin measurements retain
the existing administrator authorization.

`python3 -m tools.client_probe --serve` adds a disposable
`probeMeasurements(start|pause|resume|stop)` ExternalInterface callback, alongside
the existing shared smoke callbacks. It captures the sampler's real events for
browser inspection; it is absent from published SWFs. A browser probe exercises
Ruffle only. Native execution still requires the compatible licensed runner
described in [NATIVE_TESTING.md](NATIVE_TESTING.md); compilation is not a native
runtime pass. Visual dashboard checks use a separate seeded database, never
production analytics.
