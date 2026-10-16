"""Run a d64 in VICE several times; when a run seems stuck, show where the CPU is.

Usage: python tools/hangcheck.py <d64> [runs] [seconds]
Each run: warp mode with the binary monitor; after `seconds` the PC is sampled a few
times and mapped to the nearest label of the build (main.vs next to the d64).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402
import vicemon  # noqa: E402


def labels_for(d64: Path) -> list[tuple[int, str]]:
    vs = d64.parent / "main.vs"
    out = []
    for line in vs.read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "al":
            out.append((int(parts[1].split(":")[1], 16), parts[2].lstrip(".")))
    return sorted(out)


def nearest(labels, pc):
    best = None
    for addr, name in labels:
        if addr <= pc:
            best = (addr, name)
        else:
            break
    return f"{best[1]}+{pc - best[0]}" if best else hex(pc)


def main() -> None:
    d64 = Path(sys.argv[1]).resolve()
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 20
    labels = labels_for(d64)
    for run in range(runs):
        proc = subprocess.Popen([str(tc.vice_bin("x64sc")), "-default", "-pal", "-warp", "-sounddev", "dummy",
                                 "-debugcart", "-binarymonitor", "-autostart", str(d64)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(seconds)
            if proc.poll() is not None:
                print(f"run {run}: finished, exit {proc.returncode}")
                continue
            mon = vicemon.Monitor()
            pcs = []
            for _ in range(5):
                regs = mon.registers()
                pcs.append(regs[vicemon.REG_PC])
                zp = mon.memory(0x00, 0x10)
                mon.resume()
                time.sleep(0.3)
            regs = mon.registers()
            io = mon.memory(0xD011, 0xD01A)
            print(f"run {run}: still running; PCs {[nearest(labels, p) for p in pcs]}; "
                  f"$01={zp[1]:02x} frame={zp[2]} flags={regs[vicemon.REG_FLAGS]:02x} "
                  f"d011={io[0]:02x} d012={io[1]:02x} d019={io[8]:02x} d01a={io[9]:02x}")
            mon.resume()
            mon.close()
        finally:
            proc.kill()


if __name__ == "__main__":
    main()
