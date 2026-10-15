# Credits and licences

## Original game

Commander Keen in "Invasion of the Vorticons", Episode One: "Marooned on Mars" (1990) by id Software, published by Apogee. This C64 version is an unofficial, non-commercial fan port with no connection to id Software. The repository contains no files from the original. The converter reads your own copy of the shareware episode (`data/original/`).

## Sound effects

All 41 sound effects are converted automatically from the original's `SOUNDS.CK1` (PC speaker frequencies, played on SID voice 1). No separate permission is needed beyond what applies to the converted graphics and levels (see PLAN.md, "Data, naam en rechten").

## Music

**None yet.** PLAN.md requires recorded permission or a free licence for every SID tune before it is used. No tune has been chosen or approved. To do: choose tunes (CC0/CC-BY, or ask the composer for permission) and record them here, with composer, source and licence.

| Tune | Composer | Source | Licence / permission | Used for |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

## Tools and code

- Exomizer 3.1.0 decruncher (`src/engine/exodecrunch.asm`) © Magnus Lind, under its own licence (zlib-like); ported to KickAssembler and marked as altered.
- KickAssembler, VICE, DOSBox Staging, Python with Pillow, numpy, pytest and py65: build and test tools only, not part of the release.
- Format documentation: ModdingWiki (shikadi.net), Cosmodoc (Scott Smitelli) for LZEXE.
