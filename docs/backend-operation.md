# Replacement server and database

Run `./play.sh` (default server mode) or `./play.sh --mode server`. The launcher
starts the local service, asset server and original Flash client. Use the toolbar
**Play** button for a CPU match or resume a saved active match. The original Play
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

Profiles use random device bearer sessions, with only token hashes stored in
SQLite. Flash SharedObject retains the device token. A nickname selects a device
profile; it is not a password or ownership proof. New devices create separate
profiles. Ankama accounts, payments and Facebook linking are intentionally not
recreated. Customization is free and class statistics are enforced by server
configuration. Only owned roster identities can be edited.

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
fields; only participants can export their match. Replay does not change results
or statistics. Verification compares engine version, final state hash and events.
An engine upgrade that changes those must preserve the prior worker for old
record verification. Records include their complete rule snapshot.

General/private/match chat uses the recovered original chat protocol. Messages
are persisted; private recipients and match participants are checked. One-second
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
