// Memory layout. All segments are defined here; keep docs/memorymap.md in sync.
// Level and sprite bank layout: docs/decisions/0001-level-format.md.

.const SCREEN_A      = $c000
.const SCREEN_B      = $c400
.const CHARSET       = $c800
.const FONT          = $d800
.const COLOUR_RAM    = $d800
.const D018_SCREEN_A = $02        // screen $c000, charset $c800
.const D018_SCREEN_B = $12        // screen $c400, charset $c800
.const D018_FONT_A   = $06        // screen $c000, font $d800

// Current level, loaded from disk at LEVEL_BASE.
.const LEVEL_BASE     = $5000
.const LVL_MAGIC      = LEVEL_BASE + 0
.const LVL_NUMBER     = LEVEL_BASE + 1
.const LVL_WIDTH      = LEVEL_BASE + 2
.const LVL_HEIGHT     = LEVEL_BASE + 3
.const LVL_COLOURS    = LEVEL_BASE + 4    // background, $d022, $d023
.const LVL_START_X    = LEVEL_BASE + 7
.const LVL_START_Y    = LEVEL_BASE + 8
.const LVL_ANIM_COUNT = LEVEL_BASE + 9
.const LVL_ACTOR_COUNT = LEVEL_BASE + 10
.const LVL_ANIMS      = LEVEL_BASE + $040 // 4 bytes each: first char, frames, data lo, hi
.const LVL_CHAR_COLOUR = LEVEL_BASE + $100
.const LVL_CHARSET    = LEVEL_BASE + $200
.const TILE_TL        = LEVEL_BASE + $a00
.const TILE_TR        = LEVEL_BASE + $b00
.const TILE_BL        = LEVEL_BASE + $c00
.const TILE_BR        = LEVEL_BASE + $d00
.const TILE_BEHAVIOUR = LEVEL_BASE + $e00
.const TILE_ATTR      = LEVEL_BASE + $f00
.const TILE_ORIGIN_LO = LEVEL_BASE + $1000
.const TILE_ORIGIN_HI = LEVEL_BASE + $1100
.const LVL_ACTORS     = LEVEL_BASE + $1200 // 4 bytes each: code lo, code hi, x, y
.const LVL_MAP        = LEVEL_BASE + $1c00

// Sprite bank file, loaded at $5000 before the first level and copied under I/O.
.const SPRITE_BANK_LOAD = $5000

.segmentdef Basic [start=$0801]
.segmentdef Code  [startAfter="Basic", max=$4fff]
.segmentdef Vars  [start=$a000, max=$bfff, virtual]

.file [name="commander-keen-c64.prg", segments="Basic,Code"]
