"""M5/M6: complete levels in VICE with scripted input.

- Level 1 is played from start to exit with the input tools/bot.py finds in py65 (real
  game code, enemies included). VICE runs the complete engine; the outcome must be the
  same: exit reached, same score.
- Level 14 (23 Yorps, 7 Gargs) is walked through for 900 ticks to measure the frame rate:
  the main loop may never need more than 2 frames for one iteration (>= 25 fps).
"""
from __future__ import annotations

import struct
import subprocess

import pytest

import toolchain as tc
from conftest import require

OUT = tc.BUILD / "test"
JOY_UP, JOY_RIGHT, JOY_FIRE = 1, 8, 16


def run_script(level: int, script: list[tuple[int, int]], tag: str, extra=()) -> dict:
    lines = [f".const SCRIPT_LEVEL = {level}", "input_script:"]
    lines += [f"    .byte {n}, {joy}" for n, joy in script] + ["    .byte 0"]
    (tc.BUILD / "generated" / "gen_script.asm").write_text("\n".join(lines) + "\n")
    from build import build
    d64 = build(["LEVELTEST", "INPUTSCRIPT", *extra])
    run = tc.run([require(lambda: tc.vice_bin("x64sc")), "-default", "-pal", "-warp",
                  "-sounddev", "dummy", "-debugcart", "-limitcycles", 300_000_000,
                  "-autostart", d64],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    stats = OUT / f"{tag}_stats.prg"
    OUT.mkdir(parents=True, exist_ok=True)
    stats.unlink(missing_ok=True)
    tc.run([tc.vice_bin("c1541"), "-attach", d64, "-read", "stats", stats], capture_output=True)
    raw = stats.read_bytes()[2:] if stats.is_file() else b""
    assert len(raw) >= 11, f"no statistics (VICE exit {run.returncode})"
    return {"exit_code": run.returncode, "result": raw[0], "score": raw[1:4], "lives": raw[4],
            "max_frames": raw[8], "lost": struct.unpack_from("<H", raw, 9)[0]}


@pytest.fixture(scope="module")
def prerequisites():
    require(tc.kickass_jar)
    require(tc.exomizer)
    if not (tc.ROOT / "data" / "original" / "KEEN1.EXE").is_file():
        pytest.skip("Keen 1 files not in data/original/")
    from build import build
    build()                                         # main build: assets and labels for the bot


@pytest.fixture(scope="module")
def level1(prerequisites):
    import bot
    inputs, machine = bot.find_route(1)
    assert inputs is not None, "the bot did not reach the exit in py65"
    mem = machine.mpu.memory
    score = bytes(mem[machine.labels["score"]:machine.labels["score"] + 3])
    return run_script(1, bot.to_script(inputs), "m5"), score


def test_level_1_exit_reached_in_vice(level1):
    stats, _ = level1
    assert stats["exit_code"] == 0 and stats["result"] == 2, stats


def test_same_score_as_py65(level1):
    stats, score = level1
    assert stats["score"] == score
    assert stats["score"] != b"\0\0\0"               # items were collected on the way


def test_no_life_lost(level1):
    stats, _ = level1
    assert stats["lives"] == 4


@pytest.fixture(scope="module")
def busy_level(prerequisites):
    # walk right, jumping and shooting now and then, for 900 ticks
    script = [(40, JOY_RIGHT), (20, JOY_RIGHT | JOY_UP), (5, JOY_RIGHT | JOY_FIRE)] * 13 + [(5, 0)]
    return run_script(14, script, "m6", ["GODMODE"])


def test_frame_rate_with_many_enemies(busy_level):
    assert busy_level["result"] == 3, busy_level        # whole script played (GODMODE)
    assert busy_level["max_frames"] <= 2, busy_level       # never below 25 fps
