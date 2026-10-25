# Rulebook reconstruction choices

## Scope and identity

The active profile is `restoration-2012-v4`. See [maneuver and recovery choices](MANEUVERS_AND_RECOVERY.md). See [original powers and randomness](ORIGINAL_POWERS_AND_RANDOMNESS.md) for the new client evidence and explicit approximation. [RULEBOOK.md](RULEBOOK.md) lists all
C01–C22 cases and the active policy. Its source is `resources/rulebook.json` plus
`rules.simulation.rulebook` in `resources/game_config.json`. Every case has an
evidence code, status and implementation decision. Original post IDs are included
in the registry, pinned to preservation research commit `484d203`.

The target remains post-1.0.7 roster and post-1.0.8 match behavior, with the edited
February 2012 consequence descriptions. This is a playable reconstruction with
explicit gaps, not a claim to have recreated the missing 1.0.20 formulas. The
previous audit in [RECOVERED_RULES.md](RECOVERED_RULES.md) describes the v1 baseline.

New matches save the complete evidence/decision registry, policy and SHA-256 in
`match.rulebook`; their actual simulation rules are frozen too. Each turn records
that rulebook's ID, evidence revision and hash; replay exports carry the full
frozen rulebook. Active exports still hide private orders/seeds. Replays retain
their own inputs and events. Changing defaults cannot change a running match's
choices. Worker versions add `+rulebook:restoration-2012-v4`. Omitting
`rules.simulation.rulebook` keeps v1/legacy movement, combat, pickup and disconnect
behavior; the prior optional v1 switches still operate independently.

## Movement — M03, M06, M08; C06

The recovered client reference and maximum ranges are retained. The movement
draw is sampled once at turn start, after special effects, and reused while the
player moves. Falling occurs during movement, not at the moment the test is
recorded. Water characteristic and Water orders both reduce failure risk even
when another element supplies most of the range. Green/reference movement has
a nonzero failure risk. A stationary action does not fall merely from this draw.

The **replacement** probability is:

```text
extension = existing fall_probability_at_max × extension_ratio ^ existing exponent
failure = min(1, (safe_failure + extension)
                 / (1 + Water_characteristic × water_stat + Water_orders × water_order))
```

Default replacement coefficients are `safe_failure=.01`, `water_stat=.05`, and
`water_order=.1`. These are tunable design choices, not historical odds or values
derived from the missing intrinsic table. The CPU uses this same risk function.
Existing colored range geometry and movement speed rules remain separate.

## Combat scoring versus consequences — M09–M12; C08–C09

The missing intrinsic-value image and combat CDF remain **unrecovered**. V3 uses an explicitly requested logistic approximation to the surviving probability anchors; it is not a recovered distribution. No stat-times-orders formula is claimed. In particular, 83 minus 35 is 48; the source's arithmetic error
is not a calibration target.

The v2 baseline below describes the retained model when `combat.random_score` is absent. V3 adds the seeded logistic margin distribution documented above, while retaining the intrinsic-score proxy.

For playable v2 outcomes, the existing recreation's score/attacker/dodge
selection is retained as an explicitly **unverified deterministic proxy**. Its
Earth score is characteristic plus the existing configured per-order bonus, not
the historical intrinsic value. The proxy supplies a margin for the new table.
Consequently these results do not reproduce the original tail probabilities.
Trace events state `score_model=legacy-proxy-unverified`, margin, branch, tier,
winner and loser. Replacing this scoring provider when original evidence becomes
available is independent of the consequence table.
The journal consumes the actual proxy score values (Earth versus Fire for dodge
comparison), including the next-combat bonus, instead of recomputing them from
bare stats. The original wire format displays integer-rounded scores; exact
proxy inputs remain in the authoritative event trace.

The documented table is implemented separately and tested for every row:

| Branch | Normal | Wide | Critical |
| --- | --- | --- | --- |
| Winner explicitly pursued loser | 1 HP, stun | 3 HP, down | 5 HP, down |
| Incidental hit or successful dodge | 0 HP, stun | 2 HP, stun | 4 HP, stun |

Targeting comes from the winner's explicit `follow` order, never visual animation
direction. A dodge winner is the defender; damage/status apply to the attacker.
The independent `critical_dodge_down` flag defaults to **false**, following the
official wording. Setting it true adopts the disputed player report **only for
critical dodges**; incidental four-damage hits remain stun results.

