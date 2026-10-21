# Build the game

Run commands from the repository root:

```sh
bun run build                 # Build the game only
bun run build:website         # Build the website (including missing media)
```

The game command does not render website media or start Chromium.

## Tools and inputs

Install Bun and these system packages once:

Ubuntu/Debian:

```sh
sudo apt install python3 openjdk-17-jre-headless ffmpeg libavif-bin
```

Arch Linux:

```sh
sudo pacman -S --needed python jre17-openjdk ffmpeg libavif
```

FFmpeg and `avifenc` are needed only for website media, not the game build.
FFmpeg must support libx264, libaom-av1, libsvtav1, and libwebp; `avifenc` must
support `--qcolor`. Distribution packages on current systems normally provide them.

**Do not set `FFDEC_JAR` unless you want a custom FFDec installation.** The build
finds Java 17+ and FFDec automatically. If FFDec is absent, it downloads version
26.3.0 from its official GitHub release, verifies the pinned SHA-256, and caches it
under `${XDG_CACHE_HOME:-$HOME/.cache}/boufbowl-flash-tools/ffdec-26.3.0`.

The required game input is already tracked:
`bin/base/boufbowl-client-1.9.6.swf`, SHA-256
`b13475e837bec851157e5d02b45088d1f697ad65121a383d3e40b43074883154`.
It is a previously patched baseline; no untouched historical binary is verified.

## Build the website

```sh
bun run build:website
```

This command, in order:

1. Builds the game SWF if missing, then prepares its runtime JSON files.
2. Generates missing website videos, portraits, stadium previews, and metadata.
   Renderer packages and Chromium are downloaded automatically when needed.
3. Uses Bun to bundle/minify CSS and JavaScript and generate all static pages,
   including legal pages, robots.txt, sitemap.xml, and download size labels.

The result is **`.local/website/dist/`**, ready for your static web server.
Changed media inputs are detected automatically; unchanged media is reused. A first build can take a long time because it renders
and encodes the recovered game assets. Run the same command again after a
failure; completed work stays cached. Failed steps stop the process immediately.

You do not need to run `cp`, `tools.build_mock_fixture`, or
`tools.build_legal_pages` separately. There is no Python web-server requirement
for the generated HTML. [Hosting](HOSTING.md) explains serving the output.

## Desktop client and runtime files

To rebuild the game after changing ActionScript or game configuration:

```sh
bun run build
```

This finds the same tools and builds the SWF/runtime files without rendering the
website. Follow it with `bun run build:website` when you also need website delivery.
For native desktop play, supply `bin/flashplayer_32_sa.exe` (not included in Git),
install Wine with 32-bit support, and run `./play.sh --mode server` in a graphical
session. The web build does not require Wine or the standalone Flash player.
Use the advanced `patches/rebuild.py --original /path/to/archive.swf` only when
intentionally replacing the preserved game baseline. [Binary workflow](BINARY.md)
explains individual patches.

`play.sh` launches existing files without compiling them. Useful options:
`--mode tutorial`, `--mode menus`, `--mode mock --scene-3d`,
`--lang fr`, `--profile Alice`, and `--show-fps`.
The in-game FPS slider requests 25–240 FPS; runtime/display limits still apply.

## Simulator

The retained `backend/build/engine.js` runs without sibling sources. Rebuilding it
requires the external `../boufbowl_server/src` tree:

```sh
bun backend/build-worker.ts
```

This applies local `backend/simulator/` overlays and copies `engine_base.json`.
The TypeScript movement probe also needs the external tree; its saved fixture
and the extracted `protocol/*.json` contracts are preserved inputs.

## Distribute players

```sh
python3 -m tools.build_player_downloads --server-url https://YOUR_SERVER
```

