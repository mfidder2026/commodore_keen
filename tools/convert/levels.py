"""Keen 1-3 levels: RLEW-compressed, a 32-byte header and two planes of uint16.

References:
- https://moddingwiki.shikadi.net/wiki/Commander_Keen_1-3_Level_format
- https://moddingwiki.shikadi.net/wiki/Id_Software_RLEW_compression
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

RLEW_FLAG = 0xFEFE
HEADER_SIZE = 32
WORLD_MAP = 80


def rlew_decompress(data: bytes, flag: int = RLEW_FLAG) -> bytes:
    size, = struct.unpack_from("<I", data, 0)
    words = []
    pos = 4
    while len(words) * 2 < size:
        word, = struct.unpack_from("<H", data, pos)
        pos += 2
        if word == flag:
            count, value = struct.unpack_from("<HH", data, pos)
            pos += 4
            words.extend([value] * count)
        else:
            words.append(word)
    out = struct.pack(f"<{len(words)}H", *words)
    if len(out) != size:
        raise ValueError(f"RLEW size mismatch: got {len(out)}, header says {size}")
    return out


@dataclass
class Level:
    number: int
    width: int
    height: int
    tiles: list[list[int]]     # [y][x] tile number
    sprites: list[list[int]]   # [y][x] sprite/actor code, 0 = none


def parse(number: int, raw: bytes) -> Level:
    data = rlew_decompress(raw)
    width, height, planes = struct.unpack_from("<HHH", data, 0)
    plane_size, = struct.unpack_from("<H", data, 14)
    if planes != 2:
        raise ValueError(f"level {number}: expected 2 planes, got {planes}")

    def plane(index: int) -> list[list[int]]:
        start = HEADER_SIZE + index * plane_size
        words = struct.unpack_from(f"<{width * height}H", data, start)
        return [list(words[y * width:(y + 1) * width]) for y in range(height)]

    return Level(number, width, height, plane(0), plane(1))
