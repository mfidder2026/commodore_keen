"""M0: headless VICE runs. The debug cartridge returns pass/fail as exit code."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from PIL import Image, ImageChops

import toolchain as tc
from build import assemble
from conftest import require

HERE = Path(__file__).resolve().parent
GOLDEN = HERE.parent / "golden"
OUT = tc.BUILD / "test"

# Emulated cycles before VICE gives up; reaching the limit counts as a failure.
CYCLE_LIMIT = 30_000_000


def x64sc(*args, cycles: int = CYCLE_LIMIT) -> int:
    cmd = [require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
           "-sounddev", "dummy", "-debugcart", "-limitcycles", cycles, *args]
    return tc.run(cmd, capture_output=True, timeout=120).returncode


def test_debug_cartridge_exit_code():
    require(tc.kickass_jar)
    assemble(HERE / "m0_exitcode.asm", OUT)
    assert x64sc("-autostart", OUT / "m0_exitcode.prg") == 0


def assert_matches_golden(program: Path, shot_name: str, golden_name: str) -> None:
    shot = OUT / shot_name
    shot.unlink(missing_ok=True)
    x64sc("-exitscreenshot", shot, "-autostart", program, cycles=10_000_000)
    assert shot.is_file(), "VICE did not write a screenshot"

    golden = GOLDEN / golden_name
    if os.environ.get("UPDATE_GOLDEN") == "1":
        shutil.copyfile(shot, golden)
    assert golden.is_file(), f"no golden image yet; review {shot} and rerun with UPDATE_GOLDEN=1"
    diff = ImageChops.difference(Image.open(shot).convert("RGB"), Image.open(golden).convert("RGB"))
    assert diff.getbbox() is None, f"screenshot differs from golden in {diff.getbbox()}"


def test_title_screen_matches_golden(built_d64):
    assert_matches_golden(built_d64, "m0_title.png", "m0_title.png")


def test_exomizer_sfx_runs_title(built_d64):
    """The Exomizer-crunched program decrunches itself and shows the same title screen."""
    crunched = OUT / "m0_title_sfx.prg"
    result = tc.run([require(tc.exomizer), "sfx", "sys", "-q", "-o", crunched, tc.BUILD / tc.PRG_NAME],
                    capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert_matches_golden(crunched, "m0_title_sfx.png", "m0_title.png")
