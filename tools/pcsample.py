"""Sample the program counter of a VICE run at regular intervals (real time, no warp)
and print a timeline of routine names. For finding stalls.

Usage: python tools/pcsample.py <d64> <seconds> [pal|ntsc] [interval]
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402
import vicemon  # noqa: E402
from hangcheck import labels_for, nearest  # noqa: E402


def main() -> None:
    d64 = Path(sys.argv[1]).resolve()
    seconds = float(sys.argv[2])
    system = sys.argv[3] if len(sys.argv) > 3 else "pal"
    interval = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1
    labels = labels_for(d64)
    proc = subprocess.Popen([str(tc.vice_bin("x64sc")), "-default", f"-{system}", "-sounddev", "dummy",
                             "-debugcart", "-binarymonitor", "-autostart", str(d64)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        mon = vicemon.Monitor()
        mon.resume()
        start = time.monotonic()
        last = None
        while time.monotonic() - start < seconds and proc.poll() is None:
            regs = mon.registers()
            zp = mon.memory(0x02, 0x02)
            mon.resume()
            where = nearest(labels, regs[vicemon.REG_PC]).split("+")[0]
            if where != last:
                print(f"{time.monotonic() - start:6.2f}s frame={zp[0]:3d} {where}")
                last = where
            time.sleep(interval)
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
