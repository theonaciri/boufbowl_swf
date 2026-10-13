# Balance and general configuration

Edit `resources/game_config.json`, then run `python3 -m tools.game_config`.
Use `--stadium KARA` to print effective rules. The adjacent schema supplies editor
hints; Python validates it without dependencies. Invalid types, unknown keys,
probability intervals and periods longer than matches fail before builds.

| Section | Runtime behavior |
| --- | --- |
| general | Language, server address, sound, scene presentation, customization and startup mode |
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
