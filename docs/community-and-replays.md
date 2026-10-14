# Community, rankings, history and replays

Open **Server → Community**, or **Play → Community**. The same controls work
with anonymous device profiles and optional accounts. Two machines must connect
to the same backend to share rankings, friends, chat and live matches.

- **Friends:** click a listed nickname or enter one, then Add, Accept, Reject,
  Remove, Cancel, Block or Unblock. Requests need acceptance; crossed requests
  accept the existing request. Accepted friends show online status and active
  match IDs. Message, Challenge and Spectate act on the selected nickname.
- **Rankings:** rating, rank and W/D/L come from saved results. Click a nickname,
  or enter it and use Find player. Previous/Next page through all saved players.
- **History:** every played or watched match has its score, players, stadium,
  phase, timestamps and recorded turn count. Click a match to select its ID.
  Watch replay plays the original animation messages. Save replay prepares a
  JSON export, then **Save JSON file** opens the file chooser. Open replay file
  plays an exported JSON file. Home exits playback. An exported file can also be played offline with
  `./play.sh --mode mock --scene-3d --fixture /path/replay.json`. Completed matches with no
  resolved turns, such as an immediate surrender, have no animated replay.
- **Watch:** list running matches, select a match ID and Spectate. Stop spectating
  leaves the room. Friends can also be watched by nickname. Reconnecting restores
  the current spectator room and any pending resolution. Spectators see the
  match's chat and live scenarios but cannot submit orders or advance authority.
- **Messages:** select a nickname and Refresh to load the last 50 persisted
  private messages. Older messages pages backward; Refresh returns to the latest
  conversation. Send writes a message and reloads the conversation. The original
  chat also delivers private messages live.
- **Channels:** subscribe to one or more of `fr,en,de,es`, separated by commas.
  These are independent global rooms. Match chat includes both teams and
  spectators, and disappears on leaving or match end. The original chat supports
  language join/part and private conversations. `/ignore` and `/unignore` use
  persistent server blocks in connected mode.

Long lists scroll inside the text area. Community lists refresh on opening or
Refresh; original chat and matches continue polling live. Presence expires after
30 seconds without a request. Friend relationships, requests, blocks, language
subscriptions, messages, results and replay access survive server restarts.
Both sides' blocks prevent private messages, friend requests, challenges,
spectating and matchmaking against one another. Global/match message delivery
filters blocked senders. Blocking removes the relationship, cancels pending
invitations and ejects a blocked spectator. Unblocking does not restore a friendship.

## Rankings policy

The home card receives real rank/league fields with its W/D/L data. The
replacement service has one local league (wire league 1), split into groups
of 100 players for the original ladder's navigation. Original nickname/self
searches select the correct group and scroll to the target; nonexistent names or
unsupported groups return the original ladder error message. The Community
panel pages 20 entries at a time. Sorting is rating descending, then nickname.
Wins award +20 rating, losses subtract 20 (minimum zero), and draws leave rating
unchanged. Only distinct human opponents paired by the normal or tournament
queue count toward ranked rating and the top-level W/D/L counters. CPU results
use `statistics.practice`; arranged challenges use `statistics.casual`. Both
remain in history and receive exactly one result entry. Match source/mode is set
by the server; client-provided ranked flags cannot opt in. Tournament points also
require a ranked match created by the tournament queue.
There are no fabricated historical promotion thresholds or seasons. Rewards
are inserted once per participant; playback and exporting award nothing.

## Storage and replay behavior

SQLite schema 8 creates a fresh development database. Opening an older version
clears all application tables, including accounts, matches, turns and statistics.
There is no archive or historical migration. Reopening a current schema-8 database
keeps newly created data. The previous development database and saved replay
export were deleted for this reset.
New matches record creation/end timestamps, surrender side and their match-end
packet.

Turns are automatically saved with initial state, orders, deterministic seed,
rule snapshot, simulation result and original-client resolution messages. No
manual save is needed for server-side recording. Completed exports include full
records and animation envelopes and can be played without the simulation worker.
New turns draw independent private random seeds; a seed disclosed for an earlier turn cannot derive a later turn's seed.
Completed turn seeds remain in their recorded data for verification.
Participants retain replay ownership when an opponent is blocked. Previously
registered spectators can export watched matches while permitted by block policy;
unrelated profiles cannot. Active matches can export a snapshot of recorded
turns (`completed: false`), but these exports contain playback envelopes only:
`records: []`, `audit_available: false`, and no raw seeds, state hashes or pending
orders. Full audits unlock when the match ends; these snapshots are not final results. The History panel
advertises replay availability for ended matches with at least one recorded turn.

