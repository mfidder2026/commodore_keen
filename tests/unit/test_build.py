"""M0: the build produces a .d64 with a runnable program, checked in py65."""
from __future__ import annotations

from py65.devices.mpu6502 import MPU

import toolchain as tc
from conftest import read_vice_labels

SCREEN = 0x0400


def screencodes(text: str) -> list[int]:
    # Upper case screencodes: A-Z = 1-26, space and digits equal ASCII.
    return [ord(c) - 64 if "A" <= c <= "Z" else ord(c) for c in text]


def test_d64_is_built(built_d64):
    assert built_d64.stat().st_size == 174848           # standard 35-track .d64


def test_prg_loads_at_basic_start(built_d64):
    prg = (tc.BUILD / tc.PRG_NAME).read_bytes()
    assert prg[0] | prg[1] << 8 == 0x0801


def test_title_screen_in_py65(built_d64):
    prg = (tc.BUILD / tc.PRG_NAME).read_bytes()
    labels = read_vice_labels(tc.BUILD / "main.vs")
    mpu = MPU()
    load = prg[0] | prg[1] << 8
    mpu.memory[load:load + len(prg) - 2] = prg[2:]
    mpu.pc = labels["start"]
    for _ in range(100_000):
        if mpu.pc == labels["idle"]:
            break
        mpu.step()
    else:
        raise AssertionError("never reached idle loop")

    row = SCREEN + 10 * 40
    line = mpu.memory[row:row + 40]
    title = screencodes("COMMANDER KEEN C64")
    start = (40 - len(title)) // 2
    assert line[start:start + len(title)] == title
