# Replacement server and database

Run `./play.sh` (default server mode) or `./play.sh --mode server`. The launcher
starts the local service, asset server and original Flash client. Use the toolbar
**Play** button for human matchmaking, explicit CPU games, challenges or resume. The original Play
menu supports challenges by saved player nickname; the recipient must accept.
`--mode menus` and `--mode tutorial` keep the standalone preview/tutorial flows.

For a shared server, run:

```sh
python3 -m backend.server --host 0.0.0.0 --port 9900
./play.sh --mode server --server-url http://SERVER_ADDRESS:9900 --profile Alice
```

The Linux package bundles Bun and the compiled simulation worker. Development
builds use `~/.bun/bin/bun` or Bun on PATH. Python uses its standard library.
Android connects to the same service: enter the computer's LAN address in the
connection panel (127.0.0.1 on a phone means the phone). The APK includes assets
and the original client; the authoritative Python/Bun server runs on Linux.
HTTP bearer transport is intended for local/LAN use. Put the service behind an
HTTPS reverse proxy for Internet access and use its HTTPS URL in the client.

Profiles support anonymous device bearer sessions and optional username/password
accounts. Token hashes are stored in SQLite; Flash SharedObject retains tokens.
A device nickname is not a login credential. Account registration can link the
current anonymous profile; password login restores it on another device. Recovery
codes and password changes revoke older sessions. Remote password operations
require HTTPS. See [accounts and matchmaking](accounts-and-matchmaking.md) for
TLS setup, account controls, queue settings and migration. Ankama accounts,
payments and Facebook linking are not recreated. Customization is free and class
statistics are enforced by server configuration. Only owned identities are editable.

The default database is `$XDG_DATA_HOME/boufbowl-offline/backend.sqlite`, or
`~/.local/share/boufbowl-offline/backend.sqlite`. Override it with `--database`.
It contains profiles, clubs, sessions, challenges, spectators, chat, match
checkpoints, ordered events, command receipts, results and full turn records.
WAL, foreign keys and transactions protect updates. Commands have stable request
IDs; retrying cannot create a second match or reward a result twice. Deadlines
advance even when nobody polls. Restarting the server and reconnecting restores
placement/orders or replays a pending resolution from its initial state.

Create a consistent backup while the service is running:

```sh
python3 -m backend.manage --database /path/backend.sqlite backup /path/backup.sqlite
```

For restore, stop the service, preserve the current database, remove its stale
`-wal` and `-shm` companions, and copy the backup to the selected database path.
Keep the matching device SharedObjects to retain access to existing profiles.

Export a recorded match and reproduce its deterministic outcomes:

```sh
python3 -m backend.manage replay 1 /tmp/match-1.json --verify
./play.sh --mode mock --scene-3d --fixture /tmp/match-1.json
```

Authenticated `POST /api/replay` accepts session, match and optional verify
fields; participants and registered spectators can export their match. Replay does not change results
or statistics. Verification compares engine version, final state hash and events.
An engine upgrade that changes those must preserve the prior worker for old
record verification. Records include their complete rule snapshot.

General/private/match chat uses the recovered original chat protocol. Global
rooms are isolated by language; private conversations are persisted and scoped
to the two players. Match chat includes participants and spectators. Persistent
blocks filter delivery and invitations. One-second
message spacing is enforced. The original leaderboard reflects saved results.
`general.tournament` configures a free local points league, its stadium, active
time window (Unix seconds), and win/draw/loss points. Tournament match requests
start CPU matches and count completed results; this is the replacement league
policy, rather than the historical paid bracket system.

The replacement engine has its own deterministic combat/probability semantics.
Client field geometry, element controls, original interaction playback and
stadium turn limits are recovered. Exact historical server probabilities and
class ability effects were not present in the client. Ability entries retain
`verified: false` where they are configurable provisional effects. Editing the
balance file changes future matches; active matches retain their saved rules.
Unavailable stadium models render the supplied Farmstead model with the selected
stadium's rules. Missing regular/special animated skins use Cra of the same gender;
class identity, stats, abilities, and original portrait artwork are retained.

The **Server** toolbar button opens connection settings and a device profile-name
field. Successful selections are remembered. On desktop, an empty URL selects
the embedded local backend; Android needs a reachable server URL. An explicit
`--profile` or `--server-url` overrides the saved selection for that launch.

Use **Server → Community** for friends, rankings, match history, saved replay
playback/downloads, live spectating, private conversations and subscriptions.
See [community and replays](community-and-replays.md) for API and operator report review.
