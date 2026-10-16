from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import toolchain as tc  # noqa: E402


def require(tool) -> Path:
    """Return a tool path, or skip the test when the tool is not installed."""
    try:
        return tool()
    except tc.ToolNotFound as e:
        pytest.skip(str(e))


@pytest.fixture(scope="session")
def built_d64() -> Path:
    require(tc.kickass_jar)
    require(lambda: tc.vice_bin("c1541"))
    from build import build
    return build()


def run_vice(args: list, timeout: int = 900, attempts: int = 2):
    """Run x64sc headless. VICE 3.9 on Windows sometimes crashes (exit code is a Windows
    exception code above 255) when the machine is busy; such a crash is retried. Normal
    results (0, or 1 when -limitcycles ran out) are returned as they are."""
    import subprocess
    exe = require(lambda: tc.vice_bin("x64sc"))
    for _ in range(attempts):
        result = tc.run([exe, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        if result.returncode <= 255:
            return result
    return result


def read_vice_labels(path: Path) -> dict[str, int]:
    """Parse a VICE label file (lines like 'al C:080d .start')."""
    labels = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "al":
            labels[parts[2].lstrip(".")] = int(parts[1].split(":")[1], 16)
    return labels
