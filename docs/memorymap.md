# Memory map

Source of truth: `src/memory.asm` (segments) and `src/zp.asm` (zero page). Layout and level format: [ADR 0001](decisions/0001-level-format.md).

| Address | Content |
| --- | --- |
| `$02-$24` | engine zero page (frame counter, pointers, tile row buffer) |
| `$30-$63` | game zero page: Keen, current actor, box offsets |
| `$64-$65` | test builds: script pointer |
| `$02-$8F` | cleared at startup |
| `$90-$FF` | KERNAL during loading; Exomizer decruncher uses `$9E/$9F`, `$A7/$A8`, `$AE/$AF`, `$FD-$FF` |
| `$0801-$4FFF` | program (BASIC stub, code, generated sprite tables); on disk as an Exomizer sfx file |
| `$5000-$9FFF` | current level (crunched file is loaded and unpacked in place) |
| `$A000-$A5FF` | variables (`Vars` segment, cleared at startup) |
| `$A600-$ACFF` | colour RAM update code, generated at startup (`engine/colourfast.asm`) |
| `$B000-$BBFF` | sound data (`SOUNDS` file) |
| `$C000-$C3FF` | screen A (+ sprite pointers at `$C3F8`) |
| `$C400-$C7FF` | screen B (+ sprite pointers at `$C7F8`) |
| `$C800-$CFFF` | level character set |
| `$D000-$D7FF` | sprite shapes (pointers 64-95), under I/O |
| `$D800-$D9FF` | font, 64 hires characters, under I/O |
| `$DA00-$DFFF` | sprite shapes (pointers 104-127), under I/O |
| `$E000-$FFBF` | sprite shapes (pointers 128-254) |
| `$FFFA-$FFFF` | NMI/IRQ vectors (RAM, KERNAL banked out) |

`$01` during play: `$35`. During loading and saving: `$36` (KERNAL on).

## Space left

The `Code` segment ends at about `$45B0` (limit `$4FFF`). Free in RAM: `$AD00-$AFFF`, `$BC00-$BFFF`.
