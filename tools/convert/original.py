"""Load everything from the user's Keen 1 files in data/original/."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ega, levels, lzexe, sounds, tileinfo

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "data" / "original"
LEVEL_NUMBERS = list(range(1, 17)) + [80, 81, 90]


@dataclass
class Episode1:
    exe_image: bytes
    header: ega.EgaHeader
    latch: bytes
    sprite_data: bytes
    tileinfo: list[tileinfo.TileInfo]
    levels: dict[int, levels.Level]
    sounds: list[sounds.Sound]


def load(folder: Path = ORIGINAL) -> Episode1:
    def read(name: str) -> bytes:
        path = folder / name
        if not path.is_file():
            raise FileNotFoundError(f"{path} missing; put the Keen 1 shareware files in {folder}")
        return path.read_bytes()

    exe = read("KEEN1.EXE")
    image = lzexe.unpack(exe).image if lzexe.is_lzexe(exe) else exe
    header = ega.read_header(read("EGAHEAD.CK1"))
    return Episode1(
        exe_image=image,
        header=header,
        latch=ega.load_latch(header, read("EGALATCH.CK1")),
        sprite_data=ega.load_sprites(header, read("EGASPRIT.CK1")),
        tileinfo=tileinfo.read(image, header.tile_count),
        levels={n: levels.parse(n, read(f"LEVEL{n:02d}.CK1")) for n in LEVEL_NUMBERS},
        sounds=sounds.parse(read("SOUNDS.CK1")),
    )
