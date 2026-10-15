"""Render decoded Keen data to PNG for inspection and golden tests."""
from __future__ import annotations

from PIL import Image, ImageDraw

from .ega import PALETTE, TRANSPARENT
from .levels import Level

TILE = 16
SHEET_COLUMNS = 16
CHECKER = ((0x40, 0x40, 0x40), (0x60, 0x60, 0x60))   # backdrop for transparent pixels


def _palette_image(width: int, height: int) -> Image.Image:
    image = Image.new("P", (width, height))
    flat = [c for rgb in PALETTE for c in rgb] + [0xFF, 0x00, 0xFF]   # 16 = transparent marker
    image.putpalette(flat + [0] * (768 - len(flat)))
    return image


def graphic(rows: list[list[int]]) -> Image.Image:
    image = _palette_image(len(rows[0]), len(rows))
    image.putdata([c for row in rows for c in row])
    return image


def sheet(graphics: list[list[list[int]]], columns: int = SHEET_COLUMNS) -> Image.Image:
    """Tiles or font glyphs of equal size in a grid, in index order."""
    h = len(graphics[0])
    w = len(graphics[0][0])
    rows = (len(graphics) + columns - 1) // columns
    out = _palette_image(columns * w, rows * h)
    for i, g in enumerate(graphics):
        out.paste(graphic(g), ((i % columns) * w, (i // columns) * h))
    return out


def sprite_sheet(sprites: list[list[list[int]]], names: list[str]) -> Image.Image:
    """Sprites of mixed sizes, one per row cell, transparent pixels on a checkerboard."""
    cell_w = max(len(s[0]) for s in sprites) + 4
    cell_h = max(len(s) for s in sprites) + 12
    columns = 8
    rows = (len(sprites) + columns - 1) // columns
    out = Image.new("RGB", (columns * cell_w, rows * cell_h), (0, 0, 0))
    draw = ImageDraw.Draw(out)
    for i, rows_ in enumerate(sprites):
        ox, oy = (i % columns) * cell_w + 2, (i // columns) * cell_h + 10
        draw.text((ox, oy - 10), f"{i}", fill=(200, 200, 200))
        for y, row in enumerate(rows_):
            for x, c in enumerate(row):
                rgb = CHECKER[(x // 4 + y // 4) % 2] if c == TRANSPARENT else PALETTE[c]
                out.putpixel((ox + x, oy + y), rgb)
    return out


def level(lvl: Level, tiles: list[Image.Image], show_sprites: bool = False) -> Image.Image:
    out = Image.new("RGB", (lvl.width * TILE, lvl.height * TILE))
    for y, row in enumerate(lvl.tiles):
        for x, t in enumerate(row):
            if t < len(tiles):
                out.paste(tiles[t], (x * TILE, y * TILE))
    if show_sprites:
        draw = ImageDraw.Draw(out)
        for y, row in enumerate(lvl.sprites):
            for x, code in enumerate(row):
                if code:
                    box = (x * TILE, y * TILE, x * TILE + TILE - 1, y * TILE + TILE - 1)
                    draw.rectangle(box, outline=(255, 0, 255))
                    draw.text((x * TILE + 2, y * TILE + 3), str(code), fill=(255, 255, 255))
    return out
