"""M1: decoding the user's own Keen 1 v1.31 files in data/original/.

Skipped when the files are missing. Only counts and hashes are stored here, never id data.
The hashes guard against regressions; correctness was established by comparing renders
with DOSBox screenshots (see test_dosbox.py and docs/formats.md).
"""
from __future__ import annotations

import hashlib
import struct
from collections import Counter

import pytest

from tools.convert import ega, original

KEEN1_V131_SHA256 = "8b3f829f7eeab18a"     # first 16 hex digits of KEEN1.EXE v1.31


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


@pytest.fixture(scope="module")
def ep():
    exe = original.ORIGINAL / "KEEN1.EXE"
    if not exe.is_file():
        pytest.skip("Keen 1 files not in data/original/")
    if sha(exe.read_bytes()) != KEEN1_V131_SHA256:
        pytest.skip("KEEN1.EXE is not the v1.31 shareware release these tests were made for")
    return original.load()


def level_bytes(lvl) -> bytes:
    rows = lvl.tiles + lvl.sprites
    return b"".join(struct.pack(f"<{lvl.width}H", *row) for row in rows)


def test_tile_count_is_611(ep):
    assert ep.header.tile_count == 611
    assert len(ep.tileinfo) == 611
    assert len(ega.tiles(ep.header, ep.latch)) == 611


def test_graphics_counts_and_layout(ep):
    h = ep.header
    assert (h.font_count, len(h.bitmaps), len(h.sprites)) == (256, 18, 119)
    assert h.tile_location == h.font_location + h.font_count * 8      # font, then tiles
    assert h.bitmap_location == h.tile_location + h.tile_count * 32   # tiles, then bitmaps
    assert len(ep.latch) == 4 * h.latch_plane_size
    assert len(ep.sprite_data) == 5 * h.sprite_plane_size


def test_decoded_data_hashes(ep):
    assert sha(ep.exe_image) == "f2a38bf36ac19dba"
    assert sha(ep.latch) == "c510e298dae0db41"
    assert sha(ep.sprite_data) == "832035d656479e64"
    tileinfo_bytes = b"".join(struct.pack("<6h", *vars(t).values()) for t in ep.tileinfo)
    assert sha(tileinfo_bytes) == "ef57ffc6e959dd9a"


LEVEL_HASHES = {
    1: "9a0dd01cd7d4f08b", 2: "edc974c9e600526d", 3: "c59b05d4eb4c7d6f", 4: "9f687c0c26ff76a1",
    5: "25067072ba95d8f7", 6: "dbf2480fdb3a3c43", 7: "699c96c7384185c6", 8: "c568f8c12bcf7c9a",
    9: "775a743896341e89", 10: "10cc2f9e739a391c", 11: "268e48a427f118a3", 12: "5f367f8ce97023e6",
    13: "8667aa9342d91732", 14: "93b223bdf10601d5", 15: "3f8e57c8b0cfee76", 16: "f2c67f11fb20b066",
    80: "7dcf83ce1489fcc3", 81: "44b40cc9c53862cf", 90: "8dc87b637a375464",
}


@pytest.mark.parametrize("number", sorted(LEVEL_HASHES))
def test_level_decodes(ep, number):
    lvl = ep.levels[number]
    assert max(max(row) for row in lvl.tiles) < ep.header.tile_count
    assert sha(level_bytes(lvl)) == LEVEL_HASHES[number]


def test_world_map_has_all_16_level_entrances(ep):
    codes = {c for row in ep.levels[80].sprites for c in row}
    assert set(range(1, 17)) <= codes
    assert 255 in codes                                     # Keen's start position


def test_tileinfo_plausible(ep):
    anim = Counter(t.anim for t in ep.tileinfo)
    assert set(anim) == {1, 2, 4}
    assert all(-2 <= t.behaviour <= 28 for t in ep.tileinfo)
    assert all(t.top in (0, 1, 2, 3) for t in ep.tileinfo)


def test_sounds(ep):
    named = [s for s in ep.sounds if s.name != "__UnNamed__"]
    assert len(ep.sounds) == 60 and len(named) == 41
    assert named[0].name == "WLDWALKSND" and named[-1].name == "keensleft"
    assert sha(b"".join(struct.pack(f"<{len(s.samples)}H", *s.samples) for s in ep.sounds)) == "888436f869f16d19"
