"""Convert decoded Keen 1 levels into C64 multicolour character data.

One Keen tile (16x16 EGA pixels) becomes 2x2 multicolour characters of 4x8 fat pixels.
Per level the converter picks three shared colours (background, $D022, $D023) and gives
every character one own colour (0-7, from colour RAM). Identical characters are shared;
if a level needs more than CHAR_LIMIT characters, the most similar ones are merged.

Animated tiles (animation groups from tileinfo) get dedicated characters whose bitmap
the engine rewrites every animation step; the frames are stored separately.
See docs/decisions/0001-level-format.md for the binary layout.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .compare import animation_groups
from .levels import Level
from .tileinfo import TileInfo

# Pepto's C64 palette.
C64_PALETTE = np.array([
    (0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x68, 0x37, 0x2B), (0x70, 0xA4, 0xB2),
    (0x6F, 0x3D, 0x86), (0x58, 0x8D, 0x43), (0x35, 0x28, 0x79), (0xB8, 0xC7, 0x6F),
    (0x6F, 0x4F, 0x25), (0x43, 0x39, 0x00), (0x9A, 0x67, 0x59), (0x44, 0x44, 0x44),
    (0x6C, 0x6C, 0x6C), (0x9A, 0xD2, 0x84), (0x6C, 0x5E, 0xB5), (0x95, 0x95, 0x95),
], dtype=np.int32)

# EGA colour -> C64 colour, picked by eye for the closest look rather than plain RGB distance.
EGA_TO_C64 = [0, 6, 5, 3, 2, 4, 8, 15, 11, 14, 13, 3, 10, 4, 7, 1]

# Error of showing colour a where colour b should be: squared RGB distance plus a fixed
# penalty for any change. Without the penalty, muddy "average" greys win over the few
# colours that define a graphic (Keen's yellow helmet, for instance).
MISMATCH_PENALTY = 20000
RGB_DIST = ((C64_PALETTE[:, None, :] - C64_PALETTE[None, :, :]) ** 2).sum(axis=2)
DIST = RGB_DIST + np.where(RGB_DIST > 0, MISMATCH_PENALTY, 0)

CHAR_LIMIT = 240            # leaves room below 256 for the engine
MAX_TILES = 256
OWN_COLOURS = range(8)      # colour RAM in multicolour mode: only colours 0-7

# Tile attribute byte: bits 0-1 top (0-3), bit 2 right, bit 3 bottom, bit 4 left, bit 7 animated.
BLOCK_RIGHT, BLOCK_BOTTOM, BLOCK_LEFT, ANIMATED = 0x04, 0x08, 0x10, 0x80


def halve(rows: list[list[int]], transparent: int | None = None, rule: str = "rarer") -> np.ndarray:
    """EGA rows -> C64 colours at half horizontal resolution (fat pixels).

    rule "rarer": of each horizontal pixel pair the colour that is rarer in the whole
    graphic wins, so thin details in tiles survive. rule "right": the right pixel wins,
    which gives small sprites a calmer look. With `transparent`, an opaque pixel always
    beats a transparent one.
    """
    ega = np.array(rows)
    counts = np.bincount(ega.ravel(), minlength=17)
    left, right = ega[:, 0::2], ega[:, 1::2]
    pick = right if rule == "right" else np.where(counts[left] <= counts[right], left, right)
    if transparent is not None:
        pick = np.where(left == transparent, right, np.where(right == transparent, left, pick))
    mapping = np.array(EGA_TO_C64 + [-1])
    return mapping[pick]


def tile_chars(fat: np.ndarray) -> list[np.ndarray]:
    """16 rows x 8 fat pixels -> four 8x4 characters: top-left, top-right, bottom-left, bottom-right."""
    return [fat[0:8, 0:4], fat[0:8, 4:8], fat[8:16, 0:4], fat[8:16, 4:8]]


@dataclass
class Quantised:
    bits: np.ndarray     # 8x4 values 0-3 (00 background, 01 $D022, 10 $D023, 11 own)
    own: int             # own colour 0-7

    def key(self) -> bytes:
        return self.bits.astype(np.uint8).tobytes() + bytes([self.own])

    def colours(self, shared: tuple[int, int, int]) -> np.ndarray:
        palette = np.array([*shared, self.own])
        return palette[self.bits]

    def bytes(self) -> bytes:
        b = self.bits
        return bytes(int(b[y, 0] << 6 | b[y, 1] << 4 | b[y, 2] << 2 | b[y, 3]) for y in range(8))


def quantise(chars: list[np.ndarray], shared: tuple[int, int, int],
             own_options=OWN_COLOURS) -> tuple[list[Quantised], int]:
    """Quantise characters that must share one own colour (e.g. all frames of an animated
    character). Returns the quantised characters and the total squared error."""
    best = None
    for own in own_options:
        palette = np.array([*shared, own])
        errors = DIST[np.stack(chars)[..., None], palette]        # (n, 8, 4, 4)
        total = int(errors.min(axis=3).sum())
        if best is None or total < best[0]:
            best = (total, own, errors.argmin(axis=3))
    total, own, bits = best
    return [Quantised(bits[i], own) for i in range(len(chars))], total


def choose_shared(chars: list[np.ndarray], weights: list[int]) -> tuple[int, int, int]:
    """Pick background, $D022 and $D023 for a level: the trio with the lowest weighted error."""
    stack = np.stack(chars)
    w = np.array(weights)[:, None, None]
    counts = np.bincount(stack.ravel(), weights=np.broadcast_to(w, stack.shape).ravel(), minlength=16)
    candidates = [int(c) for c in np.argsort(counts)[::-1][:8] if counts[c] > 0]
    background = candidates[0]
    best = None
    for i, c1 in enumerate(candidates):
        for c2 in candidates[i + 1:]:
            if background in (c1, c2):
                continue
            trio = (background, c1, c2)
            pal = np.array([[*trio, own] for own in OWN_COLOURS])           # (8, 4)
            err = DIST[stack[..., None, None], pal].min(axis=4)              # (n, 8, 4, 8)
            per_char = err.sum(axis=(1, 2)).min(axis=1)                     # best own per char
            total = int((per_char * np.array(weights)).sum())
            if best is None or total < best[0]:
                best = (total, trio)
    if best is None:                                  # fewer than three colours in the level
        rest = [c for c in range(16) if c != background]
        return (background, rest[0], rest[1])
    return best[1]


@dataclass
class AnimGroup:
    first_char: int                  # first of 4 consecutive dedicated characters
    frames: list[list[Quantised]]    # per frame: 4 characters


@dataclass
class C64Level:
    number: int
    width: int
    height: int
    shared: tuple[int, int, int]
    chars: list[Quantised]
    tiles: list[tuple[int, int, int, int]]     # C64 tile -> 4 character numbers
    tile_origin: list[int]                     # C64 tile -> original Keen tile number
    tile_behaviour: list[int]
    tile_attr: list[int]
    map: list[list[int]]                       # [y][x] C64 tile
    anims: list[AnimGroup]
    actors: list[tuple[int, int, int]]         # (code, x, y) in tiles
    start: tuple[int, int]
    merged_chars: int = 0
    colour_error: int = 0
    stats: dict = field(default_factory=dict)


def convert_level(level: Level, ega_tiles: list[list[list[int]]], info: list[TileInfo]) -> C64Level:
    groups = animation_groups([t.anim for t in info])

    # Original tiles used by the map; any frame of an animation stands for its whole group.
    used = sorted({t for row in level.tiles for t in row})
    group_of = {t: tuple(groups[t]) for t in used}
    static = sorted({t for t in used if len(group_of[t]) == 1})
    anim_groups = sorted({g for g in group_of.values() if len(g) > 1})
    if len(static) + len(anim_groups) > MAX_TILES:
        raise ValueError(f"level {level.number}: {len(static) + len(anim_groups)} tiles > {MAX_TILES}")

    fat = {t: halve(ega_tiles[t]) for g in [static] + list(anim_groups) for t in g}
    usage = {t: 0 for t in used}
    for row in level.tiles:
        for t in row:
            usage[t] += 1

    # Shared colours from all characters, weighted by how often their tile appears.
    sample_chars, sample_weights = [], []
    for t in used:
        for c in tile_chars(fat[t]):
            sample_chars.append(c)
            sample_weights.append(usage[t])
    shared = choose_shared(sample_chars, sample_weights)

    # Static tiles: quantise each character on its own, then share identical ones.
    static_q = {}
    error = 0
    for t in static:
        static_q[t] = []
        for c in tile_chars(fat[t]):                     # each character picks its own colour
            (q,), e = quantise([c], shared)
            static_q[t].append(q)
            error += e * usage[t]

    unique: dict[bytes, int] = {}
    chars: list[Quantised] = []
    char_use: list[int] = []
    tile_char_ids = {}
    for t in static:
        ids = []
        for q in static_q[t]:
            k = q.key()
            if k not in unique:
                unique[k] = len(chars)
                chars.append(q)
                char_use.append(0)
            char_use[unique[k]] += usage[t]
            ids.append(unique[k])
        tile_char_ids[t] = ids

    anim_limit = CHAR_LIMIT - 4 * len(anim_groups)
    merged = 0
    if len(chars) > anim_limit:
        chars, remap, merged = merge_chars(chars, char_use, shared, anim_limit)
        tile_char_ids = {t: [remap[i] for i in ids] for t, ids in tile_char_ids.items()}

    # Animated groups: 4 dedicated characters each; per character position one own colour.
    anims = []
    group_char_ids = {}
    for g in anim_groups:
        first = len(chars)
        frames_chars = [tile_chars(fat[t]) for t in g]
        frames: list[list[Quantised]] = [[None] * 4 for _ in g]
        for pos in range(4):
            q, e = quantise([fc[pos] for fc in frames_chars], shared)
            error += e * sum(usage.get(t, 0) for t in g) // len(g)
            for f in range(len(g)):
                frames[f][pos] = q[f]
            chars.append(q[0])
        anims.append(AnimGroup(first, frames))
        group_char_ids[g] = [first, first + 1, first + 2, first + 3]

    # C64 tile numbering: static tiles first, then one tile per animation group.
    tiles, origin, behaviour, attr = [], [], [], []
    c64_tile_of = {}
    for t in static:
        c64_tile_of[t] = len(tiles)
        tiles.append(tuple(tile_char_ids[t]))
        origin.append(t)
    for g in anim_groups:
        for t in g:
            c64_tile_of[t] = len(tiles)
        tiles.append(tuple(group_char_ids[g]))
        origin.append(g[0])
    for t in origin:
        ti = info[t]
        behaviour.append(ti.behaviour & 0xFF)
        a = ti.top & 3
        a |= BLOCK_RIGHT if ti.right else 0
        a |= BLOCK_BOTTOM if ti.bottom else 0
        a |= BLOCK_LEFT if ti.left else 0
        a |= ANIMATED if len(groups[t]) > 1 else 0
        attr.append(a)

    c64_map = [[c64_tile_of[t] for t in row] for row in level.tiles]
    actors, start = [], (0, 0)
    for y, row in enumerate(level.sprites):
        for x, code in enumerate(row):
            if code == 255:
                start = (x, y)
            elif code:
                actors.append((code, x, y))

    return C64Level(level.number, level.width, level.height, shared, chars, tiles, origin,
                    behaviour, attr, c64_map, anims, actors, start, merged, error,
                    {"static_tiles": len(static), "anim_groups": len(anim_groups),
                     "chars": len(chars)})


def merge_chars(chars: list[Quantised], use: list[int], shared, limit: int):
    """Merge the most similar characters until at most `limit` remain.

    The cost of merging a into b is the colour error of showing b wherever a was used,
    weighted by a's usage; the cheapest merge goes first.
    """
    colours = np.stack([c.colours(shared) for c in chars])          # (n, 8, 4)
    n = len(chars)
    alive = list(range(n))
    target = list(range(n))
    weight = np.array(use, dtype=np.int64) + 1
    merged = 0
    while len(alive) > limit:
        a_col = colours[alive]
        diff = DIST[a_col[:, None], a_col[None, :]].sum(axis=(2, 3))   # (m, m)
        cost = diff * weight[alive][:, None]
        np.fill_diagonal(cost, np.iinfo(np.int64).max)
        i, j = np.unravel_index(np.argmin(cost), cost.shape)
        src, dst = alive[i], alive[j]
        target[src] = dst
        weight[dst] += weight[src]
        alive.remove(src)
        merged += 1

    def root(i):
        while target[i] != i:
            i = target[i]
        return i

    new_index = {old: new for new, old in enumerate(alive)}
    remap = [new_index[root(i)] for i in range(n)]
    return [chars[i] for i in alive], remap, merged


def preview(lvl: C64Level, scale: int = 1):
    """Render the level as the C64 would show it (fat pixels doubled to hires width)."""
    from PIL import Image
    char_rgb = [C64_PALETTE[c.colours(lvl.shared)] for c in lvl.chars]
    for g in lvl.anims:                                  # show frame 0 of animated chars
        for pos in range(4):
            char_rgb[g.first_char + pos] = C64_PALETTE[g.frames[0][pos].colours(lvl.shared)]
    img = np.zeros((lvl.height * 16, lvl.width * 16, 3), dtype=np.uint8)
    for y, row in enumerate(lvl.map):
        for x, t in enumerate(row):
            for pos, ch in enumerate(lvl.tiles[t]):
                cy, cx = y * 16 + (pos // 2) * 8, x * 16 + (pos % 2) * 8
                img[cy:cy + 8, cx:cx + 8] = np.repeat(char_rgb[ch], 2, axis=1)
    out = Image.fromarray(img)
    return out.resize((out.width * scale, out.height * scale), Image.NEAREST) if scale > 1 else out
