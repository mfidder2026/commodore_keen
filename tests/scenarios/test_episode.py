"""The whole game in VICE: the playthrough planned by tools/episode.py (world map walks,
levels 1, 3, 4, 5, 7, 8 and 16, the ship) is replayed in the FLOWTEST build with the real
game_main, and must reach the end with all four ship parts and no life lost.

The script is generated data (not in git): run `python tools/episode.py 150000 1 3 4 5 7 8 16`
first (it takes hours; finished level routes are cached in build/generated/routes).
"""
from __future__ import annotations

import shutil

import pytest

import toolchain as tc
from conftest import require, run_vice

SCRIPT = tc.BUILD / "generated" / "episode_script.asm"
OUT = tc.BUILD / "test"


@pytest.fixture(scope="module")
def episode():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not SCRIPT.is_file():
        pytest.skip("no planned playthrough (run tools/episode.py)")
    from build import build
    build()
    shutil.copyfile(SCRIPT, tc.BUILD / "generated" / "gen_script.asm")
    d64 = build(["FLOWTEST", "INPUTSCRIPT"])
    OUT.mkdir(parents=True, exist_ok=True)
    shot = OUT / "episode.png"
    shot.unlink(missing_ok=True)
    run = run_vice(["-default", "-pal", "-warp",
                    "-sounddev", "dummy", "-debugcart", "-limitcycles", 3_000_000_000,
                    "-exitscreenshot", shot, "-autostart", d64], timeout=3600)
    stats = OUT / "episode_stats.prg"
    stats.unlink(missing_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", d64, "-read", "stats", stats], capture_output=True)
    raw = stats.read_bytes()[2:] if stats.is_file() else b""
    assert len(raw) >= 15, f"no statistics (VICE exit {run.returncode})"
    return {"levels_done": raw[0:3], "score": raw[3:6], "lives": raw[6],
            "won": raw[13], "ship_parts": raw[14]}


def test_the_end_is_reached(episode):
    assert episode["won"] == 1, episode


def test_all_four_ship_parts(episode):
    assert episode["ship_parts"] == 15, episode


def test_the_levels_are_marked_done(episode):
    done = int.from_bytes(episode["levels_done"], "little")
    for level in (1, 3, 4, 5, 7, 8, 16):
        assert done & (1 << (level - 1)), (level, episode)


def test_no_life_lost(episode):
    assert episode["lives"] == 4, episode
