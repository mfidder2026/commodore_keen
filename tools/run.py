"""Build and start the game in VICE (x64sc), with labels loaded in the monitor.

Usage: python tools/run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402
from build import build  # noqa: E402

if __name__ == "__main__":
    d64 = build()
    labels = tc.BUILD / "main.vs"
    cmd = [tc.vice_bin("x64sc"), "-pal"]
    if labels.is_file():
        cmd += ["-moncommands", labels]
    cmd += ["-autostart", d64]
    tc.run(cmd)
