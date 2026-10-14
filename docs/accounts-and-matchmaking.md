# Accounts, matchmaking and human matches

Anonymous device profiles remain the default. The **Server** panel's **Device**
field selects the local device-profile slot; it is not an account username. Open
**Server → Account** from the lobby to create/link an account, log in, change a
password, recover an account, log out, or return to the saved device profile.

Creating an account links the currently connected anonymous profile. Clubs,
customization, statistics, recorded results and active match identity are retained.
The username is a separate login identifier; challenges use the public player
nickname shown in the game. Passwords require 10–128 characters. Usernames require
3–32 ASCII letters, digits, dots, dashes or underscores and are case insensitive.
Another device can log in with those credentials to restore the same profile.
Account switching in the client is available after finishing or surrendering a
match, preventing an old playback from sending commands for another profile.

Registration displays a random recovery code once. Save it privately. **Recover
account** uses username, recovery code and the new-password field. Recovery and
password changes revoke all existing sessions, issue a new session and replace
the recovery code. A lost registration response can be retried or followed by
login; changing the password generates a fresh recovery code if the first code
was not saved. There is no email dependency.

Logging out revokes the current account token and cancels its queue search; the
client returns to its saved anonymous device profile. Linking preserves that
existing trusted device token. Password change/recovery invalidate it along with
other old sessions. Passwords and recovery codes are never saved in client
SharedObjects; remembered access uses bearer session tokens. Private chat display
history and channel selections are cleared when switching accounts. Lobby chat
defaults to general; match chat becomes available only while playing. Device-mode logout does not silently
discard an anonymous player's only credential.

Passwords use random salts and PBKDF2-HMAC-SHA256 with 600,000 iterations, following
the [OWASP password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Only password hashes, recovery-code hashes and session-token hashes are stored in
SQLite. Failed authentication is throttled persistently per peer/username: five
failures within five minutes. Account responses never expose stored hashes.

## Shared server

Both players must connect to the same backend. For anonymous LAN play:

```sh
python3 -m backend.server --host 0.0.0.0 --port 9900
./play.sh --server-url http://SERVER_ADDRESS:9900 --profile Alice
```

Remote password requests require HTTPS. The standalone server supports TLS:

```sh
python3 -m backend.server --host 0.0.0.0 --port 9900 \
  --tls-cert /path/fullchain.pem --tls-key /path/private-key.pem
./play.sh --server-url https://YOUR_SERVER:9900 --profile Alice
```

Use a certificate trusted by each client and matching the server address. A TLS
reverse proxy may also terminate HTTPS in front of the loopback service. Loopback
password requests are allowed over HTTP for embedded desktop play and development.
The device-token option remains usable over the existing LAN HTTP setup. Android
connects to this same Linux backend; it does not host the server itself.

## Playing humans

**Play** in the top toolbar opens **Find opponent**, **CPU matchmaking**, search
cancellation and nickname challenges. Choose any enabled stadium or cycle to a
specific stadium before searching. The original matchmaking Play request also
joins the human queue. CPU opponents are explicit; a search never silently falls
back to CPU. An existing active match makes the toolbar Play button resume it.

The persistent queue pairs distinct profiles with overlapping stadium choices.
Among compatible candidates, it prefers nearby ratings and earlier arrivals.
The initial rating window is 200 and widens by five points per waiting second.
Polling refreshes queue presence; searches expire after 30 seconds without a
heartbeat or five minutes in total. Canceling removes the player immediately.
Repeat joins preserve arrival priority, and two devices using the same profile
cannot match each other. A fresh poll does not revive an expired search.

Edit `general.matchmaking` in `resources/game_config.json` to adjust
`rating_window`, `widen_per_second`, `heartbeat_timeout` and `search_timeout`.
Queue entries survive a server restart while their presence timeout remains valid.
Pair creation and queue removal are atomic, including concurrent joins. Creating
any match removes both participants from queues and cancels unrelated invitations.
Switching between a search and a challenge cancels the previous search/invitation.
Pending invitations are sent again when the invited player logs in.

Human matches use both participants' owned rosters. Both placements and orders
are collected; first submissions are immutable, including reconnect retries.
Resolution is broadcast to both clients. Both human acknowledgements are required
before advancing, with the existing deadlines handling disconnects. Reconnects
restore the active phase or replay a pending resolution. Each human receives one
persisted result and ranking update. CPU slots are not inserted into human matches.

## API and migration

`POST /api/account` accepts `action`: `register`, `login`, `password`, `recover` or
`logout`. Register can link an authenticated `session` or create a profile from
initial `clubs` and optional `nickname`. Login uses `username`/`password`; password
change also needs `session`/`new_password`; recovery needs `recovery_code` and
`new_password`; logout needs `session`. Successful authentication returns the
normal hello snapshot, a new session and `auth_mode`. Newly generated recovery
codes appear only in that response.

Authenticated `POST /api/command` operations include `queue_join` with optional
`stadiums`, `queue_leave`, `cpu_match`, and `challenge` with `nickname`/`stadium`.
Hello, command and poll responses include `matchmaking` status. Existing original
protobuf match requests, cancellation and challenge answers remain supported.

Database versions 1–3 migrate automatically to version 4. Existing profiles,
device tokens, clubs, matches and results are preserved. The new tables store
accounts, failed-authentication buckets and queue entries; sessions gain a kind
field. Standard SQLite backup/restore includes all account and queue state.

Validation includes account migration/login/linking/recovery/revocation, TLS API
requests, queue expiry/cancellation/rating/compatibility/concurrency and complete
human matches. `tools/smoke_human_match.py` runs two actual Flash clients: separate
account logins, matchmaking, two native replay turns each, four acknowledgements
and two saved results. Run it under Xvfb as a module. Native CPU regression also
passes. Android remains package-verified; no device is attached.

### Tournament matchmaking and team selection

Both the original Home Play/Tournament buttons and the toolbar Play button open
the shared controls. **Find opponent** joins the human queue; **CPU matchmaking**
starts a CPU match only when explicitly selected. **Find tournament** joins the
configured tournament's separate human queue at its fixed stadium. There is no
automatic CPU fallback for normal or tournament searches. Cancel search leaves
either queue. A profile has one queue entry, so switching queue type replaces it.

Pairing occurs under one database transaction. Entries belonging to players in
an active match are removed, and a player paired earlier in that transaction is
excluded from subsequent pairings. Blocked players cannot pair. Tournament
searches expire on heartbeat/search limits or when the tournament closes;
reconnecting restores a still-valid search. Schema 4 adds a nullable tournament
ID to queue entries while retaining old normal searches and device tokens.

The Play dialog displays **Team** and offers **Change team**. The chosen owned
`club_id` accompanies queue, CPU, challenge and tournament requests, so the server
selects that club before creating/pairing the match. This uses the stored customized
roster, not the offline seed team. `select_club` also selects an owned club explicitly;
unowned IDs fail and an active match prevents changing selection.
