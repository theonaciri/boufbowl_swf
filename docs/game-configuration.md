# Balance and general configuration

Edit `resources/game_config.json`, then run `python3 -m tools.game_config`.
Use `--stadium KARA` to print effective rules. The adjacent schema supplies editor
hints; Python validates it without dependencies. Invalid types, unknown keys,
probability intervals and periods longer than matches fail before builds.

| Section | Runtime behavior |
| --- | --- |
| general | Language, server address, sound, scene presentation, customization and startup mode |
| general.matchmaking | Rating window and widening, heartbeat timeout and total search timeout |
| general.tournament | Free local league ID, stadium, Unix-second time window and win/draw/loss points |
| rules.match | Turns, periods, ability budget, placement/planning deadlines, role limit and between-turn regeneration |
| rules.classes | Earth/air/fire/water, health, regeneration and class roles; enforced on saved and match rosters |
| rules.client_ranges | Original client's global distance previews and order controls |
| rules.simulation | Authoritative movement/range, throws, combat, recovery, probability and tick settings |
| rules.abilities | Configurable per-class heal/element effects on active teammates; live tooltips reflect these effects |
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

The replacement stat mapping is earth -> strength, fire -> agility, water ->
endurance, air -> precision. Ability effects and server probability mechanics use
the existing deterministic replacement engine. Provisional effects remain marked
`verified: false`. This identifies uncertainty about historical behavior, while
allowing balance changes. Current abilities heal active teammates and optionally
add an element bonus for the turn. Configured regeneration heals living players
between turns, capped at maximum HP; it does not revive wounded players. Period
and goal resets restore health for placement. Ability uses persist across bench
substitutions.

The service snapshots effective rules into each new match and stores them with
turn records. Editing configuration changes future matches. Restart the service
after edits; increase `rules_version` for intentional balance revisions. Recorded
replay verification uses its stored rules and seed. An engine algorithm upgrade
also needs version compatibility for previous recordings.

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
