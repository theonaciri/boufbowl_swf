# Working in this repository

Start with `docs/CODE_MAP.md` and `git status --short`. Preserve unrelated edits;
stage only files or hunks belonging to the current task.

Trace the reported behavior through its entry point, caller, state mutation,
callback and relevant test. Use `rg -l` to find candidate files, then bounded
method reads. Expand only when the current path does not explain the behavior.
Avoid recursive dumps of decompiled sources, generated SWFs, logs or `.local`.

Use `python3 -m tools.verify_client --area shared|cpu|web|all|compile|native` for
compact JSON results and log paths. Read a failing check's log before broadening
validation. Compilation and a blocked native runtime are not runtime passes.

Both client builds use `tools/client_patches.py`. New shared `.as` overrides
belong in `patches/`; same-named Android overrides belong in `android/patches/`.
Shared application-root policy belongs in `patches/ClientRuntime.as.inc`, expanded
through `tools.client_runtime_codegen.client_root_source`. Keep platform-specific
touch input, stage layout and Ruffle skins in their existing platform paths.

When touching a decompiled method, replace opaque local names in that method
with semantic names. Keep unrelated methods unchanged. Record durable findings,
runtime boundaries and validation limitations in the focused docs linked from
the code map. Generated diagnostic clients stay under `.local/client-probes`.
