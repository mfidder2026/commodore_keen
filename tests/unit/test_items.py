"""M5: items, doors and deadly tiles in py65 on the real (converted) levels."""
from __future__ import annotations

import pytest

import toolchain as tc
from test_build import Machine
from test_collision import ZP, place, pos, run

JOY_RIGHT = 8


@pytest.fixture(scope="module")
def episode():
    from tools.convert import original
    if not (original.ORIGINAL / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    return original.load()


def start(number):
    m = Machine()
    m.load(tc.BUILD / "assets" / f"l{number:02d}.prg")
    for routine in ("level_init", "anim_init", "game_new", "items_level_start", "player_init",
                    "camera_center", "scroll_init"):
        m.call(routine)
    m.mpu.memory[m.labels["play_result"]] = 0
    return m


def touch(m, ticks=1, joy=0):
    for _ in range(ticks):
        run(m, 1, joy)
        m.call("player_touch")


def map_tile(m, col, row):
    """C64 tile number at (col, row) in the level map in memory."""
    width = m.mpu.memory[0x5002]
    return m.mpu.memory[0x6C00 + row * width + col]


def bcd_score(m):
    a = m.labels["score"]
    s = m.mpu.memory[a:a + 3]
    return int(f"{s[2]:02x}{s[1]:02x}{s[0]:02x}")


def find(level, info, behaviours):
    return [(x, y, info[t].behaviour) for y, row in enumerate(level.tiles)
            for x, t in enumerate(row) if info[t].behaviour in behaviours]


def test_collecting_points_item(built_d64, episode):
    level, info = episode.levels[1], episode.tileinfo
    points = {6: 500, 7: 100, 8: 200, 9: 1000, 10: 5000}
    col, row, beh = find(level, info, points)[0]
    m = start(1)
    before = map_tile(m, col, row)
    place(m, col * 16 - 4, row * 16 + 15)          # Keen's box over the item
    m.mpu.memory[ZP["p_vy"]] = 0
    m.call("player_touch")
    assert bcd_score(m) == points[beh]
    after = map_tile(m, col, row)
    assert after != before
    behaviour_table = m.mpu.memory[0x5E00:0x5F00]
    assert behaviour_table[after] == 0             # replaced by an empty tile


def test_deadly_tile_kills(built_d64, episode):
    level, info = episode.levels[1], episode.tileinfo
    col, row, _ = find(level, info, {1})[0]
    m = start(1)
    place(m, col * 16 - 4, row * 16 + 15)
    m.call("player_touch")
    assert m.mpu.memory[m.labels["play_result"]] == 1


def door_setup(keycard: bool):
    # Level 4: door 1 at column 31, rows 4-5, in a passage Keen jumps into.
    # Keen is put in the passage (box rows 4-5), right next to the door, moving right.
    m = start(4)
    place(m, 31 * 16 - 12, 6 * 16 - 1)
    m.mpu.memory[ZP["p_vx"]] = 30
    if keycard:
        m.mpu.memory[m.labels["keycards"]] = 1
    return m


def test_door_blocks_without_keycard(built_d64):
    m = door_setup(False)
    touch(m, 1, JOY_RIGHT)
    x, _ = pos(m)
    assert x + 11 == 31 * 16 - 1                    # stopped against the door


def test_door_opens_with_keycard(built_d64):
    m = door_setup(True)
    touch(m, 1, JOY_RIGHT)
    x, _ = pos(m)
    assert x + 11 > 31 * 16 - 1                     # moved into the door column
    behaviour_table = m.mpu.memory[0x5E00:0x5F00]
    assert behaviour_table[map_tile(m, 31, 4)] == 0
    assert behaviour_table[map_tile(m, 31, 5)] == 0
