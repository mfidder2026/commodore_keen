"""The build produces a .d64; engine routines checked in py65 against the converter."""
from __future__ import annotations

import pytest
from py65.devices.mpu6502 import MPU

import toolchain as tc
from conftest import read_vice_labels

SCREEN_A, COLOUR_RAM, LEVEL_BASE = 0xC000, 0xD800, 0x5000
RETURN_TRAP = 0x0334                          # cassette buffer: unused, never executed


def test_d64_is_built(built_d64):
    assert built_d64.stat().st_size == 174848           # standard 35-track .d64


def test_prg_loads_at_basic_start(built_d64):
    prg = (tc.BUILD / tc.PRG_NAME).read_bytes()
    assert prg[0] | prg[1] << 8 == 0x0801


class Machine:
    """The game program in py65; I/O addresses are plain RAM here."""

    def __init__(self):
        prg = (tc.BUILD / tc.PRG_NAME).read_bytes()
        self.labels = read_vice_labels(tc.BUILD / "main.vs")
        self.mpu = MPU()
        load = prg[0] | prg[1] << 8
        self.mpu.memory[load:load + len(prg) - 2] = prg[2:]

    def load(self, path):
        data = path.read_bytes()
        addr = data[0] | data[1] << 8
        self.mpu.memory[addr:addr + len(data) - 2] = data[2:]

    def poke16(self, label, value):
        a = self.labels[label]
        self.mpu.memory[a] = value & 0xFF
        self.mpu.memory[a + 1] = value >> 8

    def call(self, label, max_steps=2_000_000):
        """jsr label and run until it returns."""
        m = self.mpu
        m.sp = 0xFD
        ret = RETURN_TRAP - 1
        m.memory[0x1FE] = ret & 0xFF
        m.memory[0x1FF] = ret >> 8
        m.sp = 0xFD
        m.pc = self.labels[label]
        for _ in range(max_steps):
            if m.pc == RETURN_TRAP:
                return
            m.step()
        raise AssertionError(f"{label} did not return")


@pytest.fixture(scope="module")
def level1(built_d64):
    from tools.convert import c64, ega, original
    if not (original.ORIGINAL / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    ep = original.load()
    return c64.convert_level(ep.levels[1], ega.tiles(ep.header, ep.latch), ep.tileinfo)


@pytest.mark.parametrize("cam_x, cam_y", [(0, 0), (100, 40), (1616, 144), (5000, 999)])
def test_scroll_init_renders_level_in_py65(level1, cam_x, cam_y):
    """level_init + scroll_init: screen A and colour RAM equal the converted level."""
    m = Machine()
    m.load(tc.BUILD / "assets" / "l01.prg")
    m.call("level_init")
    m.poke16("cam_x", cam_x)
    m.poke16("cam_y", cam_y)
    m.call("scroll_init")

    max_x, max_y = level1.width * 16 - 304, level1.height * 16 - 192
    cx, cy = min(cam_x, max_x) // 8, min(cam_y, max_y) // 8
    mem = m.mpu.memory
    for row in range(25):
        ty, half = divmod(cy + row, 2)
        for col in range(39):                            # column 39 is never visible
            tx, right = divmod(cx + col, 2)
            if ty >= level1.height or tx >= level1.width:
                continue
            char = level1.tiles[level1.map[ty][tx]][half * 2 + right]
            assert mem[SCREEN_A + row * 40 + col] == char, (row, col)
            colour = level1.chars[char].own | 8
            assert mem[COLOUR_RAM + row * 40 + col] == colour, (row, col)
