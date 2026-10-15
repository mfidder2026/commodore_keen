# Frame budget

A PAL frame is 63 × 312 = 19,656 cycles. Measurements start in M3. The design budget is in PLAN.md under "Framebudget".

| Task | Budget | Measured | Milestone |
| --- | --- | --- | --- |
| Copy screen RAM (spread over frames) | 2,500 | — | M3 |
| Draw new edge tiles | 1,000 | — | M3 |
| Sprite multiplexer | 2,000 | — | M6 |
| Player, physics, collision | 1,500 | — | M4 |
| Actors (up to 8) | 3,000 | — | M6 |
| Sound effects | 600 | — | M8 |

## Known problem in the design

In the swap frame, updating colour RAM costs about 8,000 cycles according to the plan, but the reserve is only 6,400. At ~11–12 cycles per character for about 900 characters it may well be more than 8,000. M3 has to measure this. Options: spread the colour RAM update over two frames, or skip other tasks in the swap frame.
