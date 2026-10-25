# Code map

Start at the relevant entry point; read dependencies only as needed.

| Behavior | Entry point and next dependency | Focused check |
| --- | --- | --- |
| Patch selection/build | `tools/client_patches.py` → `patches/rebuild.py` / `android/build.py` | `verify_client --area shared` |
| Game cache / explicit release | `package.json` → `build_project.py` / `build_players.py` → `game_build_state.py` | `bun run build --plan`; [fast loop](BUILD.md#fast-development-loop) |
| FPS/preferences | both `BoufbowlClient.as` roots → `ClientRuntime.as.inc` → `OptionsView.as`, `ResolutionMediator.as` | shared smoke, both roots |
| Android background audio | Android `BoufbowlClient` → NativeApplication activate/deactivate → SoundMixer master transform | Home/return/lock; preserve category volumes, repeated deactivation |
| Browser launch/quality | `play.html` → `web-player.js` → root `setWebDisplay` | `verify_client --area web` |
| Game measurements/admin charts | `ClientRuntime.as.inc` / `Service.run_resolution` → `backend/game_measurements.py` → `admin-game.js` | `verify_client --area all`; [coverage](GAME_MEASUREMENTS.md) |
| Chat layout/scroll | `ChatMediator.as` → `TextZone.as` → TLF controller; Ruffle stacks rendered paragraph bounds | empty, wrapped/bold, long, resized chat; [layout](PERFORMANCE.md#web-chat-layout) |
| Browser controls | `ScrollIndicator.as` → fixed-cap thumb; `RunningButtonSprite.as` → frame-aware `FlashInstanceContainer` skin | short/full thumb; normal, hover, selected tournament tabs |
| Popup geometry/layers | `MessageBoxView.as` → `MessageBox.as`, `ResizableTextBox.as`, `ServerSupport.as.inc` | browser probe, popup bounds |
| CPU roles and risk | `backend/engine.ts` → `cpu-orders.ts`, `cpu-powers.ts` → retained simulator | `verify_client --area cpu` |
| Original powers/randomness | `resources/game_config.json` → `abilities.ts` / `combat.ts` → `rulebookCombatNoise` | [evidence and choices](ORIGINAL_POWERS_AND_RANDOMNESS.md) |
| Maneuver grades and reserves | `rulebook.ts` → `ball.ts` / `movement-risk.ts` → `turn_adapter.py`; restart HP in `Service` | [choices](MANEUVERS_AND_RECOVERY.md) |
| Recovered server rules | `resources/rulebook.json` → `backend/rulebook.py` / `Service` → maintained `backend/simulator` resolvers → retained worker | `test_rulebook.py`, `rulebook.test.ts`, `test_recovered_rules.py`, CPU checks; [rulebook](RULEBOOK.md), [choices](RULEBOOK_CHOICES.md) |
| CPU roster/appearance | `backend/service.py` → `backend/cpu_team.py` | `test_backend.py` |
| Goal zones and scoring | `resources/game_config.json` → `backend/simulator/ball.ts` → `turn_adapter.py`; CPU uses the same line | `test_gameplay_fixes.py`, `verify_client --area cpu`; [geometry](GOAL_ZONES.md) |
| Resolution ordering | `backend/turn_adapter.py` → `ScriptBuilder.as`, interaction builders → `ScriptRunner` | resolution-flow tests + 3D fixture |
| Original 3D effects | `turn_adapter.py` → interaction family, movement, modifiers, stun timing → `HitAndRunFunction.as` / original interaction scripts | [effects and unresolved grading](RESOLUTION_EFFECTS.md) |
| Scene updates | `ResolutionMediator.as` → `SceneController.as` → UI, scripts, model | shared smoke + ResolutionDone/MATCH_END |
| Sprite redraw | `BoufbowlerPresenter.positionUpdated` → `MovieClipSpritePresenter.as` → shared Away3D vertex | shared smoke; move/no-op/invalidate/swap |
| Retained scene children | `View3D.render` → `SpriteSession.placeChild/render` | shared session smoke: depth order, culling, pooled shapes, lifecycle |
| Animation timing | `FrameController.as` → frame/completion events → controlled movie clips | shared smoke; loop, completion, no-skip |
| Running cadence | `Boufbowler.moveTo/Duration` → segment distance/duration → `FpsControler.setPlaybackRate` | shared Android/desktop compilation; visual gait verification |
| Travel/idle pacing | `BoufbowlerMovementFunction.travelDuration/buildNodes` → ordinary route → remaining-slot wait; `MovingBoufbowlersByTickBuilder` → footsteps | minimum70% normal travel speed; interaction join time preserved |
| Field markers | `BoufbowlerFieldRepresentationView.hasBall` / `ClassOrderIndicatorUI` → elapsed-time 25FPS timelines | possession: 960ms; power: 560ms; detach removes callbacks |
| French game rules page | `regles.html` → `tools/website/rules.mjs` + `rules-data.json` → `game_config.json` / `rulebook.json` | website build; [website](WEBSITE.md) |
| Character lookup | `SceneModel.getBoufbowler` → identity map / equivalent-ID cache | shared smoke; full 64-bit IDs and removal |
| Client updates/version | `resources/release.json` → `tools/release_version.py`; `tools/updates/updater.go`, `ClientUpdates.as.inc`, `client-updates.js` → signed `updates.json` | [updates](UPDATES.md); signature/cache/package tests |
| Downloads/publication | `tools/build_players.py` → platform packages → `tools/website/build.mjs` | `bun run check:site` + package inspection |
| Public competitions | `index.html` → `home-tournaments.js` → `Tournaments.public_tournaments`; `ladder.html` → `home-ladder.js` → `Progression.public_ladder` | public tournament/ladder tests + `bun run check:site`; [website](WEBSITE.md) |


`verify_client` abbreviates `python3 -m tools.verify_client`. Shared overrides:
`patches/`; Android substitutions: `android/patches/`; preserved SWF: `bin/base/`.
Selective decompilation/build rules: [AGENTS.md](../AGENTS.md).

## Runtime boundaries

- Desktop/web share a root; Android substitutes touch/layout/resource adapters.
  `ClientRuntime.as.inc` owns FPS policy: scene transitions use the slider's
  25–240 FPS target, native default60; browser launch presets supply their default.
  `clientRuntime=ruffle` opt-in is desktop-only.
- Ruffle skins/presets stay browser-specific. Backend owns outcomes/randomness;
  presentation must preserve ordering, callbacks and `RESOLUTION_DONE`.
- UI updates once before scripts/models; explicit sprite invalidation/replacement
  must redraw even without movement.
- Prefer actual Android APK testing on this ARM host. Desktop FEX is emulated;
  AIR smoke requires licensing. [Runtime recipes](NATIVE_TESTING.md).

## Verification

```sh
bun run build
python3 -m tools.verify_client --area compile
python3 -m tools.client_probe --serve --fixture <fixture.json>
```

Rebuild before root compilation; it uses the existing SWF. Other focused areas:
`shared|cpu|web|all|native`; JSON/logs: `.local/verification/<area>/`.
Browser probe: `sharedSmoke()`, `probeStats()`, `?replay=1`; `?runtime=flash`
exercises the native branch **inside Ruffle**, not native Flash. Probes cache by
source/tool/base fingerprints under `.local/client-probes/`.

AS3: rebuild game/downloads before publishing. Python: restart backend;
CPU TypeScript: refresh worker and restart. Keep build logs bounded.
[Build](BUILD.md) · [Server](SERVER.md) · [Resolution](BINARY.md) ·
[Performance](PERFORMANCE.md) · [Measurements](GAME_MEASUREMENTS.md)
