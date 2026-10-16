"""M3/M10: scroll engine in VICE, on PAL and on NTSC.

Builds the SCROLLTEST variant (tests/scenarios/m3_scroll.asm), runs it headless and checks:
- the final screen equals the converter's preview of level 1 at the final camera position,
- the camera was followed (statistics written by the test program as STATS on the disk),
- the measured cycle counts stay within the frame budget (docs/budget.md).
"""
from __future__ import annotations

import shutil
import struct

import numpy as np
import pytest
from PIL import Image

import toolchain as tc
from conftest import require, run_vice

OUT = tc.BUILD / "test"
WINDOW_W, WINDOW_H = 304, 192                       # the 38 x 24 character display

# Colour update deadline: it starts at raster line 251 and must finish each row before
# the beam reaches it; the beam is at row 24 after (lines to row 24) * cycles per line.
DEADLINE = {"pal": (312 - 251 + 51 + 24 * 8) * 63,    # 19,152
            "ntsc": (263 - 251 + 51 + 24 * 8) * 65}   # 16,575


@pytest.fixture(scope="module")
def d64():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not (tc.ROOT / "data" / "original" / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    from build import build
    return build(["SCROLLTEST"])


@pytest.fixture(scope="module", params=["pal", "ntsc"])
def run(request, d64):
    system = request.param
    OUT.mkdir(parents=True, exist_ok=True)
    disk = OUT / f"m3_{system}.d64"                 # own copy: STATS is saved onto the disk
    shutil.copyfile(d64, disk)
    shot = OUT / f"m3_scroll_{system}.png"
    shot.unlink(missing_ok=True)
    result = run_vice(["-default", f"-{system}", "-warp",
                       "-sounddev", "dummy", "-debugcart", "-limitcycles", 120_000_000,
                       "-exitscreenshot", shot, "-autostart", disk], timeout=300)
    assert result.returncode == 0, f"scroll test did not finish (exit {result.returncode})"
    stats_file = OUT / f"m3_stats_{system}.prg"
    stats_file.unlink(missing_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", disk, "-read", "stats", stats_file],
           capture_output=True)
    raw = stats_file.read_bytes()[2:]                   # skip load address
    names = ["lost", "lag", "max_render_step", "cam_x", "cam_y", "shown_x", "shown_y",
             "front_cx", "front_cy", "row_cycles", "colour_cycles"]
    values = struct.unpack("<BBHHHHHHBHH", raw[:struct.calcsize("<BBHHHHHHBHH")])
    return system, dict(zip(names, values)), shot


def test_camera_reached_target(run):
    _, stats, _ = run
    assert (stats["cam_x"], stats["cam_y"]) == (360, 60)
    assert (stats["shown_x"], stats["shown_y"]) == (360, 60)
    assert (stats["front_cx"], stats["front_cy"]) == (45, 7)


def match_screen(expected: np.ndarray, rgb: np.ndarray, ignore: np.ndarray):
    """Compare a VICE screenshot window with C64 colour indices. VICE uses its own palette:
    each VICE colour is mapped to the index it covers most often; that mapping must be
    one-to-one. Returns the number of differing pixels."""
    packed = (rgb[..., 0].astype(np.int32) << 16) | (rgb[..., 1].astype(np.int32) << 8) | rgb[..., 2]
    mapping = {}
    for colour in np.unique(packed):
        indices = expected[(packed == colour) & ~ignore]
        if len(indices):
            mapping[int(colour)] = int(np.bincount(indices).argmax())
    if len(set(mapping.values())) != len(mapping):
        return expected.size
    actual = np.vectorize(lambda c: mapping.get(int(c), 255))(packed)
    return int(((expected != actual) & ~ignore).sum())


def test_screen_matches_converter_preview(run):
    _, stats, shot = run
    from tools.convert import c64, ega, original
    ep = original.load()
    lvl = c64.convert_level(ep.levels[1], ega.tiles(ep.header, ep.latch), ep.tileinfo)
    x, y = stats["shown_x"], stats["shown_y"]
    expected = c64.index_image(lvl)[y:y + WINDOW_H, x:x + WINDOW_W]
    # Animated tiles may show another frame than the preview's frame 0.
    animated = np.zeros(expected.shape[:2], bool)
    for ty in range(y // 16, (y + WINDOW_H) // 16 + 1):
        for tx in range(x // 16, (x + WINDOW_W) // 16 + 1):
            if ty < lvl.height and tx < lvl.width and lvl.tile_attr[lvl.map[ty][tx]] & c64.ANIMATED:
                y0, x0 = ty * 16 - y, tx * 16 - x
                animated[max(0, y0):max(0, y0 + 16), max(0, x0):max(0, x0 + 16)] = True
    image = np.asarray(Image.open(shot).convert("RGB"))
    # The display window lies at a different place in PAL and NTSC screenshots: find it.
    best = min((match_screen(expected, image[wy:wy + WINDOW_H, wx:wx + WINDOW_W], animated), wx, wy)
               for wy in range(0, image.shape[0] - WINDOW_H + 1)
               for wx in range(30, 50)
               if wy in range(10, 60))
    assert best[0] == 0, f"{best[0]} pixels differ (best window at {best[1:]})"


def test_scrolling_keeps_up(run):
    _, stats, _ = run
    # 410 frames of movement at up to 3 px per frame.
    assert stats["lost"] <= 5, stats
    assert stats["lag"] <= 30, stats


def test_cycle_budget(run):
    system, stats, _ = run
    assert stats["row_cycles"] < 1100, stats              # one rendered row
    # The measurement includes badline and sprite DMA delays; the update runs ahead of
    # the beam when it finishes before the deadline with some margin.
    assert stats["colour_cycles"] < DEADLINE[system] - 1000, stats
