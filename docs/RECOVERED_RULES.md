# Recovered rules audit — October 2026

**Baseline audit for commit `62bc888`.** The subsequent rulebook implementation
is documented in [RULEBOOK.md](RULEBOOK.md) and [RULEBOOK_CHOICES.md](RULEBOOK_CHOICES.md).
The gaps below describe the v1 baseline; the current registry records which have
since received implemented or explicitly provisional behavior.

## Target and evidence

New matches use `forum-semantics-2012-1`. The target is the **post-1.0.7 roster /
post-1.0.8 match framework**, with the edited February 2012 designer explanations
as evidence for supported interactions. This is **not** a recovered 1.0.20 action
formula or a claim of exact historical balance. Existing experimental coefficients,
custom class effects and Saturday tournament rules remain explicitly separate.

The research input is preservation repository
[`theonaciri/boufbowl-website-legacy`, commit `484d203`](https://github.com/theonaciri/boufbowl-website-legacy/tree/484d203):
`docs/GAME_MECHANICS.md`, `docs/research/FORUM_EVIDENCE.md` and
`docs/research/mechanics-source-selection.json`, read in full. The post inventory
and read-only SQLite/HTML snapshots preserve authorship and text provenance.
The source codes below refer to that research, with original post IDs recorded
here so a running preservation website is unnecessary.

| Code | Original post | Relevant evidence |
| --- | --- | --- |
| M02 | 4463430 | Reserves recover at restarts; previous field players retain HP |
| M03 / M08 | 4463456 / 5183829 | Green can fail; Water affects movement reliability |
| M04 | 4463669 | Adjacent pickup, ally/enemy pressure and lost-combat penalties |
| M05 | 4469815 | Timed throw/catch, onward passes, contact interruption, Fire interception |
| M07 | 4817315 | One special/team/turn; caster ordinary turn replaced; Ecaflip redirects enemy healing |
| M09 | 5206184 | Targeted versus incidental consequences; missing score/CDF images |
| M10 / M11 | 5207552 / 5209678 | Player disagreement about critical-dodge knockdown |
| M18 | 5218238 | Initially stunned receiver recovers before arrival (observation) |
| P09 / P10 | 5186862 / 5186860 | 1.0.7, 14 November 2011: roles and three per roster role |
| P11 | 5190718 | 1.0.8, 28 November: Water to stand, reconnect two minutes, no five-goal cutoff |
| P16 / P17 | 5206386 / 5206384 | 1.0.20 rebalance and Water-based stun; active by 1 February 2012 |
| P18 | 5187356 | Sadida resurrection was a corrected bug |
| R06 / R09 | 5195726 / 5197710 | Historical timed loss-elimination events and matchmaking |

1.0.20's announcement was posted 26 January but describes 31 January; player
feedback establishes use by 1 February. The current profile does not substitute
June beta match endings or pre-role teams for that later framework.

## Implemented corrections

### Roster roles — P09/P10, C01–C02

The previous role defaults were a cycling class-ID placeholder. The configured
roles now use the protocol's `Role` enum: blocker=1 (Iop, Sacrier, Pandawa, Zobal),
dodger=2 (Sram, Osamodas, Feca), runner=3 (Ecaflip, Sadida, Eniripsa), thrower=4
(Cra, Enutrof, Xelor, Rogue). `roster_role_limit=3` checks **all ten players** at
active club import, club save and match creation. Three Iops are permitted; two Iops and two
Pandawas are not. The field cap is also three per role, with five players deployed.

Old stored clubs are not rewritten or deleted. A club violating the new default
must be edited before a new match; the server returns `ROSTER_ROLE_LIMIT`.
Already-running matches retain their frozen rules. Configurations omitting
`roster_role_limit` retain the previous composition policy.
Older clients submit all inactive gallery templates during first login; these are
retained for editing without applying the role cap at import. They cannot bypass
the cap when saved or entered in a match. A regression covers this compatibility
boundary so an invalid inactive gallery cannot block registration with a legal club.

### Restart health — M02, C05

`match.restart_recovery="reserves"` preserves the previous field lineup's HP
through `reset_round` and `finish_placement`. A returning living reserve receives
maximum HP. Per-player charges and Zobal masks remain persisted independently;
touchdowns do not refill charges. Rule snapshots without this setting keep the
old all-field healing behavior.

Death/revival is **not fully specified** by M02. The conservative current policy
retains zero HP even after a bench interval, using a `roster_health` ledger. A dead
center player cannot receive possession automatically. This policy is tested as
a recreation decision, **not verified as the complete historical revival rule**.
Resetting stun/down presentation does not restore HP or make death into recovery.

### Passing and interception — M05, C13–C15

- `ball.require_arrival_before_turn_end=true` computes arrival before any draw,
  order consumption or possession mutation. Arrival must be on an executable
  simulation tick (`landTick < max_ticks_per_turn`). A later viable window can
  still be considered. The exact real-time boundary is a discrete simulator
  convention, tested on both sides of the limit.
- `ball.contact_cancels_pending_throw=true` cancels an unlaunched carrier's pass
  when that carrier participates in combat/dodge contact. This also works for a
  stationary passer. `throw_cancelled(reason="contact")` records the decision.
  Already airborne passes continue; later acquisition by a player who was not
  carrying at the contact is not blanket-cancelled. Exact historical preparation
  duration is unknown; the existing delay and contact ordering remain provisional.
- `ball.interception_uses_fire_stat=true` uses `stats.agility` (Fire) for an
  opposing interceptor; intended reception still uses `stats.precision` (Air).
  Element eligibility, path samples and throw/catch tests remain separate. The CPU
  uses the same characteristic in its public-state lane estimate. The probability
  coefficients themselves remain experimental.
- A regression confirms that a passer starting without possession can receive and
  execute its already-submitted onward pass, including two flights in one turn.

The three optional ball settings preserve legacy behavior when absent/false.
They and the new Ecaflip rule add `+forum-semantics-2012-1` to the simulation trace
version. They never use rendered animation timing to decide an outcome.

### Ecaflip — M07, C18

`abilities.Ecaflip.redirect_enemy_heal=true` replaces the default random stat buff.
An opposing Eniripsa's configured positive heal targets the Ecaflip team, once,
regardless of actor-ID ordering. Living targets only, maximum-HP clamping, charge
use and caster lock still apply. An Ecaflip without an opposing heal has no effect
and consumes no random draw. Its charge is still spent on the special assignment.

The heal amount is the existing **provisional** Eniripsa configuration, not a newly
claimed historical number. Other class powers are still the previously requested
experimental effects. Other inversion combinations (including two Ecaflips and
mask/debuff interactions) are **not established** by the healing example and
are not generalized to sign inversion. Saved rules containing `enemy_chance`
retain the old random behavior; that compatibility is tested. Client descriptions
are generated from the matching rule snapshot. CPU selection conservatively skips
the counterspell rather than inspecting hidden opposing orders.

## C01–C22 audit and remaining boundaries

“Covered” means the stated server behavior was exercised; it does not certify
unknown coefficients, original timing units or the complete original implementation.

| Scenario | Current result / remaining boundary |
| --- | --- |
| C01 | Corrected; mixed-class role limit, duplicate-class legal control, saved-club bypass and legacy profile tested |
| C02 | Five-player deployment retained; ten entities total after restart covered; existing placement tests enforce five distinct owned players |
| C03 | Existing `FieldModel.activateClassOrder` cancels the earlier assignment; server deliberately rejects malformed batches containing two specials instead of guessing UI assignment chronology |
| C04 | Existing client clears ordinary orders; server and engine reject a combined ordinary/special action; existing class-power negative tests retained |
| C05 | Corrected and covered, with legacy full-heal control; full dead-reserve revival rule remains unknown |
| C06 | **Known gap:** current experimental overextension test ignores Water characteristic in its chance and makes the safe zone certain; do not claim historical accuracy |
| C07 | Covered: zero Water remains down; positive Water stands after configured delay; exact remaining movement/action budget is still provisional |
| C08 | **Pending:** current duel selection/damage/fall model is experimental, not recovered tier scoring; targeted/incidental consequence rows are not implemented faithfully |
| C09 | **Pending:** normal incidental success should allow zero HP damage plus stun; current combat cannot reproduce the documented complete state model |
| C10 | **Pending:** nearby teammates and opponents are not included in current pickup probability; exact pressure function missing |
| C11 | **Pending:** earlier combat loss is not yet a pickup difficulty input; penalty function missing |
| C12 | Existing separate throw/catch success and failures covered by ball-attempt tests; precise failed-catch scatter remains unknown (current fallback lands at target) |
| C13 | Covered: preassigned onward pass and chained possession/flight |
| C14 | Corrected; last-tick/beyond-limit and legacy controls covered |
| C15 | Corrected for carrier contact before launch; no flight/possession loss solely from cancellation; exact preparation duration remains provisional |
| C16 | Current interception samples the ball path/height and configured radius, not just passer adjacency; precise corridor and behind-passer eligibility are not verified |
| C17 | **Pending:** no recovered Water-to-stun-duration curve; current simulator does not establish the reported mid-turn recovery case |
| C18 | Corrected and covered for enemy heal/no heal, actor order, dead targets, HP cap, charge, descriptions and serialized scenario |
| C19 | Covered: score five alone does not end a match before its turn limit |
| C20 | **Intentionally different:** user-requested Saturday 14:00–18:00 Paris qualifying/bracket events remain; historical first-loss elimination is not substituted |
| C21 | Existing custom event settlement/round handling retained, not certified against historical timed-event late-match rules |
| C22 | Ongoing match/session restore exists and deadlines continue; **known gap:** no explicit 120-second disconnect abandonment state machine, especially both-offline handling |

The missing `formula1.png` intrinsic table and `formula2.png` random CDF prevent
reconstruction of combat scores/distribution. **83 − 35 = 48**; the designer's
prose arithmetic is not a calibration target. No stat-times-orders formula, curve,
CDF or threshold inclusivity at 0/15/30 was invented here. Targeted damage 1/3/5
and incidental/dodge damage 0/2/4 are documented, but an authoritative tier resolver
is still missing. Critical-dodge knockdown remains disputed (M09 versus M10/M11);
four damage must not become an automatic generic knockdown rule.

Likewise, a supported dependency on Water, pickup pressure or prior combat does
not supply a numerical curve. Those gaps are recorded rather than fitted to
anecdotes or tested with made-up “historical” constants. Stun, knockdown, shields,
temporary HP, death and possession still need a fuller combat/status model.

Stronger recovered client geometry remains authoritative: the two-column end
zones in [GOAL_ZONES.md](GOAL_ZONES.md) are not replaced by vague forum prose.
Existing match length/stadium charges, custom regeneration, class coefficients,
weekly event policy and rating rules are not certified by this audit.

## Rebuild and regression workflow

The archived simulator source tree is absent in this checkout. Maintained
`backend/simulator/ball.ts`, `abilities.ts` and the contact overlay are the source;
`backend/build/engine.js` is the retained runnable artifact. Full archive builds
consume the same overrides through `backend/build-worker.ts`. Without the archive:

```sh
bun backend/refresh-mechanics-worker.ts
bun backend/refresh-cpu-worker.ts
python3 -m tools.game_config
python3 -m unittest tests.test_recovered_rules tests.test_backend \
  tests.test_class_powers tests.test_ball_attempts tests.test_gameplay_fixes \
  tests.test_accounts_matchmaking tests.test_launcher tests.test_game_config
python3 -m tools.verify_client --area cpu
```

The refresh checks unique section boundaries and syntax before writing; repeated
refreshes must be byte-identical. New tests use fixed seeds, forced draws through
existing probability clamps, boundary controls and real protocol serialization.
No distributional accuracy claim is made without the missing distribution.

Validation on this checkout: **110 focused tests passed**; CPU strategy and
resolution checks passed; configuration validation and byte-identical repeated
refreshes passed. Full Python discovery ran **345 tests: 341 passed, one skipped,
three errors**. Those errors are in the pre-existing website-delivery fixture,
which does not create `ladder.html` required by the separate uncommitted website
changes. No website/event edits were reverted or included in this mechanics work.
Logs and compact results are under `.local/verification/recovered-rules/` and
`.local/verification/cpu/`. No native-client execution or full archive rebuild is
claimed by these server tests.

This task does not deploy or restart the production server. Applying the new
defaults requires a backend restart; client packages need a later configuration
rebuild to embed the new role defaults and descriptions. Existing online clients
receive server rules/descriptions, and already-running matches keep their snapshots.
