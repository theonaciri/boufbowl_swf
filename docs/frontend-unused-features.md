# Frontend features still unused or partly connected

Historical audit after stadium celebrations and tournament lifecycle implementation.

All proposed items below are now implemented except advanced training, explicitly
excluded by the user. The table records the pre-implementation findings; use
[frontend restoration](frontend-restoration.md) for current behavior and settings.
This is a source/asset audit of confirmed gaps, not a claim that every embedded
bitmap or rare animation branch has been exercised. Many SWF symbols are UI
states or alternate frames rather than independent features.

| Feature | Evidence/current status | Feasible implementation |
| --- | --- | --- |
| Five competitive leagues | Original `protocol/League.as` defines Craqueleur, Abraknyde, Wabbit, Tofu and Piou. League selector and cube/badge artwork exist. `backend/social.py:emit_ranking` always sends league 1. | Configurable league thresholds, qualifying games, promotion/relegation and league-specific ranking lists. Historical thresholds are unavailable; define replacement rules. |
| Tournament rounds and elimination | `ScheduledTournamentData.rounds`, `TournamentRoundData`, round start/end countdowns, qualification and eliminated button states exist. The current backend supplies a points league with `eliminated=false` and no rounds. | Qualification windows, scheduled rounds, eligibility, elimination, pairing and ties. Use original round/countdown UI; server must own advancement. |
| Wallet and progression widgets | Original G/I/C reward artwork, premium-content/credit indicators, tickets and unlock models exist. Tournament currency is now credited to `statistics.tournament_wallet`; customization is still free/all unlocked. Premium refresh currently completes without a purchase system. | Display a persistent wallet/award history, then optionally add earn/spend cosmetic unlocks. Preserve the free customization option. This is a local economy, not restoration of external Ankama purchases/prizes. |
| News/MOTD and original login presentation | `LoginMotdUI`, login components and `resources/motd.json` remain. The MOTD contains obsolete 2012-era paid-tournament news. Current local account/device access uses added controls. | A local news panel and themed account entry screen with anonymous play. Feed current tournament notices and server announcements; replace stale external links. |
| Advanced tutorial/practice | `patches/WelcomeView.as` explicitly hides `advancedTutoButton`. Original `WelcomeMediator` wires the standard tutorial only; `TutorialScreensBuilder` builds one course. | Author tactical exercises using original speech/help/field components: orange-cell risk, AIR reception, goal lines, powers and stadium differences. Simply unhiding the button will not create a working course. |
| Player-facing replay controls | Replay viewing/export already works. The original developer console injects decoded messages, while playback clocks support pause/speed adjustment. No recovered end-user seek bar was found. | Expose pause/speed and turn selection. Seeking needs state restoration and replay sequencing; it is additional UI/control work, not switching on a hidden complete replay player. |
| In-game moderation | Original `ModerationType` has kick/ban/mute, plus requests/results and chat administration commands. Current service deliberately rejects moderation/admin requests; player reports and operator review already work. | Server-authorized moderator roles, temporary mute/ban, audit records and original result notifications. Regular users must not receive administrative permissions. |

## Already used

The basic tutorial references all five supplied tutorial videos. Class/team
customization, palettes, sigils, stadium previews/textures, goal celebrations,
versus/period illustrations, tournament rewards/podium/countdowns and normal
match interaction playback are already connected. Friends, blocking, private
messages, replay history and optional accounts have working replacement controls;
those controls can be restyled without reimplementing their backend features.

Missing character skins and non-Farmstead 3D stadium models are unavailable
assets, rather than unused frontend functions. Cra/Farmstead fallbacks remain.
The legacy Facebook and external account/payment integrations have UI remnants,
but their original services are not supplied. Their presentation could be reused
for local functionality.

## Recommended order

1. League progression and correct league badges/lists.
2. Wallet/award history display, while keeping free customization available.
3. Tournament qualification/rounds and elimination.
4. Replay controls and targeted training exercises.
5. Original-style account/news/community screens and authorized moderation.

No gameplay/economy policy was changed during the audit itself. The later
implementation is documented in the restoration guide. Existing original
sources and assets remain untouched. Implementation should proceed feature by
feature, with native UI checks at the end of each feature rather than rebuilding
all packages after every edit.

## Source pointers

Original ActionScript root: `../migration-work/scripts/scripts/`.

- `com/ankamagames/boufbowl/protocol/League.as`
- `com/ankamagames/boufbowl/client/components/league/LeagueCubeUI.as`
- `com/ankamagames/boufbowl/client/matchmaking/view/tournament/TournamentView.as`
- `com/ankamagames/boufbowl/client/matchmaking/model/TournamentRoundData.as`
- `com/ankamagames/boufbowl/client/premiumservice/common/model/PremiumContentModel.as`
- `com/ankamagames/boufbowl/client/components/login/LoginMotdUI.as`
- `com/ankamagames/boufbowl/client/tutorial/TutorialScreensBuilder.as`
- `com/ankamagames/boufbowl/client/matchmaking/view/WelcomeMediator.as`
- `com/ankamagames/boufbowl/client/application/replay/view/ReplayConsoleView.as`
- `com/ankamagames/boufbowl/protocol/ModerationType.as`
