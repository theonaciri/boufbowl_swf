# Balance and general configuration

Edit `resources/game_config.json`, then run `python3 -m tools.game_config`.
Use `--stadium KARA` to print effective rules. The adjacent schema supplies editor
hints; Python validates it without dependencies. Invalid types, unknown keys,
probability intervals and periods longer than matches fail before builds.

| Section | Runtime behavior |
| --- | --- |
| general | Language, server address, sound, scene presentation, customization and startup mode |
| general.matchmaking | Rating window and widening, heartbeat timeout and total search timeout |
| general.tournament | Free scheduled qualification/knockout or points league; stadium rotation, UTC windows, rounds, points and awards |
| rules.match | Turns, periods, ability budget, placement/planning deadlines, role limit and between-turn regeneration |
| rules.classes | Earth/air/fire/water, health, regeneration and class roles; enforced on saved and match rosters |
| rules.client_ranges | Original client's global distance previews and order controls |
| rules.simulation | Authoritative movement/range, throws, combat, recovery, probability and tick settings |
| rules.abilities | Experimental class powers: target side, HP, characteristic, range, attack and mask effects; localized live tooltips reflect frozen rules |
| stadiums | Enabled stadiums and recursive overrides for match limits, simulation and abilities |

Global settings inherit into each stadium; unspecified fields retain their global
values. KARA defaults to 14 turns, 7 per period and two ability uses. Its 14/two
values come from the sibling configuration's recorded video reference; seven per
period is the chosen profile. Other stadiums default to 24/12/1. These are editable
custom rules, rather than a verified reconstruction of all historical balance.

Five active players per side, ten-player rosters, and three regular order elements
are protocol invariants. The original client has global setters for planning,
placement and role limits; stadium match overrides expose its supported turn,
period and ability-budget fields. Client distance previews and authoritative
engine ranges have separate settings and different formulas; adjust both when
changing range balance. Client previews do not determine simulation authority.

Reception and scoring settings live under `rules.simulation.ball`:

- `reception_requires_air` defaults to `true`: at least one AIR enables an airborne
  catch/interception attempt. FEU alone enables ground pickup, not reception.
  The older `actions.element_effects.feu.used_for_reception` field is retained for
  configuration compatibility and no longer controls reception.
- `goal_line_half_width` defaults to `12.5`, measured in client horizontal cell
  units (`x = q + r/2`). A living, unstunned carrier scores at or beyond the
  opponent's line. Crossing without the ball or crossing your own line cannot
  score. This is independent of reserve columns and odd-row offsets.
- Catch probability still uses `simulation.catch_base`, `catch_stat`, `catch_air`
  and `catch_feu`, clamped by the configured probability bounds. A successful
  throw and AIR allocation enable a chance to catch; they do not guarantee it.
  The ball must also pass within the configured radius and catchable height.

The placement silhouette is defined as readable row spans in
`backend/placement.py`, reconstructed from the supplied reference. It reflects
horizontally with the team's current terrain side, including even periods.
`placement.ball_exclusion_radius_cells` requires cells to be at least that many
hexes from the center; settings that erase a zone fail validation. An empty
placement submission uses the five default zone positions.

The replacement stat mapping is earth → strength, fire → agility, water →
endurance, air → precision. Every class now has a distinct experimental base
profile with 42 element points. The footage establishes HP/regen intervals for
Rogue (10/3), Sacrier (16/4), Sram (11/3) and Sadida (13/2); other defaults
remain provisional. Regeneration means one HP every N turns.
Edit `rules.classes.overrides.<CLASS>` to change these profiles.

| Class | TERRE | AIR | FEU | EAU |
|---|---:|---:|---:|---:|
| Cra | 8 | 16 | 8 | 10 |
| Ecaflip | 11 | 11 | 11 | 9 |
| Eniripsa | 7 | 12 | 10 | 13 |
| Enutrof | 11 | 9 | 8 | 14 |
| Féca | 14 | 8 | 12 | 8 |
| Iop | 17 | 8 | 9 | 8 |
| Osamodas | 10 | 10 | 10 | 12 |
| Pandawa | 14 | 10 | 8 | 10 |
| Roublard | 10 | 12 | 14 | 6 |
| Sacrieur | 16 | 6 | 12 | 8 |
| Sadida | 10 | 8 | 9 | 15 |
| Sram | 9 | 10 | 17 | 6 |
| Xelor | 7 | 15 | 12 | 8 |
| Zobal | 12 | 10 | 11 | 9 |

Class powers are experimental proposals (`verified: false`), not claims about
historical server behavior. `rules.abilities` uses internal names `Rogue` for
Roublard, `Sacrier` for Sacrieur and `Feca` for Féca. Each power has a `target`
(`allies` or `enemies`); signed `hp`, `range`, `attack`, and `elements` modifiers
are optional. Element modifiers change characteristics, not the three assigned
action slots. Range changes movement budget and pass range. Attack changes the
combat attack score. These bonuses expire before the next turn is persisted.
HP changes remain, are clamped to 0/max HP, and can eliminate a carrier and drop
the ball. Powers target living players on the field, including the caster when
allies are affected; they do not revive eliminated or benched players.

