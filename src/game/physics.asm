// Keen's movement constants, per 50 Hz tick, in 1/16 pixel.
//
// Source: measured in the original (v1.31 in DOSBox, tools/measure_keen.py, 16 October 2026):
// walking ~123 px/s, jump apex ~53 px after ~0.45 s. NOT yet checked against the
// reconstructed source (reference/keen13-src is not available); see docs/physics.md.
// All values live here so an NTSC version only needs another table.

.const SUBPX            = 16
.const WALK_SPEED       = 39      // 2.4 px per tick = 122 px/s
.const WALK_ACCEL       = 4
.const WALK_FRICTION    = 4
.const AIR_ACCEL        = 3
.const AIR_FRICTION     = 1
.const JUMP_SPEED       = 70      // apex after 24 ticks, 53 px (original: 53 px)
.const GRAVITY          = 3
.const MAX_FALL         = 80      // 5 px per tick (estimate)
.const POGO_SPEED       = 80      // estimate: bounce on the pogo stick
.const POGO_HIGH_SPEED  = 104     // estimate: bounce while holding up

// Keen's collision box inside his 16 x 24 sprite (EGAHEAD hitbox of KEENWALKR1).
.const KEEN_BOX_LEFT    = 4
.const KEEN_BOX_RIGHT   = 11
.const KEEN_BOX_TOP     = 1
.const KEEN_BOX_BOTTOM  = 23

// Camera: keep Keen's left edge between these screen x positions (304 px wide view),
// and his top between these screen y positions (192 px high view).
// Right edge measured in the original: scrolling starts at 172 of 320 px.
.const CAM_LEFT_EDGE    = 120
.const CAM_RIGHT_EDGE   = 164
.const CAM_TOP_EDGE     = 48
.const CAM_BOTTOM_EDGE  = 112

.const WALK_FRAME_TICKS = 6
