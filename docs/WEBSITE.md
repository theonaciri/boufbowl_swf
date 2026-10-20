# Build and maintain the website

The homepage is `index.html` with `home.css`/`home.js`.
`restoration.*` implements character/stadium/audio previews;
`contributions.*` handles resource proposals. `/play.html` hosts Ruffle.
[Build the game](BUILD.md#desktop-client-and-runtime-files) before exporting characters.

## Renderer setup

Use JDK 17, FFDec, Bun, FFmpeg (libx264, libsvtav1, libwebp), and the preserved
`vendor/ruffle/` runtime. Set `FFDEC_JAR` as in [Build](BUILD.md#tools-and-inputs).
The carousel exporter currently expects that documented FFDec cache location.

```sh
cd tools/website
bun install --frozen-lockfile
bunx playwright install --with-deps chromium
cd ../..
```

## Export characters and videos

Run in this order for a fresh checkout:

```sh
python3 -m tools.build_restoration_data
python3 -m tools.build_site_videos
python3 -m tools.export_home_cinematics
python3 -m tools.export_puppet_videos --ffdec "$FFDEC_JAR"
python3 -m tools.build_website --ffdec "$FFDEC_JAR"
```

| Generator | Outputs |
| --- | --- |
| `build_restoration_data` | Resource availability inventory |
| `build_site_videos` | Tutorial MP4s/poster from the preserved FLVs |
| `export_home_cinematics` | 15 films, 18 distinct legends, animated AVIF + AV1/H.264 MP4 + WebP |
| `export_puppet_videos` | Five gameplay puppet loops and posters, 700 px high |
| `build_website` | Native portraits, grid icons, refreshed inventory/legal/download manifests, public delivery |

Carousel films are 2560 × 1500 at an encoded 60 FPS, preserving native 25 FPS
pose timing. Evangelyne uses black team color. Masters/capture caches live under
`.local/`; exported media remains ignored under `assets/site/`.
The generated carousel provenance is `docs/site/media-sources.json`.

For a smaller iteration, use:

```sh
python3 -m tools.export_home_cinematics --scene lancer
python3 -m tools.export_puppet_videos --character enutrof-2 --ffdec "$FFDEC_JAR"
python3 -m tools.build_website --character hero-508 --pose default --ffdec "$FFDEC_JAR"
```

The carousel also accepts `--capture-only`, `--encode-only`, and `--force`.
Portrait rendering reuses fingerprints; edit palettes in `resources/palettes.json`,
the pose map in `tools/site_portraits.py`, and capture behavior in
`tools/site_*_capture.*` / `tools/website/*.mjs`. The final website build validates
that referenced homepage files exist.

## Serve, deliver, and check

```sh
python3 -m backend.server --host 127.0.0.1 --port 9900
# In another terminal, after exports:
python3 -m tools.build_website --check --ffdec "$FFDEC_JAR"
```

The backend serves the working checkout. The build exports public files and
available downloads to `.local/website/dist`; it excludes the database and private
server state. This static export still needs the backend API at the same origin.
The carousel loads only its active film, prefers AV1 with H.264 fallback, and
pauses/unloads outside the viewport. Reduced motion and pause controls apply.

Configure contact/download/server URLs in `resources/site.json`.
`GET /api/site` discovers local builds at `android/build/BoufbowlOffline.apk`,
`windows/build/Boufbowl-windows.zip`, and `linux/build/Boufbowl-linux.tar.gz`.
[Build packages](BUILD.md#distribute-players) before the final website build.
When changing hosts, also update canonical/OpenGraph/schema URLs in `index.html`
and rebuild clients with the new server URL. Bump changed frontend script/style
query versions so existing browsers fetch the update.

## Resource review, analytics, and legal pages

`/api/asset-catalog` exposes expected missing/replacement resources.
`/assets-admin.html` lets an administrator review quarantined proposals.
Install ClamAV with fresh signatures, Bubblewrap, prlimit (util-linux), and
FFmpeg for scans/previews. Approval fails closed if those checks fail.
Approve/download, integrate manually at the expected asset path, mark integrated,
then rebuild the website. Approval itself does not publish a file.
With a trusted Cloudflare proxy on loopback, `BOUFBOWL_TRUST_CF=1` enables its
client-IP header for quotas; otherwise quotas use the HTTP peer.

`/website-tracking.html` shows aggregate asset requests plus browser-reported
section visibility/time, character/class selections, and download/Web clicks.
Asset requests alone do not prove a section was read. `site-tracking.js` sends
no visitor identifier and sets no analytics cookie; game/session storage is
separate. Operator access is described in [Server](SERVER.md#administration).

The six files in `docs/legal/` are French legal-page sources with explicit
`[]` placeholders. Complete operator information and procedures before treating
them as final. Their content does not implement consent, deletion, or retention.

```sh
python3 -m tools.build_legal_pages
python3 -m tools.build_legal_pages --check
```

This creates `legal.html` and six document pages, all ignored build outputs.
