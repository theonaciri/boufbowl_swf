# Shared client performance work

The five optimization cycles target code shared by Ruffle, desktop Flash, and
Android AIR. Preserve action timing, coordinate mapping, explicit redraws and
completion callbacks. Renderer-specific popup skins remain scoped to Ruffle.

## Cycle 1: batch sprite vertex writes

Moving sprites formerly wrote three temporary extreme coordinates, then the
three actual coordinates. Each Sprite3D setter also read the vertex, potentially
recomputing its position repeatedly. Use the existing shared vertex's setValue
method to update all axes and invalidate geometry once. Explicit redraws use the
same method without allocating a temporary Point3. Reject NaN before mutation.

The focused benchmark in tools/shared_client_bench.as.inc compares 3,000 changing
positions using identical, preallocated points. Under this host's Ruffle runtime,
three samples were 25–26 ms for the former setter sequence and 8 ms for the
batched presenter path. These are microbenchmark results, not measured gameplay
FPS gains or native runtime results.

The shared smoke checks cover unchanged/moving positions, axis mapping, explicit
redraws, replacement sprites, rejected NaN coordinates, and chat scroll state.
Run `python3 -m tools.smoke_shared_client` on a host with a compatible, licensed
AIR runtime. Native AIR application execution on this development host is
license gated; browser probes exercise both runtime branches in Ruffle.
