# Running the first Flash backend integration

The opt-in mock harness injects actual protobuf game messages through the original
match handler. Offline menus and tutorial remain the default. This is a protocol
and rendering integration, not a multiplayer server or a database replacement.

## Run

The compiled SWF includes the harness. From this project:

```sh
./play.sh --mode mock --scene-3d
```

The fixture automatically loads two ten-player rosters with five active players
each, displays the planning phase, plays a movement turn, waits for the client's
resolution acknowledgement, applies the next authoritative field state and shows
a draw result. The fixture uses only the available male Iop animated skin.
Orders entered during this demonstration do not change the predetermined turn.
Use toolbar **Home** to cancel the fixture and return to offline menus.

The bottom status strip and `~/.local/state/boufbowl-tutorial/mock.log` show message
delivery and playback notices. Log records include generation, sequence and Flash
milliseconds; asynchronous HTTP logging can arrive out of order, so sort by sequence
when reconstructing a run. Platform-specific XDG paths follow the normal launcher.

`--scene-3d` overrides the served legacy configuration in memory for this launch;
it does not edit the configuration file. Without 3D, the original client skips
animation and still acknowledges resolution, so that path alone is not sufficient
as an animation test.

## Generate fixtures

For a purely authored movement fixture:

```sh
python3 tools/build_mock_fixture.py
```

For movement computed by the existing sibling simulator (requires Bun and the
adjacent `boufbowl_server` and `boufbowl` projects):

```sh
bun run tools/probe_engine.ts > /tmp/boufbowl-flash-engine-turn.json
python3 tools/build_mock_fixture.py --engine-turn /tmp/boufbowl-flash-engine-turn.json
```

The probe runs one isolated, seeded simulation. It does not launch the sibling
server, read account records, write its databases or modify its configuration.
It overlays this project's supported simulation settings on the sibling config
and validates them using that engine's validator. Its class stat semantics are
explicitly provisional and still belong to the replacement engine.

`resources/mock_match.json` contains raw protobuf hex and a decoded explanation
of each step. The shipped fixture is the engine-computed movement probe.
Generating a fixture changes data only; changing the harness requires a SWF rebuild.

## Verification

```sh
python3 -m unittest discover -s tests -v
xvfb-run -a -s '-screen 0 1280x800x24' python3 tools/smoke_mock.py
```

The smoke check requires Wine, Xvfb and ImageMagick's `import`. It checks a built
3D script, the real resolution acknowledgement, the next field state and match end;
it saves captures and a trace in ignored `evidence/` files. Do not run it concurrently
with another game using the same Wine prefix. Visual inspection remains necessary
to assess animations and original-player error overlays.

## Android

Both builds include the same AS3 helper. The standard APK starts in menus mode.
To build an APK that automatically starts the fixture, copy the configuration,
set `general.startup_mode` to `mock`, retain `general.android_scene_3d: true`, and
pass that file with `android/build.py --config /path/to/mock-settings.json`.
The fixture loads from `app:/resources/mock_match.json`. There is no localhost
trace endpoint on Android; the on-screen status strip remains available.
The Android build compiles and signs; this new fixture has not been run on a device.

## Current boundaries

- Movement conversion accepts integral axial cells and positive tick durations
  representable in 50 ms units. It verifies that the tracks reach authoritative
  final cells. Subcell engine motion is quantized into original grid trajectories.
- Combat, pickup, passes, goals, abilities and health/status/ball changes fail
  explicitly. Shared interactions need dedicated mappings and synchronization.
- Movement test scores are provisional display data, not recovered original test
  calculations. They must not be used as historical balancing evidence.
- Match setup, phase timing and the final draw are scripted. There is no live
  request validation, match queue, session authentication or persistence yet.
- The archive lacks some music, footsteps and interface sounds. These generate
  missing-file requests during a match, although the tested movement/draw path
  completes. Missing character skins and other stadium models remain unresolved.

Next implement ball interactions as linked `PASS` → `RECEPTION`/`REBOUND` scenarios,
then two-participant fights. Once those presentation contracts pass, connect live
commands and acknowledgement handling to transport-independent backend services.