`POST /api/replay` accepts `session`, `match` and optional `verify`. Verification
is available only after match completion (`REPLAY_ACTIVE` otherwise),
re-simulates against the installed engine and can reject old versions; playback
of the saved envelopes does not require that verification. Replay uses spectator
mode. The patched client maps animation completion in spectator mode; replay
acknowledgements stay in the local playback harness, while live spectator
acknowledgements are ignored by the authority. Playing a replay is blocked while
participating in or watching a live match. Replay initialization restores the
first period instead of reusing the match's final placement orientation, and the
recorded match-end winner/surrender/rankings are preserved.

## Community API

Authenticated `POST /api/community` accepts `session` and `action`:

| Action | Additional fields | Behavior |
| --- | --- | --- |
| overview | none | Friends, incoming/outgoing requests, blocks, presence, subscriptions and spectator room |
| friend | verb, nickname | add/accept/reject/cancel/remove/block/unblock |
| rankings | offset or nickname | 20 entries, global ranks, total and next-page flag |
| history | offset | 20 owned or watched match summaries |
| live | offset | 20 available running matches |
| spectate | match or nickname | Join a live room and record replay access |
| stop_spectating | none | Leave room and remove match chat |
| channels | languages, optional language | Persist global subscriptions and preferred language |
| messages | nickname, optional before | Last 50 messages in your private conversation, ascending; cursor pages backward |
| message | nickname, message | Persist and deliver a private message |
| report | nickname, reason | Save an operator report, limited to one per minute |

Mutation requests accept a stable `request_id`; retries return their saved receipt
and do not duplicate a message/report. The client supplies one. Game commands
retain their existing mandatory request IDs. Messages are limited to 500 characters
and one per second per sender; friend lists/requests are limited to 200 relations.
The API never exposes another profile's sessions, account credentials or private
conversations. Original protobuf chat reporting now stores a report and optionally
acknowledges it. Administrator broadcasts and external authentication remain disabled.

Review reports locally:

```sh
python3 -m backend.manage --database /path/backend.sqlite reports --limit 50
```

Reports are stored for the server operator; submitting one does not imply an
automatic ban or external delivery. There is no public administrator API.

## Validation and remaining scope

`tests/test_community.py` covers durable friendships, crossed requests, block
policy, queue isolation, language subscriptions and routing, private history,
spectator reconnect/acknowledgements/ejection, completed match history, replay
access, ranking search beyond 100 players, presence expiry, reporting and retry
safety. `tools/smoke_community.py` exercises the native desktop controls and saved
3D replay; `tools/smoke_human_match.py` covers the two-client human match path.

Historical paid brackets, seasons/promotions, account email delivery, external
Ankama/Facebook authentication and payment flows remain outside the local service.
Exact historical class abilities and probabilities remain unrecovered and use
the documented configurable replacements. Android still requires a reachable
Linux backend; Android runtime/device validation remains pending.

The recovered game protocol audit leaves four requests without local execution:
`X_GAMING_WRAPPER`, `LINK_FACEBOOK_ACCOUNT`, `MSG_ALL_REQUEST` and
`MODERATION_REQUEST`. They belong to external authentication/social linking or
privileged administration and fail explicitly. Every recovered chat request now
has a local implementation, including reports. Account login, friendships, blocks,
match history and replay controls use the documented replacement HTTP API.

## Client responsiveness and regression fixes — 2026-10-14

Event polling uses `wait_ms:1000`: the server wakes the waiting poll immediately
when a transaction saves an event, and the client starts the next poll without a
500 ms timer. The wait releases the database lock. Human turn resolution still
requires both players' orders; loading original 3D animation assets can also take
several seconds. The client hides the opponent-waiting modal when a scenario arrives.

Every replacement HTTP request has a six-second application deadline. It returns
`REQUEST_TIMEOUT`, releases the command queue and ignores late responses. This
limit does not cancel matchmaking. The Windows Flash player under Wine exits when
`URLLoader.close()` aborts a pending load, so the client detaches the completion
handler instead; the underlying connection may finish later. A timeout does not
undo a mutation already accepted by the server; refresh its state before retrying.

Original chat initialization now creates Private and Information channels before
loading General subscriptions. `/whois` and the Information action open a public
player summary. Spectate is shown only for a spectatable active match, including
in the original nickname menu. The toolbar keeps an 80 px right margin on resize.

Club palette changes clamp all three selected color indices before notification,
including switching from the ten-color default to a five-color palette. Match
creation freezes contrasting team kits; both viewers, character models and replays
use those same colors. Later club edits affect subsequent matches.

`tools/smoke_client_regressions.py` checks first-login original private chat, player
information, active-match spectate visibility, palette switching/saving, two-turn
Frigost 3D playback and six-second retirement with ignored late responses.
