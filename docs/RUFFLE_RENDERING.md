# Ruffle nightly rendering audit — 2026-10-31

Bundled runtime: `0.8.0-nightly.2026.10.31`, previously October 13.
[Official release](https://github.com/ruffle-rs/ruffle/releases/tag/nightly-2026-10-31).
The archive URL and verified SHA-256 are pinned in `vendor/ruffle/UPSTREAM.json`.

## Comparison

A disposable SWF toggled only the browser rendering workarounds. Compared:
October 13 + patches, October 31 + patches, October 31 without the selected
workarounds. Actual game widgets, identical content and 1024×600 browser viewport;
default wgpu/WebGL renderer through Chromium/SwiftShader. Native rendering was
not inferred from the Ruffle result.

| Area | October 31 without the workaround | Decision |
| --- | --- | --- |
| Wrapped/bold chat | A 29.1px paragraph advances the following line by ~14.45px; 14.65px overlap | Keep paragraph layout repair |
| Chat clipping/scrolling | TLF underestimates wrapped content; viewport ratio and scroll extent are wrong | Keep explicit viewport and rendered-bound geometry |
| Scrollbar thumbs | Full-height thumb stretches its caps into long wedges | Keep fixed-cap thumb rendering |
| Chat/input backgrounds | Corners and borders stretch into angled shapes | Keep composed nine-slice artwork |
| Tournament tabs, four states | Corners stretch with button width | Keep frame-aware skin repair |
| Tooltip and message popup | Background and button corners distort | Keep skin/popup layout repairs |
| Time/progress gauge | Fill tested at 0, 25, 50, 75 and 100%; original outer frame still distorts | Keep shared skin repair |
| Slider track | Original rounded ends stretch into long pointed outlines | Keep vector track artwork |
| 3D camera | `Matrix3D.pointAt` leaves an identity matrix unchanged for a nontrivial position/target | Keep explicit camera basis |
| 3D texture triangles | UVT test samples geometric bitmap coordinates (red=160, green=80), ignoring supplied UVT mapping | Keep perspective subdivision/fills |

With repairs enabled, the complete control gallery and all four additional
progress screenshots were byte-identical between the two nightlies. Popup
screenshots were visually consistent; the background match clock differs.
Chat checks also exercised repeated appends, narrower resize, top/bottom scroll
and clearing programmatically. An additional mouse-drag trial in the reparented
diagnostic chat was inconclusive; it is not an interaction acceptance test.
Empty content returns viewport ratio 1. No page errors in the
three comparison runs. No rendering workaround was proven obsolete.

A separate full scripted 3D replay on October 31 rendered the resolution,
emitted the real client `ResolutionDoneMessage`, received the next `FIELD_STATE`
and finished at `MATCH_END`, without page errors. This fixture tests movement,
not combat or every stadium.

## Evidence and follow-up

Disposable sources, SWFs, screenshots and JSON measurements are under
`.local/ruffle-nightly-audit/`; they are deliberately excluded from Git.
`results.json` records the three-way comparison; `replay-result.json` records
3D completion. `features.json` holds the additional primitive/slider checks.
The shared preview's screenshot operation repeatedly timed out; captures were
completed using the local Playwright runner.

For future updates, repeat the comparison with the corresponding workaround
actually disabled. Successful rendering with a patch enabled cannot establish
that the upstream issue is fixed. Keep the native Flash/AIR paths unchanged.

Website delivery: `bun run build:website:quick`, then `bun run check:site`.
Ruffle assets have a new website revision; no game SWF or native package rebuild
is needed solely for this browser-runtime update.
