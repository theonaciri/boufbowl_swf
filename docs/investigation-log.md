# Backend investigation and implementation log

## Step 1 — Channel and phase contract

Verified from the supplied reference decompile:

- Lobby and match pipelines are mapped as `LOBBY` and `MATCH`. Both use
  `FixedLengthFrameDecoder`, protobuf decoding, message dispatch, protobuf encoding
  and `FixedLengthFrameEncoder`. Frames have a four-byte big-endian payload length;
  the client caps a payload at 128 KiB. The developer replay console bypasses the
  framing/decoder stages and injects decoded envelopes at the message handler.
- `BoufbowlMessage` supplies a numeric discriminator and typed payload fields.
  `UnionProtocol` maps incoming types and wraps supported outgoing request classes.
  Its set of supported types is smaller than the full discriminator enum, which
  also includes server-to-server messages. Do not claim every enum is a client API.
- Match setup is `MATCH_INFORMATION` (1201). It changes the displayed module before
  dispatching setup data: rosters, placement zones, stadium, optional player side,
  and `skipIntro`. Without `side`, the module runs as a spectator.
- `FIELD_STATE` (1203) supplies positions/ball and can embed `TEAM_STATE` (1202).
  Team state supplies health/status, remaining class abilities, turn/period/score
  and optional updated attributes. `ClientMatchPhaseInfos` distinguishes placement
  (1) and orders (2).
- A normal flow is setup → introduction acknowledgement → placement → placement
  submission → orders → order submission → resolution → resolution acknowledgement
  → authoritative field/team state for the next phase → match end.
- `MatchStateSequentialityValidator` rejects illegal transitions. Setup with
  `skipIntro=true` enters `RESUMING`, which accepts a subsequent phase transition.
  This is useful for deterministic replay fixtures and reconnect reconstruction.
- `ResolutionDoneMessage` (2701) acknowledges displayed turn completion; it does
  not carry the resulting world state. The gateway must send subsequent state.

Artifacts: `tools/extract_protocol.py` and `protocol/client_contract.json`. The
extractor records message fields/tags/types, enum values, union mappings, handlers
and source SHA-256 values. `XGamingMessage` is an external protocol dependency;
authentication referral handling remains outside this initial game-protocol slice.

## Step 2 — Original rules and engine differences

- Original `Rules.getReferenceDistance` sums the selected elements' distance
  bonuses. `getMaxDistance` multiplies that sum by a factor. With client defaults,
  three water elements yield reference distance 9 and maximum distance 11.97.
  Three earth elements yield 6 and 7.98. These are client calculations, not proof
  of the original server's probability or rounding rules.
- The sibling replacement engine instead starts from a base movement range and
  adds/subtracts per-element modifiers. Therefore its current balancing is not
  equivalent to the original client's range preview. Do not silently identify its
  strength/agility/endurance/precision fields with Flash earth/fire/water/air stats.
- Flash `GridCoordinates` has two signed, zigzag-encoded integers. `HexVector`
  distance is `abs(x)+abs(y)` for same-sign coordinates and `max(abs(x),abs(y))`
  otherwise, equivalent to axial hex distance. World-space orientation, pitch
  dimensions and animation scale still need explicit conversion validation.
- Original `ScriptBuilder` uses 50 ms per scenario tick. The replacement config
  currently uses 100 ms simulation ticks. Convert timing explicitly; do not copy
  tick numbers between systems.
- Original scenarios contain test results, participants, shared interaction IDs,
  movement sequences and class-order information. Generic replacement events
  need enrichment to construct those original presentation objects.

Decision: first build a typed wire codec and a real-client fixture harness, then
test a movement-only scenario through the original handler/animation pipeline.
This establishes the presentation contract before adapting combat or probabilities.
Preserve the offline launcher/tutorial and use an opt-in mock mode.

## Step 3 — First implementation and runtime discoveries

