# Native client validation

The manual `Native client validation` GitHub workflow targets a self-hosted Linux
runner labeled `boufbowl-air`. Provision that runner with Python, Bun, Java 17+,
FFDec, Xvfb, AIR's shared-library dependencies, and a host-compatible AIR SDK
licensed to execute applications. Use the build-tool discovery settings described
in [BUILD.md](BUILD.md), or pass `--air-sdk` and `--runtime-libs` directly to the
smoke command. Licensing stays on the runner; no credentials belong in Git.

The pinned actions use verified v7 tags from the official
[checkout](https://github.com/actions/checkout) and
[upload-artifact](https://github.com/actions/upload-artifact) repositories. Keep
the self-hosted Actions runner current for their Node 24 runtime.

Run locally:

```sh
python3 -m tools.verify_client --area compile
python3 -m tools.verify_client --area native
```

The first compiles instrumented desktop and Android roots and reports `compiled`.
It needs Java/FFDec, not an executable or licensed AIR SDK. The second executes
both roots with isolated app ids/preferences and a 30 FPS saved cap. It requires
the shared smoke checks, 3D mode, ResolutionDone acknowledgement, and MATCH_END.
The Android root runs in desktop AIR; device touch input and GPU behavior still
need device testing.

The native smoke prints one JSON report and saves it under `.local/shared-client`.
The wrapper keeps logs and a compact summary under `.local/verification/native`.
Source/tool/base-client fingerprints cache disposable probes under
`.local/client-probes`; unchanged checks reuse compilation. These instrumented
SWFs never replace the production client or enter download packages.

Exit 0 means passed execution (or compiled when explicitly requested). Exit 77
means execution was blocked, including the AIR developer-license gate; CI does
not count that as success. Exit 1 means compilation or validation failed. A
license rejection is reported once, without repeatedly attempting execution for
the second root. This repository supplies the workflow and checks; it does not
provision a machine or provide an AIR developer license.
