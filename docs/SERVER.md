# Server and configuration

Python provides the HTTP API and SQLite persistence; Bun runs the bundled match
simulator. The SWF presents server outcomes and acknowledges playback.

## Run and connect

```sh
python3 -m backend.server --host 127.0.0.1 --port 9900 \
  --database /path/to/backend.sqlite
curl -fsS http://127.0.0.1:9900/api/health
./play.sh --mode server --server-url http://127.0.0.1:9900 --profile Alice
```

Use one shared backend for multiple clients. For LAN clients, bind to `0.0.0.0`
and use the server's LAN address; `127.0.0.1` on Android refers to the phone.
Internet deployment needs HTTPS through a reverse proxy or the server's
`--tls-cert` / `--tls-key` options. Remote password operations require TLS
or the trusted local proxy connection.

Without `--server-url`, the desktop launcher can start an embedded backend on an
automatic loopback port. Closing the launcher stops that embedded service.
Saved client connection settings can select another server; explicit launch
options override them. `play.sh` does not rebuild or update files.

## Settings and data

| File/section | Purpose |
| --- | --- |
| `resources/game_config.json` → `general` | Language, startup mode, cinematics, queues, tournaments, progression |
| `rules` and `stadiums` | Match timers/periods, class stats/powers, simulation, stadium overrides |
| `resources/palettes.json` | Character and club colors |
| `resources/stadium_art.json` | Source textures and generated stadium mappings |
| `resources/offline_characters.json` | Roster identities |
| `resources/site.json` | Hosted server, contact, and download links |

```sh
python3 -m tools.game_config
python3 -m tools.game_config --stadium KARA
```

These commands validate/print effective configuration. Client/package builds
apply generated resource changes. Restart the backend after configuration edits;
existing matches and replays keep their saved rule snapshots. Five active players
per side, ten-player rosters, and three regular-order elements are protocol limits.

Class powers/probabilities are experimental replacements, not recovered historical
balance. The default `restoration-2012-v2` profile adds role, restart, pass and
Ecaflip corrections plus explicitly provisional movement, combat, pickup, status
and reconnect policies. See the [rulebook](RULEBOOK.md) and [choices](RULEBOOK_CHOICES.md)
for source IDs, compatibility switches and remaining gaps. New rosters allow at
most three players per role across all ten members; older invalid clubs must be
edited before entering a new match. AIR enables intended airborne receptions, and FEU enables opposing
interception attempts; a live, unstunned
ball carrier scores beyond the opponent's line. Regeneration restores one HP at
the configured interval. Missing bodies/stadiums use the fallbacks in the README.

CPU teams coordinate carries, moving passes, switches, screens, wide support and
defensive cover. Roles account for strength, agility, precision, endurance and
current health. Movement risk is allowed when the tactical reward justifies it;
it is charged as a possession/recovery risk rather than treated as free range.
Defenders estimate reachable low parts of likely enemy passes from public field
state. They never read submitted opposing orders or future random draws.
Generated orders include a `cpu_plan` audit with roles and estimated pass timing;
these are predictions, not guaranteed outcomes. Saved orders are replayed as
recorded rather than replanned with a newer CPU policy.
Each CPU match uses the starter team with its first five characters shuffled,
random kit and blazon colors, and a random blazon charge and background. The CPU
primary color contrasts with the human team's color. These choices are saved
with the match and remain stable for reconnects and replays.

The default database is
`$XDG_DATA_HOME/boufbowl-offline/backend.sqlite`, falling back to
`~/.local/share/boufbowl-offline/backend.sqlite`.
It stores profiles, clubs, sessions, matches, turn records, chat, results, and
administration data. Schema 8 persists across restarts; incompatible development
schemas can be cleared at startup, so back up before upgrades.

Device sessions and optional local accounts are separate from Ankama accounts.
Nickname text is not authentication. Commands enforce ownership, phase, and
request IDs; the server owns outcomes. Active replay exports omit audit seeds
and unfinished orders. Human queue/tournament results are ranked; CPU practice
and arranged challenges use separate result ledgers.

## Administration

```sh
python3 -m backend.manage --database /path/to/backend.sqlite role "Nickname" admin
python3 -m backend.manage --database /path/to/backend.sqlite role --account "Username" admin
python3 -m backend.manage --database /path/to/backend.sqlite stats --days 30
python3 -m backend.manage --database /path/to/backend.sqlite reports --limit 50
```

| Page | Use |
| --- | --- |
| `/admin.html` | Server activity and diagnostics |
| `/website-activity.html` | Website interest, assets, and download counts |
| `/moderation.html` | Chat/report review, audited suspensions |
| `/tournaments.html` | Schedules, rules, standings, prizes |
| `/assets-admin.html` | Private resource-proposal review |

Sign in with an account/device session; server-side roles control access.
The role command looks up a game nickname by default. Use `--account` to look
up the profile linked to an account username; these names can differ when an
account is registered using an existing device session. The account/profile
must already exist in the running server's database. No server restart is needed.
Only administrators manage tournaments and resource approvals. Publishing a
tournament schedule replaces upcoming occurrences, while current events/results
remain. Match rules are frozen per match; rewards require eligible human results.

Use HTTPS for remote bearer sessions, keep the database/backups private, and
bound public request traffic at the proxy. The current server does not provide
general retention/purge or full protection against alternate-account farming and
resource exhaustion. Privacy drafts describe these limits without implementing
missing controls.

## Backup and replay

```sh
mkdir -p .local
python3 -m backend.manage --database /path/to/backend.sqlite backup /path/to/backup.sqlite
python3 -m backend.manage --database /path/to/backend.sqlite \
  replay 1 .local/match-1.json --verify
./play.sh --mode mock --scene-3d --fixture .local/match-1.json
```

Backup uses SQLite's consistent backup API. To restore, stop the service, retain
the current database, remove stale WAL/SHM companions, and replace it with the
backup. Preserve device credentials needed to regain profile access.
Replay verification compares recorded engine version, state hashes, and events;
changed engine semantics may require the earlier worker.

For loading/playback problems, inspect `/api/health`, server output, and
`~/.local/state/boufbowl-tutorial/{http,mock,wine}.log`. Confirm the process's
working directory and client/server revision. A health response or fixed `1.9.6`
SWF filename alone does not identify the deployed build.
