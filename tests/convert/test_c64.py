"""M2: C64 conversion. Synthetic tests for the building blocks, plus limits on the real data."""
from __future__ import annotations

import numpy as np
import pytest

from tools.convert import c64, export, original, sprites


def test_halve_rarer_colour_wins():
    rows = [[0, 15] * 8] * 2 + [[0, 0] * 8] * 14           # thin white stripes on black
    fat = c64.halve(rows)
    assert (fat[0] == c64.EGA_TO_C64[15]).all()
    assert (fat[5] == 0).all()


def test_quantise_exact_when_colours_fit():
    shared = (0, 1, 2)
    char = np.array([[0, 1, 2, 5]] * 8)
    (q,), err = c64.quantise([char], shared)
    assert err == 0 and q.own == 5
    assert (q.colours(shared) == char).all()
    assert q.bytes()[0] == 0b00011011


def test_merge_chars_respects_limit_and_keeps_used():
    shared = (0, 1, 2)
    chars = [c64.Quantised(np.full((8, 4), i % 4), 3) for i in range(4)]
    chars += [c64.Quantised(np.full((8, 4), 3), 3)]           # duplicate look of char 3
    kept, remap, merged = c64.merge_chars(chars, [10, 10, 10, 10, 1], shared, 4)
    assert len(kept) == 4 and merged == 1
    assert remap[4] == remap[3]


def test_sprite_squeeze_keeps_height_21():
    rows = np.array([[i % 3] * 12 for i in range(24)])
    assert sprites.squeeze(rows, 21).shape == (21, 12)


def test_sprite_encode_bit_pairs():
    rows = np.full((21, 12), sprites.TRANSPARENT)
    rows[0, 0:3] = [0, 7, 1]                                 # shared0, own, shared1
    data = sprites.encode(rows, (0, 1), 7)
    assert data[0] == 0b01101100


def test_sid_frequency():
    assert export.sid_frequency(0) == 0
    hz = 1193181 / 2712                                     # about 440 Hz
    assert abs(export.sid_frequency(2712) - hz * 16777216 / 985248) < 1


@pytest.fixture(scope="module")
def ep():
    if not (original.ORIGINAL / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    return original.load()


def test_every_level_fits(ep):
    from tools.convert import ega
    tiles = ega.tiles(ep.header, ep.latch)
    for n, lvl in ep.levels.items():
        c = c64.convert_level(lvl, tiles, ep.tileinfo)
        assert len(c.chars) <= c64.CHAR_LIMIT, n
        assert len(c.tiles) <= c64.MAX_TILES, n
        assert len(c.anims) <= export.MAX_ANIMS, n
        data = export.level_file(c)
        assert len(data) - 2 <= export.OFF_MAP + export.MAP_SIZE, n


def test_sprites_fit_in_slots(ep):
    spr, shared = sprites.convert(ep.header, ep.sprite_data)
    pointers = [p.pointer for s in spr for p in s.pieces]
    assert len(pointers) == len(set(pointers)) <= len(sprites.SLOTS)
    assert shared == (0, 1)
    assert all(len(s.pieces) == 2 for s in spr[:32])         # layered Keen
