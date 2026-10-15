"""Locate the external toolchain (Java, KickAssembler, VICE, Exomizer).

Lookup order per tool: environment variable, the shared C64 tools folder
(C64_TOOLS, default ../c64 next to this repo), the local .tools/ folder, then PATH.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_TOOLS = ROOT / ".tools"
C64_TOOLS = Path(os.environ.get("C64_TOOLS", ROOT.parent / "c64"))
BUILD = ROOT / "build"
SRC = ROOT / "src"

PRG_NAME = "commander-keen-c64.prg"
D64_NAME = "commander-keen-c64.d64"
DISK_TITLE = "commander keen,64"


class ToolNotFound(RuntimeError):
    pass


def _exe(name: str) -> str:
    return name + ".exe" if os.name == "nt" else name


def _find(env_var: str, relative: str) -> Path:
    """Find a tool; `relative` is its path inside the C64 tools folder, e.g. 'vice/bin/x64sc.exe'."""
    filename = Path(relative).name
    value = os.environ.get(env_var)
    if value:
        path = Path(value)
        if path.is_dir():
            path = path / filename
        if path.is_file():
            return path
        raise ToolNotFound(f"{env_var}={value} does not point to {filename}")
    for candidate in (C64_TOOLS / relative, LOCAL_TOOLS / relative):
        if candidate.is_file():
            return candidate
    on_path = shutil.which(filename)
    if on_path:
        return Path(on_path)
    raise ToolNotFound(f"{filename} not found (set {env_var}, put it in {C64_TOOLS / relative} or add to PATH)")


def java() -> Path:
    # The C64 tools folder wins over an older system Java on the PATH.
    return _find("JAVA", "java/bin/" + _exe("java"))


def kickass_jar() -> Path:
    return _find("KICKASS_JAR", "kick/KickAss.jar")


def vice_bin(program: str) -> Path:
    return _find("VICE_DIR", "vice/bin/" + _exe(program))


def dosbox() -> Path:
    return _find("DOSBOX", "dosbox/" + _exe("dosbox"))


def exomizer() -> Path:
    return _find("EXOMIZER", "exomizer/win32/" + _exe("exomizer"))


def run(cmd: list[str | Path], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], **kwargs)
