# Toolchain

Recorded in M0 on 16 October 2026. `tests/unit/test_toolchain.py` checks that every tool can be found.

| Tool | Version | Location |
| --- | --- | --- |
| Java | 26.0.2 (Oracle) | `../c64/java/bin/java.exe` |
| KickAssembler | 5.25 | `../c64/kick/KickAss.jar` |
| VICE (`x64sc`, `c1541`) | 3.9 | `../c64/vice/bin/` |
| DOSBox Staging | 0.83.0 | `../c64/dosbox/dosbox.exe` |
| Python | 3.12.6 | PATH |
| pytest | 9.1.1 | pip (user) |
| py65 | 1.2.0 | pip (user) |
| Pillow | 12.3.0 | pip |
| Git | 2.54.0 | PATH |
| Exomizer | 3.1.0 | `../c64/exomizer/win32/exomizer.exe` |

## Exomizer

The official download (Bitbucket wiki of magli143) is offline. The files came from the user's own downloads and are all in `../c64/exomizer/`:

- `win32/exomizer.exe`: the build the project uses, from the full 3.1.0 zip.
- `win32_standalone/`: the separate win32 zip (also v3.1.0, a different build); not used.
- `src/`, `exodecrs/`, `rawdecrs/`: source and the decrunchers for in-game loading (M3).
- `exodecrunch_3.1.0_64tass.asm`: the decruncher in 64tass syntax. It has to be ported to KickAssembler syntax before use.

`test_exomizer_sfx_runs_title` checks that an `exomizer sfx sys`-crunched build shows the same title screen in VICE.

## Lookup order

`tools/toolchain.py` looks for each tool here, in this order:

1. An environment variable: `JAVA`, `KICKASS_JAR`, `VICE_DIR`, `DOSBOX`, `EXOMIZER`.
2. The shared C64 tools folder `C64_TOOLS`, by default `../c64` next to this repo.
3. `.tools/` inside the repo (not in git).
4. The PATH.

## VICE behaviour this project relies on (checked in M0)

- `-debugcart`: a write to `$d7ff` makes VICE exit with the written value as its exit code. Writing 0 gave exit code 0 and writing 7 gave 7.
- `-limitcycles N`: VICE exits with exit code 1 when the limit is reached. A test that never reports counts as a failure.
- `-exitscreenshot file.png`: writes a screenshot on exit, including the border.
- `-default` ignores the user's VICE settings, so test runs are reproducible.
- The plan names VICE 3.10; the installed version is 3.9. Everything M0 needs works on 3.9.
