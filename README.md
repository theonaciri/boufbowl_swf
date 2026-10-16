# Boufbowl client and replacement server

## Run from a checkout on Ubuntu

The repository includes the runnable game client (`bin/boufbowl-client-1.9.6.swf`)
and simulation worker (`backend/build/engine.js` and `engine_base.json`). The
main client and build base (`bin/base/boufbowl-client-1.9.6.swf`) stay tracked;
temporary capture SWFs, standalone players and
downloadable packages are generated or supplied locally and excluded from Git.
For desktop play, supply the standalone Flash player at
`bin/flashplayer_32_sa.exe`. The Python server runs directly
from `backend/`; it has no pip dependencies.

Install the runtime dependencies once:

```sh
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install python3 wine wine32:i386 curl unzip
curl -fsSL https://bun.sh/install | bash
```

Open a new terminal after installing Bun, or use its installed
`~/.bun/bin/bun`. The launcher checks that location as well as PATH. A graphical
X11/XWayland session is required. Java, FFDec, AIR and the Android SDK are needed
only to rebuild, not to play. The Linux packages include Bun and Flash Player.

From this repository directory:

```sh
./play.sh --mode server
```

Use the original home-screen **Play / Jouer** button for human matchmaking, CPU
games, challenges or resume. **Find tournament** searches the separate human tournament queue; **CPU matchmaking**
starts a CPU game only when explicitly selected. The Play dialog shows the selected
team and offers **Change team**. The toolbar contains only Home, Quit and
Club (Server in English); Club opens only when clicked. **Server → Account** creates/links an account or logs in; anonymous device
profiles remain available. `--profile Alice` selects another device profile.
`--mode menus`, `--mode tutorial` and `--mode mock` select standalone modes.

## Language and refreshing services

Open the **gear at the top right** to select **Français, English, Deutsch or
Español**. Click the language button to cycle through choices, then close the
settings popup to save. Restart the game to apply the saved language to every
original screen. Added replacement-server dialogs still use English labels.
The preference is local to this installation/Wine profile and
works on desktop and Android. It does not reset your server profile or match.
`./play.sh --lang fr` explicitly overrides the saved choice for one launch;
without `--lang`, the saved choice takes priority over the configured default.
Global chat subscriptions are separate settings under **Server → Community →
Channels**; changing the interface language does not remove joined chat rooms.

**Mettre à jour les services** is the original customization-service refresh
button. Historically it queried credits and premium unlocks. Our local backend
acknowledges the refresh; customization is already free and locally supplied.
It does not download patches, update the client/server, or reinstall game files.
Use Git/package updates and restarts as described below for game updates.

## What does play.sh start?

`play.sh` changes into its own directory and runs `play.py`. It does not compile,
download updates, or start a previously installed copy of the game.

| Launch | Client and assets | Authoritative game server |
| --- | --- | --- |
| `./play.sh` or `./play.sh --mode server` | This checkout's Flash client through Wine, plus a local HTTP asset server | Embedded Python service, SQLite database and Bun worker |
| `./play.sh --mode server --server-url http://SERVER_ADDRESS:9900` | This checkout's client and local asset server | The server at the supplied URL; no embedded backend is created |
| `./play.sh --mode menus`, `--mode tutorial`, or `--mode mock` | Local client and asset server | No authoritative backend is created |

The default startup mode is `server` in `resources/game_config.json`; specifying
`--mode server` makes it explicit. The embedded service listens on **127.0.0.1 at
an automatically selected port**, not necessarily 9900. Closing the client stops
its local asset server and embedded backend/worker. The database persists at
`~/.local/share/boufbowl-offline/backend.sqlite` (or under `$XDG_DATA_HOME`);
`--database /path/backend.sqlite` overrides it.

**Connection settings are remembered.** A saved URL in the client can connect it
to a standalone backend even when a local backend was started. In **Server**,
clear the URL and Connect to select the embedded backend. An explicit nonempty
`--server-url` selects a standalone backend for that launch. Separate embedded
launchers do not share live event delivery; use one standalone backend for human
matches across clients.

For a shared desktop/Android server, use two terminals:

```sh
# Terminal 1: keep this running from the updated repository directory.
python3 -m backend.server --host 0.0.0.0 --port 9900

# Terminal 2: desktop client on this computer.
./play.sh --mode server --server-url http://127.0.0.1:9900 --profile Alice
```

Other computers and Android use the server computer's LAN address, for example
`http://192.168.1.20:9900`. On Android, `127.0.0.1` means the phone. The APK contains
the client and assets; it does **not** contain or launch the Python/Bun backend.
Closing a client does not stop a standalone server. Remote password login requires
HTTPS; see [accounts and matchmaking](docs/accounts-and-matchmaking.md).

