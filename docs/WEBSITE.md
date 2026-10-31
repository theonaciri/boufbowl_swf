# Build and maintain the website

The HTML, CSS, JavaScript, and `docs/legal/*.md` in the checkout are source
files. Bun generates the public website in `.local/website/dist`, including
minified inline CSS and minified JavaScript with content hashes in its filenames.
Media URLs receive an automatic revision derived from the media contents.
The build leaves source pages untouched; generated output stays out of Git.
Elements marked `data-source-only` stay as live HTML in source files and are
removed by the Bun build before bundling page scripts. The GitHub build
instructions and their stylesheet use this marker so neither enters the public bundle.
`restoration.*` implements character/stadium/audio previews;
`contributions.*` handles resource proposals. `/play.html` hosts Ruffle.
Its `web-player.js` launcher offers live balanced (30 FPS, medium quality), high
(60 FPS) and performance (25 FPS, low quality) presets. The choice is saved only
in browser storage. The `clientRuntime=ruffle` launch parameter enables the web
frame budget, chat clipping and popup skins. Chat batching/scroll calculations,
redundant 3D position suppression and modal layering are shared with desktop and
Android. The in-game slider requests 25–240 FPS through 3D scene changes;
browser presets remain startup defaults. Android defaults to
60 FPS before a preference is saved. Use the default Ruffle renderer selection: the legacy
`webgl` backend lacks the bitmap drawing required by the UI skin repair.
## Build

`regles.html` is rendered by `tools/website/rules.mjs` on every website build,
including the quick command. Values/stadium overrides come from
`resources/game_config.json`; fidelity statuses come from `resources/rulebook.json`.
French explanations live in `tools/website/rules-data.json`; untranslated cases
or unresolved questions stop the build. The text and formulas work without JavaScript.
Collapsed calculators add pass/catch/interception, pickup, movement, stun and
combat curves. `rules-calculators.js` uses coefficients embedded at build time;
its sliders change examples only. No game rebuild or saved browser settings are
needed to refresh the page. Check with `bun test tools/website/rules-calculators.test.mjs`.

