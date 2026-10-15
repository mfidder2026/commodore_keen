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


def read_vice_labels(path: Path) -> dict[str, int]:
    """Parse a VICE label file (lines like 'al C:080d .start')."""
    labels = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "al":
            labels[parts[2].lstrip(".")] = int(parts[1].split(":")[1], 16)
    return labels
