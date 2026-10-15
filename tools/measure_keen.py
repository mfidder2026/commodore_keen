"""Measure Keen's movement in the original game from DOSBox burst captures.

For every build/dosbox/b<ms>.png: find the camera (scroll position) by matching the
screen against the rendered level, then Keen's bounding box from the pixels that differ
from the level. Prints time, camera and Keen's world position (left x, feet y).

Usage: python tools/measure_keen.py [level number] [first_ms] [last_ms]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.convert import ega, original, render  # noqa: E402
from tools.convert.compare import _packed, best_match  # noqa: E402


def local_match(shot: np.ndarray, level: np.ndarray, guess: tuple[int, int], radius: int = 24):
    s, l = _packed(shot), _packed(level)
    best = None
    gx, gy = guess
    for y in range(max(0, gy - radius), min(l.shape[0] - s.shape[0], gy + radius) + 1):
        for x in range(max(0, gx - radius), min(l.shape[1] - s.shape[1], gx + radius) + 1):
            score = np.count_nonzero(l[y:y + s.shape[0], x:x + s.shape[1]] == s)
            if best is None or score > best[2]:
                best = (x, y, score)
    return best[0], best[1], best[2] / s.size


def keen_box(shot: np.ndarray, level: np.ndarray, cam: tuple[int, int]):
    x, y = cam
    view = level[y:y + 200, x:x + 320]
    diff = (shot != view).any(axis=2)
    # Keen's yellow hair (EGA 14) narrows the search to the player.
    yellow = (shot == (0xFF, 0xFF, 0x55)).all(axis=2) & diff
    if not yellow.any():
        return None
    ys, xs = np.nonzero(yellow)
    cx, cy = int(np.median(xs)), int(np.median(ys))
    window = diff[max(0, cy - 8):cy + 26, max(0, cx - 12):cx + 12]
    wy, wx = np.nonzero(window)
    if len(wy) == 0:
        return None
    left = max(0, cx - 12) + wx.min()
    bottom = max(0, cy - 8) + wy.max()
    return x + left, y + bottom


def main() -> None:
    number = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    last = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    ep = original.load()
    tiles = [render.graphic(t).convert("RGB") for t in ega.tiles(ep.header, ep.latch)]
    level = np.asarray(render.level(ep.levels[number], tiles))
    frames = sorted((ROOT / "build" / "dosbox").glob("b*.png"))
    guess = None
    for f in frames:
        ms = int(f.stem[1:])
        if not first <= ms <= last:
            continue
        shot = np.asarray(Image.open(f).convert("RGB"))
        if guess is None:
            x, y, rate = best_match(shot, level)
        else:
            x, y, rate = local_match(shot, level, guess)
        guess = (x, y)
        box = keen_box(shot, level, (x, y))
        print(f"{ms:7d} cam=({x:4d},{y:3d}) match={rate:.3f} keen={box}")


if __name__ == "__main__":
    main()
