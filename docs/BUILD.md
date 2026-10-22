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

FFmpeg is needed for website media and application icon generation when packaging
players. `avifenc` is needed only for website media. Neither is needed for the
game SWF build.
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

CPU tactics and power selection can be refreshed independently, using their local
TypeScript sources and the retained simulator bundle:

```sh
bun backend/refresh-cpu-worker.ts
```

This updates the CPU sections of `backend/build/engine.js` without changing the
simulation rules or requiring the external archive. Restart the backend to load
the updated worker. The full worker build also includes these CPU sources.

## Distribute players

```sh
python3 -m tools.build_player_downloads --server-url https://YOUR_SERVER
```

Outputs `windows/build/Boufbowl Fan.exe` and
`linux/build/Boufbowl Fan.run`: one executable download per platform.
Both embed the local SWF, game assets, resources, and Flash player. Website
stadium previews (`assets/textures/stadiums/*.avif`) are excluded from desktop
and Android packaging; the PNG textures remain included for the game.

Build prerequisites: Java/FFDec, FFmpeg, and NSIS
(`sudo apt-get install ffmpeg nsis` on Ubuntu).
Use the Java/FFDec paths printed by the game build when overrides are needed;
`--ffdec`, `--java`, and `--makensis` can specify custom tool locations. Separate cached SWFs contain each platform's defaults;
the hosted browser SWF is unchanged. Only the game API uses the remote server.

- Windows: double-click the `.exe`. The NSIS launcher prepares a versioned cache
  under `%LOCALAPPDATA%\Boufbowl\player`, configures FlashPlayerTrust, and starts
  the game without a console or installer wizard. No administrator rights needed.
- Linux x86-64: install Wine with 32-bit support, then run:

  ```sh
  chmod +x "Boufbowl Fan.run"
  ./"Boufbowl Fan.run"
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

Outputs `linux/build/Boufbowl Fan-development-linux.tar.gz` and
`Boufbowl Fan-linux-amd64.deb`. These include the backend and Bun.
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

Output: `android/build/Boufbowl Fan.apk`, ARM64. `--arch x64` builds for an
emulator; `--debug` includes AIR debugging. The APK bundles game assets, applies
shared/Android overrides to the desktop SWF, and converts FLVs to MP4. It connects
to a separate backend. On ARM build hosts, Android/AAPT2 tools need compatible
binaries or emulation.

Keep the signing certificate for updates. The default lives under
`~/.cache/boufbowl-flash-tools/android-signing/local.p12`; its random password is
stored beside it in `local.password` with mode 0600. Keep both files when moving
build tools between machines.

Signing credentials are checked before compilation starts. If an older certificate
has no password file, the script checks the historical development password from
available Git history against that certificate. Only a verified match is saved to
`local.password`; the existing certificate is preserved. With a shallow clone or
an unrelated certificate, run from an interactive terminal to enter its password
privately. The default certificate's verified password is remembered for later builds.
If the password is unknown and the legacy migration does not match, the script
cannot recover it and stops without replacing the certificate.

For a custom certificate, pass `--keystore /path/to/key.p12`. Its password can come
from `BOUFBOWL_KEYSTORE_PASSWORD`, an adjacent `.password` file, or a private terminal
prompt. Automated builds must provide the environment variable or password file.
The build never prints passwords or includes them in its Python error messages.

The combined player build also checks NSIS, FFmpeg, and the desktop Flash player
before starting package jobs. Platform failures are summarized separately, without
an additional Python traceback; successfully built downloads are kept.

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

The shared rendering/chat regression can also run in native Adobe AIR, without
Wine. It checks both desktop and Android application roots, stationary/moving
sprites, explicit animation invalidation, batched chat composition, scroll
boundaries and a complete 3D fixture at a saved FPS cap:

```sh
python3 -m tools.smoke_shared_client
```

This requires an AIR SDK containing a host-compatible `bin/adl`, its native shared
libraries, a developer license where the runtime requires one, and Xvfb on
headless Linux. `--air-sdk`, `--runtime-libs`, `--root` and
`--fixture` select overrides. Logs are written under `.local/shared-client`;
test application ids isolate their preferences from installed clients.

See [shared client performance work](PERFORMANCE.md) for the five optimization
cycles, regression coverage and focused benchmark results.

Python changes need a backend restart; AS3 changes need an SWF rebuild and client
restart; simulator changes need a worker rebuild and backend restart. Rebuild
packages after changing their client/assets or hosted URL. Generated outputs
stay ignored; commit the sources and generators.

### Application name and icons

Player downloads are named `Boufbowl Fan.exe`, `Boufbowl Fan.run`, and
`Boufbowl Fan.apk`. The shared icon source is `assets/branding/logo.png`.
Package builds generate the required sizes automatically using FFmpeg.
Windows embeds a multi-size ICO in the launcher; Android includes PNG launcher
icons. The Linux launcher registers a **Boufbowl Fan** application menu entry
and icon on first launch. Linux `.run` files themselves use the file manager's
generic executable icon; use the application menu entry for the custom icon.
The Android application ID and existing signing certificate are preserved so
installed copies can still receive updates.

## Parallel builds

Builds automatically use all available logical CPUs, accounting for CPU affinity
and Linux container CPU quotas. Python and Bun share one job budget across child
processes; idle slots are reused by queued work. Encoders are limited to one CPU
thread per job rather than each encoder starting a full-machine thread pool.

Website media stages run concurrently; images, video encodes, and independent
character captures also run in parallel. Inventory generation and the final static
website compilation happen after every media stage succeeds. The shared game SWF
must finish building before its consumers start.

To limit concurrency explicitly:

```sh
bun run build:website --jobs 4
python3 -m tools.build_player_downloads --jobs 4
```

`BOUFBOWL_BUILD_CPUS=4` applies the same ceiling to individual advanced tools.

To build Windows, Linux, and Android together with one shared CPU budget:

```sh
bun run build:players
```

Select one or more target platforms with `--platform` (also `--platforms`):

```sh
bun run build:players --platform linux
bun run build:players --platform windows linux
bun run build:players --platform android
```

The option can also be repeated: `--platform linux --platform android`.
With no selection, all three platforms are built. Only selected platform tools
are required: NSIS for Windows; AIR, Android SDK, a full JDK, and signing credentials
for Android. Desktop-only builds need Java 17+ but do not require Android tools or
signing credentials. Linux-only builds do not require NSIS. FFmpeg is needed for
application icon generation on every platform.

The desktop packager supports the same selection for its two targets:

```sh
python3 -m tools.build_player_downloads --platform linux
```

The command discovers installed AIR/Android SDKs and a full JDK automatically
when Android is selected.
It checks the Boufbowl tool cache (`$XDG_CACHE_HOME/boufbowl-flash-tools`, normally
`~/.cache/boufbowl-flash-tools`), remembered paths, standard installation folders,
and `adt`/`sdkmanager` on PATH. Common locations include `~/AIRSDK`, `/opt/AIRSDK`,
`~/Android/Sdk`, and `/usr/lib/jvm/`. Android discovery requires installed platform
and build-tools directories.

If the quick AIR or JDK checks find nothing, the script recursively searches the project,
tool cache, your home directory (including hidden folders), `/opt`, `/usr/local`,
and `/usr/share` for `lib/adt.jar` (AIR) or `bin/javac` (JDK). JDK searches also
include `/usr/lib/jvm`, `/usr/java`, and macOS Java installation folders. Java must
report version 17 or newer, and a full JDK must include both `java` and `javac`.
The game builder uses the same recursive JDK fallback when Java is missing from
PATH. A match is remembered automatically, so later builds do not repeat the search. Unreadable folders, dependency trees, and Git
metadata are skipped; directory symlinks are not followed recursively, although
links pointing directly to an SDK are recognized.

Paths can also be supplied explicitly to choose an installation:

```sh
bun run build:players \
  --air-sdk /path/to/AIRSDK \
  --android-sdk /path/to/Android/Sdk \
  --jdk /path/to/jdk-17
