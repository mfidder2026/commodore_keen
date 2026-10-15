# Keen 1 file formats

How the converter (`tools/convert/`) reads the user's Keen 1 v1.31 files. Sources: ModdingWiki (format pages linked in each module) and Cosmodoc for LZEXE.

## Files (data/original/, not in git)

33 files of episode 1 v1.31, copied from the user's DFEnd/DOSBox install. `test_original.py` checks the SHA-256 of `KEEN1.EXE` and skips if it is a different release.

| File | Format | Module | Result |
| --- | --- | --- | --- |
| `KEEN1.EXE` | LZEXE 0.91 | `lzexe.py` | 99,972-byte load image, 17 relocations |
| `EGAHEAD.CK1` | EGA header | `ega.py` | 256 font glyphs, 611 tiles, 18 bitmaps, 119 sprites |
| `EGALATCH.CK1` | Keen LZW, 4 planes | `keen_lzw.py`, `ega.py` | 119,680 bytes (4 × 29,920) |
| `EGASPRIT.CK1` | Keen LZW, 5 planes | `keen_lzw.py`, `ega.py` | 31,600 bytes (5 × 6,320) |
| `LEVELnn.CK1` | RLEW, 2 planes | `levels.py` | levels 1-16, 80 (world map), 81, 90 (title backdrop) |
| `SOUNDS.CK1` | Inverse Frequency ("SND") | `sounds.py` | 60 slots, 41 named effects |
| tileinfo in the EXE | 6 × int16 planes | `tileinfo.py` | 611 entries at image offset `0x130F8` |

## Findings that differ from the documentation

- **`KEEN1.EXE` is LZEXE-compressed.** The converter unpacks it itself. Relocation fixups are *not* applied, so the image matches what UNLZEXE writes after its header.
- **Tileinfo offset:** ModdingWiki lists `0x130F8` as the file offset in the unpacked EXE. In our unpacked load image, the table starts at that same offset `0x130F8`. It was found by content: a 3,666-word block with only valid values, ending exactly where the table should.
- **Animation plane:** tiles that do not animate have value 1, not 0 as ModdingWiki says. The values are 1 (521 tiles), 2 (2) and 4 (88).
- **The sound effects are in `SOUNDS.CK1`**, not in the EXE as PLAN.md says.
- **Keen LZW:** codes are MSB-first. The code width grows from 9 bits as soon as the next free entry reaches `2^width - 1`. Both graphics files decompress to exactly the size in their header, with the end code at the end of the data.
- **Sprites:** 5th plane is the mask; a set bit means transparent. Location = `location × 16 + extra offset` in each plane. The hitbox values in EGAHEAD are multiplied by 256.
- **Level 12** has unusual values (above 255) in its sprite plane. Check their meaning against the reconstructed source in M6.

## World map (level 80)

Sprite plane codes 1-16 mark the level entrances (some are 2×2 tiles), 255 is Keen's start position. Codes 20, 38, 41, 46 and those with bit 15 set (`0x8001`, `0x8007`) still need to be explained from the source; possibly the ship and blocking points.

## Verification against the original

`python tools/test.py -m dosbox` starts Keen 1 in DOSBox, captures the screen, starts a new game, walks to level 1 and enters it. It compares the screens with the converter's renders:

| Screen | Result |
| --- | --- |
| Title screen, backdrop = level 90 | all tile cells equal, apart from the "PRESS F1" box; animated tiles accepted in any frame |
| World map (level 80) | 99.8% of pixels equal; the rest is Keen's sprite |
| Level 1 | 99.7% of pixels equal; the rest is Keen's sprite |

Levels 2-16 and 81 go through the same decoder but have **not** been compared with a screenshot. Reaching them requires playing through the world map. Visual check: `build/original/levelNN.png`.

## Commands

- `python -m tools.convert` writes tile, font, bitmap and sprite sheets, all levels (with and without actor codes) and `summary.json` to `build/original/`.
- `python tools/dosbox_capture.py 20 25=space 28=enter 31` runs Keen in DOSBox with a timed script of screenshots and key presses (`key*N`, `key~seconds`).
- `python -m tools.convert.compare <screenshot> <level.png>` finds the scroll position and the match rate.
