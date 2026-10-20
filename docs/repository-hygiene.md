# Source inputs and generated outputs

Git preserves the files needed to recreate the project: readable patches, tools,
configuration, original artwork and sound libraries, FLV archives, reference
images, fonts, and the required game build input. Local builds, captures,
databases, credentials, and generated reports are ignored.

## Preserved game binary

`bin/base/boufbowl-client-1.9.6.swf` is the required input used by
`patches/rebuild.py`. Its SHA-256 is
`b13475e837bec851157e5d02b45088d1f697ad65121a383d3e40b43074883154`.
It is a previously patched baseline. An untouched historical game binary has
not been verified in this checkout. Preserve this input exactly; use
`--original /path/to/archive.swf` when supplying another source archive.

## Regenerate local outputs

Run these commands from the repository root with JDK 17, FFDec, Bun, FFmpeg,
and the website renderer dependencies installed as described in the build guides.

| Output | Generator |
| --- | --- |
| `bin/boufbowl-client-1.9.6.swf` and `assets/models/stadiums/theme_*` | `python3 patches/rebuild.py --ffdec /path/to/ffdec.jar` |
| `backend/build/engine_base.json` | `cp backend/engine_base.json backend/build/engine_base.json` |
| Interaction JSON/record pairs for pickup, combat, reception, interception, rebound, ability, and goal | `python3 -m tools.build_interaction_fixtures` |
| Interaction JSON/record pairs for pickup, combat, reception, interception, rebound, ability, and goal | `python3 -m tools.build_interaction_fixtures` |
| `resources/mock_match.json` | `python3 -m tools.build_mock_fixture` |
| Legal HTML pages | `python3 -m tools.build_legal_pages` |
| Tutorial MP4s and poster | `python3 -m tools.build_site_videos` |
| Portraits, grid icons, inventory, manifests, and website delivery | `python3 -m tools.build_website` |
| Legendary carousel AVIF, MP4, and WebP exports | `python3 -m tools.export_home_cinematics` |
| Gameplay puppet videos and posters | `python3 -m tools.export_puppet_videos` |
| Website benchmark reports | `python3 -m tools.benchmark_website` |

Build the client before exporting website characters. For a complete new website
build, create the inventory with `python3 -m tools.build_restoration_data`, export
the carousel and puppets, and finish with `python3 -m tools.build_website` to
refresh manifests and assemble the public delivery. Historical carousel exports
are superseded by the current legendary selection.

The following inputs are retained because the current scripts need external
sources that are absent from this checkout:

- `backend/build/engine.js`: the only available simulator implementation. A full
  rebuild with `bun backend/build-worker.ts` requires `boufbowl_server/src`.
- `tests/fixtures/movement_engine_turn.json`: a preserved input for interaction
  fixture generation; the original TypeScript probe needs the absent simulator sources.
- `tests/fixtures/movement_engine_turn.json`: a preserved input for interaction
  fixture generation; the original TypeScript probe needs the absent simulator sources.
- `protocol/*.json` and `docs/protocol-matrix.md`: extracted contracts whose
  generators require the recovered ActionScript source tree.
- `vendor/ruffle`: third-party browser runtime supplied as build input.
- Manual reference images and recovered game asset libraries without an included
  regeneration script.

## Signing and local data

Android's default signing certificate lives in the user cache under
`boufbowl-flash-tools/android-signing/`. A newly created certificate receives a
random password stored in `local.password` with mode `0600`. For an existing
certificate without that file, set `BOUFBOWL_KEYSTORE_PASSWORD`. Keep the
certificate to preserve the signing identity required for application updates.
Custom certificates also use `BOUFBOWL_KEYSTORE_PASSWORD`.

Private keys, signing files, environment files, SQLite databases, server metadata,
and `.local/` state must stay outside versioned history. After a published history
rewrite, collaborators should clone the cleaned repository again rather than
merge old branches, which would restore removed content.