```

Resolved SDK/JDK paths are remembered locally in `.local/build-tools.json`, which
is ignored by Git. `AIR_SDK`/`AIRSDK_HOME`/`AIR_HOME`, `ANDROID_HOME`/`ANDROID_SDK_ROOT`,
and `JAVA_HOME`/`JDK_HOME` are also supported. Explicit flags and SDK environment
variables take precedence; a stale remembered path falls back to discovery.

AIR and Android SDKs must already be installed; discovery does not download them.
For AIR, extracting the SDK into `~/.cache/boufbowl-flash-tools/air-sdk` makes it
available automatically. FFDec is downloaded when missing. The standalone
`python3 android/build.py` command uses the same discovery and remembered paths.

The shared game client is prepared first if missing, then all three downloads are
built by default; with a platform selection, only those downloads are rebuilt.
The website is refreshed once after the selected builds finish. `--jobs N` limits combined concurrency;
`--no-website` defers the refresh.

## Incremental player packages

Selected packages are reused when their content fingerprints and output checksums
match. Unchanged `.exe`, `.run`, archives, and APKs keep their contents and mtimes;
NSIS, compression, Android staging, and APK packaging are skipped on a cache hit.
Missing, changed, or non-executable Linux outputs are rebuilt.

Fingerprints cover bundled assets and resources (including additions and removals),
server URL, client SWFs, patches, packaging code, icons, templates, architecture and
debug options, the Android certificate, and relevant Java/FFDec/AIR/Android/NSIS/
FFmpeg toolchain inputs. Passwords are excluded. File contents are hashed; merely
touching a file does not invalidate a package. Website-only media and stadium AVIF
previews are excluded from game package inputs as well as from the bundles.

Android client compilation has a separate cache keyed by the base SWF, the actual
configured ActionScript replacements, Java, and FFDec. Changing an asset, app icon,
or certificate can rebuild the APK while reusing the compiled SWF. Video conversions
have separate source/recipe/tool fingerprints. Staging copies changed files and
removes obsolete ones when a package needs rebuilding.

Receipts live in `.local/player-builds/`, compiled clients in
`.local/player-clients/`, and Android videos in `android/build/video-cache/`.
Keep them between builds. Removing a final package rebuilds that output using the
remaining intermediate caches. Cache records are written only after success;
locks prevent simultaneous builds from publishing conflicting package outputs.
A failed build leaves its last successfully published executable/APK in place.

`build:players` still validates dependencies and signing credentials at startup,
and refreshes website download links after all selected builds succeed. Use
`--no-website` when only building or measuring packages.
