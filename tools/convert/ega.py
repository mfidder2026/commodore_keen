"""EGA graphics of Keen 1: EGAHEAD.CK1 plus the planar EGALATCH/EGASPRIT files.

References:
- https://moddingwiki.shikadi.net/wiki/Commander_Keen_EGA_Header
- https://moddingwiki.shikadi.net/wiki/Raw_EGA_data (planes B, G, R, I; mask as 5th plane)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from . import keen_lzw

# Standard 16-colour EGA palette (RGB).
PALETTE = [
    (0x00, 0x00, 0x00), (0x00, 0x00, 0xAA), (0x00, 0xAA, 0x00), (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00), (0xAA, 0x00, 0xAA), (0xAA, 0x55, 0x00), (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55), (0x55, 0x55, 0xFF), (0x55, 0xFF, 0x55), (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55), (0xFF, 0x55, 0xFF), (0xFF, 0xFF, 0x55), (0xFF, 0xFF, 0xFF),
]
TRANSPARENT = 16      # pixel value used for transparent sprite pixels

COMPRESSED_LATCH = 2
COMPRESSED_SPRITES = 1


@dataclass
class Bitmap:
    width: int        # pixels
    height: int
    location: int     # byte offset inside each plane
    name: str


@dataclass
class Sprite:
    width: int        # pixels
    height: int
    location: int     # byte offset inside each plane
    hitbox: tuple[int, int, int, int]   # left, top, right, bottom in pixels
    name: str


@dataclass
class EgaHeader:
    latch_plane_size: int
    sprite_plane_size: int
    font_count: int
    font_location: int
    tile_count: int
    tile_location: int
    bitmap_location: int
    sprite_location: int
    compression: int
    bitmaps: list[Bitmap]
    sprites: list[Sprite]


def read_header(data: bytes) -> EgaHeader:
    (latch_size, sprite_size, bitmap_table, sprite_table,
     font_count, font_loc, _unk_count, _unk_loc,
     tile_count, tile_loc, bitmap_count, bitmap_loc,
     sprite_count, sprite_loc, compression) = struct.unpack_from("<IIIIHIHIHIHIHIH", data, 0)

    bitmaps = []
    for i in range(bitmap_count):
        w, h, loc = struct.unpack_from("<HHI", data, bitmap_table + i * 16)
        name = data[bitmap_table + i * 16 + 8:bitmap_table + i * 16 + 16].split(b"\0")[0]
        bitmaps.append(Bitmap(w * 8, h, loc, name.decode("ascii", "replace")))

    sprites = []
    for i in range(sprite_count):
        base = sprite_table + i * 128      # four 32-byte copies per sprite; the first is the original
        w, h, loc_extra, loc, x0, y0, x1, y1 = struct.unpack_from("<HHHHHHHH", data, base)
        name = data[base + 16:base + 28].split(b"\0")[0]
        sprites.append(Sprite(w * 8, h, loc * 16 + loc_extra,
                              (x0 >> 8, y0 >> 8, x1 >> 8, y1 >> 8),
                              name.decode("ascii", "replace")))

    return EgaHeader(latch_size, sprite_size, font_count, font_loc, tile_count, tile_loc,
                     bitmap_loc, sprite_loc, compression, bitmaps, sprites)


def load_latch(header: EgaHeader, raw: bytes) -> bytes:
    data = keen_lzw.decompress(raw) if header.compression & COMPRESSED_LATCH else raw
    if len(data) < header.latch_plane_size * 4:
        raise ValueError("EGALATCH smaller than 4 planes")
    return data


def load_sprites(header: EgaHeader, raw: bytes) -> bytes:
    data = keen_lzw.decompress(raw) if header.compression & COMPRESSED_SPRITES else raw
    if len(data) < header.sprite_plane_size * 5:
        raise ValueError("EGASPRIT smaller than 5 planes")
    return data


def _planar(data: bytes, plane_size: int, offset: int, width: int, height: int,
            masked: bool) -> list[list[int]]:
    """Decode one planar graphic into rows of colour indices (0-15, or TRANSPARENT)."""
    row_bytes = width // 8
    rows = []
    for y in range(height):
        row = []
        for xb in range(row_bytes):
            pos = offset + y * row_bytes + xb
            b, g, r, i = (data[p * plane_size + pos] for p in range(4))
            m = data[4 * plane_size + pos] if masked else 0
            for bit in range(7, -1, -1):
                colour = ((b >> bit) & 1) | ((g >> bit) & 1) << 1 | ((r >> bit) & 1) << 2 | ((i >> bit) & 1) << 3
                if masked and (m >> bit) & 1:
                    colour = TRANSPARENT
                row.append(colour)
        rows.append(row)
    return rows


def tiles(header: EgaHeader, latch: bytes) -> list[list[list[int]]]:
    """All 16x16 tiles as rows of colour indices."""
    return [_planar(latch, header.latch_plane_size, header.tile_location + t * 32, 16, 16, False)
            for t in range(header.tile_count)]


def font(header: EgaHeader, latch: bytes) -> list[list[list[int]]]:
    return [_planar(latch, header.latch_plane_size, header.font_location + c * 8, 8, 8, False)
            for c in range(header.font_count)]


def bitmap(header: EgaHeader, latch: bytes, index: int) -> list[list[int]]:
    bm = header.bitmaps[index]
    return _planar(latch, header.latch_plane_size, header.bitmap_location + bm.location,
                   bm.width, bm.height, False)


def sprite(header: EgaHeader, sprites: bytes, index: int) -> list[list[int]]:
    sp = header.sprites[index]
    return _planar(sprites, header.sprite_plane_size, header.sprite_location + sp.location,
                   sp.width, sp.height, True)
