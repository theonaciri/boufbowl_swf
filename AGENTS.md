# Working in this repository

Start with `git status --short` and [docs/CODE_MAP.md](docs/CODE_MAP.md).
Preserve unrelated edits; stage only task-specific files/hunks.

## Navigation and ownership

- Trace entry point → caller → state mutation → callback → relevant test.
  Use `rg -l`, then bounded method reads. Avoid recursive dumps of decompiled
  sources, generated SWFs, logs or `.local`.
- Shared AS3: `patches/`; Android overrides: `android/patches/`.
  `tools/client_patches.py` discovers both. Root policy: `ClientRuntime.as.inc`
  via `tools.client_runtime_codegen.client_root_source`. Keep touch/layout and
  Ruffle skins platform-specific.
- Missing override: selectively export the class with FFDec:
  `-selectclass '<fully.qualified.Class>' -export script <scratch> <swf>`.
  `-select` means frame ranges. Rename opaque locals only in touched methods.
- Avoid side effects such as `counter++` in field initializers: FFDec26.3 can
  clobber constructor registers. Assign IDs explicitly after `super()`; see
  [performance findings](docs/PERFORMANCE.md).
- Python/Bun backend owns outcomes; AS3 renders scenarios. Follow 3D issues through
  `backend/turn_adapter.py` → `ScriptBuilder` → actions/models/presenters.
  Preserve ordering and `RESOLUTION_DONE`. Rules/evidence: `docs/RULEBOOK*.md`.
- Website sources: root HTML/CSS/JS and `tools/website/`. Generated outputs:
  `dist/`, compiled clients and packages. Tool discovery: `tools/build_tools.py`.
  Preserve Android signing credentials. Record findings in focused docs.

## Build and test

```sh
bun run build                                      # Game
python3 -m tools.verify_client --area compile        # Both application roots
bun run build:players --platform android --no-website
bun run build:website
./play.sh --show-fps --scene-3d
```

- Rebuild shared AS3 **before** `--area compile`: it uses the existing SWF.
  Rebuild/install APKs before testing changes. Other focused areas:
  `shared|cpu|web|all|native`; inspect JSON/logs in `.local/verification/<area>/`.
- **Prefer Android**: phone or native ARM64 Redroid 15. This host lacks usable KVM;
  Android 16 SurfaceFlinger and attempted x86 emulators failed here.
  Desktop fallback: Hangover 11.16, `HODLL=libwow64fex.dll`; default Box64 stalled.
  AIR smoke tests need licensing and do not validate Android devices.
- [docs/NATIVE_TESTING.md](docs/NATIVE_TESTING.md) has runnable recipes. Use isolated
  databases/profiles; keep runtimes/recordings outside the repo, diagnostic SWFs
  in `.local/client-probes`. Production restarts/deployment need separate authority.
- Runtime success requires rendered 3D, real client `RESOLUTION_DONE`, and next
  turn; include combat for interaction changes. Compilation/lobby boot is weaker.
- Compare fixed seeds/rosters/orders/resolutions and result hashes. Measure
  `game_frames` plus CPU; frame-event FPS differs from video/GPU FPS. Check capture
  ON/OFF, actual Wine client dimensions (`SetWindowPos`, not X11 clipping), and
  decoded video frames. Use H.264 YUV420P. Details: `docs/PERFORMANCE.md`.
