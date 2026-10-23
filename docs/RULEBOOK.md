# Boufbowl restoration rulebook

Profile: `restoration-2012-v2`. Evidence: preservation commit `484d203`.

Policy/evidence fingerprint: `9cd2e51e7a5e29250f9c8df217858dc0290bc1ef50c62f1cf81aa2277ac02967`.

Post-1.0.7 / 1.0.8 framework; February 2012 consequence semantics; incomplete original formulas

**Provisional does not mean historically verified.** The unknown original score table and random CDF are not reconstructed.

| Case | Rule | Status | Evidence | Decision |
| --- | --- | --- | --- | --- |
| C01 | Roster role cap | implemented | P09, P10 | Three per role across ten players; inactive old templates are editable but not playable until legal. |
| C02 | Five field players | implemented | M01 | Five owned players; role caps apply. |
| C03 | One team special | implemented | M07 | Client last assignment wins; malformed submitted double specials are rejected. |
| C04 | Caster replaces ordinary turn | implemented | M07 | Caster cannot combine ordinary assignments with a special. |
| C05 | Reserve recovery | provisional | M02 | Living reserves heal; field players retain HP; dead reserves stay dead pending revival evidence. |
| C06 | Water movement reliability | provisional | M03, M08 | One seeded draw at turn start; nonzero green risk and Water dependence use explicit replacement balance. |
| C07 | Water required to stand | implemented | P11 | Down players need Water; existing stand-up delay/resource budget retained. |
| C08 | Targeted combat consequences | provisional | M09 | Official consequence rows; existing deterministic score proxy and configurable threshold equality are unverified. |
| C09 | Incidental zero-damage stun | provisional | M09 | Normal incidental/dodge win stuns for zero HP damage; four-damage critical dodge down is a separate flag. |
| C10 | Pickup crowd pressure | provisional | M04 | Both teams count as pressure; radius and penalty are configurable replacement values. |
| C11 | Pickup prior combat losses | provisional | M04 | Each same-turn loss contributes a configurable pickup penalty; bookkeeping resets with the turn world. |
| C12 | Separate throw and catch | provisional | M05 | Separate throw/catch tests; failed tests scatter to a seeded point on the trajectory (replacement distribution). |
| C13 | Preassigned pass chains | implemented | M05 | Onward assignments survive until possession; flights chain; Air speeds travel using a configurable replacement coefficient. |
| C14 | Arrival deadline | implemented | M05 | Arrival must be before the discrete turn end. |
| C15 | Contact interrupts throw | provisional | M05 | Contact cancels an unlaunched carrier pass; converging trajectories may defer launch under an explicit timing heuristic. |
| C16 | Path interception | provisional | M05 | Path/height/radius samples plus a forward flight-segment filter; exact historical corridor and retries remain provisional. |
| C17 | Mid-turn stun recovery | provisional | M18, P16 | Water-based configurable stun duration allows a receiver to recover before ball arrival. |
| C18 | Ecaflip healing redirection | implemented | M07 | Only opposing Eniripsa healing is redirected; no opponent heal means no effect. |
| C19 | No five-score cutoff | implemented | P11 | Continue to the stadium turn limit; fifth score is not a cutoff. |
| C20 | Historical tournament format | custom | R06 | Keep the user-requested Saturday Paris qualifying/bracket competition. |
| C21 | Late tournament settlement | custom | R06 | Keep custom bracket settlement; historical timed-event accounting not claimed. |
| C22 | Reconnect grace | provisional | P11 | Two-minute grace after heartbeat loss detection; clocks continue; boundary and both-offline policy are explicit. |

## Configured class effects

These retain the requested custom profile; they are not a recovered historical spell table.

