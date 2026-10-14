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

## Gameplay, placement and French chat investigation — 2026-10-13

The original `resources/lang.json` tutorial step 5 explicitly requires at least
one AIR on the receiver. The sibling simulator's `resolveReceptions` instead
filtered on FEU, so an AIR-only receiver never reached the catch probability
roll. The local ball-module overlay now checks AIR for receptions/interceptions;
CPU receiver allocation and warning codes agree with that rule. Existing catch
range, height, one-attempt-per-flight, actor-state and probability checks remain.
A deterministic AIR-only reception probe succeeds; the forced-zero-probability
probe still produces a failed catch and landing.

`resolveGoals` previously compared the carrier's position against outer pitch
columns (-18/+17), beyond the painted goal lines. The client `GridModel` maps
horizontal position to `q+r/2`. Scoring now compares that continuous coordinate
with configurable +/-12.5, reflecting attack direction after halftime and
requiring an active carrier. Tests cover both teams, negative/positive odd/even
rows, period swapping, own-line/no-ball rejection and a custom line position.
The new goal probe crosses from column 12 to 13 rather than 16 to 17.

Placement was five hardcoded five-cell crosses. The supplied reference silhouette
has been reconstructed into row spans for orange center, green upper front,
yellow wedge, cyan lower rear and blue lower front. Horizontal reflection is
`q'=-q-r`, preserving vertical roles; negating both coordinates was a rotation.
The client `MatchModel` now reflects stored zone cells when period parity changes,
without reinitializing the match; setup resets period state for resumed matches.
The native halftime screenshot confirms the large zones on the opposite side.
An empty automatic placement packet now selects default positions, matching
server deadline maintenance and avoiding a spurious request-failed notification.

The `2_fr` chat exception came from advertising general chat as `2_null` while
client shortcuts use the account language. The service now advertises all four
supported language keys. `ReceiveChannelsConfigurationCommand` preserves the
language during registration; the original command discarded it. Chat rateLimit
is expressed in seconds, so it is now 1 instead of 1000. A native French client
sent `/g Bonjour test`, persisted it and displayed the returned message.

Status text wraps inside a maximum width of 512 logical pixels (and at most half
stage width), with its height bounded to three lines and its bottom anchored.
Readable client patches and local simulator overlays preserve original files.
Rules version is `boufbowl-custom-2`; engine version adds `+client-ball-2` so older
recordings are not mislabeled as equivalent simulations.

Validation: 49 automated tests, including an isolated source checkout worker;
native AIR reception and interior-line goal replay probes complete through
ResolutionDone, next field state and match end. Desktop SWF and ARM64 Android APK
compile; APK signature/alignment checks pass. Android runtime behavior remains
untested because no device/emulator is attached. The reproducible native French
chat/halftime smoke is `python3 -m tools.smoke_gameplay_fixes` under Xvfb, and its
screenshots/traces are in `evidence/`.

## Stadium textures and palettes — 2026-10-13

Farmstead already used the original archived textures. Eight additional court
atlases were found under sibling `boufbowl/assets/courts`; copies and provenance
are now bundled here. Stadium-specific COLLADA variants reuse the available
geometry, with atlas-adjusted ground UVs. These are visual substitutes for missing
3D models, with configurable theme mappings in `resources/stadium_art.json`.

Native testing caught two Away3D limitations: mixed parent-directory texture paths
left some fetched textures unbound, and separate UV sources appended coordinates
without correcting face indices. Generated models now use local image paths and
modify only UV indices exclusively used by the ground. Brakmar renders its atlas
and completes original-player replay. No original model or source atlas is edited.

`resources/palettes.json` supplies 11 club palettes and expanded hair/eye/skin
choices, plus universal Pastel/Vivid/Natural character palettes. Both platform
startup generators share it. Original color-grid lists have a 16-color maximum;
validation enforces that limit. Translation generation is repeatable and adds
names for the new IDs in every supported language. The native character editor
shows the expanded swatches. Details and theme mappings: `docs/visual-assets.md`.

## Accounts and human matchmaking — 2026-10-13

Database migration to version 2 adds accounts, login-attempt buckets and a
persistent queue, retaining old anonymous tokens and profile/club/match IDs.
Optional accounts use salted PBKDF2-SHA256 passwords, cross-device sessions,
one-time recovery codes, password changes and logout/revocation. Account linking
preserves the existing profile. Remote password requests require HTTPS; the
standalone server accepts certificate/key flags. TLS endpoint behavior is tested.

