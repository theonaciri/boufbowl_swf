# Original-match comparison and movement falls

## Evidence and scope

Reference: `../extra/8e de finale Tournoi de Nowel Boufbowl.mp4` (1280×720,
15 fps, 18m47s), plus its 19 supplied screenshots. The match is Kara, Les Atlantes
versus Les Ferrari Brumairiennes. It has 14 turns, halftime after turn 7, and a
0–2 finish. The first goal is visible between turns 5 and 6; the second is at the
end. Selected sidebar screenshots expose individual health and regeneration.

The replacement comparison uses authored orders and documented deterministic
probe seeds. It follows the same duration, stadium, goal timing and final score,
and exercises a risky run/fall, class power, fight and successful passes. The
recording does not expose both teams' complete orders or the historical server
seeds. This is a similar match, not an exact simulation reconstruction; no
numerical historical catch/fall odds are inferred from a handful of outcomes.
Some player names and starting positions in the fixture are invented.

## Confirmed differences and fixes

| Evidence | Previous behavior | Current behavior |
| --- | --- | --- |
| Original `Rules.as` and `FieldView.as` distinguish safe and risky radial distances | Replacement worker used a different movement budget and never tested movement falls | Client-aligned reference/max distance, increasing risk outside safe range, one deterministic draw per runner |
| `MovementTest`, interaction `FALL=10`, `FallDetails` and `MovementFailFunction` | Movement result always succeeded | Actual movement test plus original fall animation, KO and carried-ball drop |
| All four languages in `resources/lang.json`: +1 HP every N turns | Healed N HP every turn | Heals one HP at interval boundaries; immutable resolved state stays unchanged |
| Sidebar screenshots | All classes had 16 HP / interval 3 | Rogue 10/3, Sacrier 16/4, Sram 11/3, Sadida 13/2 |
| Original `PeriodStatus`, `PeriodFunction`, screenshot halftime and late warning | No period-information envelope | Two-turn warnings on turns 5/12 and halftime on turn 7 for Kara; original illustrations render |

The source root for original ActionScript is
`../migration-work/scripts/scripts/`. Relevant paths under it:

- `com/ankamagames/boufbowl/client/match/strategic/model/Rules.as` computes the
  reference distance from assigned elements and multiplies by the maximum factor.
- `com/ankamagames/boufbowl/client/match/strategic/view/field/FieldView.as`
  colors cells according to `(distance-reference)/(maximum-reference)`.
- `com/ankamagames/boufbowl/client/match/resolution/builder/InteractionComputer.as`
  converts server fall interactions into `MovementFailFunction`.
- `com/ankamagames/boufbowl/client/match/resolution/interactions/MovementFailFunction.as`
  plays impact/KO and optional ball dispersion.
- The recovered protocol has `MovementTest`, `FallDetails`, `InteractionType`,
  `PeriodStatus` and `PeriodInformations`. There is no player-issued fall command:
  it is a server decision returned in the resolution scenario.

## Falling probability

The historical server formula was not found. The recovered client only colors
risk and plays results. The separate combat-fall calculation in the replacement
simulator does not implement orange-cell running risk.

The configurable replacement formula is:

```
ratio = clamp((completed radial distance - safe distance) /
              (maximum distance - safe distance), 0, 1)
probability = fall_probability_at_max * ratio ** exponent
```

Defaults: maximum factor 1.33, probability at maximum 0.6, exponent 1. Safe
movement has zero overextension risk. One draw is reused over the turn so running
farther raises cumulative risk rather than repeatedly rolling an entire new
probability. Movement stops at a legal completed cell when the runner falls.
Range powers affect both safe and maximum distances. Water used to stand up does
not retroactively shrink the submitted movement allocation.

Configuration lives in `resources/game_config.json`,
`simulation.movement.overextension`, with stadium overrides supported. Turning
`enabled` off removes falls but retains client-aligned ranges. Worker code is in
`backend/movement-risk.ts`; overlays leave original and sibling sources intact.
The protocol test display uses percentile difficulty/roll values; these are
replacement values, not recovered historical dice rules.

## Reproduce and verify

From the repository root:

```sh
bun backend/build-worker.ts
python3 -m tools.build_reference_match --output /tmp/boufbowl-reference/comparison.json
xvfb-run -a -s '-screen 0 1280x800x24' python3 -m tools.smoke_mock \
  --fixture /tmp/boufbowl-reference/comparison.json --timeout 600 \
  --capture-turns --require-cinematic
python3 -m unittest discover -s tests -v
```

The builder verifies all 14 recorded engine turns and asserts a real 0–2 result;
it does not inject a fabricated score. Native original-client playback completed
all turns, resolution acknowledgements, next-field transitions and MATCH_END.
The trace includes touchdown, Kara crowd, halftime and the end-of-match warning
illustrations. Turn 5 carries the pre-halftime information, but its touchdown
uses the original client's goal sequence, which suppresses that warning.
Local ignored evidence: `evidence/reference-match-trace.log`,
`evidence/reference-match-result.png`, `evidence/reference-turn-01.png` through
`reference-turn-14.png`. The per-turn captures show the 3D resolution setup phase;
they are not pixel comparisons with strategic-planning screenshots.

## Remaining uncertainty

- Complete historical orders, exact random odds, tie-breaking and all individual
  player builds are unavailable from the supplied footage. Class elemental
  profiles and powers remain configurable experimental balance.
- Non-Farmstead stadiums still reuse the available Farmstead 3D surroundings;
  the Kara pitch texture and Kara crowd illustration do not restore its missing
  original 3D model. Character models use the requested Cra fallback.
- The original arrow preview visually trims beyond-maximum drag distances toward
  the reference range. Server validation rejects out-of-range movement instead;
  this input-preview distinction has not been recreated.

## Development data reset

At the user's request, the old development database and saved replay export were
deleted. Schema 8 contains no legacy-stat archive or additive historical migration.
An incompatible database is cleared, including accounts, matches, turns and
statistics. New schema-8 data persists normally across restarts. Original game
sources/assets, reference video/screenshots and reusable test fixtures remain.
