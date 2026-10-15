"""M1: the converter output matches the original game running in DOSBox.

Slow and opens a DOSBox window: run with `python tools/test.py -m dosbox`.
Starts Keen 1, captures the title screen, starts a new game, walks to level 1 and
enters it. Screens are compared with the rendered levels; only sprites, dialog
boxes and animated tiles may differ.
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

import toolchain as tc
from conftest import require
from tools.convert import ega, original, render
from tools.convert.compare import animation_groups, best_match, tile_cells

pytestmark = pytest.mark.dosbox

# Seconds after start. The title screen is up from about 14 s until the demo loop moves on.
# Space opens the menu, Enter starts a new game, then walk right/down/right to level 1.
# On the world map Space opens the status screen (closed with Enter) and Alt enters a level.
# Startup time varies a few seconds, so the title is captured at several moments.
TITLE, WORLD_MAP, LEVEL_1 = (16, 18, 20, 22, 24), 31, 49
SCRIPT = [*map(str, TITLE), "25=space", "28=enter", str(WORLD_MAP), "34=right~1.0", "37=down~0.4",
          "39=right~1.3", "41=space", "43=enter", "46=alt", str(LEVEL_1)]


@pytest.fixture(scope="module")
def run():
    require(tc.dosbox)
    if not (original.ORIGINAL / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    subprocess.run([sys.executable, str(tc.ROOT / "tools" / "dosbox_capture.py"), *SCRIPT],
                   check=True, capture_output=True, timeout=120)
    ep = original.load()
    tiles = [render.graphic(t).convert("RGB") for t in ega.tiles(ep.header, ep.latch)]
    return ep, tiles


def shot(seconds: int) -> np.ndarray:
    return np.asarray(Image.open(tc.BUILD / "dosbox" / f"t{seconds:03d}.png").convert("RGB"))


def level_image(ep, tiles, number: int) -> np.ndarray:
    return np.asarray(render.level(ep.levels[number], tiles))


def test_title_backdrop_is_level_90(run):
    ep, tiles = run
    # Below the title bitmap (screen rows 128-192) only the "PRESS F1" box may differ.
    # The intro before the title also scrolls over level 90, but with text bitmaps on top,
    # so the best of the captures is the title screen.
    level90 = level_image(ep, tiles, 90)
    groups = animation_groups([t.anim for t in ep.tileinfo])
    tile_arrays = [np.asarray(t) for t in tiles]
    results = []
    for moment in TITLE:
        backdrop = shot(moment)[128:192]
        x, y, _ = best_match(backdrop, level90)
        if x % 16 == 0 and y % 16 == 0:
            results.append(tile_cells(backdrop, ep.levels[90].tiles, tile_arrays, groups, x, y))
    matches, misses = max(results, key=lambda r: r[0])
    assert len(misses) <= 4, misses
    assert matches >= 76


def test_world_map(run):
    ep, tiles = run
    _, _, rate = best_match(shot(WORLD_MAP), level_image(ep, tiles, 80))
    assert rate > 0.99                     # only Keen's sprite differs


def test_level_1(run):
    ep, tiles = run
    _, _, rate = best_match(shot(LEVEL_1), level_image(ep, tiles, 1))
    assert rate > 0.99                     # only Keen's sprite and animated tiles differ