Normal match requests now search for humans instead of choosing CPU. Queue joins
are transactional, maintain arrival priority, enforce distinct profiles, require
intersecting enabled stadium choices, prefer nearby ratings and widen over time.
Heartbeat and total-search deadlines remove stale entries. Explicit CPU matches
and nickname challenges remain available. Pairing removes queue entries and
cancels unrelated invitations; login restores pending invitations. Committed
placements/orders are immutable on repeated submissions or reconnects.

The shared client exposes account controls in Server → Account and search/CPU/
challenge controls in Play. Password fields are masked and credentials are not
saved in SharedObjects. Account switching clears private chat display history and
is performed from the lobby. Customization confirmation now correctly states that
server-mode edits are saved, while standalone preview remains temporary.

72 automated tests pass. A two-client native regression logged into separate
accounts, queued and paired them, rendered two original 3D turns per client,
received four ResolutionDone messages and persisted exactly two human results.
The explicit CPU regression also completes two native turns and one result.
Both platform client builds compile. Android is package-verified without device
runtime testing. Reproduction and API/setup details: docs/accounts-and-matchmaking.md.

## Community completion and client regressions — 2026-10-14

Schema 3 persists accepted/pending friends, blocks, presence, language subscriptions,
private history, reports and watcher replay access while retaining existing profiles.
Rankings and history use saved results; exact turn scenarios are retained for replay
export/import. Live watchers receive the original animation protocol and chat, but
only player acknowledgements advance authority. The shared client exposes Friends,
Rankings, History, Watch, Messages and Channels. Local reports have an operator CLI.
See `docs/community-and-replays.md` for access rules and remaining external features.

Native testing verified saved JSON via the Flash FileReference dialog, replay and
live watcher animations. Four external/privileged game requests remain explicit
errors; all recovered chat requests have local handlers.

The reported chat lag was the client's 500 ms polling interval. Condition-based
long polling now wakes on commits without holding the SQLite transaction, including
safe shutdown. CPU turns already resolve when orders arrive; 3D scene loading adds
its own delay. Waiting modals now close on scenario arrival.

First-login Private/Information channels were absent because General configuration
made the chat model appear initialized. Clearing before initial server connection
restores channel creation. Player information now uses a public summary endpoint;
original nickname menus query match availability before offering Spectate. Native
screenshots cover players both with and without a match. Toolbar placement now
maintains an 80 px right margin.

Palette indices could survive a switch from ten colors to five and dereference an
undefined Color3. All selectors now clamp indices before notifications. Native
editing switched the tenth default swatch into a five-color palette, saved and
played two turns. Match rosters freeze contrasting kits, preventing viewpoint-
dependent character colors and inconsistent darkness flags.

Stadium identities were corrected against original FieldBackground frame labels
and bitmap IDs, rather than guessed atlas appearances. In particular Frigost uses
bitmap 1640 (ice), Ballotin 1646 (clouds), Pixel 1648 (wabbits), Bonta 1638 (prairies)
and Farmstead 1632 (grass). The ice JPEG is converted to a generated PNG. Existing
Farmstead geometry remains a substitute for missing stadium-specific 3D models.

A delayed eight-second response verified the six-second application deadline.
Forcibly closing a pending URLLoader exits the legacy Windows player under Wine;
the safe cancellation retires its callback and discards late responses. This is
separate from matchmaking search deadlines. Recompiling two decompiled chat command
classes also lost constructor injection metadata; those unnecessary patches were
removed and original command bytecode restored. Rebuild class indexing is now
computed by name instead of relying on fixed positions.

Validation: 90 automated tests pass. The final native regression saves an original
private message, opens player information, changes/saves the shorter palette,
completes two Frigost 3D turns and a result, then retires a deliberately delayed
request at six seconds. Waiting past the late response confirms the player stays
open and no information panel reappears. Evidence is under `evidence/client-*`.
The Linux bundle resolves two turns using its bundled Bun runtime without a system
Bun installation. Android compilation/package validation does not imply device
runtime validation.

## Palette follow-up, human tournaments and explicit teams — 2026-10-14

The user could no longer reproduce the reported palette crash. Investigation did
find a separate character-editor issue: switching from the expanded 16-hair-color
palette retained an index when its color was absent from the smaller palette.
Character indices are now validated before notifying the view and rendering.
A native probe selected the highest swatches, switched repeatedly between Cra,
Pastel and Vivid, saved Pastel (palette 101), then played a two-turn CPU match.

The original appearance and replacement actions were using the same unlocked
editor. Restored their distinction: appearance preserves class/special identity
and allows gender/name/colors; replacement allows class/special-character changes.
The original screen is shared, but class and special-character controls are now
restricted in appearance mode. Persistence retains owned player IDs.

