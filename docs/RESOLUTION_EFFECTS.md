# Original 3D effects

`backend/turn_adapter.py` maps authoritative events to original SWF interactions.
It must not roll probabilities, award bonuses or turn a failed action into a KO.

## Restored presentation

- Combat: dodge → `DODGE`; incidental hit → `HIT_AND_RUN`; targeted hit
  against Fire without Earth → `TACKLE`; other targeted hit → `BRAWL`.
  This is a restoration selection policy, inferred from original interaction
  scripts and `BoufbowlerBaseInformation.isDodging`, not recovered server code.
  Winner, tier, damage and stun/down remain the simulator's decision.
- Running actions borrow one subsequent, adjacent, recorded movement step.
  Stop at another interaction or the actor's status transition. Remove that
  step's standalone playback; never invent a cell or change the recorded world.
  This enables original running pickup/pass/reception and directional shoulder
  checks. Interaction ordering and completion joins remain unchanged.
- `granted_bonus` forwards the actual next-combat award to `fightBonusMalus`.
  Pickup pressure forwards its actual penalty sign to `maneuverBonusMalus`;
  percentage-point units are presentation metadata, not another gameplay penalty.
  Original wire fields are unsigned; the signed consumer needs two's-complement
  encoding for a malus. Original FX displays only the sign.
- Stun duration includes inserted presentation slots up to the actor's recorded
  recovery. Otherwise stars can expire before the hit animation reaches them.
- `HitAndRunFunction` stores the supplied outcome tier, fixing the original
  missing assignment that suppressed its large critical damage number.

Original hooks: `FxSprites`, `InteractionComputer`, `CommonInteractionFunctions`,
`BrawlFunction`, `TackleFunction`, `HitAndRunFunction`, `PickUpFunction`,
`PassFunction`, `ReceptionFunction`, `InterceptionFunction`, `MovementFailFunction`.
Selective exports for this audit are disposable under `.local/client-probes/`.

## Critical maneuvers: supported messages, unresolved scoring

Explicit authoritative `tier=normal|wide|critical` is preserved in ball-action
tests, along with recorded damage/KO/stun consequences. Critical reception
links throw → failed reception → rebound, enabling the original hit/fumble
branches. Ordinary failures retain their original noncritical behavior.

Profiles v1–v3 produce boolean ball tests. V4 activates seeded grades and their
original presentation consequences under an explicit **replacement** scoring
policy; it does not recover the historical maneuver formula. See
[maneuver choices](MANEUVERS_AND_RECOVERY.md). A critical interception falls
without terminating the flight; a critical reception links to a separate rebound.

`FX_ratage` already runs on movement/pickup/throw/reception failures and combat
losses. Ordinary failed interception intentionally has no cloud in the original
script. Its bonus/malus feedback is conditional on actual supplied modifiers.

## Native check (2026-10-24)

Flash32 debugger through Hangover/FEX, 1024×600, target90FPS: three CPU turns
rendered and sent real `RESOLUTION_DONE`; continued to placement/turn4.
Seeds: 683595876, 1814522046, 2067811494. Seven incidental hits and one tackle;
three moving interaction tracks. Both application roots compiled. This does not
validate every direction, critical maneuver or Android hardware rendering.
Private evidence: `~/.cache/boufbowl-desktop-testing/effects-audit/`.