| Class | Default power |
|---|---|
| Sadida | −1 range to enemies |
| Enutrof | +3 EAU to allies |
| Iop | +3 TERRE to allies |
| Osamodas | +1 each element to allies |
| Cra | +1 range to allies |
| Sacrieur | −1 HP and +2 each element to allies |
| Roublard | −2 HP to enemies |
| Eniripsa | +2 HP to allies |
| Xelor | +3 AIR to allies |
| Ecaflip | 50% +2 each element to allies; 50% +1 each element to enemies |
| Zobal | Select a different mask (1 Classic, 2 Psychopath, 3 Cowardly) |
| Sram | +3 FEU to allies |
| Féca | −1 attack to enemies |
| Pandawa | +1 attack to allies |

Ecaflip draws once from the turn's deterministic RNG; its recorded draw, target
side and effects reproduce exactly during replay verification. `enemy_chance`
and `enemy_elements` configure its alternative outcome. Zobal uses the original
mask picker and records the selected mask in orders, events, state and replay.
No extra mask bonuses have been invented; with missing skins the Cra fallback
also applies to mask appearances.

The client allows one caster per team; choosing another replaces the previous
power. Movement/pass/element editing is blocked while a power is selected.
The service and worker reject multiple powers, combined caster actions,
unavailable casters and exhausted usage counts. Power casters stay still,
cannot throw, catch, pick up or score that turn, but can be attacked and defend.
Both teams' eligible casters are collected before any effects are applied, so
a power-phase wound cannot cancel the opposing activation. Effects resolve in
stable caster ID order. The existing stadium `match.class_ability_uses` controls
each player's match allowance, including stadium overrides (KARA: two).
Uses and masks persist through goal/period resets and bench substitutions.

Configured regeneration heals living players by one HP after every N completed
turns, where N is the class regeneration interval, capped at maximum HP. Period and goal resets restore health for placement. Descriptions are
generated in French, English, German and Spanish from the effective rules;
client tooltips and character editors receive the frozen match's values.
Newly recorded matches retain their frozen rules for verification.

The service snapshots effective rules into each new match and stores them with
turn records. Editing configuration changes future matches. Restart the service
after edits; increase `rules_version` for intentional balance revisions. Recorded
replay verification uses its stored rules and seed. An engine algorithm upgrade
requires resetting incompatible development recordings.

Rebuild client defaults and menus, then package:

```sh
python3 patches/rebuild.py --ffdec /path/ffdec.jar --original /path/original.swf
python3 linux/build.py
python3 android/build.py --air-sdk /path/AIRSDK --ffdec /path/ffdec.jar \
  --jdk /path/jdk-17 --android-sdk "$HOME/Android/Sdk"
```

Desktop and Android builds accept `--config /path/settings.json`. Linux packaging
uses `resources/game_config.json`; use the same settings for the server and its
clients. Desktop compilation refuses to replace its output if configuration
changed during the build. Readable patches and reference archives are retained.

`startup_mode` supports server, menus and mock. Tutorial entry is selected through
the launcher with `--mode tutorial`. Server is the default: Linux
hosts the backend; Android connects to a reachable Linux service. Linux
`--scene-3d` enables original playback; live server mode enables it automatically.
Android uses `android_scene_3d`. General resource generation updates the original
client settings and local league descriptions. The original tutorial uses its own
scripted exercises and is not an authoritative match balance test.

Unavailable stadium models fall back to Farmstead without changing stadium rules.
Missing character animations use Cra while preserving class and identity. Assets,
music and cutscene mappings remain in `resources/stadiums.json`. See
[backend operation](backend-operation.md) for service setup and replays.

