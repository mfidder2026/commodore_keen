"""M5: a level can be played from start to exit.

tools/bot.py finds joystick input that reaches the exit of level 1, using the real game
code in py65. The LEVELTEST build replays that input in VICE with the complete engine
(scrolling, IRQ, sprites); the outcome must be the same: exit reached, same score.
"""
from __future__ import annotations

import subprocess

import pytest

import toolchain as tc
from conftest import require

OUT = tc.BUILD / "test"


@pytest.fixture(scope="module")
def outcome():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not (tc.ROOT / "data" / "original" / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    from build import build
    build()                                         # main build: assets and labels for the bot
    import bot
    inputs, machine = bot.find_route(1)
    assert inputs is not None, "the bot did not reach the exit in py65"
    mem = machine.mpu.memory
    score = bytes(mem[machine.labels["score"]:machine.labels["score"] + 3])
    script = bot.to_script(inputs)
    lines = [".const SCRIPT_LEVEL = 1", "input_script:"]
    lines += [f"    .byte {n}, {joy}" for n, joy in script] + ["    .byte 0"]
    (tc.BUILD / "generated" / "gen_script.asm").write_text("\n".join(lines) + "\n")

    d64 = build(["LEVELTEST", "INPUTSCRIPT"])
    run = tc.run([require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
                  "-sounddev", "dummy", "-debugcart", "-limitcycles", 200_000_000,
                  "-autostart", d64],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    stats = OUT / "m5_stats.prg"
    OUT.mkdir(parents=True, exist_ok=True)
    stats.unlink(missing_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", d64, "-read", "stats", stats], capture_output=True)
    return run.returncode, stats.read_bytes()[2:] if stats.is_file() else b"", score


def test_level_1_exit_reached_in_vice(outcome):
    code, stats, _ = outcome
    assert code == 0 and stats[0] == 2, f"exit code {code}, stats {stats.hex()}"


def test_same_score_as_py65(outcome):
    _, stats, score = outcome
    assert stats[1:4] == score
    assert stats[1:4] != b"\0\0\0"                   # items were collected on the way


def test_no_life_lost(outcome):
    _, stats, _ = outcome
    assert stats[4] == 4
