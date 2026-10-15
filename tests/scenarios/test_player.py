"""M4: Keen's movement in VICE compared with the original game.

The PLAYERTEST build replays a joystick script in level 1 and saves Keen's position per
tick. Reference values were measured in the original (v1.31) in DOSBox with
tools/dosbox_capture.py and tools/measure_keen.py on 16 October 2026:
- walking speed about 123 px/s (2.46 px per 50 Hz tick)
- standing at the start: feet at y = 271
- jump at x = 258: apex 53 px above the feet, landing on the platform at y = 239
  about 0.78 s after takeoff
"""
from __future__ import annotations

import struct
import subprocess

import pytest

import toolchain as tc
from conftest import require

OUT = tc.BUILD / "test"
JUMP_TICK = 20 + 86 + 74                      # first tick with the joystick up


@pytest.fixture(scope="module")
def track():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not (tc.ROOT / "data" / "original" / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    from build import build
    d64 = build(["PLAYERTEST", "INPUTSCRIPT"])
    result = tc.run([require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
                     "-sounddev", "dummy", "-debugcart", "-limitcycles", 80_000_000,
                     "-autostart", d64],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    assert result.returncode == 0, f"player test did not finish (exit {result.returncode})"
    rec = OUT / "m4_rec.prg"
    rec.unlink(missing_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", d64, "-read", "stats", rec], capture_output=True)
    raw = rec.read_bytes()[2:]
    # (x, feet y) in pixels per tick
    return [(x / 16, y / 16 + 23) for x, y in
            (struct.unpack_from("<HH", raw, i * 4) for i in range(len(raw) // 4))]


def test_start_position(track):
    assert track[0] == (48, 271)


def test_walking_speed(track):
    # steady state, after the acceleration: ticks 40..100 of walking right
    speed = (track[100][0] - track[40][0]) / 60
    assert speed == pytest.approx(2.46, abs=0.1)


def test_jump_height_and_landing(track):
    takeoff = track[JUMP_TICK - 1]
    assert takeoff[0] == pytest.approx(258, abs=4)
    apex = min(y for _, y in track[JUMP_TICK:JUMP_TICK + 40])
    assert takeoff[1] - apex == pytest.approx(53, abs=3)
    landing = next(i for i in range(JUMP_TICK + 10, len(track)) if track[i][1] == 239)
    assert (landing - JUMP_TICK) / 50 == pytest.approx(0.78, abs=0.08)
