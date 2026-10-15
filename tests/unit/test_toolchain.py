"""M0: every tool the project needs can be found and started."""
from __future__ import annotations

import pytest

import toolchain as tc


@pytest.mark.parametrize("name, locate", [
    ("java", tc.java),
    ("KickAssembler", tc.kickass_jar),
    ("x64sc", lambda: tc.vice_bin("x64sc")),
    ("c1541", lambda: tc.vice_bin("c1541")),
    ("dosbox", tc.dosbox),
    ("exomizer", tc.exomizer),
])
def test_tool_is_installed(name, locate):
    assert locate().is_file(), name


def test_java_is_17_or_newer():
    result = tc.run([tc.java(), "-version"], capture_output=True, text=True)
    first_line = result.stderr.splitlines()[0]          # e.g. openjdk version "17.0.12"
    version = first_line.split('"')[1]
    major = int(version.split(".")[1] if version.startswith("1.") else version.split(".")[0])
    assert major >= 17, first_line


def test_py65_is_installed():
    import py65  # noqa: F401
