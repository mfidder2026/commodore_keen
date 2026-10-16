"""Plan levels as if Keen already has the pogo stick and ammunition (as later in a
real game). Usage: python tools/planner_with_pogo.py <max_nodes> <levels...>"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]


def solve(args):
    level, max_nodes = args
    import planner
    carry = {"p_has_pogo": b"\x01", "ammo": bytes([20])}
    route = planner.plan(level, max_nodes, verbose=False, carry=carry)
    return level, (len(route) if route else None)


if __name__ == "__main__":
    max_nodes = int(sys.argv[1])
    levels = [int(a) for a in sys.argv[2:]]
    with ProcessPoolExecutor(len(levels)) as pool:
        for level, ticks in pool.map(solve, [(n, max_nodes) for n in levels]):
            print(f"level {level} with pogo and ammo: " + (f"exit after {ticks} ticks" if ticks else "no route"),
                  flush=True)
