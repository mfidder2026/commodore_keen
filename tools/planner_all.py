"""Run tools/planner.py for several levels in parallel processes and summarise.

Usage: python tools/planner_all.py <max_nodes> <workers> [levels...]
Output: build/generated/route_lNN.txt for every solved level; a summary at the end.
"""
from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def solve(level: int, max_nodes: int) -> str:
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "planner.py"), str(level), str(max_nodes)],
                            capture_output=True, text=True)
    lines = [l for l in result.stdout.splitlines() if l.startswith("level")]
    return lines[-1] if lines else f"level {level}: error {result.stderr[-300:]}"


def main() -> None:
    max_nodes, workers = int(sys.argv[1]), int(sys.argv[2])
    levels = [int(a) for a in sys.argv[3:]] or list(range(1, 17))
    with ThreadPoolExecutor(workers) as pool:
        for line in pool.map(lambda n: solve(n, max_nodes), levels):
            print(line, flush=True)


if __name__ == "__main__":
    main()
