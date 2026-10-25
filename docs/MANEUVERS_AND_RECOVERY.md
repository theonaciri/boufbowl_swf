# Maneuvers and reserves

Profile `restoration-2012-v4` adds playable policies for remaining gaps. They are
**reconstruction choices**, not recovered original formulas. Frozen v1–v3
matches retain their old outcomes and RNG consumption.

## Graded ball actions

Use the existing probability `p` and one seeded uniform draw `u`. Success remains
`u < p`. Grade the absolute margin `s × (logit(p) − logit(u))`, using the configured
logistic scale from v3. Wide requires >15 and critical >30 by default. Equalities
stay in the lower tier. Numerical logit endpoints are bounded by machine epsilon;
the success comparison retains the actual probability. These thresholds are
chosen defaults; evidence does **not** establish that maneuvers share combat tiers.

Original client `PickUpFunction`, `PassFunction`, `ReceptionFunction` and
`InterceptionFunction` provide the consequence/presentation branches:

- Critical throw failure: stun, with the configured Water-dependent duration.
- Critical pickup/reception/interception failure: down; no invented HP damage.
- Failed interception leaves the flight active. Critical reception ends it in a
  ground rebound; the adapter inserts only presentation time for the fumble arc.
- Disabling `critical_failures` caps failed-action grades at wide, avoiding a
  critical animation with no authoritative down/stun.

Fire pickup uses Fire characteristic; Air pickup uses Air. Tests log probability,
draw, signed margin, grade and consumed bonuses. Pickup pressure remains separate.
Legacy unlimited-pickup mode retains its original guaranteed pickup behavior.

## Carried bonuses

M03/M08 describe strong movement helping a later action; M05 describes reception
quality helping the following throw. Exact weights/lifetimes are not recovered.

A successful completed nonzero route is graded using its existing movement draw
(no extra RNG). Wide/critical gives `movement_bonus` (default1) to the next combat
or ball attempt. A successful intended reception gives `reception_throw_bonus`
(default1) times 1/2/3 for normal/wide/critical to the next throw. Slots replace,
not stack; reception bonus survives other action types. Both expire at turn end.
Combat adds the movement bonus to its score; ball actions add it in log-odds score
units (`logit(p) + bonus/s`), then apply the configured probability bounds.

## Revival policy

M02 documents reserve recovery, not the complete death rules. V4 explicitly allows
a dead reserve to return at maximum HP after spending the preceding field phase
on the bench. A just-dead field player retains zero HP at the immediate restart;
benching and a later restart are necessary. Charges and masks persist. No ability
revives the dead. Set `recovery.revive_rested_reserves=false` to retain v3 policy.
This choice remains provisional, rather than interpreting a fixed Sadida revival
bug as an intended power.

## Remaining historical uncertainties

The missing intrinsic table/CDF image, exact mask statistics, counterspell/mask
and two-counterspell combinations, original maneuver grade probabilities,
bonus magnitudes and complete revival rules remain unresolved. Existing explicit
policies cover gameplay; none is promoted to historical fact by implementing it.

```sh
python3 -m tools.game_config
bun backend/refresh-mechanics-worker.ts
python3 -m tools.rulebook --write docs/RULEBOOK.md
bun run build:website:quick
```

## Build and native check (2026-10-24)

`bun run build`, both roots (`verify_client --area compile`), all platform
packages (`build:players --no-website`) and the quick website build succeeded.
Website package hashes match their platform outputs. No automated suite was run.

Native Flash32/Hangover/FEX, 1024×600, target90FPS: three rendered turns, eleven
combat contacts, one pickup, seven movement-bonus awards and a goal. Real client
`RESOLUTION_DONE` for all three; continued to orders/turn4. Seeds: 3207361521,
3932387101, 1005157681. Private evidence and result hashes:
`~/.cache/boufbowl-desktop-testing/maneuvers/summary.json` and its SQLite turn
records; H.264/YUV420P recording inspected after decoding. This run did not
exercise passing, rare critical failures, reserve revival or Android hardware.
