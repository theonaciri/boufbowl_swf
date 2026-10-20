# Build the game

Run commands from the repository root. Rebuild the desktop SWF before packaging
Android or exporting website characters.

## Tools and inputs

- Python 3 (standard library only), Bun, JDK 17, and JPEXS FFDec 26.3.0.
- Native desktop play: Wine with 32-bit support, a graphical session, and the
  supplied Flash projector at `bin/flashplayer_32_sa.exe`.
- Video builds: FFmpeg with libx264, libsvtav1, and libwebp.
- Android: AIR SDK 51.4, Android SDK platform 35/build-tools 35.0.1, and
  host-compatible Android tools. AIR/Gradle may download dependencies.

Install Bun and FFDec separately. Put Java and Bun on PATH and set:

```sh
export PATH="/path/to/jdk-17/bin:$HOME/.bun/bin:$PATH"
export FFDEC_JAR="$HOME/.cache/boufbowl-flash-tools/ffdec-26.3.0/ffdec.jar"
```

Place FFDec at that path for the carousel exporter, which currently uses this
cache location directly. Other builders accept `--ffdec`.

The preserved input is `bin/base/boufbowl-client-1.9.6.swf`, SHA-256
`b13475e837bec851157e5d02b45088d1f697ad65121a383d3e40b43074883154`.
It is already patched; no untouched historical binary is verified here.

## Desktop client and runtime files

```sh
python3 -m tools.game_config
python3 patches/rebuild.py --ffdec "$FFDEC_JAR"
cp backend/engine_base.json backend/build/engine_base.json
python3 -m tools.build_mock_fixture
python3 -m tools.build_legal_pages
./play.sh --mode server
```

The first command validates configuration. The rebuild applies `patches/*.as`,
generated startup/FlashVars/palette code, and creates
`bin/boufbowl-client-1.9.6.swf` plus themed stadium models/resources.
It preserves the input. Use `--original /path/to/archive.swf` to supply another
baseline. [Binary workflow](BINARY.md) explains how to add a patch.

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

Outputs `windows/build/Boufbowl-windows.zip` and
`linux/build/Boufbowl-linux.tar.gz`. Both include game assets and the Flash player;
they load the hosted SWF and use its server. Windows runs `Jouer.cmd`; Linux needs
Wine with 32-bit support and runs `jouer.sh`. Players need no Python/Bun backend.

For the separate Linux development bundle:

```sh
python3 linux/build.py --archive-only
# With dpkg-deb installed, also build the .deb:
python3 linux/build.py
```

Outputs `linux/build/BoufbowlOffline-linux.tar.gz` and
`BoufbowlOffline-linux-amd64.deb`. These include the backend and Bun.
Generate legal pages first; packaging copies the current files without compiling
Flash. `--rebuild-worker` requires the external simulator sources.

## Android

```sh
python3 android/build.py \
  --air-sdk /path/to/AIRSDK \
  --ffdec "$FFDEC_JAR" \
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
