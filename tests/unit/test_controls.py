"""M9: alternative control layout (fire jumps, down + fire shoots) in py65."""
from __future__ import annotations

import pytest

from test_build import Machine

UP, DOWN, LEFT, RIGHT, FIRE, SPACE = 1, 2, 4, 8, 16, 32


@pytest.fixture
def m(built_d64):
    return Machine()


def remap(m, joy, alt):
    mem, L = m.mpu.memory, m.labels
    mem[L["ctrl_alt"]] = alt
    mem[0x3B] = joy
    m.call("remap_controls")
    return mem[0x3B]


@pytest.mark.parametrize("joy", [UP, FIRE, DOWN | FIRE, LEFT | FIRE, SPACE])
def test_standard_layout_unchanged(m, joy):
    assert remap(m, joy, 0) == joy


@pytest.mark.parametrize("joy, expected", [
    (FIRE, UP),                       # fire jumps
    (DOWN | FIRE, FIRE),              # down + fire shoots
    (RIGHT | FIRE, RIGHT | UP),       # jump while walking
    (UP, 0),                          # up does nothing
    (DOWN, 0),                        # no down+fire pogo: down is dropped
    (SPACE, SPACE),                   # pogo on space
])
def test_alternative_layout(m, joy, expected):
    assert remap(m, joy, 1) == expected


def test_new_presses_follow_the_remapped_bits(m):
    mem, L = m.mpu.memory, m.labels
    remap(m, 0, 1)
    remap(m, FIRE, 1)
    assert mem[0x3D] == UP                           # joy_new: jump pressed now
    remap(m, FIRE, 1)
    assert mem[0x3D] == 0                            # held, not new


# Keyboard: kb_rows holds keyboard rows PA0-PA2 (1 = pressed), see the C64-Wiki matrix.
ROW = {"W": (1, 0x02), "A": (1, 0x04), "S": (1, 0x20), "D": (2, 0x04), "RETURN": (0, 0x02)}


def keys(m, pressed, joy=0):
    mem, L = m.mpu.memory, m.labels
    rows = [0, 0, 0]
    for key in pressed:
        r, bit = ROW[key]
        rows[r] |= bit
    mem[L["kb_rows"]:L["kb_rows"] + 3] = rows
    mem[0x3B] = joy
    m.call("keys_decode")
    return mem[0x3B]


@pytest.mark.parametrize("pressed, expected", [
    ((), 0),
    (("W",), UP),
    (("A",), LEFT),
    (("S",), DOWN),
    (("D",), RIGHT),
    (("RETURN",), FIRE),
    (("D", "W"), RIGHT | UP),                 # jump while walking right
    (("S", "RETURN"), DOWN | FIRE),           # pogo
])
def test_keys_become_joystick_bits(m, pressed, expected):
    assert keys(m, pressed) == expected


def test_keys_add_to_the_joystick(m):
    assert keys(m, ("A",), joy=FIRE | SPACE) == LEFT | FIRE | SPACE


def test_other_keys_in_the_rows_are_ignored(m):
    mem, L = m.mpu.memory, m.labels
    mem[L["kb_rows"]:L["kb_rows"] + 3] = [0xFF & ~0x02, 0xFF & ~0x26, 0xFF & ~0x04]
    mem[0x3B] = 0
    m.call("keys_decode")
    assert mem[0x3B] == 0
