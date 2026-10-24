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

## Android startup and diagnostics

For an APK that runs independently and shows startup locations:

```sh
python3 android/build.py --diagnostic --no-website
```

This produces `android/build/Boufbowl Fan-diagnostic.apk`, using the normal AIR
runtime with debug locations in a separately cached SWF. The production APK and
compiled release client stay separate. `--arch x64` selects emulator packaging.
`--debug` instead includes AIR's debugger runtime and waits for a USB debugger
on port 7936; it is not a standalone diagnostic download. Both modes preserve
the application ID and signing certificate so existing app data is retained.

Android registers startup error handling before initializing logging, catches
synchronous root startup errors, and displays the last startup phase. Diagnostics
and configuration-loading errors use device fonts; the retained MainApp's
embedded-Verdana error field could otherwise render invisibly. Private local
startup diagnostics remain in `.local/client-probes`; never package them as game
assets or source files.

### Confirmed native timer binding fix

A phone screenshot isolated Error #1065 to `runtime policy`. The packaged root's
P-code showed that FFDec compiled `flash.utils.getTimer()` into `getlex flash`,
`getproperty utils`, and `callproperty getTimer`. Native AIR has no lexical
variable named `flash`, so startup stopped before configuration loading.

`tools/client_runtime_codegen.py` now imports `flash.utils.getTimer` explicitly
in both roots, and `patches/ClientRuntime.as.inc` calls `getTimer()` directly.
The correction covers startup and all measurement callbacks. Shared-root
regressions require a single explicit import and reject the ambiguous spelling.
The rebuilt ARM64 APK contains direct native timer references and no `getlex
flash`; its website copy matches the build output checksum. The user confirmed
successful phone startup. This confirms boot, not a complete gameplay/device
regression pass. Logger and dependency-injection behavior was not changed.

### Local execution limits

The ARM64 server has no usable KVM device. Android Emulator 37.2.12 was attempted
through an x64 compatibility layer: API 36 stalled during kernel setup, and API
28 exceeded Android's device-discovery boot timeout. No APK ran in those guests.
The attempted emulator downloads and virtual disks were removed after diagnosis;
compact evidence remains under `.local/verification/android-startup/`. Use an
Android device or an emulator host with working virtualization for runtime checks.
