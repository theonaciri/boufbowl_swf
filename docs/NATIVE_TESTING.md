# Native client testing

Prefer a phone or native ARM64 **Redroid 15** on this host. Desktop Flash uses
x86 emulation; both server paths use software graphics. Recipes below assume
repository-root cwd. Build/tool discovery: [BUILD.md](BUILD.md).

## Build

```sh
bun run build
python3 -m tools.verify_client --area compile
bun run build:players --platform android --no-website
```

`--area compile` replaces roots in the existing SWF; rebuild shared patches first.
An existing APK/download remains stale until repackaged.

## Android device

Use `adb` from PATH or the Android SDK's `platform-tools`:

```sh
adb install -r 'android/build/Boufbowl Fan.apk'
adb reverse tcp:41983 tcp:41983
adb shell am start -W -n air.org.boufbowl.offline/.AIRAppEntry
```

In **Server**, connect to `http://127.0.0.1:41983` through that reverse mapping.
Use a separate backend database/profile.

Android root mutes `SoundMixer` on NativeApplication deactivation and restores
the previous master transform on activation. Category preferences are untouched;
duplicate deactivations must not replace the saved transform with silence.
Device check: music → Home/lock → silence → return → previous volume, including
zero-volume settings. This mutes output; it does not pause server match timers.

## Redroid on this ARM64 host

External helpers require rootful Podman and `binder_linux`. They recreate the
removed Android image/data: Android 15/API35, ARM64, memfd, ANGLE/SwiftShader,
640×376 at 60 Hz. No KVM or outbound network. Dismiss fullscreen help.

```sh
trial="$HOME/.cache/boufbowl-android-testing/performance"
"$trial/start-trial.sh" "$PWD/android/build/Boufbowl Fan.apk"
"$trial/podman-trial" exec boufbowl-redroid-performance /system/bin/wm density 160
```

Run the backend in that network namespace, in another terminal:

```sh
trial="$HOME/.cache/boufbowl-android-testing/performance"
redroid_pid=$("$trial/podman-trial" inspect --format '{{.State.Pid}}' boufbowl-redroid-performance)
sudo nsenter -t "$redroid_pid" -n -- runuser -u "$USER" -- \
  env PYTHONPATH="$PWD" python3 -m backend.server --host 127.0.0.1 \
  --port 41983 --database "$trial/manual-test.sqlite"
```

Set **Server** to `http://127.0.0.1:41983`; start a CPU match. External benchmark
scripts retain old PIDs/ports: adapt before reuse. The older
`redroid-20261024` helper uses 1280×720 **15 Hz**, unsuitable for FPS comparisons.

```sh
"$trial/podman-trial" exec boufbowl-redroid-performance /system/bin/screencap -p > "$trial/game.png"
"$trial/podman-trial" exec boufbowl-redroid-performance /system/bin/screenrecord \
  --time-limit 120 --size 640x376 --bit-rate 2000000 /data/local/tmp/game.mp4
"$trial/podman-trial" exec boufbowl-redroid-performance /system/bin/cat \
  /data/local/tmp/game.mp4 > "$trial/game.mp4"
```

After stopping the recording/backend:

```sh
"$trial/podman-trial" stop -t 5 boufbowl-redroid-performance
"$trial/podman-trial" rm boufbowl-redroid-performance
sudo umount "$trial/binderfs"
```

Keep scripts/evidence; remove disposable OS data/images. Do not force-unload busy
kernel modules. Android 16 failed in SurfaceFlinger here; x86 Emulator 37.2.12
(API36/API28) failed to boot through compatibility layers without usable KVM.

## Desktop on this ARM64 host

Tested: Hangover 11.16 / Ubuntu26.04 ARM64, Windows i386 Flash32. Select FEX;
default Box64 stalled. Cache: `~/.cache/boufbowl-desktop-testing/`.

```sh
desktop_trial="$HOME/.cache/boufbowl-desktop-testing"
python3 -m backend.server --host 127.0.0.1 --port 41984 \
  --database "$desktop_trial/manual-test.sqlite"
```

In separate terminals, start Xvfb and launch:

```sh
Xvfb :118 -screen 0 1280x800x24 -nolisten tcp -ac
```

```sh
desktop_trial="$HOME/.cache/boufbowl-desktop-testing"
game_origin='http://127.0.0.1:41984'
DISPLAY=:118 WINEPREFIX="$desktop_trial/wine-prefix" WINEDEBUG=-all \
  WINEDLLOVERRIDES='mscoree,mshtml=' HODLL=libwow64fex.dll \
  "$desktop_trial/runtime/usr/bin/wine" "$PWD/bin/flashplayer_32_sa.exe" \
  "$game_origin/bin/boufbowl-client-1.9.6.swf?server=1&backend=$game_origin&profile=DesktopTrial&lang=en&scene3d=1&showFps=1&clientRuntime=flash"
```

