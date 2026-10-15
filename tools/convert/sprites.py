"""Convert Keen sprites to C64 multicolour hardware sprites.

Each EGA sprite is halved horizontally (fat pixels) and cropped to its opaque area.
Up to 24 rows high it is squeezed to 21 rows by dropping the rows most similar to their
neighbour (feet stay in place); taller sprites are split into a top sprite of 21 rows and
a bottom sprite with the rest. Colours: two shared multicolour registers ($D025, $D026)
for all sprites plus one own colour per hardware sprite.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import ega
from .c64 import DIST, halve

HEIGHT = 21
FAT_WIDTH = 12
SQUEEZE_MAX = 24
TRANSPARENT = -1

# Hardware sprite slots visible to the VIC in bank 3: $D000-$D7FF (pointers 64-95, under
# I/O), $DA00-$DFFF (104-127; the font uses $D800-$D9FF) and $E000-$FFBF (128-254).
SLOTS = list(range(64, 96)) + list(range(104, 128)) + list(range(128, 255))

# Keen's in-level frames get two overlaid hardware sprites: two own colours on top of the
# shared pair, so the player keeps four colours.
LAYERED = range(0, 32)
# Hand-picked art decision: yellow hair and purple shirt. Error minimisation picks greys
# (close to every colour) and pixel counts pick cyan, both lose what makes Keen Keen.
KEEN_COLOURS = (7, 4)


@dataclass
class Piece:
    pointer: int        # VIC sprite pointer
    colour: int         # own colour ($D027+n)
    dx: int             # offset in hires pixels from the EGA sprite's top-left corner
    dy: int
    data: bytes         # 63 bytes


@dataclass
class C64Sprite:
    name: str
    pieces: list[Piece]


def squeeze(rows: np.ndarray, height: int) -> np.ndarray:
    rows = list(rows)
    while len(rows) > height:
        diffs = [np.count_nonzero(rows[i] != rows[i + 1]) for i in range(len(rows) - 1)]
        drop = int(np.argmin(diffs))
        del rows[drop + 1]
    return np.array(rows)


def shapes(fat: np.ndarray) -> list[tuple[int, np.ndarray]]:
    """Crop to opaque rows/columns; return (row offset, rows) per hardware sprite."""
    opaque_rows = np.where((fat != TRANSPARENT).any(axis=1))[0]
    if len(opaque_rows) == 0:
        return [(0, np.full((1, fat.shape[1]), TRANSPARENT))]
    top, bottom = opaque_rows[0], opaque_rows[-1] + 1
    body = fat[top:bottom]
    if len(body) <= HEIGHT:
        return [(top, body)]
    if len(body) <= SQUEEZE_MAX:
        squeezed = squeeze(body, HEIGHT)
        return [(bottom - HEIGHT, squeezed)]
    return [(top, body[:HEIGHT]), (top + HEIGHT, body[HEIGHT:])]


def best_own(rows: np.ndarray, shared: tuple[int, int]) -> tuple[int, int]:
    """Own colour with the lowest error for the opaque pixels, and that error."""
    pixels = rows[rows != TRANSPARENT]
    if len(pixels) == 0:
        return 1, 0
    best = None
    for own in range(16):
        pal = np.array([shared[0], own, shared[1]])
        err = int(DIST[pixels[:, None], pal].min(axis=1).sum())
        if best is None or err < best[1]:
            best = (own, err)
    return best


def choose_shared(all_rows: list[np.ndarray]) -> tuple[int, int]:
    best = None
    for a in range(16):
        for b in range(a + 1, 16):
            err = sum(best_own(r, (a, b))[1] for r in all_rows)
            if best is None or err < best[0]:
                best = (err, (a, b))
    return best[1]


def encode(rows: np.ndarray, shared: tuple[int, int], own: int) -> bytes:
    """Multicolour sprite bytes: 00 transparent, 01 $D025, 10 own colour, 11 $D026."""
    pal = np.array([shared[0], own, shared[1]])
    out = bytearray(63)
    for y, row in enumerate(rows[:HEIGHT]):
        for x, c in enumerate(row[:FAT_WIDTH]):
            if c == TRANSPARENT:
                continue
            bits = int(DIST[c, pal].argmin()) + 1          # 1, 2 or 3
            byte = y * 3 + x // 4
            out[byte] |= bits << (6 - 2 * (x % 4))
    return bytes(out)


def convert(header: ega.EgaHeader, sprite_data: bytes) -> tuple[list[C64Sprite], tuple[int, int]]:
    fats, pieces_rows = [], []
    for i in range(len(header.sprites)):
        rows = ega.sprite(header, sprite_data, i)
        fat = halve(rows, transparent=ega.TRANSPARENT, rule="right")
        fat = np.where(fat < 0, TRANSPARENT, fat)
        fats.append(fat)
        pieces_rows.append(shapes(fat))
    shared = choose_shared([r for ps in pieces_rows for _, r in ps])

    sprites, slot = [], 0

    def add(rows, own, top):
        nonlocal slot
        if slot >= len(SLOTS):
            raise ValueError("out of sprite slots")
        piece = Piece(SLOTS[slot], own, 0, int(top), encode(rows, shared, own))
        slot += 1
        return piece

    # One colour pair for all of Keen's frames, so his colours do not change while animating.
    keen_pair = KEEN_COLOURS

    for i, ps in enumerate(pieces_rows):
        pieces = []
        for top, rows in ps:
            if i in LAYERED:
                own_a, own_b = keen_pair
                rows_a, rows_b = split_layers(rows, shared, own_a, own_b)
                pieces.append(add(rows_b, own_b, top))
                pieces.append(add(rows_a, own_a, top))
            else:
                pieces.append(add(rows, best_own(rows, shared)[0], top))
        sprites.append(C64Sprite(header.sprites[i].name, pieces))
    return sprites, shared


def best_layer_pair(pixels: np.ndarray, shared: tuple[int, int]) -> tuple[int, int]:
    pixels = pixels[pixels != TRANSPARENT]
    best = None
    for a in range(16):
        for b in range(a + 1, 16):
            pal = np.array([shared[0], shared[1], a, b])
            err = int(DIST[pixels[:, None], pal].min(axis=1).sum())
            if best is None or err < best[0]:
                best = (err, (a, b))
    return best[1]


def split_layers(rows, shared, own_a, own_b):
    """Pixels closest to own_b go to layer B only; everything else to layer A."""
    pal = np.array([shared[0], shared[1], own_a, own_b])
    nearest = np.where(rows == TRANSPARENT, -1, DIST[np.maximum(rows, 0)[..., None], pal].argmin(axis=-1))
    rows_b = np.where(nearest == 3, own_b, TRANSPARENT)
    rows_a = np.where((nearest >= 0) & (nearest != 3), rows, TRANSPARENT)
    return rows_a, rows_b


def sheet(sprites: list[C64Sprite], shared: tuple[int, int]):
    """Preview of all converted sprites (each piece at its offset), 4x scaled."""
    from PIL import Image, ImageDraw
    from .c64 import C64_PALETTE
    cell_w, cell_h, columns = 28, 40, 12
    rows = (len(sprites) + columns - 1) // columns
    img = Image.new("RGB", (columns * cell_w, rows * cell_h), (40, 40, 40))
    for i, sp in enumerate(sprites):
        ox, oy = (i % columns) * cell_w + 2, (i // columns) * cell_h + 2
        for p in sp.pieces:
            pal = [None, shared[0], p.colour, shared[1]]
            for y in range(HEIGHT):
                for x in range(FAT_WIDTH):
                    byte = p.data[y * 3 + x // 4]
                    bits = (byte >> (6 - 2 * (x % 4))) & 3
                    if bits:
                        rgb = tuple(int(v) for v in C64_PALETTE[pal[bits]])
                        for dx in range(2):
                            px, py = ox + p.dx + 2 * x + dx, oy + p.dy + y
                            if 0 <= px < img.width and 0 <= py < img.height:
                                img.putpixel((px, py), rgb)
    return img.resize((img.width * 3, img.height * 3), Image.NEAREST)