- Added a strict, dependency-free protobuf codec with signed/unsigned numeric
  validation, zigzag encoding, packed repeated enums, discriminator validation,
  duplicate-field checks, size/depth limits and streaming frame assembly.
  JSON-facing 64-bit IDs are decimal strings; the fixture uses
  `9007199254740993` to exercise values above JavaScript's exact integer range.
- Added a shared readable AS3 mock harness included in desktop and Android startup
  patches. It loads encoded fixture steps, injects decoded envelopes at the original
  match handler, and waits for the real `ResolutionDoneMessage` before continuing.
  Home cancels scheduled work; failed loads/messages/acknowledgements are visible.
- The first real-client run displayed the strategic match screen and acknowledged
  a scripted turn through the existing controller chain. It used 2D mode, which
  skips the resolution animation script; this alone does not validate animations.
- The initial end screen failed because `FieldModel.getSideCaptain` selects the
  eighth roster member per side. Updated the fixture to ten-player club rosters,
  with five active players per side. The active-team invariant is not roster size.
- `DisplaySituationCommand` divides `ClientMatchPhaseInfos.remainingTime` by 1000:
  this field is milliseconds, although the client planning configuration is seconds.
  Corrected the fixture; sending 60 meant a near-immediate order timeout.
- Normal match playback injects `SlowableTimeProvider(AsvmTimeProvider)`, based on
  Flash `getTimer()`, rather than the separate `FrameTimeProvider` class. Corrected
  the playback documentation after tracing the actual injection binding.
- Special gameplay skin IDs are the special-character ID directly: `computeSkinId`
  returns the third argument when nonzero, otherwise concatenates class and gender.
  The missing special skins are therefore `501.swl` through `518.swl` under
  `assets/sprites/skins/`. Their embedded portrait artwork remains separate.

The movement fixture is predetermined and does not implement server simulation,
account persistence, multiplayer, combat, or ball interactions yet. The next gate
is successful 3D playback and match end with the corrected roster/timing contract.

## Step 4 — Engine-computed movement and 3D playback gate

Implemented `tools/probe_engine.ts` to call the existing sibling simulator directly
for one seeded, isolated movement turn. It imports its rules/simulator modules,
overlays the supported balance settings, and opens no account databases or sockets.
The current probe produced simulation version 2.5.0, 100 ms ticks and 61 events
(`move` and `final_state`). The seed is 12345.

`tools/movement_adapter.py` converts that result into original player tracks. It
checks identity agreement, adjacent cells, monotonic sample timing, unchanged
health/status/ball/score and agreement with final authoritative positions. Unsupported
interactions and unrepresentable tick durations raise errors. Converted motion is
quantized to grid cells; this is a limited movement compatibility experiment.
Movement-test display scores are explicitly synthetic/provisional.

The Linux smoke check passed under Wine/Xvfb with these observed steps:

1. Original `MATCH_INFORMATION` handler displayed and initialized the match module.
2. Original `FIELD_STATE` handler displayed a planning phase with ten active players.
3. `ComputeResolutionCommand` reported **Playback mode 3D** and **Playback script built**.
4. The original renderer displayed the available Farmstead stadium and character
   sprites, then sent the real **ResolutionDoneMessage**.
5. The fixture delivered the next authoritative field state after that acknowledgement.
6. Original **MATCH_END** handling displayed a 0–0 draw billboard with both captains.

Evidence: ignored `evidence/mock-engine-playback.png`, `mock-engine-movement.png`,
`mock-engine-result.png` and `mock-engine-trace.log`. `tools/smoke_mock.py` makes this
repeatable and checks the message sequence. The trace includes sequence/time because
HTTP diagnostic requests can arrive out of order. Twenty-one focused unit tests
currently cover configuration, wire vectors, frame fragmentation, malformed input,
fixture lifecycle and adapter acceptance/rejection.

Android compilation/packaging with the shared helper succeeded. Standard startup
remains the offline menu; an explicit mock-start configuration is required to enter
the fixture in AIR. The new fixture has not been runtime-tested on Android hardware.

