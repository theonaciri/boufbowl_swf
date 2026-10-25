# Client releases and updates

Public version starts at **0.1.0** in `resources/release.json`; the preserved
SWF/protocol identifier1.9.6 stays unchanged. Bump it only for client or game-server changes: fixes → PATCH, features → MINOR,
incompatible changes → MAJOR. Website-only and documentation edits need no bump.

```sh
bun run version:bump patch       # 0.1.0 → 0.1.1; also increments Android build
bun run version:bump minor       # e.g. 0.1.1 → 0.2.0
bun run version:bump major       # e.g. 0.2.0 → 1.0.0
bun run build:players            # Incremental packages + website/update manifest
bun run release                 # Also refresh website media; explicit full release
```

Android's old APK had versionCode1000000. Internal AIR `versionNumber` starts
at1.0.1 (code1000001); public `versionLabel` is0.1.0. The bump command keeps the
internal code increasing independently of semantic version resets. Preserve the
existing APK signing certificate and password; never uninstall to upgrade.

## Delivery

- **Windows/Linux:** bundled native bootstrap checks `updates.json` before
  launching Flash. Verify the pinned Ed25519 signature, version, HTTPS origin,
  package size and SHA256. Download to a temporary file, then atomically publish
  into the user's cache. Retain the last complete signed package as an offline
  fallback. Never modify an already-running match or its extracted assets.
- **Android:** nonblocking startup check; a newer APK adds a French update
  button. It opens the trusted website download after the match. The user handles
  installation in Android. There is no silent APK installation or downloaded AS3.
- **Web:** startup, return-to-tab and30-minute checks. A newer version offers
  reload/later; reloading requires confirmation. No automatic mid-match reload.

Existing installations need **one manual upgrade** to acquire this updater.
Subsequent desktop launches update automatically. Desktop updates currently
fetch full executable packages; unchanged assets remain bundled/offline.
The Linux desktop shortcut and extracted archive entry points invoke the updater.

## Publishing and keys

`bun run updates:key` creates an Ed25519 private key under
`~/.config/boufbowl/update-signing.pem` only for the initial setup, with its public
key pinned in `resources/update-key.json`. Back up the private key securely.
Set `BOUFBOWL_UPDATE_KEY` to its restored path on another build machine. Never
commit it, put it under resources, or replace the pinned key casually: installed
updaters trust that key. `bun run release` validates the key before packaging.
Android signing and update-manifest signing use separate keys.

Package builders write `.release.json` sidecars after successful output. The
website advertises each package's **actual built version/hash**, omitting packages
without valid provenance instead of labelling stale binaries as new releases.
`updates.json` is a signed envelope with a JSON-string payload. Windows/Linux
fail closed on missing/invalid signatures while still launching an existing copy.
Without the private key, ordinary website builds emit unsigned development
metadata; do not publish those over a signed production release. Web/APK notices
rely on HTTPS; Android independently verifies the installed APK's signature.

Go is a build-only dependency for the small standalone desktop bootstrap. The
builder finds it on PATH or downloads/caches the official host archive and checks
its published SHA256. Players need neither Go, Bun nor Python. Windows updater
is32-bit (also works on64-bit Windows); Linux updater is x86-64.

```sh
python3 -m unittest tests.test_release_version tests.test_player_downloads tests.test_build_players
bun test tools/website/updates.test.mjs tests/web_player.test.js
# Use the discovered/cached Go executable if go is not on PATH:
go test tools/updates/updater.go tools/updates/updater_test.go
```

Validated for0.1.0:10 Python tests,4 Bun tests,4 Go tests; native ARM64 bootstrap
with a signed HTTPS fixture (online, offline, corrupted cache); Windows386
bootstrap under Hangover/Wine with an unavailable endpoint and a stub game entry.
All packages and the website built; APK reports versionName0.1.0/code1000001.
Origin manifest signature/package hashes verified. Android device installation
and a real future-version upgrade remain untested; launcher smoke entries did
not run a gameplay session.
