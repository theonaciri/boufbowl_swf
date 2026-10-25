# Original powers and approximate combat randomness

Introduced in `restoration-2012-v3`; retained by v4. V4 adds [maneuver grades and recovery](MANEUVERS_AND_RECOVERY.md). Existing matches keep their frozen powers and
distribution. No additional random draw is taken without `combat.random_score`.

## Stronger power evidence

Original client translations, before restoration edits:

```sh
git show e3d29c4:resources/lang.json
```

Read `classes_order_tooltip_desc_enum` and `classes_order_combatlog_desc_enum`.
They supply numbers missing from the designer's M07 post, including Pandawa:

| Class | Original described effect, now configured |
| --- | --- |
| Crâ | Allies +5 Air for the turn |
| Sram | Allies +5 Fire |
| Xélor | Allies +10 Water |
| Sacrieur | Allies −1 permanent HP, +5 Earth |
| Sadida | Allies +1 temporary HP, +2 Earth |
| Osamodas | Enemies −5 Air |
| Enutrof | Enemies −5 Fire |
| Roublard | Enemies −5 Earth |
| Eniripsa | Allies heal 2 HP, bounded by maximum HP |
| Féca | Allies gain a 2-HP shield for the turn |
| Iop | Every combat, on either team, deals +1 damage for the turn |
| Pandawa | Enemies −2 in all four characteristics |
| Écaflip | Reverse the teams targeted by the opposing ability |
| Zobal | Change mask for the rest of the match; different characteristics |

Element effects alter characteristics, never the three assigned order slots.
One special per team/turn, caster ordinary-action lock and stadium charge limits
remain. Temporary HP and shield expire separately from permanent HP. Sacrieur
HP cost bypasses attack shields. Iop extra damage passes through protection.

### Explicit remaining choices

- Team effects include the caster. Stat floor is zero. These conventions were
  already used by the reconstruction; the tooltips do not settle every boundary.
- Écaflip redirects team buffs, costs, healing, protection and debuffs by swapping
  recipient teams, without changing signs. This follows the original tooltip's
  **target** reversal. Two counterspells have no ordinary effect to redirect;
  self-only masks have no specified team recipient; global Iop stays global.
  Those exceptional combinations are not claimed as recovered server behavior.
- Shield absorbs before temporary HP, then permanent HP. Two global Iop effects
  add together. Historical stacking/expiry arithmetic is not fully recovered.
- The original mask tooltip identifies strong pairs: Water/Air, Earth/Air,
  Fire/Water. **Exact mask numbers remain missing.** The restoration sorts the
  player's existing four stat values and assigns the largest two to that pair.
  This adds no stat points; the detailed ordering is configurable `mask_order`.
  Masks remain marked unverified. Base stats are restored after each turn and
  the persisted mask reapplies before next turn's powers.

## Search for formula2.png (2026-10-24)

The server's `boufbowl-website-legacy` preservation project contains the original
HTML post `post:5206184`, also in `archive/8124b9cf36024d9a.html`:

- Intrinsic table: `http://staticns.ankama.com/comm/news/boufbowl/www/01_2012/formula1.png`
- CDF: `http://staticns.ankama.com/comm/news/akiba-manga/www/01_2012/formula2.png`

Its `archive/recovery-report.json` lists both as `unresolved_asset_references`;
neither is in `archive/assets.json`. Wayback CDX returned no captures for the
exact URLs, the CDF on `static.ankama.com`, or the alternate `boufbowl` path.
Arquivo.pt version history returned zero results. Direct CDN requests returned
empty HTML/HTTP202, not PNGs. Broader directory CDX queries timed out; this does
not establish that no copy exists anywhere. **No original image was recovered.**

## Requested approximation

M09's surviving text gives `F(0)=.5`, `F(-6)≈.15`, and `F(-35)<.001`.
Use a symmetric logistic CDF and its inverse:

```text
s = 6 / ln(17/3) ≈ 3.459
F(x) = 1 / (1 + exp(-x/s))
noise = s × ln(u / (1-u)), u from the turn's seeded RNG
```

It gives exactly .15 at −6 and about .0000403 at −35. The latter is only a
consistency bound, not a fit to the prose's incorrect `83−35=35` arithmetic.
This is **a chosen similar curve, not the recovered original CDF**. Endpoint
draws are bounded to machine epsilon before taking the logarithm.

The existing intrinsic-score proxy remains: characteristic plus configured
order/ability/next-combat bonuses. It is **not formula1.png**. One noise draw is
added to the attack-minus-defense margin; Fire-without-Earth defense uses Fire,
otherwise Earth. Either side may win. The absolute noisy margin selects the
existing normal/wide/critical consequences. Original boundary ambiguity remains.
A common shift makes wire scores nonnegative without altering their difference.
The trace retains raw draw, noise, model, scores, winner and severity.

V3 changes combat only. V4 separately adds provisional maneuver grades; see
[the chosen policy](MANEUVERS_AND_RECOVERY.md). Neither version claims original
odds for the still-unrecovered intrinsic table.

## Build and native playback

Game build, both application-root compilation, all three player packages and the
static website build succeeded. Published download copies match package hashes.
No automated test suite was run for this change.

Flash32 debugger through Hangover/FEX, 1024×600, target90FPS: two rendered CPU
turns acknowledged `RESOLUTION_DONE` and reached orders/turn3. Seeds 1178503745
and 1392524598; eight contacts included a wide outcome from a recorded logistic
draw. Powers exercised: Iop (+1, ten targets), Crâ (+5 Air) and Enutrof (−5 Fire).
This does not validate every counterspell, protection, mask or Android device.
Private evidence: `~/.cache/boufbowl-desktop-testing/powers-randomness/`.