## Step 5 — Remaining interaction contract and implementation boundary

Further original-client inspection establishes:

| Interaction | Original presentation requirements | Current adapter |
| --- | --- | --- |
| Movement | Player ID, accepted order, timed grid path, movement-test display result | Implemented for the isolated probe |
| Pickup | One participant, ball position, maneuver result, shared track interaction ID | Rejected; mapping next |
| Pass | Thrower/receiver roles, target cell, target ID, next interaction ID, maneuver result | Rejected; mapping next |
| Reception/interception | Receiver/interceptor trajectory at arrival, maneuver result, linked ball outcome | Rejected; mapping next |
| Rebound/out of bounds | Ball origin and ground positions, stadium rebound presentation | Rejected; mapping next |
| Fight | Two participants, fight type/result, damage/status/bonus details, optional ball dispersion | Rejected; mapping next |
| Touchdown | Scorer or conceded side, running/cinematic flags, stadium celebration assets | Rejected; mapping next |
| Class abilities | Class-order information and buff/debuff/mask presentation data | Rejected; mapping later |

Pass playback follows `PassDetails.nextInteractionId` to reception, interception or
rebound; flight duration derives from the linked interaction's start tick. A generic
throw event without that linkage cannot drive correct original playback. Fights
dispatch BRAWL, DODGE, TACKLE and HIT_AND_RUN functions and synchronize participants
through shared interaction nodes. Treat client animation order as presentation,
not proof of the lost server's interaction-resolution priority.

Original axial-to-world conversion uses the standard pointy-top formula with scale
100. The replacement engine uses a configurable world scale and fixed-point
subcell coordinates. Pass original grid cells through the original renderer rather
than sending the replacement world coordinates into it.

Next implementation order: linked ball scenarios → two-participant combat → class
abilities/score transitions → live command and event transport → persistent services.
Retain the current fail-closed adapter boundaries until each new mapping has an
original-client rendering fixture and an authoritative final-state check.

## Step 6 — Packaging and regression verification

- Rebuilt the desktop client and Linux `.deb`/portable archive with the current
  codec inventory, settings and engine-generated fixture. Validated the packaged
  configuration and decoded every packaged fixture envelope.
- Rebuilt the ARM64 Android APK with the shared startup helper. APK signature,
  ZIP integrity and 16 KiB alignment checks pass; packaged settings/schema/fixture
  match the current project files. Android runtime verification remains pending.
- Reopened default menus after the mock changes and visually checked Home. The
  launcher still defaults to menus, while `--mode mock --scene-3d` opts into the
  integration probe. The ordinary Home screen contains no mock status overlay.
- No sibling backend source, existing account database or original archive was
  changed. The probe invoked only its simulation/config modules.

This completes the first movement/protocol implementation gate. Live networking,
database replacement and the remaining interaction mappings are not complete.

## Stage 7 — live backend and Cra fallback

Implemented SQLite device profiles, owned persistent clubs, hashed bearer sessions,
retry-safe commands, ordered protobuf events, CPU/human match services, deadline
handling, simulation records and exactly-once match statistics. Live startup now
uses the original lobby/match handlers rather than a replacement renderer.

The original 64-bit string helpers are defective (signed concatenates words;
unsigned inherits the object string). Added exact two-word decimal conversion to
club snapshots. Verified the original player connects and opens placement.

Missing regular and special animated skins now render Cra of the same gender.
Class identity, portraits and statistics remain unchanged. Custom animation looks
also filter unavailable skin symbols. Android now merges shared patches with its
platform-specific replacements; previously the new shared patches were omitted.

28 tests pass, including seven real-engine/database tests. Deadline fallback
orders originally included both teams; filtering by team_id fixes validation.
Simulation workers now have a 30-second response timeout and close their pipes.
Background maintenance advances deadlines even without client polling.