After installing the [system prerequisites](BUILD.md#tools-and-inputs), run:

```sh
bun run build:website
```

This is also the command for a fresh checkout: it prepares the game client and
missing media before compiling the website. No FFDec environment variable or
manual command sequence is needed. First builds download FFDec and renderer tools
and can take a long time; subsequent builds refresh changed media inputs and reuse unchanged exports.
The generated site is **`.local/website/dist/`**. Serve it locally with:

```sh
bun run serve:website
```

Open **http://127.0.0.1:9900**. This serves the existing build without rebuilding it.
The game API must run separately for interactive features. Stop with Ctrl+C.

For a quick HTML, CSS, or JavaScript edit when all required media already exists,
run `bun run build:website:quick`. It skips game preparation and media rendering,
then recompiles the static site into the same output folder. Use the full
`bun run build:website` command for a fresh checkout or after changing game/media
inputs.
Choose another port or expose it to your local network with:

```sh
bun run serve:website --port 8080
bun run serve:website --host 0.0.0.0
```

Use `--directory /path/to/public` to serve a custom website output directory.

For another output directory:

```sh
bun run build:website --output /path/to/public
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

## Orbis side project

Boufbowl remains the default site and builds solely from its own sources/assets.
Its homepage banner links to `/orbis/`; the Orbis repository owns that website,
Web player and downloads. Run `bun run build:website` in `~/projects/orbis` to
publish Orbis independently to its `.local/website/dist`. Nginx mounts that
separate directory at `/orbis/`, and preserves the earlier Orbis URL redirects.
Rebuilding either website does not build or replace the other.

## Automatic media updates

The same `bun run build:website` command detects changes to media inputs, palettes,
capture code, and encoding settings. After a character's default colors change,
only that character's portraits, cinematic scenes containing that character, and
its puppet demo (if one exists) are rendered again. Shared palettes can affect
several characters. Other scenes and characters reuse their existing exports.
A palette-only `bun run build` also preserves this reuse: the game build records
its palette-independent renderer identity in `.local/game-build.json`. Unrecognized
or manually replaced client SWFs conservatively invalidate the rendering cache.

Logo and stadium AVIFs are cached separately by source image and encoding recipe;
character color changes do not reconvert them. Tutorial videos are independent.
The default command skips media stages when their input and output contents match
the completed build records. A Git pull that changes only HTML/CSS/JavaScript does
not invalidate those records; output timestamp changes do not invalidate them either.
When a stage needs updating, the build prints the reason. The quick command always
skips media checks and rendering.

Stage fingerprints live in `.local/website/media-stages.json`; individual render
receipts and image fingerprints live alongside their capture caches under
`.local/`. Puppet captures and encodes are cached separately, so encoding changes
reuse native frames. Keep these caches between builds. The first build using the
new fingerprints refreshes existing exports once; later builds reuse them.
Missing stage records require one completed media build to establish which inputs
produced the existing files. A Git pull does not transfer these local records.

Media stages and independent images, captures, and encodes run concurrently with
one CPU budget shared between Python and Bun. The default uses all available CPUs
and respects Linux container quotas. Use `bun run build:website --jobs 4` to lower
the ceiling. Manifests are saved by a single coordinator, and static compilation
runs once after every media stage succeeds.

Renderer packages and Chromium are prepared only when a rendering stage needs an
update. If Chromium reports missing Linux shared libraries, install the libraries
it lists; on Ubuntu/Debian the Playwright helper is available from `tools/website`
with `bunx playwright install-deps chromium`.

The following modules remain available for targeted advanced work. Their normal
order is managed by `tools/build_project.py`; do not run them all manually for a
fresh checkout.

| Generator | Outputs |
| --- | --- |
| `build_restoration_data` | Resource availability inventory |
| `build_site_videos` | Tutorial MP4s and AVIF poster from the preserved FLVs |
| `export_home_cinematics` | 15 films, 18 distinct legends, AV1 MP4 |
| `export_puppet_videos` | Five gameplay puppet loops, AV1 CRF 35 at 530 px high |
| `build_website` | Minified Bun JavaScript bundle, bundled and inlined Bun CSS, stadium previews and transparent logo as AVIF, native portraits, grid icons, refreshed inventory/legal/download manifests, public delivery |

Carousel films are 1015 × 595 in AV1 (CRF 35) at 60 FPS,
preserving native 25 FPS pose timing from the 2560 × 1500 captures.
Evangelyne uses black team color. Masters/capture caches live under
`.local/`; exported media remains ignored under `assets/site/`.
Keep only the cinematic version selected by `cinematicMediaVersion` in `home.js`
(currently `legends-v3`), with one `.av1.mp4` file per scene. The carousel uses
AV1 directly; the exporter removes older versions and alternate formats. Site MP4s are generated media and are not
tracked by Git; the tutorial sources remain preserved under `assets/videos/`.
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

The homepage’s `#tournois` section reads `GET /api/tournaments` for the current
event (open, or finishing its last matches) and the single next upcoming event.
It reuses the stadium images from the restoration inventory and
displays start/end dates in Paris time, effective match rules, qualification/round times,
and the live top ten (with the first five featured and a podium for the first
three). It loads once when the section approaches the viewport. The “Actualiser”
button updates the tournaments and rankings on demand; there is no polling or
refresh when returning to the browser tab.

The default competition runs every Saturday from 14:00 to 18:00 in
`Europe/Paris`. Weekly recurrence advances calendar weeks in that timezone, so
the local hours stay fixed through daylight saving changes. Qualifications run
until 17:30, followed by two 15-minute knockout rounds. Late matches can finish
after their entry window; they do not move the next Saturday’s schedule.

Players sign in with their existing game account through `/api/account`.
`POST /api/tournaments` with `action: "participate"`, `session`, `tournament_id`,
and an explicit boolean `participating` records or removes an attendance
confirmation. Confirmations persist in `tournament_intentions`, independently
of competitive entries and scores: players still join their tournament from
the game. Authenticated `action: "list"` returns their confirmation state;
`action: "logout"` revokes the website session without leaving the game queue.
The website keeps that session in tab-scoped session storage. All tournament API
responses use `Cache-Control: no-store`. Deploy the backend changes and restart
the backend when publishing this feature; the existing Nginx `/api/` proxy needs
no additional rule. A static-only preview shows a server-unavailable message.

The public `ladder.html` page, linked from the homepage tournament section, reads the anonymous
`GET /api/ladder?page=1` endpoint. Each page contains up to ten players in the
same rating/nickname order as the game, with their global ranks, clubs, ratings,
league/qualification state, and ranked wins/draws/losses. Previous/next buttons
retain absolute ranks across pages. It loads once near the viewport and refreshes
the currently displayed page every 30 minutes after the last request; the
“Actualiser” button can also refresh it. This timer does not refresh tournaments.
Requests past the last page return that last page, including after the player
count changes. No account or session is required, and private profile IDs and
account fields are excluded.

Occurrence names live in each tournament’s `settings_json`; changing one name
does not rename the recurring series. Removing the first generated occurrence
also requires advancing the stored series anchor/ID and rotating its stadium
sequence by the same number of weeks, otherwise maintenance would recreate it.
Preserve later occurrence IDs, frozen settings, and completed tournament history.

```sh
bun run build:website
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
`GET /api/site` discovers local builds at `android/build/Boufbowl Fan.apk`,
`windows/build/Boufbowl Fan.exe`, and `linux/build/Boufbowl Fan.run`.
[Build packages](BUILD.md#distribute-players) before the final website build.
Desktop/Android bundle commands refresh the website automatically unless passed
`--no-website`. Download URLs include a content revision and size labels are
generated from the published bytes (for example `Linux x86-64 · 48,9 Mo`),
including in static HTML. The browser uses the generated
`resources/site-manifest.json` first so links and sizes match the published
files even when the backend has not restarted. `/api/site` is a fallback.
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
bun run build:website
bun run check:site
```

This creates `legal.html` and six document pages inside the output directory.
Their shared template and renderer are `tools/website/legal.html` and
`tools/website/legal.mjs`. The old Python legal-page command delegates to Bun.
