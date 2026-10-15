"""Build and start the game on the C64 Ultimate through its REST API.

Usage: python tools/deploy.py
Environment: C64U_HOST (e.g. 192.168.1.64), optional C64U_PASSWORD.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402
from build import build  # noqa: E402


def run_prg(host: str, prg: Path, password: str | None) -> str:
    request = urllib.request.Request(
        f"http://{host}/v1/runners:run_prg",
        data=prg.read_bytes(),
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )
    if password:
        request.add_header("X-Password", password)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read().decode(errors="replace")


if __name__ == "__main__":
    host = os.environ.get("C64U_HOST")
    if not host:
        raise SystemExit("set C64U_HOST to the IP address or hostname of the C64 Ultimate")
    build()
    print(run_prg(host, tc.BUILD / tc.PRG_NAME, os.environ.get("C64U_PASSWORD")))
