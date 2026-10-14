# Browser playback options

The shipped launcher currently runs the Flash standalone player through Wine.
Browser gameplay has not been validated for Boufbowl. The first implementation
option to evaluate is self-hosted Ruffle: its WebAssembly player runs the SWF in
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

## Prototype setup

1. Download an official Ruffle **self-hosted web** release and extract its complete
   distribution, including the JavaScript and WASM files, to `vendor/ruffle/`.
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
  parameters: {
    lang: "fr", tuto: "0", mock: "0", server: "1",
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
