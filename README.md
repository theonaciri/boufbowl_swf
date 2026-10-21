# Boufbowl

Restored Flash client with a Python/SQLite backend and a Bun match simulator.
The game supports human and CPU matches, clubs, chat, tournaments, and replays.
The French website serves the browser client, downloads, and restoration tools.

## Start here

- [Build](docs/BUILD.md): prerequisites, desktop SWF, Android, packages, and checks.
- [Website](docs/WEBSITE.md): assets, portraits, video exports, and delivery.
- [Binary](docs/BINARY.md): find functions, export AS3/assets, and patch the SWF.
- [Server](docs/SERVER.md): configuration, accounts, administration, and backups.

## Build the website

Install the [system prerequisites](docs/BUILD.md#tools-and-inputs), then run from
the repository root:

```sh
bun run build
```

The build finds/downloads FFDec, prepares a missing game client and website media,
and generates **`.local/website/dist/`**. Serve that folder with a static web
server; [Hosting](docs/HOSTING.md) explains Nginx and the separate game API.
First builds can take a long time; existing media is reused on later builds.
You do not need `FFDEC_JAR`, manual file copies, or a separate legal-page build.

For native desktop development (with Wine and the standalone Flash player):

```sh
bun run build:game
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
