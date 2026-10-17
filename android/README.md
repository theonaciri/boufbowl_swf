# Boufbowl Offline for Android

The APK packages the modified Flash client with the AIR Android runtime and all
game assets; website-only media is excluded. It runs the original ActionScript client without Wine. Assets are
local; persistent matches connect to the hosted server configured in
`resources/site.json` (`server_url`). Packaging starts in server mode by default;
`--server-url` explicitly overrides the hosted endpoint.

## Install

Use [BoufbowlOffline.apk](build/BoufbowlOffline.apk) on a **64-bit ARM Android
phone or tablet running Android 6 or newer**. Copy it to the device, open it, and
allow installation from that file manager when Android prompts. Launch
**Boufbowl Offline**. The game uses landscape orientation; tap the original
buttons and use **Tutorial** in the top toolbar to start playing.
The free AIR runtime displays its HARMAN/AIR splash screen during startup.
In the tutorial, drag a character's icon to the highlighted cell and tap **OK**
to confirm the movement order.

Offline menus, the tutorial, and the unlocked character roster are included.
The two special-character teams are **Offline Legends** and **Offline Heroes**.
Customization persists when connected to the replacement server. Missing regular
and hero animations use Cra while retaining original character illustrations.

The APK is signed with a local development certificate. Keep that certificate
if you want future builds to install as updates. Its private key is stored in
`~/.cache/boufbowl-flash-tools/android-signing/local.p12`, outside the APK.
On Android, pinch with two fingers to zoom the full game view between 70% and
400%. Zoom snaps to 100% when it enters the 95–105% range. The midpoint stays
anchored as you zoom; the game view moves with the gesture, and single-finger
taps and drags remain available.

## Rebuild on Linux

Requirements: **AIR SDK 51.4**, **JPEXS FFDec 26.3.0**, **JDK 17**, and
the Android SDK with platform 35 and build tools 35.0.1, plus **FFmpeg** with
the `libx264` encoder. AIR invokes Gradle,
which downloads build dependencies the first time.
Use JDK 17 for AIR 51.4.1.2: JDK 21 was not detected by its Android Gradle
packager and caused it to fall back to the legacy D8 path, which failed.

From `boufbowl_swf`:

```sh
python3 android/build.py \
  --air-sdk /path/to/AIRSDK \
  --ffdec /path/to/ffdec.jar \
  --jdk /path/to/jdk-17 \
  --android-sdk "$HOME/Android/Sdk"
```

Output: `android/build/BoufbowlOffline.apk`.
Use `--arch x64` for the separate emulator build. For your own PKCS12 signing
certificate, set `BOUFBOWL_KEYSTORE_PASSWORD` and add `--keystore /path/to/key.p12`.
The default certificate is intended for local testing and has the password
`SET_WITH_BOUFBOWL_KEYSTORE_PASSWORD`.

The build starts from the desktop's already patched SWF and applies the readable
classes in `android/patches/` to a separate staging copy:

- Asset and configuration URLs use `app:/assets` and `app:/resources`.
- `SwlAdapter` enables AIR code import for the packaged animation libraries.
- The toolbar's Quit button calls AIR's native application exit method.
- The Away3D COLLADA parser uses explicit XML namespaces and iteration for its
  texture and vertex lookups, including explicit namespaces for attributes.
  It converts XML values to strings before splitting them.
- The stadium scene is enabled so scripted tutorial animations have their
  original background.
- The five VP6/FLV clips are converted to H.264/AAC MP4 for Android playback.
  Dimensions and timing are preserved; the source FLV files are unchanged.
- Remote logging is replaced with console logging.
- The application descriptor enables automatic rotation between both
  landscape orientations, full screen, CPU rendering, and the Android package
  identity `air.org.boufbowl.offline`.

The desktop SWF and the original archive are unchanged by this build.

## Verification

Installed and rendered on an Android 15 x86_64 emulator. Checked offline launch
in airplane mode, Home, the Legends team, tutorial videos, the stadium during
scripted animations, and touch dragging a movement order.
The ARM64 APK's signature and ZIP integrity pass; its native library and APK
layout support 16 KB page alignment. The ARM64 package has not been tested on
a physical phone.

Screenshots: [Home](evidence/home.png), [Legends](evidence/legends.png),
[tutorial video](evidence/tutorial-entry.png), [stadium](evidence/tutorial-stadium.png),
[touch movement order](evidence/tutorial-drag.png).

Sources: [AIR packaging](https://airsdk.dev/docs/building/air-developer-tool/commands/package),
[AIR asset URLs](https://airsdk.dev/docs/development/security/security-sandboxes),
[AIR LoaderContext](https://airsdk.dev/reference/actionscript/3.0/flash/system/LoaderContext.html).

## Replacement server build

The current build merges all shared gameplay/Cra fallback patches with Android
platform overrides. It defaults to live server mode. Enter the Linux computer's
LAN URL in the connection panel; start that service with
`python3 -m backend.server --host 0.0.0.0 --port 9900`. Android hosts the client;
the authoritative server and SQLite database run on Linux.

The latest replacement-server APK was compiled and its package/signature checked
on Ubuntu. No Android device/emulator is currently attached, so the new live
backend flows have not been verified on Android hardware. The earlier emulator
checks above apply to the prior offline build.

### Build for the website's shared server

Pass `--server-url https://YOUR_SERVER` to the build command to set the default
remote endpoint in the packaged Android client. Existing saved connection choices
remain available. The website discovers `android/build/BoufbowlOffline.apk` and
links it at `/downloads/BoufbowlOffline.apk`; no public GitHub release is required.
Rebuild when the remote server URL changes. On ARM Linux build hosts, the Android
SDK's host tools must be ARM-compatible; the upstream Linux command-line package
may contain x86-64 `aapt`/`aapt2` binaries.

On an ARM64 build host, Gradle may select an x86-64 AAPT2 executable. Configure
`android.aapt2FromMavenOverride=/path/to/host-compatible/aapt2` in
`~/.gradle/gradle.properties` to use a compatible executable or emulation wrapper.
The AIR SDK and Gradle must both be able to run their Android packaging tools.