Tournament requests still used the earlier CPU league policy. They now join a
persistent human queue isolated from normal searches, respecting configured
tournament times and stadium. Transactional pairing removes busy entrants and
never pairs one player twice during a batch. Expired/closed searches do not turn
into CPU games. Database schema 4 adds tournament_id to queue entries while
preserving existing queued device profiles.

The original Home Play and Tournament actions now expose the shared dialog with
human search, explicit CPU matchmaking, tournament search and cancellation. Team
selection is displayed there and the owned club ID is included in match requests.
The backend selects that stored club before pairing rather than relying on a
potentially stale implicit selection. Native probing chose team 2 and confirmed
Offline Brakmar's roster was used; its two turns and result completed.

Regression coverage adds separate tournament/normal queues, four-player pairing
without busy-opponent reuse, restart/search expiry without CPU fallback, closed
tournament cleanup, explicit team selection/ownership and schema-3 queue migration.
`tools/smoke_matchmaking_colors.py` reproduces native customization and queue checks.

## Gear language selector and service refresh — 2026-10-14

The original Services refresh triggers RefreshPremiumContentCommand, sending
UpdatePremiumContentMessage. Backend UPDATE_PREMIUM_CONTENT replies with an empty
PREMIUM_CONTENT_UPDATED, which clears the pending flag. Customization is already
locally unlocked; this is not a game updater.

The original gear popup now includes a four-language selector. Closing settings
saves the selection in local BoufbowlPreferences SharedObject storage. Startup
FlashVars language resolution uses explicit launcher override, then saved choice,
then launch/configuration default. Desktop --lang marks an explicit override;
normal launches no longer accidentally override the player's saved setting.
Android reads the same preference through the shared patch. The restart requirement
avoids rebuilding active match views or losing unsaved editor changes. Chat language
subscriptions and server accounts remain independent of local interface language.

Validation: 97 automated tests pass. `tools/smoke_language.py` opened the original
gear popup, cycled all four choices, saved French, restarted into French, launched
once in English using --lang, then restarted into French again. The same server
profile was retained across all four launches. The regression restores the smoke
Wine prefix's previous language preference afterward. Original labels translate;
new replacement-server dialog labels remain English. Android's shared patch is
compiled/package-checked; device runtime language testing remains pending.

## Full-screen cinematics — 2026-10-14

The prior service always sent skipIntro=true and the turn adapter always marked
isCutscene=false. Both policies are now configurable and enabled by default.
New matches freeze presentation settings. Introduction acknowledgements are saved
per human side, require both players for human matches, ignore spectators/duplicate
acks, restore across restart and release placement with its full clock. Missing
acks use a 90-second configurable watchdog. Farmstead camera movement matches the
available shared stadium geometry; the original versus artwork uses actual kits.

Goal, combat, pass, reception/interception and rebound paths use existing illustration
and movie SWFs, rather than the missing animated-cutscene library. Client movie/
cutscene loaders catch unavailable symbols and finish callbacks instead of leaving
a frozen scene. New turn records store the exact cinematic scenario and presentation
policy; historical scenarios stay unchanged. No authoritative simulation code changed.

102 automated tests pass, including introduction gating, restart, duplicate and
spectator acknowledgements, watchdog behavior, legacy flags and unchanged outcomes.
The native desktop check captured the stadium/versus sequence, INTRODUCTION_DONE,
subsequent placement, turn completion and one result. A forced touchdown replay
rendered Illustration_touchdown and Illustration_bouftous_contents, completed both
and sent ResolutionDone before the final state/result. Native combat also rendered
its cinematic and completed playback. Reproduction tools: tools/smoke_cinematics.py
and tools/smoke_mock.py --require-cinematic with a cinematic-enabled fixture.
Evidence: evidence/cinematic-versus.png, cinematic-touchdown.png and cinematic-combat.png.


### 2026-10-14 — Experimental class powers and distinct base statistics

- Replaced provisional teammate heals with the proposed 14 class effects in
  `resources/game_config.json`. Powers remain explicitly experimental.
- Element bonuses adjust characteristics (strength/agility/precision/endurance),
  keeping allocation at three action slots. Temporary range/attack/stat modifiers
  expire before final state hashing. HP and masks persist.
- The original FieldModel already enforced one selected power and exposed Zobal's
  three-mask picker. Added guards against movement/pass edits while selected;
  the backend and worker now enforce one power, caster exclusivity, eligibility,
  stadium usage budgets and valid mask transitions.