Outputs `windows/build/Boufbowl-windows.exe` and
`linux/build/Boufbowl-linux.run`: one executable download per platform.
Both embed the local SWF, game assets, resources, and Flash player. Website
stadium previews (`assets/textures/stadiums/*.avif`) are excluded from desktop
and Android packaging; the PNG textures remain included for the game.

Build prerequisites: Java/FFDec and NSIS (`sudo apt-get install nsis` on Ubuntu).
Use the Java/FFDec paths printed by the game build when overrides are needed;
`--ffdec`, `--java`, and `--makensis` can specify custom tool locations. Separate cached SWFs contain each platform's defaults;
the hosted browser SWF is unchanged. Only the game API uses the remote server.

- Windows: double-click the `.exe`. The NSIS launcher prepares a versioned cache
  under `%LOCALAPPDATA%\Boufbowl\player`, configures FlashPlayerTrust, and starts
  the game without a console or installer wizard. No administrator rights needed.
- Linux x86-64: install Wine with 32-bit support, then run:

  ```sh
  chmod +x Boufbowl-linux.run
  ./Boufbowl-linux.run
  ```

  The executable verifies and extracts its embedded payload on first launch under
  `${XDG_CACHE_HOME:-$HOME/.cache}/boufbowl/player`, reuses it on later launches,
  and starts the bundled client through Wine. Standard `tar`, `gzip`, `sha256sum`,
  and GNU `mv` are required; Python and Bun are not required on players' machines.

The local client and assets load from the cache; no local HTTP server is started.
ZIP/tar.gz files remain intermediate build artifacts. Rebuild the packages and
website after changing the server URL or game assets. Desktop and Android build
commands automatically run the Bun website compiler after creating their bundles,
refreshing published files, versioned download links, and French size labels. Use
`--no-website` only to defer delivery (for example before the first media export);
then run `bun run build:website` once those inputs are ready. `--bun` selects Bun’s path.

For the separate Linux development bundle:

```sh
python3 linux/build.py --archive-only
# With dpkg-deb installed, also build the .deb:
python3 linux/build.py
```

Outputs `linux/build/BoufbowlOffline-linux.tar.gz` and
`BoufbowlOffline-linux-amd64.deb`. These include the backend and Bun.
Build the website first; packaging copies current files without compiling Flash. `--rebuild-worker` requires the external simulator sources.

## Android

```sh
python3 android/build.py \
  --air-sdk /path/to/AIRSDK \
  --ffdec /path/to/ffdec.jar \
  --jdk /path/to/jdk-17 \
  --android-sdk "$HOME/Android/Sdk" \
  --server-url https://YOUR_SERVER
```

Output: `android/build/BoufbowlOffline.apk`, ARM64. `--arch x64` builds for an
emulator; `--debug` includes AIR debugging. The APK bundles game assets, applies
shared/Android overrides to the desktop SWF, and converts FLVs to MP4. It connects
to a separate backend. On ARM build hosts, Android/AAPT2 tools need compatible
binaries or emulation.

Keep the signing certificate for updates. The default lives under
`~/.cache/boufbowl-flash-tools/android-signing/local.p12`; its random password is
stored beside it in `local.password` with mode 0600. For a custom certificate,
set `BOUFBOWL_KEYSTORE_PASSWORD` and pass `--keystore /path/to/key.p12`.

## Check changes and refresh

```sh
python3 -m tools.build_interaction_fixtures
python3 -m unittest discover -s tests -v
```

Generate [website outputs](WEBSITE.md) before website-specific tests. For native
playback, with Wine, Flash Player, and Xvfb available:

```sh
xvfb-run -a -s '-screen 0 1280x800x24' python3 tools/smoke_mock.py \
  --fixture tests/fixtures/interactions/goal.json --require-cinematic
```

Python changes need a backend restart; AS3 changes need an SWF rebuild and client
restart; simulator changes need a worker rebuild and backend restart. Rebuild
packages after changing their client/assets or hosted URL. Generated outputs
stay ignored; commit the sources and generators.
