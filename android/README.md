# Boufbowl Offline for Android

The APK packages the modified Flash client with the AIR Android runtime and all
90 game asset files. It runs the original ActionScript game. Wine and a separate
game or asset server are not needed on Android.

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
Customization changes last for the current session. Online matches still need
a game server. The hero previews use original illustrations; the archive did
not contain their individual animated skins.

The APK is signed with a local development certificate. Keep that certificate
if you want future builds to install as updates. Its private key is stored in
`~/.cache/boufbowl-flash-tools/android-signing/local.p12`, outside the APK.

## Rebuild on Linux

Requirements: **AIR SDK 51.4**, **JPEXS FFDec 26.3.0**, **JDK 17 or newer**, and
the Android SDK with platform 35 and build tools 35.0.1, plus **FFmpeg** with
the `libx264` encoder. AIR invokes Gradle,
which downloads build dependencies the first time.

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
- The application descriptor sets landscape orientation, full screen, CPU
  rendering, and the Android package identity `air.org.boufbowl.offline`.

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
