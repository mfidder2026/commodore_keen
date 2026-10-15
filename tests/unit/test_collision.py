"""M4: Keen's collision routines in py65, on the real level 1 data.

Keen is placed at known spots and player_update runs for a number of ticks with a fixed
joystick state; the result must follow the tile flags (tileinfo) of the converted level.
"""
from __future__ import annotations

import pytest

import toolchain as tc
from test_build import Machine

JOY_UP, JOY_LEFT, JOY_RIGHT = 1, 4, 8
ZP = {"p_x": 0x30, "p_y": 0x32, "p_vx": 0x34, "p_vy": 0x35, "p_ground": 0x36, "joy": 0x3B}


@pytest.fixture
def keen(built_d64):
    if not (tc.BUILD / "assets" / "l01.prg").is_file():
        pytest.skip("converted level 1 not available")
    m = Machine()
    m.load(tc.BUILD / "assets" / "l01.prg")
    m.call("level_init")
    m.call("player_init")
    return m


def place(m, x_px, feet_y):
    mem = m.mpu.memory
    x, y = x_px * 16, (feet_y - 23) * 16
    mem[ZP["p_x"]], mem[ZP["p_x"] + 1] = x & 0xFF, x >> 8
    mem[ZP["p_y"]], mem[ZP["p_y"] + 1] = y & 0xFF, y >> 8
    mem[ZP["p_vx"]] = mem[ZP["p_vy"]] = 0


def run(m, ticks, joy=0):
    for _ in range(ticks):
        m.mpu.memory[ZP["joy"]] = joy
        m.mpu.memory[0x3D] = 0                   # joy_new
        m.call("player_update")


def pos(m):
    mem = m.mpu.memory
    x = mem[ZP["p_x"]] | mem[ZP["p_x"] + 1] << 8
    y = mem[ZP["p_y"]] | mem[ZP["p_y"] + 1] << 8
    return x / 16, y / 16 + 23


@pytest.fixture(scope="module")
def info():
    from tools.convert import original
    ep = original.load()
    return ep.levels[1], ep.tileinfo


@pytest.mark.parametrize("x", [48, 130, 200, 500])
def test_falls_and_lands_on_first_floor_below(keen, info, x):
    level, ti = info
    cols = {(x + 4) // 16, (x + 11) // 16}
    start_feet = 120
    floor_row = next(r for r in range(start_feet // 16 + 1, level.height)
                     if any(ti[level.tiles[r][c]].top for c in cols))
    place(keen, x, start_feet)
    run(keen, 80)
    assert pos(keen)[1] == floor_row * 16 - 1
    assert keen.mpu.memory[ZP["p_ground"]] == 1


def test_stands_still_on_the_floor(keen):
    place(keen, 48, 271)
    run(keen, 30)
    assert pos(keen) == (48, 271)


def test_wall_stops_walking_left(keen, info):
    level, ti = info
    row_feet = 271 // 16
    rows = range((271 - 22) // 16, row_feet + 1)
    wall_col = max(c for c in range(0, 3) if any(ti[level.tiles[r][c]].right for r in rows))
    place(keen, 48, 271)
    run(keen, 60, JOY_LEFT)
    x, y = pos(keen)
    assert x + 4 == (wall_col + 1) * 16           # box left edge against the wall's right side
    assert y == 271


def test_ceiling_stops_jump(keen):
    place(keen, 340, 271)                         # under the platform of row 13 (bottom at 223)
    run(keen, 1, JOY_UP)
    run(keen, 20)
    apex = min(pos(keen)[1] for _ in range(1))
    top = pos(keen)[1] - 23
    assert top >= 224 - 1                         # never above the ceiling
