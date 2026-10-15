# Browser playback options

The shipped launcher currently runs the Flash standalone player through Wine.
The repository now includes `browser.html` and a self-hosted Ruffle distribution
in `vendor/ruffle/`. The backend serves the browser page, Ruffle, game assets and
API from the same origin; `/` also opens the browser page. Start it independently
from the repository directory (Python 3 and Bun are required):

```sh
python3 -m backend.server --host 127.0.0.1 --port 9900
```

Open `http://127.0.0.1:9900/browser.html`. Keep the server terminal running;
Ctrl+C stops it. For access from other machines, use `--host 0.0.0.0` and open
the server's LAN address instead of `127.0.0.1`.
The embedded player fits both viewport dimensions, preserving the game's aspect
ratio and centering it without page scrolling.
The browser passes `scene3d: "1"` explicitly so a cached/menu-mode config cannot
silently acknowledge a turn without animation. Hidden tabs pause playback rather
than consume it in the background; the browser scene clock also caps long frame
gaps after loading or resuming. Native Flash keeps its original timing.

The page obtains the current SWF URL from `/api/client`, with a SHA-256 revision
in its query string. A reload therefore loads the current compiled client instead
of an older cached SWF. Restart the Python server after backend source updates;
the page reports this requirement if the running server lacks the manifest route.

Browser checks on October 14, 2026 with the installed nightly verified the home
screen, chat/frame proportions, resource loading, and a short CPU match with two
resolved turns, client acknowledgements and match completion. The camera fix
shows animated players and power effects in the 3D view. A subsequent texture
patch maps Away3D's UV coordinates with subdivided bitmap fills, correcting the
warped stadium/field textures caused by Ruffle ignoring triangle UV data.
Several unavailable sound files still return 404. This
does not establish parity with native Flash or validate the broader acceptance
checks below. The rebuilt SWF includes these compatibility fixes:

- `patches/ConstructorInjectionPoint.as` restores known named constructor
  dependencies when Ruffle omits class-level `Inject` metadata from reflection.
  This fixes the missing `IMap`/`viewDescriptors` dependency at startup. Existing
  metadata takes priority; empty argument names preserve parameter positions.
- `patches/Uri.as` uses numbered regex captures in place of unsupported PCRE
  extensions, allowing the Tiphon sprite index and libraries to load.
- `patches/SwlAdapter.as` waits for SWF library completion and supplies explicit
  child application domains, avoiding missing exported skin symbols when loaders
  are reused.
- `patches/FlashInstanceContainer.as` renders bounded static decorative sprites
  in nine slices in the browser, preserving their corners and borders. Ruffle
  stores `scale9Grid` but does not render it. Native Flash/AIR retains the original
  vectors; text and interactive contents are excluded from rasterization. The
  slider track explicitly opts into snapshots of its decorative timeline states.
- `patches/BoufbowlCamera.as` constructs the browser camera's basis directly.
  Ruffle's `Matrix3D.pointAt()` is a stub, leaving the original camera pointed
  away from the field. The native player still uses its original `lookAt()` path.
  Its cross-product order matches native Flash; the earlier fallback reversed
  the right/up axes. Four native matrix reference cases agree within `8e-8`.
- `patches/SliderTrack.as` repairs the browser track artwork for each timeline
  state. `patches/Slider.as` converts browser track clicks to slider-local
  coordinates. Both preserve the native paths.
- Server popups use a browser-only vector frame and explicit text formatting,
  matching the native rectangular frame and embedded button/heading fonts.
- `patches/Tooltip.as` applies the same browser corner-scaling repair when hover
  text changes size. Tooltip extends `Sprite`, so the component repair pass alone
  did not cover its background.
- `patches/AbstractSession.as` replaces UVT triangles in the browser with adaptive
  affine bitmap triangles; native Flash retains its original perspective path.
- `patches/ChatContextPart.as` maps the chat model before the view/mediator can be
  created. `patches/ChatMediator.as` restores channel state when a view is created
  and refreshes the selected channel when messages arrive.
- `patches/ChannelButton.as` reapplies the channel color to the current timeline
  star when a button changes state. Live `ColorableZone` indicators are excluded
  from the browser artwork rasterization. General chat is gray by design; match
  chat uses its separate color.

The final compiled client was checked in native Flash/Wine on an isolated X
display: the General FR selector populated, the star retained its channel color,
and keyboard-entered chat was saved and echoed. Browser chat was also saved and
echoed, and resolved turns visibly animated. These checks use temporary databases,
not a user's existing game profile or installed Linux package.

