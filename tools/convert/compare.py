"""Compare a DOSBox screenshot with a rendered level: find the scroll position and the match rate.

Usage: python -m tools.convert.compare <screenshot.png> <level.png> [top bottom]
The rows top..bottom of the screenshot (default: all) are searched in the level image.
Sprites and dialog boxes in the screenshot show up as the mismatching fraction.
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image


def _packed(rgb: np.ndarray) -> np.ndarray:
    # One integer per pixel so comparisons are cheap.
    return (rgb[..., 0].astype(np.int32) << 16) | (rgb[..., 1].astype(np.int32) << 8) | rgb[..., 2]


def best_match(shot: np.ndarray, level: np.ndarray, samples: int = 400,
               candidates: int = 20) -> tuple[int, int, float]:
    """Return (x, y, match fraction) of the best placement of shot inside level.

    First scores every placement on a fixed random sample of pixels, then compares
    the best candidates in full.
    """
    s, l = _packed(shot), _packed(level)
    sh, sw = s.shape
    lh, lw = l.shape
    nx, ny = lw - sw + 1, lh - sh + 1
    rng = np.random.default_rng(0)
    pys = rng.integers(0, sh, samples)
    pxs = rng.integers(0, sw, samples)
    score = np.zeros((ny, nx), dtype=np.int32)
    for py, px in zip(pys, pxs):
        score += l[py:py + ny, px:px + nx] == s[py, px]
    best = (0, 0, -1)
    for flat in np.argsort(score, axis=None)[-candidates:]:
        y, x = divmod(int(flat), nx)
        full = np.count_nonzero(l[y:y + sh, x:x + sw] == s)
        if full > best[2]:
            best = (x, y, full)
    return best[0], best[1], best[2] / s.size


def animation_groups(anim: list[int]) -> list[list[int]]:
    """For each tile, all tiles of its animation loop (consecutive tiles with value 2 or 4)."""
    groups = [[t] for t in range(len(anim))]
    t = 0
    while t < len(anim):
        n = anim[t]
        if n in (2, 4):
            loop = list(range(t, min(t + n, len(anim))))
            for member in loop:
                groups[member] = loop
            t += n
        else:
            t += 1
    return groups


def tile_cells(shot: np.ndarray, level_tiles: list[list[int]], tile_images: list[np.ndarray],
               groups: list[list[int]], scroll_x: int, scroll_y: int) -> tuple[int, list[tuple[int, int]]]:
    """Compare a tile-aligned screenshot cell by cell. Returns (matching cells, mismatching cells)."""
    if scroll_x % 16 or scroll_y % 16:
        raise ValueError("tile comparison needs a tile-aligned scroll position")
    matches, misses = 0, []
    for cy in range(shot.shape[0] // 16):
        for cx in range(shot.shape[1] // 16):
            ty, tx = scroll_y // 16 + cy, scroll_x // 16 + cx
            cell = shot[cy * 16:(cy + 1) * 16, cx * 16:(cx + 1) * 16]
            tile = level_tiles[ty][tx]
            if any(np.array_equal(cell, tile_images[t]) for t in groups[tile]):
                matches += 1
            else:
                misses.append((tx, ty))
    return matches, misses


def main() -> None:
    shot = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
    level = np.asarray(Image.open(sys.argv[2]).convert("RGB"))
    if len(sys.argv) > 4:
        top, bottom = int(sys.argv[3]), int(sys.argv[4])
        x, y, rate = best_match(shot[top:bottom], level)
        y -= top
    else:
        x, y, rate = best_match(shot, level)
    print(f"scroll x={x} y={y}  match {rate:.2%}")


if __name__ == "__main__":
    main()
