"""M3: scroll engine in VICE.

Builds the SCROLLTEST variant (tests/scenarios/m3_scroll.asm), runs it headless and checks:
- the final screen equals the converter's preview of level 1 at the final camera position,
- the camera was followed (statistics written by the test program as STATS on the disk),
- the measured cycle counts stay within the frame budget (docs/budget.md).
"""
from __future__ import annotations

import struct
import subprocess

import numpy as np
import pytest
from PIL import Image

import toolchain as tc
from conftest import require

OUT = tc.BUILD / "test"
# Window of the 38 x 24 character display inside a VICE PAL screenshot (384 x 272):
# the text area starts at (32, 35) in 40 x 25 mode; 38 columns hide 7 pixels left,
# 24 rows hide 4 pixels at the top.
WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H = 32 + 7, 35 + 4, 304, 192


@pytest.fixture(scope="module")
def run():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not (tc.ROOT / "data" / "original" / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    from build import build
    d64 = build(["SCROLLTEST"])
    shot = OUT / "m3_scroll.png"
    shot.unlink(missing_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    result = tc.run([require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
                     "-sounddev", "dummy", "-debugcart", "-limitcycles", 80_000_000,
                     "-VICIIextpal", "-VICIIpalette", "pepto-pal.vpl", "-VICIIfilter", 0,
                     "-exitscreenshot", shot, "-autostart", d64],
                    # VICE 3.9 on Windows sometimes crashes (0xC0000409) when its output
                    # goes to a pipe; it is not needed here.
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    assert result.returncode == 0, f"scroll test did not finish (exit {result.returncode})"
    stats_file = OUT / "m3_stats.prg"
    stats_file.unlink(missing_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", d64, "-read", "stats", stats_file],
           capture_output=True)
    raw = stats_file.read_bytes()[2:]                   # skip load address
    names = ["lost", "lag", "max_render_step", "cam_x", "cam_y", "shown_x", "shown_y",
             "front_cx", "front_cy", "row_cycles", "colour_cycles"]
    values = struct.unpack("<BBHHHHHHBHH", raw[:struct.calcsize("<BBHHHHHHBHH")])
    return dict(zip(names, values)), shot


def test_camera_reached_target(run):
    stats, _ = run
    assert (stats["cam_x"], stats["cam_y"]) == (360, 60)
    assert (stats["shown_x"], stats["shown_y"]) == (360, 60)
    assert (stats["front_cx"], stats["front_cy"]) == (45, 7)


def test_screen_matches_converter_preview(run):
    stats, shot = run
    from tools.convert import c64, ega, original
    ep = original.load()
    lvl = c64.convert_level(ep.levels[1], ega.tiles(ep.header, ep.latch), ep.tileinfo)
    x, y = stats["shown_x"], stats["shown_y"]
    expected = c64.index_image(lvl)[y:y + WINDOW_H, x:x + WINDOW_W]
    rgb = np.asarray(Image.open(shot).convert("RGB"))[WINDOW_Y:WINDOW_Y + WINDOW_H,
                                                      WINDOW_X:WINDOW_X + WINDOW_W]
    # Animated tiles may show another frame than the preview's frame 0.
    animated = np.zeros(expected.shape[:2], bool)
    for ty in range(y // 16, (y + WINDOW_H) // 16 + 1):
        for tx in range(x // 16, (x + WINDOW_W) // 16 + 1):
            if ty < lvl.height and tx < lvl.width and lvl.tile_attr[lvl.map[ty][tx]] & c64.ANIMATED:
                y0, x0 = ty * 16 - y, tx * 16 - x
                animated[max(0, y0):max(0, y0 + 16), max(0, x0):max(0, x0 + 16)] = True
    # VICE screenshots use its own palette: map each VICE colour to the C64 colour index
    # it covers most often; that mapping must be one-to-one.
    packed = (rgb[..., 0].astype(np.int32) << 16) | (rgb[..., 1].astype(np.int32) << 8) | rgb[..., 2]
    mapping = {}
    for colour in np.unique(packed):
        indices = expected[(packed == colour) & ~animated]
        if len(indices):
            mapping[int(colour)] = int(np.bincount(indices).argmax())
    assert len(set(mapping.values())) == len(mapping), f"palette mapping not one-to-one: {mapping}"
    actual = np.vectorize(lambda c: mapping.get(int(c), 255))(packed)
    diff = (expected != actual) & ~animated
    assert diff.sum() == 0, f"{diff.sum()} pixels differ, first at {np.argwhere(diff)[0]}"


def test_scrolling_keeps_up(run):
    stats, _ = run
    # 410 frames of movement at up to 3 px per frame.
    assert stats["lost"] <= 5, stats
    assert stats["lag"] <= 30, stats


def test_cycle_budget(run):
    stats, _ = run
    assert stats["row_cycles"] < 1100, stats              # one rendered row
    # The colour update starts at line 251 and must finish each row before the beam
    # reaches it: the beam is at row 24 after (312 - 251 + 51 + 24 * 8) * 63 = 19,152
    # cycles. The measurement includes badline and sprite DMA delays.
    assert stats["colour_cycles"] < 18500, stats
