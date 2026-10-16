"""Screenshots for the README: the real game in VICE, stopped part-way through a scripted
route (title screen, world map, levels). Writes docs/screenshots/*.png (2x, nearest).

The level routes come from tools/planner.py (build/generated/route_lNN.txt); run
`python tools/planner_all.py 80000 8` first.

Usage: python tools/screenshots.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]

import toolchain as tc  # noqa: E402
from build import build  # noqa: E402
from conftest import run_vice  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
# level, fraction of its route played before the screenshot, file name
LEVELS = [
    (1, 0.45, "level01"),
    (3, 0.55, "level03"),
    (7, 0.40, "level07"),
    (8, 0.60, "level08"),
    (10, 0.50, "level10"),
]


def shoot(d64: Path, name: str, cycles: int) -> Path:
    raw = tc.BUILD / "test" / f"shot_{name}.png"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.unlink(missing_ok=True)
    run_vice(["-default", "-pal", "-warp", "-sounddev", "dummy", "-debugcart",
              "-limitcycles", cycles, "-exitscreenshot", raw, "-autostart", d64], timeout=900)
    from PIL import Image
    image = Image.open(raw).convert("RGB")
    image = image.resize((image.width * 2, image.height * 2), Image.NEAREST)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}.png"
    image.save(out, optimize=True)
    print(f"-> {out}")
    return out


def script_file(lines: list[str]) -> None:
    (tc.BUILD / "generated" / "gen_script.asm").write_text("\n".join(lines) + "\n")


def to_lines(inputs: list[int]) -> list[str]:
    import bot
    return [f"    .byte {n}, {joy}" for n, joy in bot.to_script(inputs)] + ["    .byte 0"]


def main() -> None:
    import bot
    shoot(build(), "title", 150_000_000)

    # world map: walk part of the way to level 1
    walker = bot.MapWalker()
    walker.walk_to(walker.spots[1][0])
    script_file(["input_script:"] + to_lines(walker.inputs[: len(walker.inputs) * 2 // 3]))
    shoot(build(["FLOWTEST", "INPUTSCRIPT"]), "worldmap", 600_000_000)

    for level, fraction, name in LEVELS:
        route = tc.BUILD / "generated" / f"route_l{level:02d}.txt"
        if not route.is_file():
            print(f"no route for level {level}, skipped")
            continue
        inputs = [int(v) for v in route.read_text().split()]
        script_file([f".const SCRIPT_LEVEL = {level}", "input_script:"]
                    + to_lines(inputs[: int(len(inputs) * fraction)]))
        shoot(build(["LEVELTEST", "INPUTSCRIPT"]), name, 300_000_000)


if __name__ == "__main__":
    main()
