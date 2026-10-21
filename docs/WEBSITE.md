# Build and maintain the website

The HTML, CSS, JavaScript, and `docs/legal/*.md` in the checkout are source
files. Bun generates the public website in `.local/website/dist`, including
minified inline CSS and minified JavaScript with content hashes in its filenames.
Media URLs receive an automatic revision derived from the media contents.
The build leaves source pages untouched; generated output stays out of Git.
`restoration.*` implements character/stadium/audio previews;
`contributions.*` handles resource proposals. `/play.html` hosts Ruffle.
[Build the game](BUILD.md#desktop-client-and-runtime-files) before exporting characters.

For frontend changes with existing media exports, run Bun. FFmpeg and `avifenc`
are also needed when generating responsive AVIF variants for the first time:

```sh
bun run build
bun run check:site
# Optional destination outside the checkout (or under .local):
bun run build --output /path/to/public
```

The compiler is `tools/website/build.mjs`; it renders the legal Markdown pages,
bundles scripts and styles, copies public assets/downloads, and writes a delivery
manifest. It replaces the output folder only after the new build succeeds.
Repeated builds with the same inputs keep the same hashes. Generated HTML,
JavaScript, fonts, images, and downloads are ordinary static files.

The logo and tutorial poster have responsive AVIF variants generated from
`assets/site/logo.webp` and the original tutorial frame. Color/alpha quality is
80; the transparent logo keeps 4:4:4 color and the poster uses 4:2:0 compression.
The image cache is `.local/website/image-cache`; unchanged inputs reuse it.
Variants are emitted only into the static output. `srcset`/`sizes` retain the
full 630/1024-pixel candidates for dense screens. The poster's cover crop is
included in its source-size calculation to avoid upscaling undersized images.

## Renderer setup

Use JDK 17, FFDec, Bun 1.4.3, FFmpeg (libx264, libsvtav1), libavif's `avifenc`, and the preserved
`vendor/ruffle/` runtime. Set `FFDEC_JAR` as in [Build](BUILD.md#tools-and-inputs).
The carousel exporter currently expects that documented FFDec cache location.

```sh
cd tools/website
bun install --frozen-lockfile
bunx playwright install --with-deps chromium
cd ../..
```

## Export characters and videos

For a fresh checkout, after the renderer setup and game build, generate the
media and site in this order. The final Python command generates media/metadata
and calls the same Bun compiler to produce `.local/website/dist`.

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
| `build_site_videos` | Tutorial MP4s and AVIF poster from the preserved FLVs |
| `export_home_cinematics` | 15 films, 18 distinct legends, animated AVIF + AV1/H.264 MP4 + WebP |
| `export_puppet_videos` | Five gameplay puppet loops, AV1 CRF 35 at 530 px high |
| `build_website` | Minified Bun JavaScript bundle, bundled and inlined Bun CSS, stadium previews and transparent logo as AVIF, native portraits, grid icons, refreshed inventory/legal/download manifests, public delivery |

Carousel films are 1015 × 595 in AV1 (CRF 35) and animated AVIF at 60 FPS,
preserving native 25 FPS pose timing from the 2560 × 1500 captures. H.264 fallbacks
add one pixel of padding at the right and bottom for 4:2:0 compatibility.
Evangelyne uses black team color. Masters/capture caches live under
`.local/`; exported media remains ignored under `assets/site/`.
The generated carousel provenance is `docs/site/media-sources.json`.

Use `python3 -m tools.export_home_cinematics --encode-only` to reconvert cached
captures without recording again.

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

Nginx serves `.local/website/dist` directly on port 9900; see
[Hosting](HOSTING.md) and `ops/nginx/boufbowl.conf`. No Python process is needed
to serve the HTML or assets. The database and private server state are excluded
from the output. Game sessions, accounts, administration, and browser activity
still use `/api/`, which Nginx proxies to the Python backend on port 9901.
Browsing static pages does not require the API; interactive server features do.

```sh
bun run build
bun run check:site
curl -I http://127.0.0.1:9900/
curl -fsS http://127.0.0.1:9900/api/health
# Optional full media/metadata verification after exports:
python3 -m tools.build_website --check --ffdec "$FFDEC_JAR"
```
The carousel loads only its active film, prefers AV1 with H.264 fallback, and
pauses/unloads outside the viewport. Reduced motion and pause controls apply.

Configure contact/download/server URLs in `resources/site.json`.
`GET /api/site` discovers local builds at `android/build/BoufbowlOffline.apk`,
`windows/build/Boufbowl-windows.zip`, and `linux/build/Boufbowl-linux.tar.gz`.
[Build packages](BUILD.md#distribute-players) before the final website build.
When changing hosts, also update canonical/OpenGraph/schema URLs in `index.html`
and rebuild clients with the new server URL. Asset revisions and script hashes
are generated automatically; do not add manual cache versions to source pages.

## Resource review, activity, and legal pages

`/api/asset-catalog` exposes expected missing/replacement resources.
`/assets-admin.html` lets an administrator review quarantined proposals.
Install ClamAV with fresh signatures, Bubblewrap, prlimit (util-linux), and
FFmpeg for scans/previews. Approval fails closed if those checks fail.
Approve/download, integrate manually at the expected asset path, mark integrated,
then rebuild the website. Approval itself does not publish a file.
With a trusted Cloudflare proxy on loopback, `BOUFBOWL_TRUST_CF=1` enables its
client-IP header for quotas; otherwise quotas use the HTTP peer.

`/website-activity.html` shows browser-reported section visibility/time,
character/class selections, and download/Web clicks. Historical Python-observed
asset counts remain visible; new static requests are recorded in the Nginx access
log instead of passing through Python. Asset requests alone do not prove a section
was read. `site-activity.js` sends
no visitor identifier and sets no activity cookie; game/session storage is
separate. Operator access is described in [Server](SERVER.md#administration).

The six files in `docs/legal/` are French legal-page sources with explicit
`[]` placeholders. Complete operator information and procedures before treating
them as final. Their content does not implement consent, deletion, or retention.

```sh
bun run build
bun run check:site
```

This creates `legal.html` and six document pages inside the output directory.
Their shared template and renderer are `tools/website/legal.html` and
`tools/website/legal.mjs`. The old Python legal-page command delegates to Bun.
