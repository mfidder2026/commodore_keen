"""Decode the Keen 1 files and write inspection output to build/original/.

Usage (from the repo root): python -m tools.convert
"""
from __future__ import annotations

import json
from pathlib import Path

from . import ega, original, render

OUT = original.ROOT / "build" / "original"


def main() -> None:
    ep = original.load()
    OUT.mkdir(parents=True, exist_ok=True)
    h = ep.header

    tile_rows = ega.tiles(h, ep.latch)
    tile_images = [render.graphic(t).convert("RGB") for t in tile_rows]
    render.sheet(tile_rows).save(OUT / "tiles.png")
    render.sheet(ega.font(h, ep.latch)).save(OUT / "font.png")
    for i, bm in enumerate(h.bitmaps):
        render.graphic(ega.bitmap(h, ep.latch, i)).save(OUT / f"bitmap_{i:02d}_{bm.name}.png")
    sprite_rows = [ega.sprite(h, ep.sprite_data, i) for i in range(len(h.sprites))]
    render.sprite_sheet(sprite_rows, [s.name for s in h.sprites]).save(OUT / "sprites.png")

    for n, lvl in ep.levels.items():
        render.level(lvl, tile_images).save(OUT / f"level{n:02d}.png")
        render.level(lvl, tile_images, show_sprites=True).save(OUT / f"level{n:02d}_actors.png")

    summary = {
        "tiles": h.tile_count,
        "font_glyphs": h.font_count,
        "bitmaps": [bm.name for bm in h.bitmaps],
        "sprites": [s.name for s in h.sprites],
        "levels": {n: {"width": l.width, "height": l.height} for n, l in ep.levels.items()},
        "sounds": [{"index": s.index, "name": s.name, "samples": len(s.samples)}
                   for s in ep.sounds if s.name != "__UnNamed__"],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"{h.tile_count} tiles, {len(h.sprites)} sprites, {len(h.bitmaps)} bitmaps, "
          f"{len(ep.levels)} levels, {len(summary['sounds'])} sounds -> {OUT}")


if __name__ == "__main__":
    main()
