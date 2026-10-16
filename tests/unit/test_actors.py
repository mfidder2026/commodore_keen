"""M6: raygun and enemies in py65 (level 1, with an enemy put in front of Keen)."""
from __future__ import annotations

import pytest

from test_collision import ZP, place
from test_items import start

JOY_FIRE = 16
T_YORP, T_VORT, T_BUTLER, T_KEENSHOT = 1, 3, 4, 11
S_DEAD = 3


def setup(enemy_type, ammo=5):
    m = start(1)
    mem, L = m.mpu.memory, m.labels
    for i in range(48):                              # clear the level's own actors
        mem[L["act_type"] + i] = 0
    place(m, 48, 271)                                # Keen at the start, facing right
    mem[0x37] = 0
    x, y = 48 + 64, 271 - 31                         # enemy 64 px to the right on the floor
    slot = 0
    mem[L["act_type"] + slot] = enemy_type
    mem[L["act_state"] + slot] = 0
    mem[L["act_hp"] + slot] = 4
    mem[L["act_dir"] + slot] = 1
    for name, value in (("act_x", x * 16), ("act_y", y * 16)):
        mem[L[name + "_lo"] + slot] = value & 0xFF
        mem[L[name + "_hi"] + slot] = value >> 8
    mem[L["ammo"]] = ammo
    return m


def tick(m, joy=0, new=0):
    m.mpu.memory[ZP["joy"]] = joy
    m.mpu.memory[0x3D] = new
    for routine in ("player_update", "player_touch", "actors_update", "camera_follow"):
        m.call(routine)


def fire(m, ticks=20):
    tick(m, JOY_FIRE, JOY_FIRE)
    for _ in range(ticks):
        tick(m)


def state(m, slot=0):
    return m.mpu.memory[m.labels["act_state"] + slot]


def shots(m):
    L, mem = m.labels, m.mpu.memory
    return sum(1 for i in range(48) if mem[L["act_type"] + i] == T_KEENSHOT)


@pytest.fixture(autouse=True)
def built(built_d64):
    pass


def test_shot_kills_yorp():
    m = setup(T_YORP)
    fire(m)
    assert state(m) == S_DEAD
    assert m.mpu.memory[m.labels["ammo"]] == 4


def test_vorticon_needs_four_hits():
    # The Vorticon jumps towards Keen now and then, so not every shot hits: count hits.
    m = setup(T_VORT, ammo=20)
    hp = m.mpu.memory[m.labels["act_hp"]]
    hits = 0
    for _ in range(20):
        fire(m)
        now = m.mpu.memory[m.labels["act_hp"]]
        if now < hp or state(m) == S_DEAD:
            hits += 1
        hp = now
        if state(m) == S_DEAD:
            break
        assert hits < 4, "still alive after four hits"
    assert state(m) == S_DEAD and hits == 4


def test_butler_absorbs_shots():
    m = setup(T_BUTLER)
    fire(m)
    assert state(m) != S_DEAD


def test_no_ammo_no_shot():
    m = setup(T_YORP, ammo=0)
    tick(m, JOY_FIRE, JOY_FIRE)
    assert shots(m) == 0
    fire(m)
    assert state(m) != S_DEAD
