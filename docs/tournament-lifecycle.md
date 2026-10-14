# Tournament lifecycle investigation

## Original client contract

Sources are under `../migration-work/scripts/scripts/`:

- `client/matchmaking/model/ServerTime.as` anchors time to server milliseconds
  and advances it using `getTimer()`, rather than trusting the local wall clock.
- `TournamentsModel.as` classifies future/running tournaments by start/end time,
  selects a relevant tournament and maintains boundary refresh timers. It supports
  only one running tournament. Past tournaments arrive in a separate message.
- `view/tournament/CountdownModel.as` updates every 200 ms and clamps at zero.
- `TournamentView.as` supplies stadium art/rules, progress gauge, future countdown,
  round countdowns, participant counts, podium, rewards, and past/future lists.
- `ReceiveTournamentClosedCommand` requests refreshed lists; the companion chat
  command adds a translated closure notification.
- `protocol/ScheduledTournamentData.as` contains absolute times, stadium, rewards,
  podium, own ranking, participant counts and closed flag, plus optional rounds.
- `TournamentReward` enums select labeled frames in the original reward artwork.
- Original text explicitly allows entry to close while in-progress matches finish;
  results only become final after those matches complete.

## Replacement implementation

The original Tournament button opens its native view. Server-owned scheduling
reuses original future/round countdowns, qualification/eliminated states, stadium
rules/artwork, participant counts, reward icons, podium, and current/past lists.
`ScheduledTournamentData` supplies original round time slots; supplemental round
metadata identifies qualification, waiting, played and bye states.

`general.tournament` defines UTC epoch `start_time`/`end_time`, `repeat_seconds`,
`upcoming_count`, `past_count`, `stadium_rotation` and original reward enum codes.
Defaults rotate all nine stadiums hourly: qualification 900 seconds, top four,
two rounds of 900 seconds, followed by a 900-second gap. Set repeat to zero for a
single event. `format: "league"` retains points-only tournaments; default
`format: "elimination"` adds server-owned qualification and knockout rounds.
`qualification_seconds`, `qualifying_top`, `round_count` and `round_seconds` must
fit the total duration and bracket capacity; configuration validates this.

Instances persist snapshots of rules, stadium, rewards and schedule. Config edits
do not rewrite scheduled instances; use a new base ID/start time for a new
schedule. Startup creates the current occurrence and upcoming events, rather
than inventing results for previous unplayed tournaments. The original client
supports only one running tournament.

Qualification points use completed trusted human tournament-queue matches only.
Registration alone does not qualify. Fixed seeded opponents pair first/last,
second/second-last; an odd middle entrant receives a bye. Draws advance the higher
qualification seed. Queues enforce current round, eligibility, fixed opponent and
one result per round. There are no CPU tournament opponents. Walkovers require
a currently queued, recently present player. Eliminated, played and bye entrants
receive the appropriate original waiting/eliminated presentation.

Round deadlines cancel outstanding searches, using the original cancellation
message. Started matches remain playable; advancement waits for their results.
Late completion shifts remaining rounds and upcoming events to preserve a gap
and prevent simultaneous running tournaments. Final closure freezes standings,
credits rewards once and sends `TOURNAMENT_CLOSED` to refresh original lists/chat.
No champion means no awards. The alternate league format likewise counts games
started before closure even if they finish afterward.

Local rewards use original G/I/C artwork: code 1 = 20/10/10, code 2 = 10/10/10,
code 3 = 0/5/10, code 4 = 0/0/10. They credit the wallet; first place, second/third,
fourth–tenth, and the top third thereafter use original reward bands. A completed
human tournament match is required. External prizes/subscriptions are not used.
Names, rules and countdown wording have the four original languages.

Schema 8 persists instances, registrations, viewers, awards and bracket rounds.
Incompatible disposable databases reset without legacy migrations. This is a
replacement bracket implementation; original server code/thresholds were absent.

## Verification

```sh
python3 -m unittest tests.test_tournament_lifecycle tests.test_tournament_rounds -v
xvfb-run -a -s '-screen 0 1280x800x24' python3 -m tools.smoke_tournaments
xvfb-run -a -s '-screen 0 1280x800x24' python3 -m tools.smoke_knockout
```

Native tests verified the original future timer, stadium/rewards, running and
closing states, final podium/closure chat, upcoming event and Register and Play
path with two human profiles and actual resolution acknowledgements. The knockout
probe additionally verified qualification timer, semifinal/final countdowns,
unqualified viewer elimination and final podium, with four human profiles.
Evidence is in `evidence/tournament-lifecycle/` and `evidence/knockout/`.
Android shares the patches; current flows have not been run on an Android device.
See [frontend restoration](frontend-restoration.md) for the full operating guide.