## Make sure client and server are current

1. Close the game and stop any standalone server you run (Ctrl+C in its terminal).
   If managed by a service manager, restart that service after updating its files.
2. Update the intended checkout:

   ```sh
   cd /path/to/boufbowl_swf
   git pull --ff-only
   git log -1 --format='%h %s'
   git status --short
   ```

   A failed pull means the update did not complete. Review local changes rather
   than discarding them. The commit printed identifies your checkout; it must
   match the revision you intend to run.
3. Start `./play.sh --mode server` from that checkout and verify the **Server**
   connection settings. Restart a separate backend from its updated checkout too;
   updating a client machine does not update a remote server.

The SWF's filename and protocol version stay `1.9.6` across patches; they are not
build revision indicators. Check the tracked client and simulation artifacts for local changes:

```sh
git diff HEAD --exit-code -- bin/boufbowl-client-1.9.6.swf backend/build/engine.js backend/build/engine_base.json
```

No output and exit status 0 means these files match your checkout's commit.
The main SWF is tracked in Git; rebuild and commit it after updating client patches.
Updating `.as` patches alone does
not update the running Flash client: rebuild it as below, then close and reopen
the game. Python source changes require a backend restart; simulation changes
require rebuilding the worker and restarting the backend.

To identify copies that are still running:

```sh
ps -eo pid,lstart,args | rg 'play.py|backend.server|engine.js|flashplayer_32_sa'
# Substitute a Python launcher/server PID from the output:
readlink -f /proc/PID/cwd
```

The working directory should be the intended checkout or installed bundle. A
launcher uses files beside `play.py`; an installed desktop shortcut uses
`/opt/boufbowl-offline/play.sh`. Pulling Git does not update `/opt`: rebuild and
reinstall the .deb, or explicitly run your checkout's `./play.sh`. An extracted
tar bundle is another independent copy and must also be replaced.

For a standalone server, check that the intended endpoint responds:

```sh
curl -fsS http://127.0.0.1:9900/api/health
```

Health reports service, protocol, schema and rules versions, **not a Git commit or
client hash**. It proves availability, not that the remote deployment is newest.
Verify the Git revision on the server machine and restart its process. For an
embedded server, its port can be found with `ss -ltnp` for the `play.py` PID.
Launcher logs are in `~/.local/state/boufbowl-tutorial/` (or `$XDG_STATE_HOME`):
`wine.log`, `http.log`, and `mock.log`. They help confirm requests and playback;
the logs themselves are not revision identifiers.

Android APKs and Linux packages are build outputs, not updated automatically by
`git pull`. Build/install the new APK on the phone, keep the same signing
certificate, then fully close and reopen the app. Separately update/restart its
Linux backend. Reinstall the new Linux package when using the desktop shortcut.

## Build the client and packages

Run commands from `boufbowl_swf`. The preserved build input is
`bin/base/boufbowl-client-1.9.6.swf`; the runnable output is
`bin/boufbowl-client-1.9.6.swf`. Both retain the original filename and are tracked.
The current base is the local patched client preserved before the latest rebuild;
it is not an untouched historical archive. The build applies the readable
`patches/` sources to this stable base without overwriting it. Pass `--original`
to use a different source archive. No full decompile is required. Build outputs
are not automatically launched or installed.

| Changed files | Required action |
| --- | --- |
| `backend/*.py` | Restart the backend; no client compilation |
| `backend/engine.ts`, `backend/simulator/`, or sibling simulator source | Rebuild worker, then restart backend |
| Shared ActionScript patches or client generation code | Rebuild desktop SWF; rebuild Android APK if used; reopen client |
| `android/patches/` | Rebuild/install Android APK |
| Balance/general configuration | Validate and restart backend; rebuild clients for embedded defaults/UI; existing matches retain saved rules |
| Palettes or stadium art manifest | Rebuild clients/resources and any distributed packages |

### Desktop Flash client

Install JDK 17 and obtain JPEXS FFDec 26.3.0. The rebuild script finds FFDec
in `~/.cache/boufbowl-flash-tools/ffdec/ffdec.jar` when it has already been
downloaded there. Otherwise pass its path with `--ffdec`, or set `FFDEC_JAR`.

```sh
sudo apt-get install openjdk-17-jdk
python3 -m tools.game_config
python3 patches/rebuild.py
./play.sh --mode server
```