The default `boundary=lower` assigns exact 15 to normal and exact 30 to wide;
`upper` assigns them to wide and critical. Equality at zero follows the existing
actor-ID attacker selection. All three equality choices are **unverified** and
must not be cited as recovered thresholds. Positive-margin cases inside a tier
are independent of that choice.

Wide/critical next-combat bonuses have an isolated per-player slot, consumed on
the next combat and expired at turn end. The amount defaults to **one proxy-score
point**, an explicit replacement because the original magnitude is missing.
Setting `combat.next_bonus=0` disables the replacement bonus. No indefinite
accumulation or cross-turn bonus is assumed.
`official_effects=false` restores the prior experimental combat consequences.

## Stun, down, HP and protection — P11, P16, P18; C07/C17

Stun is temporary inability to act; down is a separate state requiring a Water
order to stand; zero HP is death. They are distinct in world state, event traces
and serialized scenario participants. Stun can end during a flight, permitting a
previously stunned receiver to catch after recovery. Remaining stun ticks survive
the turn boundary and are consumed in subsequent simulation time.

The **replacement** duration is `max(minimum_ticks, ceil(base_ticks - Water ×
water_reduction))`. Defaults: base 20 simulation ticks, reduction 1 tick per Water
point, minimum 1 tick. At the default tick interval this is at most two seconds
for nonnegative Water, but neither these units nor this curve are recovered facts.
Movement/ball actions check the current stun state; presentation timing never
decides when recovery occurs.

Abilities can configure `shield` and `temporary_hp` independently of permanent HP.
Combat damage consumes shield first, temporary HP second, permanent HP last.
Both protection pools expire at turn end without subtracting permanent HP. This
ordering and expiry are explicit reconstruction choices; the historical stacking
and corrected Sadida arithmetic remain unknown. Dead players are not eligible
ability targets at phase entry and temporary HP cannot resurrect them. Existing
same-phase simultaneous-heal handling is retained: a later heal can offset an
earlier lethal HP change within that phase. Its historical ordering is unverified.
Damage traces report
permanent HP loss and each absorbed amount separately.

The v2 class-power profile described below is retained only in frozen older matches. V3 restores the original client values and target reversal; mask numerical values and exceptional inversion cases remain explicitly provisional.

The former class-power profile was **not**
the historical spell table: several class names/effects differ from M07. Shield
and temporary-HP capability do not silently redefine Féca or the version-ambiguous
Sadida effect. Their configured spell values remain experimental. Ecaflip's
documented Eniripsa-heal interaction from v1 stays active; other inversions are
unresolved. HP costs and ordinary healing are not treated as shieldable attacks.

## Pickup pressure and combat history — M04; C10–C11

Living nearby players count from both teams, excluding the collector. Distance
uses current logical hex positions. Defaults: radius one hex, `.05` probability
penalty per nearby player, `.05` per earlier lost combat that turn. These radius,
magnitude and additive-combination choices are **replacement balance**. The
existing Air/Fire eligibility, action budgets and mixed-element handling are
retained as separate provisional policies. There is no hard three-player cutoff.

Penalties are subtracted from the existing pickup chance before the configured
probability clamp. The clamp can impose a floor, so adding pressure need not
change an already-floor-limited probability. Trace fields include nearby count
and lost-combat count. Loss bookkeeping is keyed by the cloned turn world,
never persisted in the next turn's entity state. A zero-HP-damage combat loss
still counts. Stun may delay pickup; it does not erase the penalty.

## Passing and scatter — M05; C12–C16

v1 already implements separate throw/catch tests, preassigned onward passes,
arrival deadlines and carrier-contact cancellation. This work adds the missing
wire mapping for cancelled throws, separate stun/recovery and protection traces.
The pass chain tests serialize actual scenarios.

The v2 passing policy adds these explicit reconstruction choices:

- Speed is configured base speed × `(1 + Air_orders × air_speed_bonus)`, with
  replacement coefficient `.1`. Receiver prediction and the CPU use that same
  speed. When guessing opposing passes, the CPU covers the fastest legal Air
  allocation without reading the submitted opposing orders.
- With `favorable_timing`, a pass waits while the actual thrower/receiver distance
  is decreasing, until it stops decreasing or the last viable arrival window is
  reached. Diverging/unchanged distances permit early release. This implements
  the documented qualitative distinction without claiming the original scheduler.
