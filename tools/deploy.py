"""Build and start the game on the C64 Ultimate through its REST API.

The game loads its levels, sprites and sounds from disk, so the disk image is mounted
in drive A (device 8) first; then the crunched main program is started.

Usage: python tools/deploy.py
Environment: C64U_HOST (e.g. 192.168.0.123), optional C64U_PASSWORD (the Ultimate's
"Network Password"; without it the API answers 403 Forbidden).

API: https://1541u-documentation.readthedocs.io/en/latest/api/api_calls.html
(POST /v1/drives/<drive>:mount, POST /v1/runners:run_prg, X-Password header).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402
from build import build  # noqa: E402


def call(host: str, path: str, body: bytes | None, password: str | None, method: str = "POST") -> dict:
    request = urllib.request.Request(f"http://{host}/v1/{path}", data=body, method=method,
                                     headers={"Content-Type": "application/octet-stream"})
    if password:
        request.add_header("X-Password", password)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        if error.code == 403:
            raise SystemExit("403 Forbidden: set C64U_PASSWORD to the Ultimate's network password")
        raise
    result = json.loads(text) if text.strip() else {"errors": []}
    if result.get("errors"):
        raise SystemExit(f"{path}: {result['errors']}")
    return result


def deploy(host: str, d64: Path, prg: Path, password: str | None) -> None:
    call(host, "drives/a:mount?type=d64&mode=unlinked", d64.read_bytes(), password)
    print(f"mounted {d64.name} in drive A")
    call(host, "runners:run_prg", prg.read_bytes(), password)
    print(f"started {prg.name}")


if __name__ == "__main__":
    host = os.environ.get("C64U_HOST")
    if not host:
        raise SystemExit("set C64U_HOST to the IP address or hostname of the C64 Ultimate")
    d64 = build()
    deploy(host, d64, tc.BUILD / "keen-sfx.prg", os.environ.get("C64U_PASSWORD"))