Rebuild simulation source overlays with `bun backend/build-worker.ts` (or Linux
packaging's `--rebuild-worker`). The build substitutes `backend/simulator/ball.ts`
for the sibling ball module without modifying archived or sibling files. Normal
checkouts continue to use the distributed `backend/build/engine.js`.

The corrected simulation is marked `+client-ball-2`. Older saved scenarios can
still be exported and played, but re-simulation verification of recordings made
under earlier reception/scoring algorithms can fail. Existing matches use the
corrected default algorithm; explicit balance values remain snapshotted.

## Cinematic presentation

`general.cinematics` controls the original full-screen presentation:

```json
"cinematics": {
  "introductions": true,
  "interactions": true,
  "introduction_timeout_seconds": 90
}
```

Both switches are enabled by default. Introductions show the available stadium
camera tour and original versus sequence. The camera tour uses Farmstead for the
current Farmstead geometry substitutes; pitch textures and match rules retain
the selected stadium. Placement starts after the participating clients acknowledge
introduction completion; CPU and spectator slots do not delay it. After the
configured timeout, the server starts placement with a full placement clock.
Reconnects preserve acknowledgements and skip an already-completed introduction.

Interaction cinematics enable goal/celebration, ball-carrier combat, pass,
reception/interception and rebound sequences. Each action type gets at most one
full-screen sequence per turn, shared by both teams; off-ball fights do not
consume the fight slot. Later actions still animate on the field, using the supplied illustration
and movie libraries. They require 3D playback; desktop server mode enables it.
Unavailable movie/cutscene symbols are skipped without blocking completion.
The missing `cutscenes-animated.swf` library is not needed by these illustration
paths. Simulation results, scoring and balance are unchanged.

These presentation settings are saved with new matches/turn records. Restart the
backend after editing. Stored replay records remain unchanged. Playback filters even old saved flags
through the same ball-only, once-per-type policy. Turning introductions off starts
placement immediately; turning interactions off uses normal field animations.

To generate a cinematic test replay without changing the existing fixtures:

```sh
python3 -m tools.build_interaction_fixtures --cinematics --output /tmp/boufbowl-cinematic-fixtures
xvfb-run -a -s '-screen 0 1280x800x24' python3 tools/smoke_mock.py \
  --fixture /tmp/boufbowl-cinematic-fixtures/goal.json --require-cinematic
```


Normal and expert CPU games now choose at most one experimental power from the
public field state. Selection considers healing, damage, buffs, lost caster
movement and sacrifice risks. Carriers, planned pass receivers and immediate
ball retrievers keep their actions. Sacrieur is avoided when its HP cost would
eliminate an active ally. Zobal changes masks occasionally while idle, since
current masks have no stat bonuses. Beginner does not use powers. The choice
uses no opponent orders or simulation seed, and the generated order is recorded
so replay verification does not make a new CPU decision.

## Movement overextension

`client_ranges` contains the original per-element reference distance and maximum
factor. With `simulation.movement.overextension` configured, order validation uses
the same reference distance × maximum factor as the client. Safe-range movement
never triggers this risk. Beyond it, completed radial distance determines the
increasing probability; each runner uses one private deterministic roll per turn.

`simulation.movement.overextension.enabled` toggles falls without changing ranges.
`fall_probability_at_max` (default 0.6) sets the probability at maximum range;
`exponent` (default 1) controls the curve. These are replacement balance choices:
the recovered client identifies orange risk cells but contains no historical odds.
Falling stops movement, knocks the runner down and drops a carried ball. Stadiums
can override these simulation settings. See [comparison findings](reference-match-comparison.md).

## Stadium goal celebrations

`resources/stadium_celebrations.json` defines the original goal-celebration
animation and reaction sound for every stadium. Build preparation applies these
independently of 3D model/texture fallbacks and validates that each animation is
present in the supplied illustration library. Brakmar and Bonta share the
original crowd animation; the other stadiums use their own themed illustration.
Sable/Beach uses `Illustration_crabes_contents`, not the human crowd.

| Stadium | Goal celebration |
| --- | --- |
| Farmstead | Bouftous |
| Brakmar | Human crowd |
| Bonta | Human crowd (same original animation as Brakmar) |
| Sable / Beach | Crabs |
| Frigost | Yetis |
| Kara | Canyon crowd |
| Forest | Forest crowd |
| Ballotin | Ballotin crowd |
| Pixel | Pixel crowd |

Goals and conceded goals both read the selected stadium's celebration through
the original client. Full-screen interaction cinematics must be enabled. Missing
original reaction sounds do not prevent the animation from playing.

Validate all stadiums in the native client:

```sh
xvfb-run -a -s '-screen 0 1280x800x24' python3 -m tools.smoke_stadium_celebrations
```

Use `--stadiums BEACH` for a focused Sable check. Screenshots and traces are
saved under the ignored `evidence/stadium-celebrations/` directory.


## Frontend progression, economy and moderation

`general.progression` sets qualifying ranked games and five league rating
thresholds. Its `seasons` block enables optional timed resets/archives; disabled
by default. `general.economy.free_customization` defaults true; false enforces
server-owned unlocks and trusted catalog prices from
`resources/cosmetic_catalog.json`. `general.news` supplies four localized
announcements. Tournament format/qualification/round parameters select the
points-only or knockout schedule. See [frontend restoration](frontend-restoration.md)
for complete behavior and the local CLI used to provision moderator/admin roles.


Power descriptions contain only their effects in all four languages. The former
constraint paragraph is removed from tooltips/log descriptions; authoritative
one-caster, exclusive-order and stadium-use rules still apply. Class-order targets
have an optional repeated `effectDeltas` field for animated values. These numbers
are separate from actual HP deltas, so a +3 element bonus cannot heal a player.
Zero changes do not produce +0 popups; mixed effects such as Sacrier -1/+2 are
shown in successive number animations. Regeneration remains +1 HP after each
class's configured number of completed turns, capped at maximum, with no revival.
