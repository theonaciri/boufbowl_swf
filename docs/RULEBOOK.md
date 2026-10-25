# Boufbowl restoration rulebook

Profile: `restoration-2012-v4`. Evidence: preservation commit `484d203`.

Policy/evidence fingerprint: `53ad6644596c6aba70dd202ba16c85347edac733c096163363ca733bd603ad1b`.

Post-1.0.7 / 1.0.8 framework; February 2012 consequence semantics; incomplete original formulas

**Provisional does not mean historically verified.** The unknown original score table and random CDF are not reconstructed.

| Case | Rule | Status | Evidence | Decision |
| --- | --- | --- | --- | --- |
| C01 | Roster role cap | implemented | P09, P10 | Three per role across ten players; inactive old templates are editable but not playable until legal. |
| C02 | Five field players | implemented | M01 | Five owned players; role caps apply. |
| C03 | One team special | implemented | M07 | Client last assignment wins; malformed submitted double specials are rejected. |
| C04 | Caster replaces ordinary turn | implemented | M07 | Caster cannot combine ordinary assignments with a special. |
| C05 | Reserve recovery | provisional | M02 | Rested reserves regain maximum HP, including dead reserves under the explicit v4 revival policy. Former field players retain HP; no immediate revival or ability-charge reset. Complete historical revival semantics are unknown. |
| C06 | Water movement reliability | provisional | M03, M08 | One seeded movement draw; Water-dependent replacement risk. On route completion, wide/critical success grants a nonstacking next-action bonus, expiring at turn end. Grading and coefficients are reconstruction choices. |
| C07 | Water required to stand | implemented | P11 | Down players need Water; existing stand-up delay/resource budget retained. |
| C08 | Targeted combat consequences | provisional | M09 | Official consequences; seeded logistic margin noise approximates M09 probabilities. Intrinsic score proxy and exact boundaries remain provisional. |
| C09 | Incidental zero-damage stun | provisional | M09 | Normal incidental/dodge win stuns for zero HP damage; four-damage critical dodge down is a separate flag. |
| C10 | Pickup crowd pressure | provisional | M04 | Both teams count as pressure; radius and penalty are configurable replacement values. |
| C11 | Pickup prior combat losses | provisional | M04 | Each same-turn loss contributes a configurable pickup penalty; bookkeeping resets with the turn world. |
| C12 | Separate throw and catch | provisional | M05, CLIENTFX | Separate seeded throw/catch tests with configurable log-odds maneuver grades. Critical throw stuns; critical pickup/reception/interception knocks down without invented HP damage. A failed interception does not terminate flight. Thresholds and severity probabilities are provisional. |
| C13 | Preassigned pass chains | provisional | M05 | Preassigned passes chain. Successful reception grants a quality-dependent next-throw bonus in v4, consumed once and expiring at turn end. Air travel coefficient and bonus magnitude are provisional. |
| C14 | Arrival deadline | implemented | M05 | Arrival must be before the discrete turn end. |
| C15 | Contact interrupts throw | provisional | M05 | Contact cancels an unlaunched carrier pass; converging trajectories may defer launch under an explicit timing heuristic. |
| C16 | Path interception | provisional | M05 | Path/height/radius samples plus a forward flight-segment filter; exact historical corridor and retries remain provisional. |
| C17 | Mid-turn stun recovery | provisional | M18, P16 | Water-based configurable stun duration allows a receiver to recover before ball arrival. |
| C18 | Ecaflip healing redirection | implemented | M07, CLIENT19 | Original client target reversal for team-targeted powers; self-only masks and two counterspells have no redirectable team target. |
| C19 | No five-score cutoff | implemented | P11 | Continue to the stadium turn limit; fifth score is not a cutoff. |
| C20 | Historical tournament format | custom | R06 | Keep the user-requested Saturday Paris qualifying/bracket competition. |
| C21 | Late tournament settlement | custom | R06 | Keep custom bracket settlement; historical timed-event accounting not claimed. |
| C22 | Reconnect grace | provisional | P11 | Two-minute grace after heartbeat loss detection; clocks continue; boundary and both-offline policy are explicit. |

## Configured class effects

Values follow the preserved original client tooltips. Mask numbers and exceptional inversion/stacking cases remain provisional.

| Class | Configured effect | Historically verified |
| --- | --- | --- |
| Sadida | `{"elements": {"TERRE": 2}, "target": "allies", "temporary_hp": 1}` | yes |
| Enutrof | `{"elements": {"FEU": -5}, "target": "enemies"}` | yes |
| Iop | `{"combat_damage": 1, "target": "all"}` | yes |
| Osamodas | `{"elements": {"AIR": -5}, "target": "enemies"}` | yes |
| Cra | `{"elements": {"AIR": 5}, "target": "allies"}` | yes |
| Sacrier | `{"elements": {"TERRE": 5}, "hp": -1, "target": "allies"}` | yes |
| Rogue | `{"elements": {"TERRE": -5}, "target": "enemies"}` | yes |
| Eniripsa | `{"hp": 2, "target": "allies"}` | yes |
| Xelor | `{"elements": {"EAU": 10}, "target": "allies"}` | yes |
| Ecaflip | `{"redirect_enemy_ability": true, "target": "allies"}` | yes |
| Zobal | `{"change_mask": true, "mask_order": {"1": ["endurance", "precision", "agility", "strength"], "2": ["strength", "precision", "endurance", "agility"], "3": ["agility", "endurance", "precision", "strength"]}, "target": "allies"}` | no |
| Sram | `{"elements": {"FEU": 5}, "target": "allies"}` | yes |
| Feca | `{"shield": 2, "target": "allies"}` | yes |
| Pandawa | `{"elements": {"AIR": -2, "EAU": -2, "FEU": -2, "TERRE": -2}, "target": "enemies"}` | yes |

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
  "id": "restoration-2012-v4",
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
    "next_bonus": 1,
    "random_score": {
      "model": "logistic-approximation",
      "scale": 3.4590086183578026
    }
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
  },
  "maneuvers": {
    "wide_margin": 15,
    "critical_margin": 30,
    "movement_bonus": 1,
    "reception_throw_bonus": 1,
    "critical_failures": true
  },
  "recovery": {
    "revive_rested_reserves": true
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
