"""Headless VICE runs. The debug cartridge returns pass/fail as exit code."""
from __future__ import annotations

import subprocess
from pathlib import Path

import toolchain as tc
from build import assemble
from conftest import require

HERE = Path(__file__).resolve().parent
OUT = tc.BUILD / "test"

# Emulated cycles before VICE gives up; reaching the limit counts as a failure.
CYCLE_LIMIT = 30_000_000


def x64sc(*args, cycles: int = CYCLE_LIMIT) -> int:
    cmd = [require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
           "-sounddev", "dummy", "-debugcart", "-limitcycles", cycles, *args]
    # VICE 3.9 on Windows sometimes crashes when its output goes to a pipe.
    return tc.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120).returncode


def test_debug_cartridge_exit_code():
    require(tc.kickass_jar)
    assemble(HERE / "m0_exitcode.asm", OUT)
    assert x64sc("-autostart", OUT / "m0_exitcode.prg") == 0


def test_exomizer_sfx_program_still_runs():
    """An Exomizer-crunched program decrunches itself and still reports success."""
    require(tc.kickass_jar)
    assemble(HERE / "m0_exitcode.asm", OUT)
    crunched = OUT / "m0_exitcode_sfx.prg"
    result = tc.run([require(tc.exomizer), "sfx", "sys", "-q", "-o", crunched, OUT / "m0_exitcode.prg"],
                    capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert x64sc("-autostart", crunched) == 0
