# Keen 1 file formats

Notes for the converter (M1). The full descriptions are on the ModdingWiki; see the sources in PLAN.md.

## The user's copy (data/original/)

33 files of episode 1, copied from the DFEnd/DOSBox install. Not in git.

Observations from M0 that differ from PLAN.md:

- **`KEEN1.EXE` is LZEXE-compressed** (signature `LZ91` in the header). The converter must unpack the EXE before it can read the EGA header, tileinfo and other tables.
- **The sound effects are in `SOUNDS.CK1`** (8,898 bytes), not in the EXE.
- `LEVEL80.CK1` is the world map. `LEVEL81.CK1` and `LEVEL90.CK1` are the other special levels; check their role in M1.