`play.sh` explicitly passes the backend address created for that launch, so an
old saved server address cannot leave the native client disconnected with empty
chat and the offline-preview match warning. Its SWF URL also includes the current
client hash. Restart the launcher after rebuilding. The server placement data
includes the yellow upper outer strip above the cyan region for both teams.

The standalone backend also serves `resources/config.json` with
`3dActivated: "true"`, matching `play.py --mode server`. With the on-disk menu
default (`"false"`), the client immediately acknowledges resolutions without
animating them. The stored file and menu/tutorial launcher configuration stay
separate from this server-mode override.

These patches are included by `patches/rebuild.py`; the checkout's compiled SWF
already contains them. If named constructor metadata changes, update its fallback
table to match the compiled class traits, including empty positional entries.
Avoid local variables named `name` in the constructor metadata fallback: FFDec
can compile `@name` as the local variable in an XML filter, append duplicate
metadata, and break the native player's constructor injection.
Chrome's AudioContext warning means audio needs a click/user gesture on the
player; it does not indicate an injection or asset-loading failure. The backend
also acknowledges optional client trace requests without storing them.

The implementation uses self-hosted Ruffle: its WebAssembly player runs the SWF in
modern browsers, while the existing Python/Bun service still runs on the server.
The Python backend does not need to be converted to browser code.

Ruffle supports ActionScript 3 but its API compatibility remains incomplete;
a successful menu load is not proof that a complete game works. Official sources:
[Ruffle compatibility](https://ruffle.rs/compatibility),
[self-hosting instructions](https://github.com/ruffle-rs/ruffle/wiki/Using-Ruffle),
and [web player overview](https://github.com/ruffle-rs/ruffle/blob/master/web/README.md).

This client's 3D scene uses the older Away3D display-list/SpriteSession renderer
(`resolution/display/scene/SceneView.as` in the recovered sources). Do not assume
it needs modern Flash Stage3D support merely because it has a 3D view. Its dynamic
SWF libraries, fonts, filters, audio, loading and timing still need game-specific
compatibility tests.

## Recreating the prototype setup

1. Download an official Ruffle **self-hosted web** release and extract its complete
   distribution, including the JavaScript and WASM files, to `vendor/ruffle/`.
   The installed release is `nightly-2026-10-13`:

   ```sh
   mkdir -p vendor/ruffle
   curl -fL https://github.com/ruffle-rs/ruffle/releases/download/nightly-2026-10-13/ruffle-nightly-2026_10_13-web-selfhosted.zip -o /tmp/boufbowl-ruffle.zip
   unzip -o /tmp/boufbowl-ruffle.zip -d vendor/ruffle
   ```
2. Keep the repository's `bin/`, `assets/` and `resources/` structure. Serve the
   browser page, SWF, resources and `/api/` from the same HTTP origin.
3. Create `browser.html` in the repository root with the following prototype.
   This is an integration example, not an already-tested deployment:

```html
<!doctype html>
<meta charset="utf-8">
<title>Boufbowl browser prototype</title>
<div id="game"></div>
<script src="vendor/ruffle/ruffle.js"></script>
<script>
const player = window.RufflePlayer.newest().createPlayer();
player.style.width = "1024px";
player.style.height = "600px";
document.getElementById("game").appendChild(player);
player.load({
  url: "bin/boufbowl-client-1.9.6.swf",
  backgroundExecutionMode: "none",
  parameters: {
    lang: "fr", tuto: "0", mock: "0", server: "1", scene3d: "1",
    backend: location.origin
  }
});
</script>
```

4. Start the existing asset/API server:

```sh
python3 -m backend.server --host 127.0.0.1 --port 9900
```

Open `http://127.0.0.1:9900/browser.html` and inspect the browser console and
network panel. Do not load the page through `file://`. Remote account login uses
the existing HTTPS requirement. Browser anonymous storage is separate from the
standalone player's device token; account login can select the existing profile.

## Acceptance checks

Verify menus/customization and resource loading, anonymous/account persistence,
two human clients, placement, several resolved turns, ball-action cinematics,
power-number effects, chat, goals, replays and match completion. Also test audio
unlock by a user gesture, tab backgrounding, reconnects and mobile input. The
standalone player's Quit command needs a browser-appropriate exit/reset behavior;
web pages generally cannot close arbitrary tabs.

If emulator limitations block these checks, the reliable alternative is a native
HTML5 client using Canvas/WebGL and the existing server APIs/protocol. That is a
client port, not a simple SWF rebuild; it can retain backend simulation, accounts,
match records and rules. Ruffle is the smaller first experiment before committing
to that larger rewrite.
