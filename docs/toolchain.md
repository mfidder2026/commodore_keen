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
| Exomizer | **missing** | `../c64/exomizer/exomizer.exe` |

## Exomizer

The official download (Bitbucket wiki of magli143) has been offline since at least October 2026, and this PC has no C compiler to build the source. Exomizer is not needed before level loading (M3). The toolchain test marks it as an expected failure until then.

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
