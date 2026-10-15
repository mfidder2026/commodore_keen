# Enemies and shots

Code: `src/game/actors.asm`. Tests: `tests/unit/test_actors.py`, `tests/scenarios/test_level.py`.

**Status: behaviour is an estimate.** It is based on the known gameplay of Keen 1, not on the reconstructed source; that source has not been downloaded yet (it needs your approval). Speeds, timings and AI choices must be checked against `reference/keen13-src` and DOSBox recordings.

## Actor codes (sprite plane of the levels)

| Code | Actor | Behaviour in the C64 version | Shot |
| --- | --- | --- | --- |
| 1 | Yorp | walks, stops to look around, hops now and then; pushes Keen; stunned (2.5 s) when Keen lands on its head | dies |
| 2 | Garg | walks; when Keen is on about the same height: looks, then charges until it hits a wall; deadly | dies |
| 3 | Vorticon | walks, jumps towards Keen now and then; deadly | 4 shots |
| 4 | Butler robot | walks back and forth, pushes Keen | immune |
| 5 | Tank robot | patrols, fires at Keen every 2 s; its shots are deadly | immune |
| 6-9 | Ice cannon | invisible, fires ice every 2.4 s diagonally (up-right, up-left, down-right, down-left: direction mapping is a guess) | — |
| 10 | Vorticon commander (level 16) | like a Vorticon | 10 shots (estimate) |

Ice freezes Keen for 2 s (KEENSICLE frames). Codes above 10 (only in level 12's sprite plane, apparently stray data) are ignored.

## Raygun

The fire button fires a shot (7 px per tick) if Keen has ammunition; each raygun pick-up gives 5 shots. A shot that hits a wall or an immune enemy becomes a splash. Down + fire toggles the pogo, like the space bar.

## Activation and drawing

- Actors in the camera view plus 6 tiles move; the others wait (the original also activates enemies only near the screen).
- Keen uses hardware sprites 0-1. Enemies and shots share sprites 2-7: one sprite for small actors, two stacked sprites for Gargs and Vorticons (32 px high). With more pieces than sprites, the starting actor rotates every frame, so actors flicker instead of disappearing. Since only 8 sprites exist, there are never more than 8 on one raster line; there is no multiplexer.
- Enemy positions follow the same convention as Keen: the sprite's top starts at the top of the marker tile, then gravity puts the actor on the floor.

## Frame rate

Level 14 (23 Yorps, 7 Gargs) for 900 ticks with GODMODE: never more than 2 frames per main loop iteration (≥ 25 fps), 17 frames lost in total.