| Class | Configured effect | Historically verified |
| --- | --- | --- |
| Sadida | `{"range": -1, "target": "enemies"}` | no |
| Enutrof | `{"elements": {"EAU": 3}, "target": "allies"}` | no |
| Iop | `{"elements": {"TERRE": 3}, "target": "allies"}` | no |
| Osamodas | `{"elements": {"AIR": 1, "EAU": 1, "FEU": 1, "TERRE": 1}, "target": "allies"}` | no |
| Cra | `{"range": 1, "target": "allies"}` | no |
| Sacrier | `{"elements": {"AIR": 2, "EAU": 2, "FEU": 2, "TERRE": 2}, "hp": -1, "target": "allies"}` | no |
| Rogue | `{"hp": -2, "target": "enemies"}` | no |
| Eniripsa | `{"hp": 2, "target": "allies"}` | no |
| Xelor | `{"elements": {"AIR": 3}, "target": "allies"}` | no |
| Ecaflip | `{"redirect_enemy_heal": true, "target": "allies"}` | no |
| Zobal | `{"change_mask": true, "target": "allies"}` | no |
| Sram | `{"elements": {"FEU": 3}, "target": "allies"}` | no |
| Feca | `{"attack": -1, "target": "enemies"}` | no |
| Pandawa | `{"attack": 1, "target": "allies"}` | no |

## Configured attributes

Roles follow the recovered composition rule; numeric balance is not certified as the original table.

| Class | Role | Earth | Fire | Air | Water | HP | Regeneration interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CRA | Thrower | 8 | 8 | 16 | 10 | 16 | 3 |
| ECAFLIP | Runner | 11 | 11 | 11 | 9 | 16 | 3 |
| ENIRIPSA | Runner | 7 | 10 | 12 | 13 | 16 | 3 |
| ENUTROF | Thrower | 11 | 8 | 9 | 14 | 16 | 3 |
| FECA | Dodger | 14 | 12 | 8 | 8 | 16 | 3 |
| IOP | Blocker | 17 | 9 | 8 | 8 | 16 | 3 |
| OSAMODAS | Dodger | 10 | 10 | 10 | 12 | 16 | 3 |
| PANDAWA | Blocker | 14 | 8 | 10 | 10 | 16 | 3 |
| ROUBLARD | Thrower | 10 | 14 | 12 | 6 | 10 | 3 |
| SACRIEUR | Blocker | 16 | 12 | 6 | 8 | 16 | 4 |
| SADIDA | Runner | 10 | 9 | 8 | 15 | 13 | 2 |
| SRAM | Dodger | 9 | 17 | 10 | 6 | 11 | 3 |
| XELOR | Thrower | 7 | 12 | 15 | 8 | 16 | 3 |
| ZOBAL | Blocker | 12 | 11 | 10 | 9 | 16 | 3 |

## Match configuration

```json
{
  "turns_per_match": 24,
  "turns_per_period": 12,
  "class_ability_uses": 1,
  "placement_seconds": 60,
  "planning_seconds": 60,
  "max_players_per_role": 3,
  "regenerate_between_turns": true,
  "restart_recovery": "reserves",
  "roster_role_limit": 3
}
```

Use `--stadium KARA` (or another configured stadium) to print its resolved match/ability policy.

## Active reconstruction policy

These values are configurable replacement balance, not recovered historical constants.

```json
{
  "id": "restoration-2012-v2",
  "movement": {
    "safe_failure": 0.01,
    "water_stat": 0.05,
    "water_order": 0.1
  },
  "pickup": {
    "radius": 1,
    "nearby_penalty": 0.05,
    "loss_penalty": 0.05
  },
  "status": {
    "base_ticks": 20,
    "water_reduction": 1,
    "minimum_ticks": 1
  },
  "combat": {
    "official_effects": true,
    "boundary": "lower",
    "critical_dodge_down": false,
    "next_bonus": 1
  },
  "connection": {
    "heartbeat_timeout": 30,
    "grace_seconds": 120,
    "both_expired": "finish-current-score"
  },
  "passing": {
    "air_speed_bonus": 0.1,
    "favorable_timing": true,
    "scatter_failures": true,
    "path_interception": true
  }
}
```

## Still unresolved

- Intrinsic-value formula1.png and random CDF formula2.png
- Exact tier boundaries 0/15/30
- Critical-dodge knockdown
- Original movement/pressure/stun coefficients
- Original exact pass scheduler, pressure/quality transfer and scatter distribution
- Complete revival and ability inversion combinations

See [reconstruction choices](RULEBOOK_CHOICES.md) for formulas, boundaries, scope and compatibility.
See [original audit](RECOVERED_RULES.md) for provenance and the previous implementation baseline.

Generated by `python3 -m tools.rulebook --write docs/RULEBOOK.md` from `resources/rulebook.json` and the active configuration.