Normal desktop launcher: `./play.sh --show-fps --scene-3d`.
For 640×375 content, use Windows `SetWindowPos`/`WM_SIZE`; X11 resizing only clipped
this window. Cached helper: `cpu-small/resize.c` / `resize.exe`; run with the same
Wine environment. Inspect `DISPLAY=:118 xwininfo -root -tree` for fresh geometry.
Original content is 1024×600, plus a 19px menu.

Example capture for the verified 640×394 window at (8,60); adjust coordinates:

```sh
ffmpeg -y -f x11grab -framerate 15 -video_size 640x394 -i :118+8,60 \
  -t 120 -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p \
  -movflags +faststart "$desktop_trial/game.mp4"
```

Decode/check a frame before sharing; YUV444P displayed black for the user.
Stop the test backend/Xvfb and only the isolated prefix:

```sh
WINEPREFIX="$desktop_trial/wine-prefix" "$desktop_trial/runtime/usr/bin/wineserver" -k
```

## AIR diagnostics and smoke harness

```sh
python3 android/build.py --diagnostic --no-website
python3 -m tools.verify_client --area native
```

- Diagnostic APK: `android/build/Boufbowl Fan-diagnostic.apk`; standalone runtime
  with SWF debug locations. `--debug` instead waits for a debugger on port7936;
  `--arch x64` selects emulator packaging. Preserve app ID/signing credentials.
- Error1065 at `runtime policy` was FFDec compiling `flash.utils.getTimer()` as
  `getlex flash`. Keep the explicit import and bare `getTimer()` in shared roots.
- AIR smoke executes both roots at a saved 30FPS cap; Android-on-desktop AIR is
  not a device test. Requires licensed host-compatible AIR, Xvfb and dependencies.
  CI runner label: `boufbowl-air`. Reports: `.local/verification/native/` and
  `.local/shared-client/`; probes: `.local/client-probes/`.
- Exit0: executed/compiled as requested; exit77: blocked (including licensing);
  exit1: failed. Do not retry a license block as though it were a client bug.

## Acceptance and measurements

Require actual 3D, real client `RESOLUTION_DONE`, then next turn. Include combat;
check `MATCH_END` for end-flow changes. Record build hashes, runtime, dimensions,
orders and targetFPS. Never inject completion to claim success.

Use `game_frames` and process CPU/RSS (100% = one CPU). Match seeds/rosters/orders
and result hashes; warm up and bracket recording ON with OFF runs. Frame-event,
video and GPU FPS differ. Keep session-bearing logs/DBs private. Earlier videos
do not validate later code. Results: [PERFORMANCE.md](PERFORMANCE.md).

## Power description tooltips

Standard game tooltips open on click/tap: power icons, element gauges, health,
regeneration, character/role information, tournament rewards and controls using
`setTooltip`. Click again or press elsewhere to dismiss. Hover keeps its 300ms
delay. Changed content, disabled controls and removed owners dismiss stale text.

`BaseComponent.as` runs ordinary click actions first without cancelling them;
removed/disabled sources do not open orphan tooltips. Nested controls select the
deepest tooltip owner. Inline graphics use the same factories as hover.
`TooltipFrameMediator.as` owns the pinned state; there is no power-only override.

A disposable compiled Ruffle probe passed 25 event-level checks, including power
regressions, generic information, nested targets, graphics, repeated assignment,
button actions and lifecycle cleanup. Real Ruffle clicks were also checked.
Native Android touch delivery still requires an installed APK check.

## Match setup page

Play uses the original full-page matchmaking view. Match/challenge tabs share
one stadium selection; zero means a random enabled stadium. Hover previews do
not change selection, and a click needs no preceding hover. The left panel
contains team selection, random choice, CPU, queue cancellation, tournament entry
and community access. State updates use existing server metadata events.

CPU/challenge requests draw one enabled stadium when random is selected. Human
matchmaking draws from the intersection of both players’ accepted stadiums;
opponent/rating ordering is unchanged. Tournament stadiums follow the event.

```sh
python3 -m unittest tests.test_accounts_matchmaking tests.test_public_tournaments
```

39 tests passed, including forced non-first stadium selection, disjoint pools and
per-stadium waiting counts.
Isolated Ruffle checks covered team/card updates, no-hover taps, hover stability,
shared selection/reset, queue/cancel, tournament/cancel, challenge/cancel and CPU
launch. Layout checked at the authored 1024×600 viewport. Native touch remains a
phone check after installing the new APK.

Stadium badges count other live regular-queue players who accept that stadium;
self, blocks, tournament queues, expired searches and active matches are excluded.
One player may count on several stadiums; rating matching still applies. Counts
travel in existing matchmaking metadata. Ruffle checks verified nine badges per
tab, click-through selection and refresh after queue departures.
