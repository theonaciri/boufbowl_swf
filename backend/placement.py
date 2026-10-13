"""Reference placement silhouette, expressed as inclusive offset-column spans.

Rows use the client's axial y (positive toward the top of the field). The
reference shows the right team. Horizontal reflection preserves each row:
x' = -x-y, since rendered horizontal position is x+y/2.
"""
from math import floor

# type: (default offset column/row, (row, first column, last column), ...)
REFERENCE_ZONES = {
    1: ((3, 0), ((4, 1, 2), (3, 0, 2), (2, 2, 3), (1, 2, 3), (0, 3, 4),
                 (-1, 2, 3), (-2, 2, 3), (-3, 0, 2), (-4, 1, 2))),
    2: ((5, 5), tuple((r, 2 if r >= 9 else 3 if r >= 5 else 4, 7) for r in range(1, 11))),
    3: ((3, -3), ((-3, 3, 3), (-4, 3, 3), (-5, 2, 2))),
    4: ((9, -5), tuple((r, 8, 11) for r in range(-10, 0))),
    5: ((5, -5), tuple((r, 4 if r >= -4 else 3 if r >= -8 else 2, 7) for r in range(-10, 0))),
}


def placement_zones(side, period=1, exclusion=3):
    right = (side == 2) != (period % 2 == 0)

    def coordinate(column, row):
        x = column - floor(row / 2)
        return {"x": x if right else -x-row, "y": row}

    zones = []
    for kind, (default, rows) in REFERENCE_ZONES.items():
        cells = [coordinate(c, r) for r, first, last in rows for c in range(first, last + 1)]
        cells = [p for p in cells if max(abs(p['x']), abs(p['y']), abs(p['x']+p['y'])) >= exclusion]
        if not cells:
            raise ValueError("Ball exclusion radius removes an entire placement zone")
        preferred = coordinate(*default)
        if preferred not in cells:
            preferred = cells[len(cells)//2].copy()
        zones.append({"type": kind, "defaultCell": preferred, "cell": cells})
    return zones
