# Client request policies

Game wire schemas are in `protocol/client_contract.json`; separate chat schemas
are in `protocol/chat_contract.json`. The transport uses authenticated HTTP
commands and ordered events carrying the original protobuf envelopes.

| Requests | Replacement behavior |
| --- | --- |
| Match request, cancel, challenge answer | Persistent human matchmaking, explicit CPU games, nickname challenges, acceptance/decline/cancellation |
| Placement, orders, introduction done, resolution done, surrender | Authoritative ownership/phase/element validation, deadlines, simulation, acknowledgement, results |
| Match spectate, stop spectating | Live room list, scoped chat, reconnect snapshots, join/part events and saved replay access; spectator acknowledgements do not advance authority |
| Predefined club selection | Owned persisted starter clubs; appearance and names persist |
| Customization session, player/team changes, cancellation | Free local customization; owned identities and server class attributes enforced |
| Update premium content | Marks refresh complete; local client assets are unlocked without purchases |
| Ladder by league/nickname | Rating-ordered profiles, real nickname/self lookup, groups of 100 and recorded wins/draws/defeats |
| Outstanding tournaments, leaderboard, running matches | Configured free points league, current/past lists, CPU entries, persisted results |
| Ping, time, whois, stats | Timestamp echo, server clock, local profile lookup, service counts |
| Chat send to channel/client, join/part | Language-isolated global rooms, persisted private conversations, participant/spectator match chat and durable join/part |
| Facebook linking, moderation, administrative broadcast, external XGaming authentication | Intentionally disabled; returns an explicit service/policy error |
| Chat reporting | Stored operator reports, optional original-client success notification and local review CLI |
| Friends, blocking, history, replay browser | Community API and client controls, durable relationships/blocks and owned or watched replay access |

The local league is divided into groups of 100; nickname requests select the
correct group and index. Historical league segmentation and paid elimination
brackets remain replaced by the documented local policy. Connected-client stats
use requests seen within the last 30 seconds. Sessions last one year. Anonymous
device credentials remain available; optional local accounts add password login
and recovery. Account usernames and public player nicknames are distinct. See
[accounts and matchmaking](accounts-and-matchmaking.md) and
[community and replays](community-and-replays.md).

Unknown or malformed commands fail explicitly rather than altering authoritative
state. Network retries retain their command request ID. No original external
account/payment/admin service is contacted by the replacement game service.
