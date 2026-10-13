# Completion checklist — replacement client/server

- [x] Recover original game/chat schemas and turn playback contract.
- [x] Preserve reference originals and readable patch/build workflow.
- [x] Central validated balance, abilities, general settings and stadium overrides.
- [x] Cra fallback in shared Linux/Android patches; native special-roster playback and editor verified.
- [x] Authenticated live original-client command/event transport and network retries.
- [x] Persistent profiles, owned clubs/customization and retry-safe results.
- [x] Placement/orders/deadlines, CPU and two-human match completion.
- [x] Persistent rating-aware human queue, cancellation, presence expiry and concurrent pairing.
- [x] Optional accounts, anonymous linking, cross-device login, recovery and session revocation.
- [x] Native two-client account login, matchmaking, playback and result checks.
- [x] Original-player pickup/combat/pass/reception/interception/rebound/goal/ability rendering.
- [x] Restart checkpoints, deterministic recorded replay export and native multi-turn playback.
- [x] Original home/ladder ranks, paged ranking search and configured free tournament league.
- [x] Automatic match history/turn recording, spectator replay access, replay browser and JSON saving.
- [x] Persistent friends/requests/blocks, presence and list actions.
- [x] Language subscriptions, scoped private history, participant/spectator chat and room reconnect.
- [x] Stored player reports and local operator review.
- [x] Reachable request implementation or explicit documented replacement policy.
- [x] Standalone Linux backend/runtime, Linux packages and Android client package.
- [x] Focused database/engine/protocol tests and native Linux player checks.
- [x] Setup, backup/restore, compatibility, configuration and findings documentation.

Limits are explicit: the latest Android live flows have not been run on a device;
the APK is compile/package/signature checked. Exact historical server probabilities
and abilities are unavailable, so the replacement uses configurable engine rules.
The local tournament is a free CPU points league, rather than the paid historical
bracket system. Optional local accounts and device bearer sessions replace external accounts. Missing stadium
models reuse Farmstead, and missing animated character skins reuse Cra.
