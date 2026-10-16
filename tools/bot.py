"""Find a joystick script that plays a level from start to exit, using the real 6502
game code in py65 (deterministic, so the script replays identically in VICE).

Policy: hold right; jump when a blocking or deadly tile is close ahead, or when stuck.
Usage: python tools/bot.py [level] -> writes build/generated/gen_script.asm
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tests"), str(ROOT / "tests" / "unit")]

import toolchain as tc  # noqa: E402
from test_build import Machine  # noqa: E402

JOY_UP, JOY_RIGHT = 1, 8
RESULT_DIED, RESULT_EXIT = 1, 2
MAX_TICKS = 6000


class Level:
    def __init__(self, number: int):
        from tools.convert import original
        ep = original.load()
        self.level = ep.levels[number]
        self.info = ep.tileinfo

    def tile(self, col, row):
        if not (0 <= row < self.level.height and 0 <= col < self.level.width):
            return None
        return self.info[self.level.tiles[row][col]]


def play(number: int, policy_jump_ahead: int = 20, verbose: bool = False):
    m = Machine()
    m.load(tc.BUILD / "assets" / f"l{number:02d}.prg")
    for routine in ("level_init", "anim_init", "game_new", "items_level_start", "actors_init", "player_init",
                    "camera_center", "scroll_init"):
        m.call(routine)
    lvl = Level(number)
    mem = m.mpu.memory
    result_addr = m.labels["play_result"]
    mem[result_addr] = 0
    inputs, last_x, stuck = [], 0, 0
    for tick in range(MAX_TICKS):
        x = (mem[0x30] | mem[0x31] << 8) / 16
        y = (mem[0x32] | mem[0x33] << 8) / 16
        ground = mem[0x36]
        joy = JOY_RIGHT
        if ground:
            front = int(x + 11 + policy_jump_ahead) // 16
            rows = range(int(y + 1) // 16, int(y + 23) // 16 + 1)
            feet_row = int(y + 24) // 16
            blocked = any((t := lvl.tile(front, r)) and t.left for r in rows)
            deadly = any((t := lvl.tile(c, r)) and t.behaviour == 1
                         for c in range(int(x + 4) // 16, front + 2) for r in list(rows) + [feet_row])
            gap = all((t := lvl.tile(c, feet_row)) is None or not t.top
                      for c in (front, front + 1))
            if blocked or deadly or gap or stuck > 10:
                joy |= JOY_UP
        stuck = stuck + 1 if abs(x - last_x) < 0.5 else 0
        last_x = x
        mem[0x3B] = joy
        mem[0x3D] = 0
        inputs.append(joy)
        m.call("player_update")
        m.call("player_touch")
        m.call("actors_update")
        m.call("camera_follow")
        if (mem[0x33] >> 4) >= lvl.level.height:      # fell out of the map
            mem[result_addr] = RESULT_DIED
        if mem[result_addr]:
            if verbose:
                print(f"tick {tick}: result {mem[result_addr]} at ({x:.0f}, {y:.0f})")
            return mem[result_addr], inputs, m
    return 0, inputs, m


JOY_DOWN, JOY_LEFT, JOY_FIRE = 2, 4, 16


class MapWalker:
    """The world map in py65: walk Keen with the joystick along a tile path."""

    def __init__(self, done_levels=(), keen=None):
        from collections import deque  # noqa: F401
        self.m = Machine()
        self.m.load(tc.BUILD / "assets" / "l80.prg")
        for routine in ("level_init", "anim_init", "map_collect_spots"):
            self.m.call(routine)
        mem, L = self.m.mpu.memory, self.m.labels
        mem[L["map_mode"]] = 1
        mem[L["teleport_lock"]] = 1               # as map_enter: no teleport where Keen starts
        for n in done_levels:
            mem[L["levels_done"] + (n - 1) // 8] |= 1 << ((n - 1) % 8)
        if keen is None:
            keen = (mem[0x5007] * 256, mem[0x5008] * 256)
        self.set_keen(*keen)
        self.inputs: list[int] = []
        self.prev = 0
        from tools.convert import original
        ep = original.load()
        self.map, self.info = ep.levels[80], ep.tileinfo
        self.spots = {}
        for y, row in enumerate(self.map.sprites):
            for x, code in enumerate(row):
                if code:
                    self.spots.setdefault(code, []).append((x, y))
        self.done = set(done_levels)

    def set_keen(self, x, y):
        mem = self.m.mpu.memory
        mem[0x30], mem[0x31], mem[0x32], mem[0x33] = x & 0xFF, x >> 8, y & 0xFF, y >> 8

    def keen(self):
        mem = self.m.mpu.memory
        return (mem[0x30] | mem[0x31] << 8) / 16, (mem[0x32] | mem[0x33] << 8) / 16

    def centre_tile(self):
        x, y = self.keen()
        return int(x + 6) // 16, int(y + 12) // 16

    def walkable(self, x, y):
        if not (0 <= x < self.map.width and 0 <= y < self.map.height):
            return False
        i = self.info[self.map.tiles[y][x]]
        if i.top or i.right or i.bottom or i.left:
            return False
        code = self.map.sprites[y][x]
        return not (code & 0x8000 and (code & 0xFF) not in self.done)

    def path(self, goal):
        from collections import deque
        start = self.centre_tile()
        prev, q = {start: None}, deque([start])
        while q:
            p = q.popleft()
            if p == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (p[0] + dx, p[1] + dy)
                if n not in prev and self.walkable(*n):
                    prev[n] = p
                    q.append(n)
        if goal not in prev:
            raise SystemExit(f"no map path to {goal}")
        route, p = [], goal
        while p:
            route.append(p)
            p = prev[p]
        return route[::-1]

    def tick(self, joy):
        mem = self.m.mpu.memory
        mem[0x3B], mem[0x3D] = joy, joy & ~self.prev & 0xFF
        self.prev = joy
        self.inputs.append(joy)
        for routine in ("map_move", "camera_follow", "map_spots"):
            self.m.call(routine)

    def path_exists(self, goal):
        try:
            self.path(goal)
            return True
        except SystemExit:
            return False

    TELEPORTERS = (38, 41, 46)

    def go_to(self, goal, hops=4):
        """Walk to goal, using teleporters when it lies in another region."""
        for _ in range(hops + 1):
            if self.path_exists(goal):
                if self.walk_to(goal):
                    return
                continue                                 # teleported on the way: plan again
            here = self.centre_tile()
            options = [p for code in self.TELEPORTERS for p in self.spots.get(code, [])
                       if self.path_exists(p)]
            if not options:
                raise SystemExit(f"no way from {here} to {goal}")
            target = min(options, key=lambda p: len(self.path(p)))
            if target == here:                           # standing on it: step off first
                for n in ((here[0] + 1, here[1]), (here[0] - 1, here[1]),
                          (here[0], here[1] + 1), (here[0], here[1] - 1)):
                    if self.walkable(*n):
                        self.walk_to(n)
                        break
            self.walk_to(target)
        raise SystemExit(f"could not reach {goal}")

    def walk_to(self, goal, max_ticks=4000):
        """Follow the tile path; steer Keen's centre to each tile centre.
        Returns False when Keen was teleported on the way (the walk stops there)."""
        for tx, ty in self.path(goal):
            for _ in range(max_ticks):
                before = self.centre_tile()
                x, y = self.keen()
                cx, cy = x, y                      # sprite position
                tcx, tcy = tx * 16 + 2, ty * 16 - 4    # feet box inside the tile
                joy = 0
                if cx < tcx - 2:
                    joy |= JOY_RIGHT
                elif cx > tcx + 2:
                    joy |= JOY_LEFT
                if cy < tcy - 2:
                    joy |= JOY_DOWN
                elif cy > tcy + 2:
                    joy |= JOY_UP
                if not joy:
                    break
                self.tick(joy)
                after = self.centre_tile()
                if abs(after[0] - before[0]) + abs(after[1] - before[1]) > 2:
                    return False                         # teleported
            else:
                raise SystemExit(f"stuck walking to {(tx, ty)} at {self.keen()}")
        return True

    def press_fire(self):
        """Release, then fire. The game stops reading map input in the tick that
        enters a level, so nothing may follow the fire tick in the script."""
        self.tick(0)
        self.tick(JOY_FIRE)

    def result(self):
        return self.m.mpu.memory[self.m.labels["map_result"]]


def to_script(inputs: list[int]) -> list[tuple[int, int]]:
    script = []
    for joy in inputs:
        if script and script[-1][1] == joy and script[-1][0] < 255:
            script[-1] = (script[-1][0] + 1, joy)
        else:
            script.append((1, joy))
    return script


def find_route(number: int, verbose: bool = False):
    """Try a few jump distances; returns (inputs, machine) of the first run that exits."""
    for ahead in (20, 12, 28, 6, 36):
        result, inputs, m = play(number, ahead, verbose)
        if result == RESULT_EXIT:
            return inputs, m
    return None, None


def main() -> None:
    number = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    inputs, m = find_route(number, verbose=True)
    if inputs is None:
        raise SystemExit("no route found")
    script = to_script(inputs)
    out = ROOT / "build" / "generated" / "gen_script.asm"
    lines = [f"// Generated by tools/bot.py for level {number}: {len(inputs)} ticks to the exit.",
             f".const SCRIPT_LEVEL = {number}", f".const SCRIPT_TICKS = {len(inputs)}", "input_script:"]
    lines += [f"    .byte {n}, {joy}" for n, joy in script] + ["    .byte 0"]
    out.write_text("\n".join(lines) + "\n")
    mem = m.mpu.memory
    score = mem[m.labels["score"]:m.labels["score"] + 3]
    print(f"exit after {len(inputs)} ticks ({len(script)} script entries), "
          f"score {score[2]:02x}{score[1]:02x}{score[0]:02x} -> {out}")


if __name__ == "__main__":
    main()
