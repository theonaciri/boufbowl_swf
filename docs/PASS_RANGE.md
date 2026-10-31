# Pass range

New matches use `(7 + Air orders) × 1.3` cells: 10.4, 11.7 or 13,
plus any temporary range bonus. This is a requested balance change, not a
recovered historical rule. Frozen matches without these settings retain their
old range and wait-until-in-range behavior.

With `ball.attempt_out_of_range`, an eligible thrower attempts the pass even if
the projected receiver is too far away. The trajectory stops within maximum
range, on a hex cell; accurate underthrows are ordinary misses. Actual critical
fumbles keep their existing consequences. Contact cancellation, possession,
Air requirements and the arrival deadline still apply. One attempt consumes the
order. CPU passes retain their planned release tick and consider both shorter
and extended passing windows.

Selecting/dragging the pass icon draws an opaque black perimeter around reachable
grid cells. Dropping, deselecting, switching drag mode or ending the phase clears
it. Both client roots get the range coefficients from `game_config.json` during
startup generation. The French rules page shows the configured formula.

```sh
bun backend/refresh-mechanics-worker.ts
bun backend/refresh-cpu-worker.ts
bun run build
python3 -m tools.verify_client --area compile
python3 -m unittest tests.test_game_config tests.test_cpu_strategy tests.test_recovered_rules.RecoveredBallRulesTests
```
