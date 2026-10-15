# ADR 0001: C64 level format, sprite bank and memory layout

Status: accepted (M2, 16 October 2026)

## Context

PLAN.md fixes the rough memory map. M2 needs a concrete binary format that the converter writes and the engine reads, without parsing at runtime.

## Decision

### Level file (`Lnn`, PRG loaded at `$5000`)

Fixed layout, so the engine uses absolute addresses:

| Address | Size | Content |
| --- | --- | --- |
| `$5000` | 64 | header: `K`, number, width, height, background, `$D022`, `$D023`, start x, start y (tiles), animation group count, actor count, tile count |
| `$5040` | 64 | animation groups (max 16): first character, frame count, frame data address (lo, hi) |
| `$5100` | 256 | colour RAM value per character (own colour \| 8 = multicolour) |
| `$5200` | 2048 | character set, copied to `$C800` when the level starts |
| `$5A00` | 8 × 256 | tile tables: char top-left, top-right, bottom-left, bottom-right, behaviour, attributes, original tile lo, hi |
| `$6200` | 512 | actors (max 128): code lo, code hi, x, y in tiles |
| `$6400` | 2048 | animation frames: per group, per frame, 4 characters of 8 bytes |
| `$6C00` | ≤ 13,312 | map, 1 byte (C64 tile number) per tile, row by row |

Attribute byte: bits 0-1 top blocking (0 none, 1 solid, 2 slippery, 3 ice), bit 2 right, bit 3 bottom, bit 4 left, bit 7 animated.

### Sprite bank (`SPRITES`, PRG loaded at `$5000`)

`$5000-$5FFF` is copied to `$D000-$DFFF` (sprite shapes, font at `$D800-$D9FF`), `$6000-$7FBF` to `$E000-$FFBF`. Frame table (pieces per Keen sprite: pointer, colour, y offset) is generated as `src/generated/sprites.asm`.

### Memory map

| Address | Content |
| --- | --- |
| `$0801-$4FFF` | code, generated tables, sound data |
| `$5000-$9FFF` | current level (see above) |
| `$A000-$BFFF` | runtime tables: actors, map row pointers |
| `$C000-$C3FF` / `$C400-$C7FF` | screen A / B (double buffered) |
| `$C800-$CFFF` | level character set |
| `$D000-$D7FF` | sprites (pointers 64-95), under I/O |
| `$D800-$D9FF` | font (64 hires characters) for text screens |
| `$DA00-$DFFF` | sprites (pointers 104-127) |
| `$E000-$FFBF` | sprites (pointers 128-254) |

### Graphics

- Tiles: of each horizontal pixel pair the rarer colour (in that tile) wins. Shared colours per level are chosen by lowest error; the error is the squared RGB distance plus a fixed penalty per changed pixel, so defining colours win over greys.
- More than 240 characters: the cheapest (usage × difference) pairs are merged. Only the world map needs this (119 merges).
- Animated tiles: 4 dedicated characters per animation group; the engine copies frames into the character set. All instances animate in sync (the PC staggers some).
- Sprites: right pixel of each pair wins; up to 24 rows squeezed to 21, taller split in two. Shared multicolours black and white. Keen in-level: two overlaid sprites, own colours yellow and purple (hand-picked).

## Consequences

- Loading a level is one KERNAL LOAD plus a 2 KB copy.
- 176 sprite shapes fit in the 183 slots; adding shapes leaves little room.
- Colour fidelity is limited; hand touch-ups (CharPad/SpritePad) can be added later via override files.
