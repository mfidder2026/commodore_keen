"""Build build/commander-keen-c64.d64 from src/main.asm.

Usage: python tools/build.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402


def assemble(source: Path, out_dir: Path) -> None:
    """Assemble one KickAssembler source; writes the .prg and VICE labels (.vs) to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    result = tc.run(
        [tc.java(), "-jar", tc.kickass_jar(), source,
         "-odir", out_dir.resolve(), "-vicesymbols", "-showmem"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"assembly failed: {source}")


def make_d64(prg: Path, d64: Path) -> None:
    d64.unlink(missing_ok=True)
    result = tc.run(
        [tc.vice_bin("c1541"), "-format", tc.DISK_TITLE, "d64", d64,
         "-write", prg, "keen"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not d64.is_file():
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit("c1541 failed")


def build() -> Path:
    assemble(tc.SRC / "main.asm", tc.BUILD)
    prg = tc.BUILD / tc.PRG_NAME
    if not prg.is_file():
        raise SystemExit(f"expected {prg} after assembly")
    d64 = tc.BUILD / tc.D64_NAME
    make_d64(prg, d64)
    return d64


if __name__ == "__main__":
    try:
        print(build())
    except tc.ToolNotFound as e:
        raise SystemExit(f"toolchain: {e}")