This replaces `bin/boufbowl-client-1.9.6.swf` and prepares generated resources and
stadium models. It leaves the supplied original SWF unchanged. In the investigation
workspace, the reference files are `../migration-work/ffdec/ffdec.jar` and
`../boufbowl/art_sources/flash_vectors/libraries/bin/boufbowl-client-1.9.6.swf/original.swf`;
these neighboring directories are not required for normal checkout playback and
may not exist on another machine.

### Simulation worker, only when its source changed

Bun and the sibling `../boufbowl_server/src/` source tree are required to compile
the simulator imports:

```sh
bun backend/build-worker.ts
```

This updates `backend/build/engine.js` and `backend/build/engine_base.json`.
Restart the authoritative backend afterward. A normal Git update already carries
these compiled files; rebuilding this worker does not rebuild the Flash client.

### Linux .deb and tar archive

After any required client/worker builds, package the current files:

```sh
sudo apt-get install dpkg-dev
python3 linux/build.py
sudo apt install ./linux/build/BoufbowlOffline-linux-amd64.deb
```

Outputs: `linux/build/BoufbowlOffline-linux-amd64.deb` and
`linux/build/BoufbowlOffline-linux.tar.gz`. Packaging includes the current SWF,
Python backend, compiled worker, assets/resources and a bundled Bun runtime. It
**does not compile the Flash client**. `--rebuild-worker` optionally compiles the
worker first and requires the sibling source tree. Launch the installed game from
the application menu or `/opt/boufbowl-offline/play.sh`. More details:
[Linux instructions](linux/README.md).

### Android APK

First rebuild the desktop SWF if shared client code changed. Android packaging
starts from that patched SWF and applies shared patches plus Android overrides.
Requirements: AIR SDK 51.4, FFDec 26.3.0, JDK 17, Android SDK platform 35/build-tools
35.0.1, and FFmpeg with libx264. Gradle downloads dependencies on the first build.

```sh
python3 android/build.py \
  --air-sdk /path/to/AIRSDK \
  --ffdec /path/to/ffdec.jar \
  --jdk /path/to/jdk-17 \
  --android-sdk "$HOME/Android/Sdk"
```

Output: `android/build/BoufbowlOffline.apk` for ARM64. Copy/install it on the phone
(or use `adb install -r android/build/BoufbowlOffline.apk` with a connected device).
Retain the signing certificate for updates; the default local certificate is at
`~/.cache/boufbowl-flash-tools/android-signing/local.p12`. A differently signed APK
cannot update the installed app. The APK build leaves the desktop SWF unchanged.
See [Android instructions](android/README.md) for signing and emulator builds.

Run `python3 -m unittest discover -s tests -v` to check server/configuration changes.
The current validation passed 169 automated tests and native desktop playback
of a complete 14-turn Kara comparison match;
the latest live-server APK has package checks but no current device validation.

