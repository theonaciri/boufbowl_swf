# Boufbowl

Restored Flash client with a Python/SQLite backend and a Bun match simulator.
The game supports human and CPU matches, clubs, chat, tournaments, and replays.
The French website serves the browser client, downloads, and restoration tools.

## Start here

- [Build](docs/BUILD.md): prerequisites, desktop SWF, Android, packages, and checks.
- [Website](docs/WEBSITE.md): assets, portraits, video exports, and delivery.
- [Binary](docs/BINARY.md): find functions, export AS3/assets, and patch the SWF.
- [Server](docs/SERVER.md): configuration, accounts, administration, and backups.

All commands run from the repository root. After completing the build steps:

```sh
./play.sh --mode server
# Or run a shared website/game server:
python3 -m backend.server --host 127.0.0.1 --port 9900
```

Open `http://127.0.0.1:9900/` for the homepage or `/play.html` for Ruffle.
To connect the desktop client to that server:

```sh
./play.sh --mode server --server-url http://127.0.0.1:9900 --profile Alice
```

## Preserved inputs

`bin/base/boufbowl-client-1.9.6.swf` is the required, previously patched build
input. Generated clients and media are ignored. The simulator bundle and
extracted protocol contracts remain because their external source trees are
absent from this checkout. Keep private keys, passwords, databases, and local
captures outside Git.

Missing character bodies use Crâ of the same gender; unavailable stadium models
use Farmstead geometry. Character identities and class rules are retained.
Exact historical server odds and class powers were not recovered; the replacement
rules are configurable and experimental. This is an independent fan restoration.
