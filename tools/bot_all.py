"""Try the level bot on every level (py65, real game code) and report which ones it
finishes. A level the bot cannot finish is not necessarily unbeatable: the bot only
walks right and jumps.

Usage: python tools/bot_all.py [levels...]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]
import bot  # noqa: E402


def main() -> None:
    levels = [int(a) for a in sys.argv[1:]] or list(range(1, 17))
    for n in levels:
        best = None
        for ahead in (20, 12, 28, 6, 36):
            result, inputs, m = bot.play(n, ahead)
            x = (m.mpu.memory[0x30] | m.mpu.memory[0x31] << 8) / 16
            y = (m.mpu.memory[0x32] | m.mpu.memory[0x33] << 8) / 16
            if result == bot.RESULT_EXIT:
                best = f"EXIT after {len(inputs)} ticks (jump distance {ahead})"
                break
            outcome = {0: "timeout", 1: "died"}.get(result, str(result))
            best = best or f"{outcome} at ({x:.0f}, {y:.0f})"
        print(f"level {n:2d}: {best}", flush=True)


if __name__ == "__main__":
    main()
