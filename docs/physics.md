# Keen's physics

Constants: `src/game/physics.asm` (per 50 Hz tick, in 1/16 pixel). Code: `src/game/player.asm`.

## Source of the values

The reconstructed source (`reference/keen13-src`) was **not** available when M4 was built: it has to be downloaded from the Keen modding forum, and that needs the user's approval. The values were measured in the original v1.31 instead (DOSBox, `tools/dosbox_capture.py` burst captures at ~65 fps and `tools/measure_keen.py`, 16 October 2026). They must be checked against the source once it is available; CLAUDE.md requires that.

| Quantity | Original (measured) | C64 (test_player.py) |
| --- | --- | --- |
| Walking speed | ~123 px/s | 2.44 px/tick = 122 px/s |
| Acceleration to walking speed | ~0.2 s | ~0.2 s (4/16 px per tick²) |
| Jump height (held), level 1 at x = 258 | 53 px | 53 px |
| Time to land on the platform at y = 239 | ~0.78 s | 0.80 s |
| Holding jump on landing | jumps again | jumps again |
| Start position level 1 | feet at y = 271 | feet at y = 271 |
| Camera starts scrolling right | Keen at 172 of 320 px | 164 of 304 px |

## Estimates (not measured yet)

- Maximum fall speed: 5 px/tick.
- Pogo bounce: 80 (normal) and 104 (joystick up) in 1/16 px per tick. Measuring needs the pogo stick, which Keen only gets later in the game; the C+T+Space cheat gives it in the original.
- Air control: acceleration 3, friction 1 per tick.
- Short jumps: the original's jump height may depend on how long the button is held; the C64 version always jumps the full height.
- Vertical camera margins (48 and 112 px from the top of the view).

## Collision

Tile sides from tileinfo: moving right tests the left side of the tile ahead, moving left its right side, falling tests the top (any non-zero top value: solid, slippery or ice), rising tests the bottom. Outside the map, left and right are solid and top and bottom are open; falling out of the bottom of the map kills Keen. `tests/unit/test_collision.py` checks landing, standing, walls and ceilings on level 1 in py65.
