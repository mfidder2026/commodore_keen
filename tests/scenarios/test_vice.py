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


def test_title_screen_matches_golden(built_d64):
    shot = OUT / "m0_title.png"
    shot.unlink(missing_ok=True)
    x64sc("-exitscreenshot", shot, "-autostart", built_d64, cycles=10_000_000)
    assert shot.is_file(), "VICE did not write a screenshot"

    golden = GOLDEN / "m0_title.png"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        shutil.copyfile(shot, golden)
    assert golden.is_file(), "no golden image yet; review build/test/m0_title.png and rerun with UPDATE_GOLDEN=1"
    diff = ImageChops.difference(Image.open(shot).convert("RGB"), Image.open(golden).convert("RGB"))
    assert diff.getbbox() is None, f"screenshot differs from golden in {diff.getbbox()}"