- Ecaflip uses the turn RNG and records the outcome. Signed HP deltas and mask
  selections flow through the recovered resolution protocol. Previous rules
  without `target` keep their old implementation and simulation version.
- Added 14 distinct experimental base profiles, each totaling 42 element points.
  Both AS3 preview construction and server normalization use these overrides.
- Localized descriptions in all four languages come from effective rules,
  including live stadium overrides. Validation and runtime checks are recorded
  below after completion.

- Validation: all 113 tests passed, including all 14 effects, seeded Ecaflip
  outcomes, caster exclusivity, stadium allowances, signed HP replay deltas,
  persistent masks, distinct base stats and unchanged legacy replay hashes/events.
  The rebuilt original native 3D client completed three power probes: Sacrieur /
  Roublard, Zobal / Ecaflip, and Cra / Sadida. All reached acknowledgement, next
  field state and match end without a client error. Traces/screenshots are under
  `evidence/class-powers-*`. Linux packages and the signed Android APK were
  refreshed; Android runtime behavior still requires a device check.
- Reproduce probes: `python3 -m tools.build_power_fixtures --output /tmp/powers`,
  then `xvfb-run -a -s '-screen 0 1280x800x24' python3 -m tools.smoke_mock
  --fixture /tmp/powers/wounds.json` (also `masks.json` and `range.json`).


### 2026-10-14 — CPU powers and cheating/abuse review

- Added a deterministic CPU power selector for normal/expert games using only
  public field state. It replaces every regular action of the selected caster,
  preserves carriers/receivers/retrievers, observes status and stadium allowances,
  and avoids lethal sacrifices. Beginner remains simpler. Recorded explicit
  orders bypass selection, preserving deterministic replay verification.
- Reviewed authoritative validation, rating rewards, active replay exports,
  turn-seed derivation, authentication, queue/social limits and server work locks.
  [Cheating and abuse review](cheating-and-abuse.md) separates existing safeguards
  from proposed hardening. Priority gaps are future-seed disclosure through active
  replay exports and practice/arranged matches contributing to competitive rating.
  No hardening policy was silently applied during this review.

- Validation: the complete 117-test suite passed after the worker change; five
  focused CPU tests passed, including a subsequently added difficulty/legacy-rule
  check. Tests cover single-caster exclusivity, deterministic choices, exhausted
  or disabled casters, carrier/receiver preservation, sacrifice safety, useful
  healing, and reuse of recorded orders. The compiled worker is updated; this is
  a backend change and requires no client/SWF or Android APK rebuild.


### 2026-10-14 — Seed privacy and ranked result separation

- Active exports retain animation envelopes but omit raw turn records, seeds and
  audit hashes; full verification is rejected until completion. Completed exports
  retain records and verify with the recorded seed. Each newly resolved turn draws
  an independent private seed, including unfinished legacy matches.
- Added server-owned source/mode and result-policy version to new matches. Human
  normal/tournament queues create ranked matches; CPU and direct challenges remain
  practice/casual. Ranked counters/rating and tournament points require provenance;
  client-supplied ranked flags cannot alter the policy. History exposes result kind.
- Schema 5 transactionally archives legacy statistics, reconstructs non-ranked
  counters and starts clean ranked statistics at 1000. Legacy matches without
  queue provenance are casual. Neither results nor historical replay packets are
  deleted, and reopening does not reset new ranked progress.
- Updated the History mode label and tournament help text in all four languages.
  Verification covers live participant/spectator exports, pending-order privacy,
  independent legacy-match seeds, completed replay verification, forged flags,
  ranked wins/losses/draws, non-ranked counts, tournament eligibility and migration.

- Validation: all 125 tests passed. Native 3D playback of a redacted live snapshot
  (no raw audit records) reached script completion, resolution acknowledgement,
  next field state and match end. Evidence is in `evidence/seed-private-live-replay*`.
  Linux packages and Android APK are refreshed; Android runtime remains a device
  validation item. Match records and legacy statistics are preserved by schema 5.

## 2026-10-14 — Disposable data, orange-cell falls and reference match

- User clarified that all prior matches/replays should be removed and this game
  has no live data. Deleted the development DB/export and obsolete stored-replay
  evidence. Removed legacy-stat archives and migration/reconstruction code.
  Schema 6 clears incompatible databases. This supersedes the schema-5
  preservation approach described earlier in this chronological log.
- Traced original safe/risky cell ranges, MovementTest/FALL/ball dispersion and
  period illustration protocol. Historical movement-fall odds were not recovered.
- Added configurable cumulative overextension risk with client-aligned ranges,
  original fall interaction, knockdown and carried-ball drop.
