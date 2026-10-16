"""Search for joystick input that finishes a level, with the real game code in py65.

Best-first search over short actions (walk, jump, pogo jump, shoot, wait). After every
action the machine state is stored, so other actions can be tried from there. Visited
situations (Keen's position in 8 px cells, on the ground or not, pogo, keycards) are not
expanded twice. The heuristic is the distance to the nearest exit tile.

Usage: python tools/planner.py <level> [max_nodes]  -> build/generated/route_lNN.txt
The found input replays identically in VICE (deterministic game logic).
"""
from __future__ import annotations

import heapq
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tests"), str(ROOT / "tests" / "unit")]

import toolchain as tc  # noqa: E402
from test_build import Machine  # noqa: E402

UP, DOWN, LEFT, RIGHT, FIRE, SPACE = 1, 2, 4, 8, 16, 32
RESULT_DIED, RESULT_EXIT = 1, 2

# (name, list of joystick states per tick)
ACTIONS = [
    ("right", [RIGHT] * 8),
    ("left", [LEFT] * 8),
    ("jump right", [UP | RIGHT] * 4 + [RIGHT] * 24),
    ("jump left", [UP | LEFT] * 4 + [LEFT] * 24),
    ("jump", [UP] * 4 + [0] * 24),
    ("long right", [RIGHT] * 24),
    ("long left", [LEFT] * 24),
    ("shoot", [0, FIRE, 0, 0, 0, 0]),
    ("pogo", [SPACE, 0]),
    ("wait", [0] * 12),
]


class Game:
    def __init__(self, number: int):
        from tools.convert import original
        self.m = Machine()
        self.m.load(tc.BUILD / "assets" / f"l{number:02d}.prg")
        for routine in ("level_init", "anim_init", "game_new", "items_level_start", "actors_init",
                        "player_init", "camera_center", "scroll_init"):
            self.m.call(routine)
        self.mem = self.m.mpu.memory
        self.L = self.m.labels
        self.mem[self.L["play_result"]] = 0
        ep = original.load()
        self.level = ep.levels[number]
        self.height = self.level.height
        self.info = ep.tileinfo
        self.exits = [(x, y) for y, row in enumerate(self.level.tiles) for x, t in enumerate(row)
                      if ep.tileinfo[t].behaviour == 17]
        self.keys = {}
        for y, row in enumerate(self.level.tiles):
            for x, t in enumerate(row):
                if 18 <= ep.tileinfo[t].behaviour <= 21:
                    self.keys.setdefault(ep.tileinfo[t].behaviour - 18, []).append((x, y))
        self._maps = {}
        self.prev = 0

    def snapshot(self):
        return list(self.mem), self.prev

    def restore(self, snap):
        self.mem[:] = snap[0]
        self.prev = snap[1]

    def keen(self):
        m = self.mem
        return (m[0x30] | m[0x31] << 8) / 16, (m[0x32] | m[0x33] << 8) / 16

    def result(self):
        return self.mem[self.L["play_result"]]

    def tick(self, joy):
        m = self.mem
        m[0x3C] = self.prev                     # joy_prev
        m[0x3B] = joy
        m[0x3D] = joy & ~self.prev & 0xFF        # joy_new, as input_read computes it
        self.prev = joy
        for routine in ("player_update", "player_touch", "actors_update", "camera_follow"):
            self.m.call(routine)
        if (m[0x33]) >= self.height:            # fell out of the map (p_y / 256 = tile row)
            m[self.L["play_result"]] = RESULT_DIED

    def run(self, inputs):
        for i, joy in enumerate(inputs):
            self.tick(joy)
            if self.result():
                return i + 1
        return len(inputs)

    # --- heuristic: walking distance through the level (walls, doors, deadly tiles) ---

    def passable(self, x, y, mask):
        if not (0 <= x < self.level.width and 0 <= y < self.level.height):
            return False
        info = self.info[self.level.tiles[y][x]]
        if info.behaviour == 1:
            return False
        if 2 <= info.behaviour <= 5:
            return bool(mask & (1 << (info.behaviour - 2)))
        return not (info.left or info.right or info.bottom)

    def distance_map(self, sources, mask):
        from collections import deque
        cache_key = (tuple(sources), mask)
        if cache_key in self._maps:
            return self._maps[cache_key]
        dist = {s: 0 for s in sources}
        q = deque(sources)
        while q:
            x, y = q.popleft()
            for dx, dy, cost in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 2)):
                n = (x + dx, y + dy)
                if n not in dist and self.passable(*n, mask):
                    dist[n] = dist[(x, y)] + cost
                    q.append(n)
        self._maps[cache_key] = dist
        return dist

    def distance(self):
        x, y = self.keen()
        cell = (int(x + 8) // 16, int(y + 16) // 16)
        return self.estimate(cell, self.mem[self.L["keycards"]], 0)

    def estimate(self, cell, mask, depth):
        """Walking distance to an exit, through keycards (in any order) where needed."""
        d = self.distance_map(self.exits, mask).get(cell)
        if d is not None:
            return d
        if depth >= 4:
            return 999.0
        best = 999.0
        for bit, keys in self.keys.items():
            if mask & (1 << bit):
                continue
            to_key = self.distance_map(keys, mask).get(cell)
            if to_key is None:
                continue
            after = min(self.estimate(k, mask | (1 << bit), depth + 1) for k in keys)
            best = min(best, to_key + after + 5)
        return best

    def key(self):
        x, y = self.keen()
        m = self.mem
        return (int(x) // 8, int(y) // 8, m[0x36], m[0x3A], m[self.L["keycards"]], m[0x4F])


def plan(number: int, max_nodes: int = 4000, verbose: bool = True):
    game = Game(number)
    counter = itertools.count()
    start = game.snapshot()
    frontier = [(game.distance(), next(counter), start, [])]
    seen = {game.key()}
    nodes = 0
    best = (game.distance(), [])
    while frontier and nodes < max_nodes:
        _, _, snap, inputs = heapq.heappop(frontier)
        for name, action in ACTIONS:
            game.restore(snap)
            used = game.run(action)
            nodes += 1
            result = game.result()
            route = inputs + action[:used]
            if result == RESULT_EXIT:
                if verbose:
                    print(f"level {number}: exit after {len(route)} ticks, {nodes} nodes")
                return route
            if result == RESULT_DIED:
                continue
            k = game.key()
            if k in seen:
                continue
            seen.add(k)
            d = game.distance()
            if d < best[0]:
                best = (d, route)
            # cost: distance to the exit plus a little for the route length
            heapq.heappush(frontier, (d + len(route) / 400, next(counter), game.snapshot(), route))
        if verbose and nodes % 500 < len(ACTIONS):
            print(f"  {nodes} nodes, best distance {best[0]:.1f} tiles, frontier {len(frontier)}", flush=True)
    if verbose:
        print(f"level {number}: no route within {max_nodes} nodes (closest {best[0]:.1f} tiles)")
    return None


def main() -> None:
    number = int(sys.argv[1])
    max_nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    route = plan(number, max_nodes)
    if route is not None:
        out = ROOT / "build" / "generated" / f"route_l{number:02d}.txt"
        out.write_text(" ".join(str(j) for j in route))
        print(f"-> {out}")


if __name__ == "__main__":
    main()
