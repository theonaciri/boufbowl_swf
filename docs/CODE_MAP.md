# Focused repository map

Use the behavior below to choose a starting path. This map records ownership and
boundaries; search for current symbols rather than relying on fixed line numbers.

| Behavior | Entry point and next dependency | Focused check |
| --- | --- | --- |
| Patch selection/build | `tools/client_patches.py` → `patches/rebuild.py` / `android/build.py` | `verify_client --area shared` |
| FPS/preferences | both `BoufbowlClient.as` roots → `ClientRuntime.as.inc` → `OptionsView.as`, `ResolutionMediator.as` | shared smoke, both roots |
| Browser launch/quality | `play.html` → `web-player.js` → root `setWebDisplay` | `verify_client --area web` |
| Chat layout/scroll | `ChatMediator.as` → `TextZone.as` → TLF controller | shared smoke; empty, long, resized chat |
| Popup geometry/layers | `MessageBoxView.as` → `MessageBox.as`, `ResizableTextBox.as`, `ServerSupport.as.inc` | browser probe, popup bounds |
| CPU roles and risk | `backend/engine.ts` → `cpu-orders.ts`, `cpu-powers.ts` → retained simulator | `verify_client --area cpu` |
| CPU roster/appearance | `backend/service.py` → `backend/cpu_team.py` | `test_backend.py` |
| Resolution ordering | `backend/turn_adapter.py` → `ScriptBuilder.as`, interaction builders → `ScriptRunner` | resolution-flow tests + 3D fixture |
| Scene updates | `ResolutionMediator.as` → `SceneController.as` → UI, scripts, model | shared smoke + ResolutionDone/MATCH_END |
| Sprite redraw | `BoufbowlerPresenter.positionUpdated` → `MovieClipSpritePresenter.as` → shared Away3D vertex | shared smoke; move/no-op/invalidate/swap |
| Animation timing | `FrameController.as` → frame/completion events → controlled movie clips | shared smoke; loop, completion, no-skip |
| Character lookup | `SceneModel.getBoufbowler` → identity map / equivalent-ID cache | shared smoke; full 64-bit IDs and removal |
| Downloads/publication | `tools/build_players.py` → platform packages → `tools/website/build.mjs` | `bun run check:site` + package inspection |

Commands above abbreviate `python3 -m tools.verify_client`. Shared AS3 overrides
are in `patches/`; preserved sources live in `bin/base/`. Full decompilations are
temporary evidence, not the first search target. AS3 classes without an override
can be exported selectively with FFDec when a caller requires inspection.

## Runtime boundaries

- Desktop and web use the desktop application root; Android substitutes its root
  and touch/layout/resource adapters through the shared patch registry.
- Both roots expand the same FPS policy fragment. Desktop permits the explicit
  `clientRuntime=ruffle` opt-in; Android disables it. Native scene defaults remain
  50/25 FPS, capped by a saved choice. Unset native menu FPS is 60.
- Ruffle popup skins, clipping and launcher presets remain browser-specific.
  Sprite updates, frame controllers, text batching and scene lookup are shared.
- The backend owns outcomes and randomness. Presentation optimizations must keep
  positions, interaction order, callbacks and ResolutionDone acknowledgement.
- One SceneController update owns one UI update before scripts/models. Explicit
  sprite invalidation and sprite replacement must still redraw without movement.
- Native AIR execution needs a compatible licensed runtime. Compiling the
  Android root on desktop AIR does not test an Android device or its GPU.

## Efficient verification

Start with the focused check. Full command output is retained under
`.local/verification/<area>/`; read the JSON status and failure excerpt first.
Use `--area all` for integration changes, and `--area compile` when AS3 changes.
See [native validation](NATIVE_TESTING.md) for the licensed runner.

`python3 -m tools.client_probe --serve --fixture <fixture.json>` creates a cached
browser diagnostic client. Open its printed URL; `sharedSmoke()` returns a small
runtime/benchmark report, and `probeStats()` reports the current FPS policy. Add
`?replay=1` to play the fixture, or `?runtime=flash` to exercise the native branch
inside Ruffle. Inspect the printed replay log for ResolutionDone and MATCH_END.
This is not native-runtime validation. Repeated unchanged probes reuse cached
compilation; output tampering and source changes invalidate that cache.

AS3 changes require a game rebuild; then rebuild downloads before publication.
Backend Python changes require a backend restart. CPU TypeScript changes need a
worker refresh and restart. Keep long build output in logs and use bounded waits
with meaningful progress updates instead of repeated source/log dumps.

See [performance findings](PERFORMANCE.md), [build details](BUILD.md),
[resolution contract](BINARY.md) and [server behavior](SERVER.md) when the focused
path reaches those boundaries. Update this map when ownership or commands change.
