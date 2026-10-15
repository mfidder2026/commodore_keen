"""M8: the sound engine in py65 with the converted SOUNDS file."""
from __future__ import annotations

import struct

import pytest

import toolchain as tc
from test_build import Machine

SID = 0xD400


@pytest.fixture
def machine(built_d64):
    path = tc.BUILD / "assets" / "sounds.prg"
    if not path.is_file():
        pytest.skip("converted sounds not available")
    m = Machine()
    m.load(path)
    m.call("sound_init")
    return m


def constants():
    values = {}
    for line in (tc.BUILD / "generated" / "gen_sounds.asm").read_text().splitlines():
        if line.startswith(".const "):
            name, _, value = line[7:].partition(" = ")
            values[name] = int(value.replace("$", "0x"), 0)
    return values


def frequencies(m, number):
    """The frequency list of a sound, read from the loaded SOUNDS data."""
    c = constants()
    mem = m.mpu.memory
    addr = mem[c["SOUND_LO"] + number] | mem[c["SOUND_HI"] + number] << 8
    out = []
    while True:
        v = mem[addr] | mem[addr + 1] << 8
        if v == 0xFFFF:
            return out
        out.append(v)
        addr += 2


def play(m, number):
    m.mpu.a = number
    m.call("sound_play")


def tick(m):
    m.call("sound_tick")
    mem = m.mpu.memory
    return mem[SID] | mem[SID + 1] << 8, mem[SID + 4] & 1


def test_init_sets_volume_and_pulse(machine):
    mem = machine.mpu.memory
    assert mem[SID + 0x18] == 0x0F
    assert mem[SID + 3] == 0x08                     # 50 % pulse width


def test_sound_plays_frame_by_frame_then_stops(machine):
    jump = constants()["SND_KEENJUMPSND"]
    expected = frequencies(machine, jump)
    assert expected
    play(machine, jump)
    for f in expected:
        freq, gate = tick(machine)
        if f:
            assert (freq, gate) == (f, 1)
        else:
            assert gate == 0
    assert tick(machine)[1] == 0                   # finished: gate off
    assert machine.mpu.memory[machine.labels["snd_active"]] == 0


def test_priority(machine):
    c = constants()
    die, walk = c["SND_KEENDIESND"], c["SND_KEENWALKSND"]   # priority 255 and 128
    play(machine, die)
    tick(machine)
    play(machine, walk)                            # lower priority: ignored
    assert tick(machine)[0] == frequencies(machine, die)[1] or frequencies(machine, die)[1] == 0
    play(machine, c["SND_LVLDONESND"])             # equal priority (255): interrupts
    assert tick(machine)[0] == frequencies(machine, c["SND_LVLDONESND"])[0]


def test_frequency_conversion(machine):
    from tools.convert import original, export
    ep = original.load()
    jump = constants()["SND_KEENJUMPSND"]
    first = ep.sounds[jump].samples[0]
    assert frequencies(machine, jump)[0] == export.sid_frequency(first)
