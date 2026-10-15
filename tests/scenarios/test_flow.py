"""M7: the game flow in VICE: world map -> level 1 -> back on the map -> through the
barrier that level 1 opens.

The input is planned in py65 with the real game code (tools/bot.py: MapWalker for the map,
find_route for the level) and replayed in the FLOWTEST build, which runs the real
game_main (title, map, level loading, death/exit handling).
"""
from __future__ import annotations

import subprocess

import pytest

import toolchain as tc
from conftest import require

OUT = tc.BUILD / "test"
JOY_RIGHT = 8


@pytest.fixture(scope="module")
def flow():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not (tc.ROOT / "data" / "original" / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    from build import build
    build()
    import bot
    walker = bot.MapWalker()
    entrance = walker.spots[1][0]
    walker.walk_to(entrance)
    walker.press_fire()
    assert walker.result() == 1, "py65: fire on the level 1 entrance did not enter it"
    keen = walker.keen()
    level_inputs, _ = bot.find_route(1)
    assert level_inputs is not None
    back = bot.MapWalker(done_levels=[1], keen=(int(keen[0] * 16), int(keen[1] * 16)))
    back.walk_to((24, 39))
    inputs = walker.inputs + level_inputs + back.inputs
    script = bot.to_script(inputs)
    lines = ["input_script:"] + [f"    .byte {n}, {joy}" for n, joy in script] + ["    .byte 0"]
    (tc.BUILD / "generated" / "gen_script.asm").write_text("\n".join(lines) + "\n")

    d64 = build(["FLOWTEST", "INPUTSCRIPT"])
    shot = OUT / "m7_flow.png"
    OUT.mkdir(parents=True, exist_ok=True)
    shot.unlink(missing_ok=True)
    run = tc.run([require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
                  "-sounddev", "dummy", "-debugcart", "-limitcycles", 600_000_000,
                  "-exitscreenshot", shot, "-autostart", d64],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    stats = OUT / "m7_stats.prg"
    stats.unlink(missing_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", d64, "-read", "stats", stats], capture_output=True)
    raw = stats.read_bytes()[2:] if stats.is_file() else b""
    assert len(raw) >= 13, f"no statistics (VICE exit {run.returncode})"
    return {"levels_done": raw[0:3], "score": raw[3:6], "lives": raw[6],
            "x": (raw[7] | raw[8] << 8) / 16, "y": (raw[9] | raw[10] << 8) / 16,
            "map_mode": raw[11], "level": raw[12]}


def test_back_on_the_map(flow):
    assert flow["map_mode"] == 1 and flow["level"] == 80, flow


def test_level_1_marked_done(flow):
    assert flow["levels_done"][0] & 1, flow


def test_walked_through_the_opened_barrier(flow):
    assert int(flow["x"] + 6) // 16 == 24, flow          # barrier at column 22


def test_no_life_lost_and_points_scored(flow):
    assert flow["lives"] == 4
    assert flow["score"] != b"\0\0\0"


def test_barrier_blocks_before_level_1(built_d64):
    import bot
    walker = bot.MapWalker()
    walker.walk_to(walker.spots[1][0])
    for _ in range(80):
        walker.tick(JOY_RIGHT)
    x, _ = walker.keen()
    assert int(x + 8) // 16 < 22                          # stopped before the barrier
