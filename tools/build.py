"""Build build/commander-keen-c64.d64: convert assets, assemble, write the disk image.

Usage: python tools/build.py [-D SYMBOL ...]
  -D SYMBOL   pass a KickAssembler define (e.g. -D SCROLLTEST for the M3 scroll test)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import toolchain as tc  # noqa: E402

GENERATED = tc.BUILD / "generated"
ASSETS = tc.BUILD / "assets"
# Disk file name -> asset file. Levels are loaded by the game by these names.
LEVEL_NUMBERS = list(range(1, 17)) + [80, 81, 90]
DISK_FILES = {"sprites": "sprites.prg", "sounds": "sounds.prg",
              **{f"l{n:02d}": f"l{n:02d}.prg" for n in LEVEL_NUMBERS}}


CRUNCHED = ASSETS / "crunched"


def convert_assets() -> None:
    from tools.convert import export
    if not (ASSETS / "sprites.prg").is_file() or newer_than_assets():
        export.main()
    crunch_assets()


def crunch_assets() -> None:
    """Exomizer 'mem' (backwards, in-place load address) for every disk file."""
    CRUNCHED.mkdir(parents=True, exist_ok=True)
    for file in DISK_FILES.values():
        src, dst = ASSETS / file, CRUNCHED / file
        if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        result = tc.run([tc.exomizer(), "mem", "-q", "-o", dst, src], capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout + result.stderr)
            raise SystemExit(f"exomizer failed on {file}")


def newer_than_assets() -> bool:
    """Re-export when converter code changed after the last export."""
    marker = ASSETS / "report.json"
    if not marker.is_file():
        return True
    newest = max(p.stat().st_mtime for p in (tc.ROOT / "tools" / "convert").glob("*.py"))
    return newest > marker.stat().st_mtime


def assemble(source: Path, out_dir: Path, defines: list[str] = ()) -> None:
    """Assemble one KickAssembler source; writes the .prg and VICE labels (.vs) to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [tc.java(), "-jar", tc.kickass_jar(), source,
           "-odir", out_dir.resolve(), "-vicesymbols", "-showmem",
           "-libdir", GENERATED.resolve(), "-libdir", tc.SRC.resolve()]
    for d in defines:
        cmd += ["-define", d]
    result = tc.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"assembly failed: {source}")
    (out_dir / "kickass.log").write_text(result.stdout)


def make_d64(prg: Path, d64: Path, extra: dict[str, Path] | None = None) -> None:
    d64.unlink(missing_ok=True)
    cmd = [tc.vice_bin("c1541"), "-format", tc.DISK_TITLE, "d64", d64, "-write", prg, "keen"]
    for name, path in (extra or {}).items():
        cmd += ["-write", path, name]
    result = tc.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not d64.is_file():
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit("c1541 failed")


def build(defines: list[str] = (), name: str | None = None) -> Path:
    convert_assets()
    out = tc.BUILD if not defines else tc.BUILD / "variants" / "_".join(d.lower() for d in defines)
    assemble(tc.SRC / "main.asm", out, defines)
    prg = out / tc.PRG_NAME
    if not prg.is_file():
        raise SystemExit(f"expected {prg} after assembly")
    d64 = out / (name or tc.D64_NAME)
    make_d64(prg, d64, {disk: CRUNCHED / file for disk, file in DISK_FILES.items()})
    return d64


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-D", dest="defines", action="append", default=[])
    args = parser.parse_args()
    try:
        print(build(args.defines))
    except tc.ToolNotFound as e:
        raise SystemExit(f"toolchain: {e}")
