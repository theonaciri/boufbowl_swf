# Cursor wheel zoom

Desktop Flash and web/Ruffle use the same `MouseEvent.MOUSE_WHEEL` capture
handler in `patches/BoufbowlClient.as`. It transforms a wrapper around `MainApp`;
stage overlays such as the FPS label remain fixed. Ruffle's existing wheel input
path supplies AS3 events; there is no JavaScript wheel bridge or duplicate zoom.
Wheel events inside the authored canvas are consumed before game controls scroll.

`ClientRuntime.as.inc::wheelZoomTransform` computes the transform in the authored
actual stage canvas coordinates (normally1024×600 in the preserved SWF;
FFDec does not change the SWF header to match replacement-source metadata). `SHOW_ALL` handles window/fullscreen sizing. Positive
wheel deltas zoom in, negative deltas zoom out: three delta units multiply scale
by 1.12. Fractional deltas work; per-event deltas are capped at ±30 and total
scale at 1–8. There is no separate mouse drag gesture.

The content point under the cursor stays fixed while scaling, unless doing so
would expose an edge of the original canvas. Translation clamps independently
on each axis to `[dimension * (1 - scale), 0]`. At the lower scale limit both
translations reset exactly to zero. A 1e-10 tolerance at scale 1 removes residual
floating-point zoom after reciprocal wheel steps. Changing cursor position between
wheel events provides bounded movement through the enlarged view.

Android keeps midpoint-anchored pinch input and the near-1 snap. Its minimum
is now1× too: returning to1× resets both translations, and enlarged content
is clamped to the1024×600 authored viewport. Wheel listeners remain desktop/web
only. The maximum zoom is8× on both paths.

## Focused verification

`bun test tests/client_zoom.test.js` executes the production AS3 math body after
removing type annotations. It checks center/corner/interior anchors, inverse
steps and exact reset, movement clamping when zooming out from a different edge,
maximum scale, fractional/extreme deltas, and 2,000 seeded cursor/delta changes.

`python3 -m unittest tests.test_client_tooling.ClientToolingTests.test_checked_in_roots_expand_and_probe_anchors_are_valid`
checks both roots still expand and existing probe instrumentation anchors remain
valid. These checks do not compile AS3 or exercise browser/native input delivery.

Integration verification (0.3.0): shared SWF and Windows/Linux/Android packages
built successfully. A disposable Ruffle probe exercised real pointer coordinates
plus canvas wheel events: cursor anchoring, bounded zoom-out after changing
cursor position, and exact reset to scale1/x0/y0. Hardware wheel input,
fullscreen/letterboxing and physical Android pinch remain device checks.
