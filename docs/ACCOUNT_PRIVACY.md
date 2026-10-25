# Self-service account privacy

Entry point: `Accounts.account` → `backend/account_privacy.py`, via existing
`POST /api/account` (remote calls require TLS; JSON responses use `no-store`).
Game UI: Club / Account → **Mes données / Supprimer**, shared by Android and
desktop/browser clients. No new webpage, static-page list or codegen changes.

## Authentication and export

`action: "export"` authenticates `session`; a supplied username/profile ID cannot
select another owner. For a linked account, `password` must match that account,
even when the session is a device session. Bad-password attempts use the existing
peer/username five-attempt, five-minute throttle and persist across API failures.
An unlinked device profile has no independent password/recovery identity: session
possession is its only authentication. Lost/expired or sanctioned sessions need
the documented support route, not a weaker identity fallback.

The export is a positive selection of personal columns, never a SQLite, event,
command, replay or match-state dump. It includes clubs/statistics, personal match
results, sent messages (without recipient identities), public friend nicknames,
own blocks/channels, tournament participation/rewards, purchases/cosmetics,
season standings, daily activity (including pending memory counters), submitted
reports and session kind/expiry. It excludes received messages, other accounts,
moderation internals, passwords/hashes/salts, recovery codes, session/client
identifiers, opponent orders, and all simulation records/seeds. Detailed client
diagnostics, visits and moderation records are outside this convenience export;
use the policy's access-request channel for those categories.

## Deletion transaction and retained records

`action: "delete"` additionally requires exact `nickname` and
`confirmation: "SUPPRIMER"`. An active participant match, including an in-flight
simulation/resolution, rejects the action before mutation. Export is permitted
by the API during matches; the game account panel currently opens outside matches.

One SQLite transaction cancels queue/challenges/spectating; deletes credentials,
all profile sessions (retaining unowned revocation digests as described below), friendships/blocks, sent chat and incoming direct chat,
reports involving the profile, subscriptions, personal event/command caches,
replay access, presence, watcher/intentions, roles, economy inventory/ledger and
profile-linked tracking rows. Pending tracking caches are also removed so the
next flush cannot recreate erased activity. Waiting polls are notified and must
reauthenticate. Original profile ID is deleted, never reused.

A new non-login profile with a random UUID/pseudonym replaces retained foreign
keys in participants, results, tournament participation, season rankings and
admin attribution. Match/turn JSON, frozen standings and bracket IDs are scrubbed
and rekeyed; cached JSON/protobuf packets for other users are scrubbed too. Own
historical roster/club names become generic. Scores, mechanics, appearances,
timestamps, historical score counters and brackets remain to preserve opponents'
history, replay verification and tournament ordering. A future unplayed bracket
slot uses normal absent-player/walkover rules. Other people's sanctions remain;
deleted actors/reasons are dissociated and administrative detail text is cleared.
This is pseudonymization, not a claim of irreversible anonymity.

The UI clears only locally saved session tokens owned by the deleted profile,
stops polling/recovery, and does not automatically register a replacement device
profile. Other independent device/account credentials remain saved. Local/offline
clubs are not erased. An explicit later login without credentials creates a
separate profile. If deletion's response is lost, the client suppresses automatic
invalid-session recovery; retry/status requires explicit interaction. `deleted_sessions`
retains only unowned token digests and original expiry times: `SESSION_DELETED`
blocks the automatic device-profile fallback on other devices too. Expired markers
are removed on subsequent deletions. No raw token or original profile ID is kept
in this security table.

Scope limits: existing downloaded replays/received copies, third-party free text,
infrastructure logs, SQLite WAL/free pages, backups, aggregate diagnostics without
profile ownership, and the independent asset-contribution database are not erased
by this action. Backup/log retention and support handling are operator policy,
not silently claimed by the UI. Short-lived auth throttle hashes have no reversible
profile ownership and are separate security state. The `deleted_sessions` table is additive; no destructive schema-version change.
Never bump schema version to deploy this feature.

## Focused verification

`python3 -m unittest tests.test_account_privacy -q`

Covers session ownership, linked-device password reauthentication, persisted
throttling, explicit device confirmation, token invalidation/no stale-token
revival, secret/opponent-data exclusion, active-game rejection, unrelated active
game preservation, FK dependents, cached encoded chat/rosters, memory tracking
flush, frozen standings, rollback, replay verification after rekeying, and the
actual HTTP route/no-store response. Root coordinates account/community/tournament
regressions and shared AS3 compilation. Client rendering is not validated by these
Python tests.

## Integration verification (0.3.0)

The focused privacy/account/community/results/tournament suite passed 65 tests.
Shared SWF and Android packaging compiled the account controls. In Ruffle against
an isolated SQLite backend, the account panel downloaded valid personal JSON;
explicit deletion removed the test profile and retained one revoked-session
marker. Production backend activation requires its separately authorized restart.
