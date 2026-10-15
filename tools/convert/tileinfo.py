"""Keen 1-3 tileinfo: six planes of int16 per tile, stored in the (unpacked) EXE.

Reference: https://moddingwiki.shikadi.net/wiki/Keen_1-3_Tileinfo_format
Measured on KEEN1.EXE v1.31: the table starts at offset 0x130F8 of the LZEXE load
image, and the animation plane uses 1 (not 0) for tiles that do not animate.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

TILEINFO_OFFSET_V131 = 0x130F8


@dataclass(frozen=True)
class TileInfo:
    anim: int        # number of animation frames (1, 2 or 4)
    behaviour: int   # -2 masked, -1 foreground, 0 nothing, 1 kills, 2-5 doors, ...
    top: int         # 0 fall through, 1 solid, 2 slippery, 3 ice
    right: int
    bottom: int
    left: int


def read(image: bytes, count: int, offset: int = TILEINFO_OFFSET_V131) -> list[TileInfo]:
    words = struct.unpack_from(f"<{count * 6}h", image, offset)
    planes = [words[p * count:(p + 1) * count] for p in range(6)]
    return [TileInfo(*(plane[t] for plane in planes)) for t in range(count)]
