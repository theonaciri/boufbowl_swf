# Restored frontend features

The unused-feature audit is implemented except advanced training, which was
explicitly excluded. Original sources and artwork remain unchanged; shared
ActionScript patches are used by Linux and Android builds.

## Leagues and seasons

**Server → Leagues** shows qualification, rating thresholds and season history.
The original ladder displays the five league badges and league-specific groups
of 100. Three ranked human results qualify a player by default; CPU practice and
nickname challenges do not qualify or change ranked rating. Promotion/relegation
follows rating: Piou below 1000, Tofu 1000, Wabbit 1100, Abraknyde 1200 and
Craqueleur 1400. These are replacement thresholds, configurable under
`general.progression`, not recovered historical server settings.

Seasons are optional and disabled by default. Enabling
`general.progression.seasons` uses its UTC start time, duration (default 28 days)
and initial rating. Rollover archives ranked counters/rating, resets qualification,
and retains wallet, cosmetics, practice/casual results, lifetime results and match
history. A match finishing after rollover credits the season in which it began.

## Wallet and cosmetics

**Server → Wallet** displays glory, influence, coins, purchases and tournament
awards. Six palette unlocks reuse existing assets; catalog names and prices are in
`resources/cosmetic_catalog.json`. Prices and balances are server-owned. Purchases
are atomic, retry-safe and cannot charge twice for an already-owned item.

`general.economy.free_customization` defaults to true: all customization stays
available, and Claim records ownership without charging. Set it to false to
require catalog ownership in team/character customization. Existing base palettes
remain free. Tournament awards fund the wallet; no real payments or external
Ankama services are used.

## Tournaments

The original **Tournament** button opens the original stadium, rules, countdown,
reward, ranking and podium screens. The default hourly tournament has a 15-minute
qualification window, four qualifiers, 15-minute semifinals and a 15-minute final,
then a 15-minute gap. Stadiums rotate through all nine configured grounds.

The server fixes opponents and advancement. Registration without completing a
human tournament match cannot qualify or earn awards. Qualification seeds pair
first/last and second/third; a draw advances the higher seed. Odd entries receive
byes. A walkover requires a current queued search and recent presence. No champion
means no awards. Knockout losers and players who did not qualify see the original
eliminated state. A player cannot replay a completed round or face a different
opponent. CPU opponents are excluded.

Started matches may finish after a round deadline. Advancement waits for those
results and shifts remaining rounds and the next tournament to avoid overlap.
`format: "league"` retains the points-only alternative. See
[tournament lifecycle](tournament-lifecycle.md) for the protocol and settings.

## Replays

**Server → Community → History → Watch** opens saved playback. Controls provide
pause/resume, speed 0.5/1/2/4 and previous/next turn. Scene and cinematic clocks
follow pause/speed. Seeking recreates the match context from the recorded pre-turn
field snapshot, including period, side, score and Zobal masks, then plays the
remaining recorded scenarios. A paused seek remains paused.

Replay controls do not submit live orders, modify results or grant access to
another player's private replay. Active exports remain playback-only, with seeds
and audit records withheld until completion. Live spectating uses the live feed
rather than replay controls.

## News and account/community presentation

**Server → News** uses original `LoginMotdUI` artwork with configurable localized
announcements and current tournament/progression data. `general.news` has the four
existing languages. Obsolete external paid-tournament announcements were replaced.
Added screens and the top toolbar reuse original `SimpleButton` artwork and
`MessageBoxResizableTextUI` frames, including their bevels/shadows. Body text uses
embedded Verdana, with original Copperplate headings/buttons; cream surfaces, olive headings and input focus states follow
the existing interface. Wallet balances use original Bowlton reward tokens,
cosmetics have palette previews, and league rows use original league cubes.
Moderation separates reports, sanctions and audit views. Main labels are localized
in `resources/local_ui.json`; long button captions shrink to fit. Status notices
use the same palette, stay within half the screen and dismiss after eight seconds.
Anonymous device access remains available.

## Moderator role

Roles are player (default), moderator and admin. Only a local operator can grant
roles; the client cannot self-promote:

```sh
python3 -m backend.manage --database /absolute/path/state.sqlite role "Nickname" moderator
python3 -m backend.manage --database /absolute/path/state.sqlite role "Nickname" admin
python3 -m backend.manage --database /absolute/path/state.sqlite role "Nickname" player
```

Use the database path printed by the running backend. Reconnect after changing a
role. **Server → Moderation** provides player reports, active sanctions and audit
history, with nickname/reason/duration controls for kick, ban, mute, unban and
unmute. Original moderation protocol requests/results are also supported.

Kick removes searches and forfeits an active match; its default duration is 30
seconds. Ban blocks authentication and forfeits an active match; mute blocks both
public and private chat. Ban/mute default to 900 seconds; temporary sanctions may
last up to seven days. Duration zero requests a permanent sanction and requires
admin. Moderators cannot penalize moderators/admins. Every action is authorized
on the server and audited. Revocation is audited too.

Device tokens remain valid after a temporary sanction expires, preserving the
anonymous profile; the player can reconnect. Sanctions are profile-based and do
not prevent somebody from creating an unrelated anonymous profile. See
[abuse review](cheating-and-abuse.md) for remaining anti-abuse risks.

## Verification and packages

All 163 automated tests passed. Tests cover qualification, league filtering, season rollover and late
results, currency enforcement/retries, trusted roles, sanctions and bracket
boundaries. Native Flash checks exercised wallet purchase, original news artwork,
moderator mute, replay pause/speed/seek, qualification/round countdowns,
eliminated state and final podium. Evidence is under
`evidence/frontend-restoration/` and `evidence/knockout/`.

Shared patches are included in the Linux and Android packages. Android has build,
archive and signature checks; the current flows have not been tested on a device.
Advanced training remains hidden and was not implemented.


## Toolbar and connection recovery

The toolbar contains Home, Quit and Club (Server in English). Redundant Play,
Teams and Tutorial toolbar buttons are removed; use the original home Play button
and original game screens. Club opens only when clicked, including after startup
connection failures. Unknown/expired anonymous credentials renew before wallet
and league queries; expired account credentials require account login instead.
`tools.smoke_session_recovery` checks startup, expiry during wallet/league requests
and account re-login in the native client.
