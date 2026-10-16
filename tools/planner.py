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


CARRIED = ("score", "lives", "ammo", "ship_parts", "next_life")   # labels; plus p_has_pogo ($4f)


class Game:
    def __init__(self, number: int, carry: dict | None = None, min_ammo: int = 0,
                 need_pogo: bool = False, need_part: bool = False):
        """carry: game state from earlier levels (see carried_state). min_ammo / need_pogo /
        need_part: the exit only counts with that many shots / with the pogo stick / with
        this level's ship part (items needed later in the game)."""
        from tools.convert import original
        self.m = Machine()
        self.m.load(tc.BUILD / "assets" / f"l{number:02d}.prg")
        self.m.call("game_new")
        self.mem = self.m.mpu.memory
        self.L = self.m.labels
        if carry:
            for name, value in carry.items():
                if name == "p_has_pogo":
                    self.mem[0x4F] = value[0]
                else:
                    a = self.L[name]
                    self.mem[a:a + len(value)] = list(value)
        for routine in ("level_init", "anim_init", "items_level_start", "actors_init",
                        "player_init", "camera_center", "scroll_init"):
            self.m.call(routine)
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
        self.rayguns = self.item_tiles(15)
        self.pogos = self.item_tiles(16)
        self.parts = [t for b in range(11, 15) for t in self.item_tiles(b)] if need_part else []
        self.min_ammo = min_ammo
        self.need_pogo = need_pogo
        self._maps = {}
        self._heights = {}
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

    def passable(self, x, y, mask, walls=frozenset()):
        if not (0 <= x < self.level.width and 0 <= y < self.level.height) or (x, y) in walls:
            return False
        info = self.info[self.level.tiles[y][x]]
        if info.behaviour == 1:
            return False
        if 2 <= info.behaviour <= 5:
            return bool(mask & (1 << (info.behaviour - 2)))
        return not (info.left or info.right or info.bottom)

    def above_floor(self, x, y, mask):
        """Height of cell (x, y) above the nearest floor in its own column or up to two
        columns aside (Keen drifts sideways while he rises): 0 when he can stand there."""
        key = (x, y, mask)
        if key not in self._heights:
            best = 99
            for cx in range(x - 2, x + 3):
                if not self.passable(cx, y, mask):
                    continue
                h = 0
                while (h < 20 and self.passable(cx, y + h + 1, mask)
                       and not self.info[self.level.tiles[y + h + 1][cx]].top):
                    h += 1
                best = min(best, h)
            self._heights[key] = best
        return self._heights[key]

    def distance_map(self, sources, mask, walls=frozenset()):
        """Walking distance from every cell to the nearest source. Keen can only rise into
        cells at most a jump (3 tiles) or a pogo bounce (7 tiles) above a floor; he can
        fall anywhere except through the top of a platform. Searched backwards from the sources."""
        from collections import deque
        reach = 7 if self.mem[0x4F] else 3
        cache_key = (tuple(sources), mask, walls, reach)
        if cache_key in self._maps:
            return self._maps[cache_key]
        dist = {s: 0 for s in sources}
        q = deque(sources)
        while q:
            x, y = q.popleft()
            for dx, dy, cost in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 2)):
                n = (x + dx, y + dy)
                if dy == 1 and self.above_floor(x, y, mask) > reach:
                    continue                       # Keen would have to rise from n to (x, y)
                if dy == -1 and self.info[self.level.tiles[y][x]].top:
                    continue                       # one-way platform: no falling through
                if n not in dist and self.passable(*n, mask, walls):
                    dist[n] = dist[(x, y)] + cost
                    q.append(n)
        self._maps[cache_key] = dist
        return dist

    def distance(self):
        x, y = self.keen()
        cell = (int(x + 8) // 16, int(y + 16) // 16)
        mask = self.mem[self.L["keycards"]]
        items = self.needed_items()
        if items:
            # the exit ends the level, so the way to the items must not lead through it
            to_item = self.distance_map(items, mask, frozenset(self.exits)).get(cell, 999.0)
            return to_item + min(self.estimate(c, mask, 0) for c in items) + 5
        return self.estimate(cell, mask, 0)

    def item_tiles(self, behaviour):
        """(cell, map address, tile byte) of every item tile with this behaviour; the item
        is still there while the map byte is unchanged."""
        rows = (self.L["map_row_lo"], self.L["map_row_hi"])
        found = []
        for y, row in enumerate(self.level.tiles):
            for x, t in enumerate(row):
                if self.info[t].behaviour == behaviour:
                    a = (self.mem[rows[0] + y] | self.mem[rows[1] + y] << 8) + x
                    found.append(((x, y), a, self.mem[a]))
        return found

    def remaining(self, items):
        return [cell for cell, a, tile in items if self.mem[a] == tile]

    def needed_items(self):
        """Cells of the items still to fetch before the exit counts."""
        if self.mem[self.L["ammo"]] < self.min_ammo and self.remaining(self.rayguns):
            return self.remaining(self.rayguns)
        if self.need_pogo and not self.mem[0x4F]:
            return self.remaining(self.pogos)
        return self.remaining(self.parts)

    def has_items(self):
        return (self.mem[self.L["ammo"]] >= self.min_ammo and (self.mem[0x4F] or not self.need_pogo)
                and not self.remaining(self.parts))

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

    def carried_state(self) -> dict:
        state = {"p_has_pogo": bytes([self.mem[0x4F]])}
        sizes = {"score": 3}
        for name in CARRIED:
            a = self.L[name]
            state[name] = bytes(self.mem[a:a + sizes.get(name, 1)])
        return state

    def key(self):
        x, y = self.keen()
        m = self.mem
        return (int(x) // 8, int(y) // 8, m[0x36], m[0x3A], m[self.L["keycards"]], m[0x4F],
                m[self.L["ammo"]], m[0x4F], len(self.remaining(self.parts)))


def plan(number: int, max_nodes: int = 4000, verbose: bool = True, carry: dict | None = None,
         min_ammo: int = 0, need_pogo: bool = False, need_part: bool = False):
    """Returns the input list that reaches the exit, or None. With carry, the level
    starts with that game state (score, lives, ammo, pogo stick, ship parts); with
    min_ammo / need_pogo / need_part, the exit only counts once Keen has that many shots /
    the pogo stick / the level's ship part."""
    game = Game(number, carry, min_ammo, need_pogo, need_part)
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
            if result == RESULT_EXIT and not game.has_items():
                continue
            if result == RESULT_EXIT:
                if verbose:
                    print(f"level {number}: exit after {len(route)} ticks, {nodes} nodes")
                plan.final_state = game.carried_state()
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
