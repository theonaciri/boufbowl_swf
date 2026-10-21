# Boufbowl

Restored Flash client with a Python/SQLite backend and a Bun match simulator.
The game supports human and CPU matches, clubs, chat, tournaments, and replays.
The French website serves the browser client, downloads, and restoration tools.

## Start here

- [Build](docs/BUILD.md): prerequisites, desktop SWF, Android, packages, and checks.
- [Website](docs/WEBSITE.md): assets, portraits, video exports, and delivery.
- [Binary](docs/BINARY.md): find functions, export AS3/assets, and patch the SWF.
- [Server](docs/SERVER.md): configuration, accounts, administration, and backups.

## Build

Install the [system prerequisites](docs/BUILD.md#tools-and-inputs), then run from
the repository root:

```sh
bun run build                 # Game client and runtime files only
bun run build:website         # Static website and any missing website media
bun run serve:website         # Serve the built website at http://127.0.0.1:9900
```

Both commands find/download FFDec when needed. The game build does not render
website media or start Chromium. The website command reuses the game client,
preparing it first only if missing, and generates **`.local/website/dist/`**.
First website builds can take a long time; later builds automatically refresh changed media and reuse unchanged exports.
Serve that folder with a static web server; [Hosting](docs/HOSTING.md) explains
Nginx and the separate game API. No manual file copies or legal-page build needed.

For native desktop development (with Wine and the standalone Flash player):

```sh
bun run build
./play.sh --mode server
```

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
