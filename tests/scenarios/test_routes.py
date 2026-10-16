"""Levels can be finished in VICE: every route found by tools/planner.py (stored as
build/generated/route_lNN.txt, from a fresh game) is replayed in the LEVELTEST build with
the complete engine and must reach the exit without losing a life.

Routes are generated data (not in git): run `python tools/planner_all.py 60000 8` first.
"""
from __future__ import annotations

import pytest

import toolchain as tc
from test_level import prerequisites, run_script  # noqa: F401  (fixture)

ROUTES = sorted((tc.BUILD / "generated").glob("route_l*.txt"))


def to_script(inputs):
    script = []
    for joy in inputs:
        if script and script[-1][1] == joy and script[-1][0] < 255:
            script[-1] = (script[-1][0] + 1, joy)
        else:
            script.append((1, joy))
    return script


@pytest.mark.skipif(not ROUTES, reason="no planned routes in build/generated")
@pytest.mark.parametrize("route", ROUTES, ids=lambda p: p.stem)
def test_route_reaches_the_exit_in_vice(prerequisites, route):  # noqa: F811
    level = int(route.stem[len("route_l"):])
    inputs = [int(v) for v in route.read_text().split()]
    stats = run_script(level, to_script(inputs), f"route_l{level:02d}")
    assert stats["result"] == 2, f"level {level}: result {stats['result']} (2 = exit)"
    assert stats["lives"] == 4
