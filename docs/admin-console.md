# Administrator console

Open `/admin.html` for server statistics, `/moderation.html` for moderation, and
`/tournaments.html` for competition management. The header links all three pages.
Sign in with an existing account or device session. The session is kept in the
current browser tab's session storage so navigation does not require another
login. Sign out clears that console session from the tab.

Assign roles locally, using the database used by the running server:

```sh
python3 -m backend.manage --database /path/to/backend.sqlite role "Nickname" admin
```

## Moderation

Administrators and moderators can review the message stream. It polls every two
seconds, pauses when the tab is hidden, supports a manual pause, and filters by
message text, player, channel type and public-room language. Newest messages are
first; load older messages to review history. The counts and hourly activity
chart cover the last 24 hours across all channels, independently of filters.

Select a private message to see messages in both directions between those two
profiles. Select a match message to see that match's conversation, including
spectators. Conversation focus temporarily overrides search and channel filters.
Click outside the conversation panel, use Clear focus, or press Escape to restore
the filters. Player actions prefill the suspension form; reports can also select
a player for review.

Suspensions last one day, seven days, or indefinitely. Only administrators may
apply indefinite sanctions or sanction another moderator. The console requires
reviewing the target, duration and reason before applying a suspension, and
prevents self-suspension. Existing server sanctions reject subsequent requests,
remove matchmaking searches and forfeit active matches. Active suspensions can
be lifted. Player reports and the latest 50 moderation audit entries appear
alongside the feed. Actions go through the existing authoritative moderation
service; no role or sanction is enforced only in the browser.

## Tournaments

Only administrators can access competition management. Current, upcoming and
previous tabs show the latest 100 persisted events, their schedules, participant
counts, rating limits and progress. Selecting an event shows qualification and
round times, active match scores, rules, prizes and the top 20 standings. The
page refreshes every ten seconds.

The schedule builder publishes either a one-time event or an hourly, daily or
weekly series. A published schedule **replaces all upcoming occurrences and the
previous recurrence**. Current events and finalized results remain intact. The
start must be in the future and after any current event's scheduled end. Running
matches may delay later events. Publishing displays a review dialog explaining
the replacement before applying it.

Configure a stadium, league or qualification/knockout format, numerical minimum
and maximum player ratings, points, match and period turn limits, planning and
placement timers, class ability uses, and regeneration. Rating limits are checked
when joining the tournament queue. Match rules are copied into the match's rules
snapshot without modifying global or already-running match rules. Knockout
qualification and round durations must fit the event, and qualifying players
must fit the configured bracket capacity.

The champion's glory, influence and coin prize is customizable. Other places use
the existing reward bands. Awards require a completed human tournament game and
are credited once to the existing tournament wallet. These are game currencies.
The native client's reward artwork still uses the original reward codes; exact
custom amounts and special settings are shown in this console.

Schedules, snapshots and publication audit records persist in SQLite. Tables and
chat indexes are added to schema 8 without resetting existing schema-8 data.
Password login follows the server's existing TLS restrictions.

## Verification

```sh
python3 -m unittest tests.test_admin tests.test_browser_server tests.test_community tests.test_tournament_lifecycle tests.test_tournament_rounds -v
```