Full-screen cinematics are enabled for new matches: stadium camera introduction,
versus, goals/celebrations, ball-carrier combat, passes, receptions/interceptions and rebounds.
Each ball-action type gets at most one full-screen sequence per turn.
Placement waits for introduction completion, with a timeout fallback. Configure
`general.cinematics` in [game_config.json](resources/game_config.json); see
[cinematic settings](docs/game-configuration.md#cinematic-presentation).
Stored replay data is retained; playback applies the same ball-only cinematic limit.

General settings, balance, class abilities and stadium overrides are in
[resources/game_config.json](resources/game_config.json). Configuration is
validated before builds. Existing matches keep a snapshot of their rules.
See [configuration instructions](docs/game-configuration.md).

Profiles, owned clubs, customization, matches, chat, ranking results and turn
records persist. The backend validates orders and runs the simulation; the
original client animates its protobuf resolution scenarios and acknowledges
completion. It supports automatic human matchmaking, CPU matches, two-player challenges, spectating, chat,
rankings and configurable free local tournaments.

Missing regular and special animated skins reuse Cra of the same gender in
team views, editors and match playback. Their original identity, class, stats,
abilities and portrait artwork remain available. The full roster is in
[resources/offline_characters.json](resources/offline_characters.json).
Unavailable stadium models reuse Farmstead with the selected stadium's rules.

For server setup, sessions, backup/restore and recorded replays, read
[backend operation](docs/backend-operation.md). Historical account, payment and
administrative services are intentionally disabled. Optional local accounts support
cross-device login alongside anonymous device sessions. Remote password login
requires HTTPS; see [accounts and matchmaking](docs/accounts-and-matchmaking.md). Exact historical server probabilities and ability effects
were not recoverable from the client. These use documented configurable engine
rules; provisional effects remain marked `verified: false`.

Development references:

- [Original turn playback findings](docs/turn-playback.md)
- [Implementation and verification log](docs/investigation-log.md)
- [Request coverage and replacement policies](docs/request-coverage.md)
- [Recovered protocol matrix](docs/protocol-matrix.md)
- [Server/database and asset plan](docs/backend-and-assets-plan.md)
- [Scripted replay harness](docs/mock-replay.md)

Run tests with `python3 -m unittest discover -s tests -v`. Native player checks use
`xvfb-run -a -s '-screen 0 1280x800x24' python3 tools/smoke_mock.py --fixture PATH`.
Original reference SWFs and decompiled source remain untouched; readable changes
are maintained in `patches/`, with platform adjustments in `android/patches/`.

Stadium surface themes and expanded customization colors: [visual assets](docs/visual-assets.md).

**Server → Community** opens rankings, friends/blocks, match history, replay
playback and JSON saving, live spectating, private messages and language chat
subscriptions. See [community and replays](docs/community-and-replays.md).


Class powers and class statistics are experimental and editable in
[resources/game_config.json](resources/game_config.json). All 14 classes have
distinct base element profiles. Powers enforce one caster per team per turn,
exclude other caster actions, and use the stadium's per-character match allowance.
See [the balance tables and effect semantics](docs/game-configuration.md).
Restart the client and server and start a new match to use changed balance rules;
existing matches and saved replays retain their recorded rules.


Normal and expert CPU matches now use class powers; beginner keeps regular
orders. See [the cheating and abuse review](docs/cheating-and-abuse.md) for current
protections, identified gaps, and a prioritized server-hardening plan.


Ranked results now come only from human normal/tournament matchmaking. CPU games
are practice; nickname challenges are casual. Both remain in history, with
separate counters. Schema 8 discards incompatible development databases and starts fresh
statistics at 1000. No legacy statistics, matches or replays are migrated. Active replay exports contain playback data only; full audits and
verification unlock after completion. New turn seeds are independently generated.
See [result and replay policies](docs/community-and-replays.md).

Orange movement cells now carry increasing fall risk. See the
[reference-match investigation](docs/reference-match-comparison.md) for source
evidence, configurable odds, corrected regeneration and replay validation.

Scheduled tournaments now rotate stadiums, qualify four players and run knockout
rounds over 45 minutes each hour. They show upcoming countdowns and finalized standings in the original interface.
Started matches may finish after entry closes. See [tournament lifecycle](docs/tournament-lifecycle.md)
for schedules, local rewards, source findings and verification.

The [frontend restoration guide](docs/frontend-restoration.md) covers five ranked
leagues, optional seasons, wallet/cosmetics, replay pause/speed/turn selection,
news and moderator roles. Advanced training is excluded. Grant moderator roles
with the local `backend.manage role` command; clients cannot self-promote.

All embedded heraldry is available: 27 blason icons and 32 backgrounds, including
the two previously unmapped heart backgrounds. See [visual assets](docs/visual-assets.md).


The top Accueil/Quitter/Club toolbar appears outside matches only. Power numbers
show actual nonzero bonuses/maluses instead of +0, and power descriptions contain
only their effects. Regeneration was verified across six real turns and a restart.
[Browser playback options](docs/browser-play.md) explain how to launch the included
self-hosted Ruffle prototype, its startup compatibility fixes, and the gameplay
checks still required.

### Administrator pages

Use `/admin.html`, `/moderation.html`, and `/tournaments.html` for statistics, live chat moderation, and tournament scheduling. See [the administrator console guide](docs/admin-console.md) for roles, conversation filters, suspensions, recurring events, rules, and prizes.

### Textes juridiques en français

Les projets de politique de confidentialité, CGU, mentions légales, notice sur les traceurs, charte communautaire et règlement des tournois sont accessibles à `/legal.html`. Leurs sources et les champs `[]` à compléter sont présentés dans [le guide des textes juridiques](docs/legal/README.md).

### French homepage and builds

The website root serves the French fan-game homepage. Play at `/play.html`;
`/browser.html` redirects there. See [homepage assets, configuration and build distribution](docs/site/README.md).
Configure Discord, external download links and the future source for the Tot quote in `resources/site.json`.
Android, Windows and Linux player artifacts are discovered automatically by `/api/site` and distributed under `/downloads/`.
Build the remote-only desktop player downloads with `python3 -m tools.build_player_downloads --server-url https://YOUR_SERVER`.
These archives contain the Flash player and a launcher that loads the game and resources from the shared server;
players need no Python or local backend. Windows runs directly; Linux requires Wine with 32-bit support.
The larger `linux/build.py` offline/development bundle remains available for developers but is not the website's player download.
Use `--server-url https://YOUR_SERVER` with the Android build script to target the shared game server.