- `scatter_failures` chooses a seeded uniform point along the intended trajectory,
  rounded to a hex, after a failed throw or attempted reception. There is no
  invented four-hex scatter radius. This uniform scatter choice is **not** the
  missing combat CDF and is not claimed as the original scatter distribution.
- `path_interception` requires projection onto the finite forward flight segment,
  in addition to existing radius/height/Fire conditions. Behind-passer adjacency
  alone cannot intercept. The exact corridor width and retry priority remain
  the existing configurable provisional model.

Each policy can be disabled independently; old snapshots retain fixed-speed,
earliest-release/target-landing behavior. Throw-pressure/quality transfer, exact
favorable-time selection and the original scatter distribution remain unresolved.
Maximum range remains configured base plus Air bonus (ten hexes by default),
rather than treating the older guide's twenty-hex example as a universal
post-rebalance range. None of these replacement coefficients establishes the
missing historical success formula.

## Reconnection — P11; C22

A disconnected player has a two-minute grace window and the opponent's match
continues. Default detection is **30 seconds without an authenticated heartbeat**;
the 120-second grace begins at that inferred disconnect instant. Forfeit occurs
at equality (`now >= disconnected_at + grace`). The detection interval, exact
boundary and score settlement are reconstruction choices. CPU seats never
disconnect.

Maintenance checks every active match independently of its planning/resolution
deadline. Hello, poll and command requests check expiration **before** refreshing
presence, so a late request cannot erase an expired disconnect. Reconnection
clears the marker, preserves turn/score/orders, and notifies the opponent through
the existing protocol. Disconnection notifications are emitted only on a state
transition. A simulation completing after a forfeit cannot overwrite the ended
match; the existing phase/turn guard handles that race.

If only one seat expires, the existing surrender result policy awards the other
side a winning score. If both expire, the explicit `finish-current-score` policy
ends the match with its current score and existing result/reward policy. Neither
both-offline behavior nor the awarded score is claimed as historical. Server
downtime counts toward this clock; reconnect timers are not a pause mechanism.
Legacy match snapshots lacking the policy do not acquire new forfeits.

## Retained custom policies and missing evidence

The user-requested Saturday 14:00–18:00 Europe/Paris qualifying/bracket events,
their entry/settlement policy, regeneration, stadium configuration and class
balance are retained. C20–C21 therefore explicitly say **custom**. Recovered
two-column goal geometry remains stronger evidence than generic forum prose.
The old inactive gallery compatibility exception remains: templates are retained
for editing but invalid teams cannot enter a new match.

The rulebook system covers all 22 scenarios; it does not certify all historical
behavior. Missing original combat formulas, threshold equality, complete revival,
precise passing/scatter, class-effect values/inversions and several stadium details
remain visible in the registry. New evidence must update status, decision, policy
identity and regression tests together.

## Commands and validation

```sh
python3 -m tools.rulebook                         # human-readable active rules
python3 -m tools.rulebook --json                  # policy + evidence + hash
python3 -m tools.rulebook --stadium KARA          # resolved stadium policy
python3 -m tools.rulebook --write docs/RULEBOOK.md
python3 -m tools.game_config
bun backend/refresh-mechanics-worker.ts
bun backend/refresh-cpu-worker.ts
bun test tests/rulebook.test.ts
python3 -m unittest tests.test_rulebook tests.test_recovered_rules
python3 -m tools.verify_client --area cpu
```

The retained worker and full archive build consume the same maintained combat,
ball, ability, movement and rulebook modules. Refresh checks section boundaries
and syntax before writing and must be byte-identical on repeated runs. The
archived upstream source tree is absent here, so a full archive build cannot be
claimed as validation. No native AIR execution is claimed by server/protocol tests.
Production deployment and restart are separate from this implementation.

Historical v2 validation (not rerun for v3): **135 focused server tests**, **13 Bun rulebook
tests**, **13 CPU strategy tests** and **two resolution checks** passed.
Configuration validation and byte-identical repeated runtime refresh/document
generation passed. Full Python discovery ran **364 tests: 360 passed, one skipped,
three errors**. The three errors remain in the pre-existing website-delivery
fixture, which does not create the separately added `ladder.html`. That website
work is preserved outside this mechanics commit. Reports and full logs are in
`.local/verification/rulebook/` and `.local/verification/cpu/`.
