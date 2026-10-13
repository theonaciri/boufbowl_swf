# Client request policies

Game wire schemas are in `protocol/client_contract.json`; separate chat schemas
are in `protocol/chat_contract.json`. The transport uses authenticated HTTP
commands and ordered events carrying the original protobuf envelopes.

| Requests | Replacement behavior |
| --- | --- |
| Match request, cancel, challenge answer | CPU matches, nickname challenges, acceptance/decline/cancellation |
| Placement, orders, introduction done, resolution done, surrender | Authoritative ownership/phase/element validation, deadlines, simulation, acknowledgement, results |
| Match spectate, stop spectating | Public active match snapshots and live events; spectator acknowledgements do not advance authority |
| Predefined club selection | Owned persisted starter clubs; appearance and names persist |
| Customization session, player/team changes, cancellation | Free local customization; owned identities and server class attributes enforced |
| Update premium content | Marks refresh complete; local client assets are unlocked without purchases |
| Ladder by league/nickname | Rating-ordered local profiles and recorded wins/draws/defeats |
| Outstanding tournaments, leaderboard, running matches | Configured free points league, current/past lists, CPU entries, persisted results |
| Ping, time, whois, stats | Timestamp echo, server clock, local profile lookup, service counts |
| Chat send to channel/client, join/part | Original general/private/match chat, persisted messages, scoped recipients, service-managed subscriptions |
| Facebook linking, moderation, administrative broadcast, external XGaming authentication | Intentionally disabled; returns an explicit service/policy error |
| Chat reporting and administration | Intentionally disabled on the local service; returns CHAT_POLICY |

League/nickname ladder requests currently return the first 100 local ranking
rows with the requester's own row. Historical league segmentation and paid
elimination brackets are replaced by the documented local league policy. Stats
counts saved profiles rather than live socket connections, since sessions use
HTTP. Sessions last one year and tokens are device credentials, not nickname login.

Unknown or malformed commands fail explicitly rather than altering authoritative
state. Network retries retain their command request ID. No original external
account/payment/admin service is contacted by the replacement game service.