Live 3D turn 1 built, played and produced ResolutionDoneMessage. Turn 2 exposed
an original-client constraint: regular orders must target a cell or actor even
when waiting. The adapter now targets each waiting actor's current cell. Full
match rerun is pending; do not treat the first-turn result as complete verification.

Class ability balance is now included in resources/game_config.json and validated
by its schema. Per-player ability usage survives bench substitutions.

## Stage 8 — complete matches, interactions and persistence

Verified two consecutive engine turns through the original 3D player. Both emitted
ResolutionDoneMessage, the next field state loaded, and MATCH_END appeared. Waiting
orders now explicitly target their current cell, satisfying the original renderer.

Seven deterministic native probes passed: pickup, combat/KO, pass/reception,
pass/interception, rebound, ability and goal. Their engine records and wire fixtures
are in tests/fixtures/interactions; screenshots/traces are in evidence/interactions.
Cra fallback passed a special-character movement fixture and the live team/editor
flow: original character illustration remains, animated preview is Cra and posture
controls work. Selecting a hero starter club persisted its name and roster.

Recovered the separate ChatMessage union and serializers into chat_contract.json.
Implemented persisted general/private/match chat, recipient isolation, rate limits,
local rankings, a configured free points league, timestamps/whois/stats and live
spectators. Native menu checks verified leaderboard, tournament data and teams.
Tournament loading requires PAST_TOURNAMENTS as well as OUTSTANDING_TOURNAMENTS;
UPDATE_PREMIUM_CONTENT must also complete its original refresh lifecycle.

Recorded match 2 reproduced its engine version, final hash and events, then played
both stored turns to completion in the original player. Replay acknowledgements
now validate the recorded turn rather than assuming turn 1. Replay export checks
participant ownership; replay does not alter results. SQLite online backup passed.

35 focused tests pass, including two-human completion, private-message isolation,
tournament points, spectator acknowledgement isolation, replay verification,
regeneration and immutable turn results. Regeneration is configurable at turn
boundaries; zero-health players are not revived by it. Period/goal resets restore
health for placement. Ability HP display deltas are clamped to actual healing, and
live ability tooltips use server effects rather than misleading historical text.

Linux packages include the compiled worker and Bun runtime, avoiding sibling-source
or Bun installation requirements at runtime. Android merges shared patches with
platform overrides. Linux .deb/tar and ARM64 APK builds passed. The latest Android
backend flows are package-verified only; no attached device/emulator is available.
Exact historical server probabilities/abilities remain unrecovered and documented
as configurable provisional behavior. External accounts/payments/admin services
are intentionally disabled; their policies are in docs/request-coverage.md.

## Stage 9 — final distribution checks

The latest original-client live smoke again completed two 3D turns and persisted
exactly one result; reproducible harness: `python3 -m tools.smoke_server` under
Xvfb. An isolated Linux bundle completed a CPU match using its bundled Bun, with
no sibling imports or separate Bun executable on PATH. Android's packaged balance
file matches the source configuration exactly. APK ZIP integrity and v1/v2
signature verification pass; its native library is ARM64. Linux archive integrity
passes. The simulation worker restarts after an unexpected exit, and transient
worker failures retain command IDs for retry. Final checks include 35 tests.

## Checkout startup fix

A user checkout exposed an omitted distribution file: backend/build was ignored,
so Engine fell back to engine.ts and its sibling source imports. The worker exited
without a useful diagnostic because stderr was discarded. The small bundled
engine.js and engine_base.json are now included in source checkouts. Engine no
longer silently falls back to sibling imports. It checks readiness before starting
match maintenance, captures startup/runtime errors, and clearly identifies a
missing Bun runtime or worker. Its handshake remains compatible with older bridges.
The launcher prints startup errors directly instead of a repeated maintenance loop.

39 tests pass, including missing worker/runtime, stderr diagnostics and an isolated
checkout test with no engine.ts or sibling source. Linux packaging uses the included
worker by default; --rebuild-worker explicitly requests a source rebuild. No SWF
rebuild is required to play from a checkout. Saved databases are unchanged.