- Reference screenshots/source exposed incorrect regeneration semantics and
  four class health caps. Corrected these and added period warning/halftime data.
- Built and verified an authored 14-turn Kara comparison (goals 5/14, halftime 7,
  score 0–2), then played it through the original native client. All 14 turns,
  acknowledgements and match-end presentation completed, including cinematics.
- Detailed evidence, reproduction commands and limitations:
  [reference-match-comparison.md](reference-match-comparison.md).
- Final validation: 130 automated tests passed, configuration/schema validation
  and whitespace checks passed. Linux .deb/tar and Android ARM64 APK rebuilt;
  APK ZIP integrity and signing verification passed. No Android device run.

## 2026-10-14 — Stadium-specific goal celebrations

- Confirmed original stadium mappings and all referenced illustration symbols.
  Added a dedicated celebration manifest and build-time validation/application,
  independent of the substitute geometry paths. Original Brakmar/Bonta share
  the human crowd; Sable/Beach uses the crab illustration.
- All nine native original-client goal probes rendered their expected animation,
  finished and acknowledged resolution before MATCH_END. Captured each stadium
  under `evidence/stadium-celebrations/`; focused 18-test suite passed.
- Started original tournament source investigation and documented protocol,
  timer/panel behavior and implementation plan in `tournament-lifecycle.md`.

## 2026-10-14 — Original tournament interface and scheduled lifecycle

- Original source confirms server-clock milliseconds, future/running/past tabs,
  200 ms countdowns, stadium/reward artwork and closing-with-live-matches state.
  Restored the Tournament button: it had been redirected into generic Play controls.
- Added schema 7 with frozen scheduled instances, registrations, watchers and
  unique award ledger; incompatible development DBs reset without migration.
- Default entry window is 45 minutes every hour, with a 15-minute gap and rotating
  stadiums. Upcoming instances and history are delivered in original packets.
- Stopped entry/queues at cutoff while allowing already-started matches to finish
  and count. Closing appears in past with closed=false. Final standings/podium
  and local G/I/C currency awards are committed once, with closure notifications.
- Added a running countdown to TournamentView, four-language local names/rewards
  and shorter finished label. Play popup requests the current tournament at runtime.
- Full suite: 138 tests passed. Native live original-client future/running/closing/
  past/next panels, reward artwork, podium and closure chat passed. Lifecycle and
  late-finish/restart/idempotency probes are documented in tournament-lifecycle.md.
- Original Register and Play native probe also passed: second human pairing,
  one engine-recorded turn, native 3D resolution, both acknowledgements and MATCH_END.
  The scripted peer acknowledges through the same protocol; it is not a CPU player.
- Refreshed Android ARM64 APK; ZIP integrity, signing and packaged stadium
  mappings passed. Linux packages refreshed with final backend/docs. No device run.


## 2026-10-14 — remaining frontend restoration

Implemented the unused-feature audit except explicitly excluded advanced training.
Schema 8 adds trusted moderator/admin roles, profile sanctions and action audit,
cosmetic ownership/spending, optional seasons and persistent knockout rounds.
No legacy migration/archive layer was added; original assets/sources are retained.

Five ranked leagues now qualify after configurable ranked human results and
promote/relegate by rating; optional seasons archive counters and credit late
results to the originating season. Wallet purchases use server-owned prices,
atomic receipts and persisted unlocks. Free customization remains the default.

Hourly default tournaments now use qualification/top four, fixed semifinals and
finals. Draws advance the higher qualification seed; byes and active-player
walkovers are explicit. Unplayed registration cannot qualify/earn awards, and
late games postpone subsequent rounds/events to avoid overlapping running cups.
The original qualification/countdown/eliminated/podium interface is reused.

Replay pause/speed/previous-next turn controls use the original scene clock and
restore pre-turn snapshots/period/score/masks without submitting live commands.
News uses original LoginMotdUI artwork; added account/community controls are
styled consistently. Moderator actions authorize every entry path, enforce
mute on public/private chat, reject ban/kick authentication, preserve anonymous
identity after expiry and audit changes. Provision roles using backend.manage,
never a client role request.

Native checks passed wallet purchase, league/news panels, moderator mute,
replay pause/resume/speed/seek/result, and tournament qualification/round/final
screens. Captures are in evidence/frontend-restoration and evidence/knockout.
The edge tests also cover late season results, halftime replay chapters/masks,
bracket capacity, late-round calendar protection and offline walkovers.
See frontend-restoration.md for operating instructions and explicit limitations.

Final automated validation: 160 tests passed; git diff --check passed. Linux
package contents match the current workspace client, backend and settings.
