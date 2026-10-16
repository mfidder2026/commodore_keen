# Commander Keen C64

An unofficial, non-commercial fan port of *Commander Keen 1: Marooned on Mars* (id Software, 1990) for the Commodore 64. **Not affiliated with id Software.** The repository contains no files from the original. A converter reads your own copy of the shareware episode and builds the C64 disk image locally.

Status, open points and decisions: [docs/status.md](docs/status.md). Design and milestones: [PLAN.md](PLAN.md).

## What you need

- A stock PAL C64 with a 1541, or VICE (`x64sc`)
- The files of Commander Keen 1 v1.31 (shareware) in `data/original/` (`KEEN1.EXE`, `EGAHEAD.CK1`, `EGALATCH.CK1`, `EGASPRIT.CK1`, `LEVEL*.CK1`, `SOUNDS.CK1`, …)
- To build: Java, KickAssembler 5.25, VICE 3.9+ (`c1541`), Exomizer 3.1, Python 3.11+ with Pillow, numpy, pytest and py65. `tools/toolchain.py` finds the tools via environment variables, in `../c64/` (java, kick, vice, exomizer, dosbox) or on the PATH; see [docs/toolchain.md](docs/toolchain.md).

## Build and run

```
python tools/build.py        # build/commander-keen-c64.d64
python tools/run.py          # start in VICE
python tools/test.py         # all tests (converter, py65, headless VICE)
python tools/deploy.py       # start on a C64 Ultimate (C64U_HOST=<ip>)
```

`python -m tools.convert` writes inspection images of the original to `build/original/`. `python -m tools.convert.export` writes the C64 assets to `build/assets/`.

## Controls (joystick in port 2)

| Action | Control |
| --- | --- |
| Walk | left / right |
| Jump | up |
| Shoot | fire |
| Pogo on/off | down + fire, or space |
| Enter a level (map) | fire |
| Status and pause | RUN/STOP |

## Structure

- `tools/convert/`: reads the original formats (LZEXE, LZW, RLEW, EGA, sounds) and converts them to C64 characters, sprites and sound data
- `src/engine/`: scrolling, IRQ, loading, Exomizer decruncher, sound
- `src/game/`: Keen, enemies, items, world map, text screens, game flow
- `tests/`: pytest; py65 tests of 6502 routines; VICE scenarios with scripted input; DOSBox comparisons (`-m dosbox`)
- `docs/`: decisions (ADRs), formats, physics, enemies, memory map, frame budget, credits

## Rights

Commander Keen is a trademark of its owner. The disk image you build contains converted graphics, levels and sounds of the original. Share it only free of charge, with this disclaimer, and take it offline if the rights holder asks. See [docs/credits.md](docs/credits.md).
