# Two-column end zones

The original strategic grid injects width 35 and half-height 10 through
`StrategicViewContextPart`. `GridModel.spacePoint` renders horizontal position as
`q + r/2`; its outside edge is at +/-17.5. The end zones extend two hex widths
inward from that edge, starting beyond +/-15.5. The old +/-12.5 scoring boundary
was an inner pitch marking, three hex widths too early.

`rules.simulation.ball.goal_line_half_width` defaults to 15.5. It is the distance
from midfield to the inner boundary, despite its historical name. Standing on
the line does not score: both the precise carrier position and its rounded hex
must be strictly beyond the opponent's boundary. In the original visible grid,
each end has two eligible columns on both even and odd rows. A rounded hex on
the boundary must not receive a touchdown while continuous motion is only part
of the way to the next hex. This also keeps final-position settlement from
placing the scorer back on the line during the animation.

Team 0 attacks right before halftime; `sides_swapped` reverses that direction.
Only a live, active ball carrier scores. The CPU uses the same boundary and
rounded-position condition when predicting scoring and pass release. Goal
events enter `turn_adapter.adapt_turn`, whose participant track reaches the
goal hex before the touchdown interaction. No client-specific rule is involved.

Regression coverage checks both teams, both halves, row parity, exactly two
visible scoring columns, precise movement and arrival before the animation.
CPU scoring fixtures were moved three columns forward to preserve their original
distance to the corrected goal, without weakening risk or passing assertions.
Previously saved fixtures/replays retain their rules; the interaction fixture
generator uses the corrected 15-to-16 scoring run for new examples.

New matches snapshot the corrected configuration. Existing matches retain their
saved line setting. Saved replays remain authoritative rather than being
resimulated; new simulations advertise `+goal-zones-1`.

The archived simulator source is absent in this checkout. For a full rebuild use
`bun backend/build-worker.ts` when that archive is available. Otherwise run
`bun backend/refresh-goal-worker.ts`, followed by
`bun backend/refresh-cpu-worker.ts`: the former transpiles only the final goal
resolver from the maintained ball source into the retained bundle and adds its
version suffix, checking unique section boundaries before writing. Repeated
refreshes are idempotent. Other authoritative simulator functions are preserved.
Run the gameplay and CPU checks, then `verify_client --area all`. Restart the
backend and rebuild player packages to distribute the corrected configuration.
The shipped clients connect to the shared backend, which owns scoring; local
development servers must also use the updated retained worker. No AS3 or native
runtime execution is required for this server-side rule change.
