# ADR 0002: Scroll engine

Status: accepted (M3, 16 October 2026)

## Context

Eight-way scrolling over levels of up to 142 × 80 tiles, with an own colour per character. Colour RAM cannot be double buffered, and a full redraw costs more than one frame.

## Decision

- **Double-buffered screen RAM** at `$C000`/`$C400`, 40 × 25 characters, 38 × 24 visible (`$D016`/`$D011` fine scroll, CSEL = RSEL = 0).
- **Full redraw of the back buffer** from the map (no shift copy), row by row. Four row variants (top/bottom half × even/odd column) are unrolled per tile. The main loop renders in the free time of each frame and stops when the next frame starts.
- **Prediction:** when the camera moves towards a character boundary (fine offset ≥ 4 in the direction of motion), the next coarse position is rendered in advance. If the camera crosses before the buffer is ready, the screen holds the nearest position the front buffer allows (lag of a frame or so).
- **Swap in the raster IRQ** at line 251, together with the fine scroll. The same IRQ rewrites colour RAM via a char → colour table, row by row from the top. It stays ahead of the beam because it starts about 7,000 cycles before row 0 is displayed.
- **Variables** in `$A000-$BFFF` (cleared at startup), zero page `$02-$7F`.
- **Files** are Exomizer-crunched (`exomizer mem`, in-place load address). `kernal_load` returns the end address, and the ported decruncher unpacks from there. All 19 levels plus the sprite bank take 38 KB of the disk.

## Consequences

- The colour update costs about 17,600 cycles in the swap frame. Game logic in that frame is delayed but not lost; the main loop counts frames and catches up.
- Raster interrupts for other purposes (a sprite multiplexer) cannot run during the colour update. A multiplexer must fit around it (M6).
- Animated tiles change only character set data, never screen or colour RAM.
