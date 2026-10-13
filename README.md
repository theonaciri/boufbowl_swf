# Boufbowl client and replacement server

Run `./play.sh` on Ubuntu. It starts the original patched Flash client, a local
server and a persistent SQLite database. Use **Play** in the top toolbar for
human matchmaking, CPU games, nickname challenges or resume. Use **Server → Account**
to create/link an account or log in; anonymous device profiles remain available.
Use `--profile Alice` to select another device profile. Menus and tutorial remain
available with `--mode menus` and `--mode tutorial`.

A source checkout includes the compiled Flash client and simulation worker. You
do not need to build anything to play. Install Python 3, Wine with 32-bit support,
and Bun once, then run `./play.sh`. Java, AIR, FFDec and Android SDK are only
needed for rebuilding. The Linux package bundles Bun.

Linux requires Python 3, Wine with 32-bit support, and X11/XWayland. The package
includes Flash Player and Bun for the simulation worker. Dependencies and build
instructions are in [linux/README.md](linux/README.md) and
[android/README.md](android/README.md).

The Android APK includes the same client, patches and assets. Connect it to the
Linux service using the computer's LAN address:

```sh
python3 -m backend.server --host 0.0.0.0 --port 9900
```

General settings, balance, class abilities and stadium overrides are in
[resources/game_config.json](resources/game_config.json). Configuration is
validated before builds. Existing matches keep a snapshot of their rules.
See [configuration instructions](docs/game-configuration.md).

Profiles, owned clubs, customization, matches, chat, ranking results and turn
records persist. The backend validates orders and runs the simulation; the
original client animates its protobuf resolution scenarios and acknowledges
completion. It supports automatic human matchmaking, CPU matches, two-player challenges, spectating, chat,
rankings and a configurable free local tournament league.

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
