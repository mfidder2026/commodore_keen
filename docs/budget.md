# Frame budget

A PAL frame is 63 × 312 = 19,656 cycles. The design budget is in PLAN.md under "Framebudget". Measured values come from the M3 scroll test (`tests/scenarios/test_scroll.py`). They are taken with CIA2 timer A, so badline and sprite DMA delays are included.

## Scroll engine (M3, measured 16 October 2026 in VICE 3.9)

| Part | Measured | Notes |
| --- | --- | --- |
| Render one row of the back buffer | 994 cycles | 25 rows = ~25,000 cycles per coarse step, spread over the free time of several frames |
| Colour RAM from screen RAM (in the IRQ at line 251) | 14,486 cycles (PAL), 14,892 (NTSC) | code generated at startup at `$A600`, 13 cycles per character; stays ahead of the beam (row 24 deadline: 19,152 PAL, 16,575 NTSC). First version: 17,568, too slow for NTSC |
| Swap + fine scroll + sprite registers | < 400 cycles | every frame |

## NTSC (M10)

NTSC frames have 17,095 cycles. The game runs 5 ticks per 6 frames, so it plays at the same speed. Scroll test on NTSC: 0 lost frames, same lag as PAL, screen pixel-exact. Level 14 with many enemies: a few iterations take 3 frames (20 fps), 70 frames lost in about 1,080 (PAL: at most 2 frames, 14 lost; 16 October, after the keyboard and the exit-after-items change).

**Alignment matters in level 14.** The margin there is thin: shifting `game/actors.asm` by 0-224 bytes gives PAL results between 2 frames / 14 lost and 3 frames / 24 lost (measured in 32-byte steps), because page crossings in the actor code (indexed reads, taken branches) add up over 30 actors. Page-aligning the collision box tables alone did not help. New code therefore goes after the game code (like `game/keys.asm`), and `test_frame_rate_with_many_enemies` guards the result. Finding the exact hot spot (`tools/pcsample.py`) is still open.

Scroll test path: 410 frames at up to 3 px per frame horizontally and 1 px vertically. **0 frames lost.** In 28 frames the screen showed the nearest position the front buffer allowed (the camera waited one frame for the back buffer).

## Consequences

- A coarse step costs about 25,000 (render) + 17,600 (colour) cycles. At walking speed (2-3 px per frame, a coarse step every 3-4 frames) that is 11,000-14,000 cycles per frame on average. About 5,000 cycles per frame remain for game logic.
- The planned reserve of 6,400 cycles does not cover the colour update. The design was changed accordingly: the colour update runs in the IRQ, and the game logic simply waits for the next frame (see ADR 0002).

## Later milestones

| Task | Budget | Measured | Milestone |
| --- | --- | --- | --- |
| Sprite multiplexer | 2,000 | — | M6 |
| Player, physics, collision | 1,500 | — | M4 |
| Actors (up to 8) | 3,000 | — | M6 |
| Sound effects | 600 | — | M8 |
