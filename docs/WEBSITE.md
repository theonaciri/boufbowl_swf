# Build and maintain the website

The HTML, CSS, JavaScript, and `docs/legal/*.md` in the checkout are source
files. Bun generates the public website in `.local/website/dist`, including
minified inline CSS and minified JavaScript with content hashes in its filenames.
Media URLs receive an automatic revision derived from the media contents.
The build leaves source pages untouched; generated output stays out of Git.
`restoration.*` implements character/stadium/audio previews;
`contributions.*` handles resource proposals. `/play.html` hosts Ruffle.
## Build

After installing the [system prerequisites](BUILD.md#tools-and-inputs), run:

```sh
bun run build
```

This is also the command for a fresh checkout: it prepares the game client and
missing media before compiling the website. No FFDec environment variable or
manual command sequence is needed. First builds download FFDec and renderer tools
and can take a long time; subsequent frontend builds reuse the existing inputs.
The generated site is **`.local/website/dist/`**.

For another output directory:

```sh
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
Exactly two widths are emitted per image, only into the static output: 240/630 px
for the logo and 768/1024 px for the tutorial poster. `srcset`/`sizes` retain the
full 630/1024-pixel candidates for dense screens. The poster's cover crop is
included in its source-size calculation to avoid upscaling undersized images.

## Regenerate existing media

For changes to capture code, palettes, or media encoders, run:

```sh
bun run build:media
```

This refreshes all exporters using their caches and finishes with the same Bun
compiler. To rebuild ActionScript first, run `bun run build:game`.
Renderer packages and Chromium are installed by the orchestrator when media is missing.
If Chromium reports missing Linux shared libraries, install the libraries it
lists; on Ubuntu/Debian the Playwright helper is available from `tools/website`
with `bunx playwright install-deps chromium`.

The following modules remain available for targeted advanced work. Their normal
order is managed by `tools/build_project.py`; do not run them all manually for a
fresh checkout.

| Generator | Outputs |
| --- | --- |
| `build_restoration_data` | Resource availability inventory |
| `build_site_videos` | Tutorial MP4s and AVIF poster from the preserved FLVs |
| `export_home_cinematics` | 15 films, 18 distinct legends, animated AVIF + AV1/H.264 MP4 |
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
python3 -m tools.export_puppet_videos --character enutrof-2
python3 -m tools.build_website --character hero-508 --pose default
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
python3 -m tools.build_website --check
```
The carousel loads only its active film, prefers AV1 with H.264 fallback, and
pauses/unloads outside the viewport. Reduced motion and pause controls apply.

Configure contact/download/server URLs in `resources/site.json`. Set `site_url`
to the public HTTPS origin (currently `https://boufbowl-fan.fr`). Bun uses it for
canonical links, Open Graph/Twitter image and page URLs, and structured data.
Generated legal and redirect pages also receive absolute canonical links.
Bun also generates `robots.txt` (allows crawling except `/api/`) and `sitemap.xml`
from canonical URLs of pages without `noindex` or a refresh redirect. Private
consoles and draft legal pages retain their `noindex` tags and are omitted from
the sitemap; their HTML remains crawlable so search engines can read those tags.
`GET /api/site` discovers local builds at `android/build/BoufbowlOffline.apk`,
`windows/build/Boufbowl-windows.exe`, and `linux/build/Boufbowl-linux.run`.
[Build packages](BUILD.md#distribute-players) before the final website build.
Desktop/Android bundle commands refresh the website automatically unless passed
`--no-website`. Download URLs include a content revision and size labels are
generated from the published bytes (for example `Linux x86-64 · 48,9 Mo`),
including in static HTML before the browser fetches the live manifest.
Windows and Linux downloads load the included desktop SWF and game assets from
the extracted folder; only the game API uses `server_url`. They do not download
the browser SWF or its assets at startup.
When changing hosts, update `site_url` and `server_url`, rebuild the website,
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
