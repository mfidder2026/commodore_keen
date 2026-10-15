// Tile behaviour (tileinfo plane 2) under Keen: items, deadly tiles, exit, doors.
// Behaviour values: https://moddingwiki.shikadi.net/wiki/Keen_1-3_Tileinfo_format

.const BEH_KILLS     = 1
.const BEH_DOOR1     = 2          // doors 2-5 open with keycards 18-21
.const BEH_DOOR4     = 5
.const BEH_POINTS500 = 6
.const BEH_POINTS5000 = 10
.const BEH_JOYSTICK  = 11         // ship parts 11-14
.const BEH_EVERCLEAR = 14
.const BEH_RAYGUN    = 15
.const BEH_POGO      = 16
.const BEH_EXIT      = 17
.const BEH_KEY1      = 18
.const BEH_KEY4      = 21

.const START_LIVES   = 4
.const RAYGUN_SHOTS  = 5

.segment Code

// New game: score, lives, items.
game_new:
    lda #0
    sta score
    sta score + 1
    sta score + 2
    sta ammo
    sta p_has_pogo
    sta ship_parts
    sta levels_done
    sta levels_done + 1
    sta levels_done + 2
    lda #START_LIVES
    sta lives
    lda #$02                      // next extra life at 20000 (BCD ten-thousands digit)
    sta next_life
    rts

// Start of a level: keycards are per level.
items_level_start:
    lda #0
    sta keycards
    rts

// Check the tiles that overlap Keen's box. Sets play_result for death and exit.
player_touch:
    PixelsOf(p_x, box_left)
    PixelsOf(p_y, box_top)
    TileOf(box_left, KEEN_BOX_LEFT, touch_col0)
    TileOf(box_left, KEEN_BOX_RIGHT, touch_col1)
    TileOf(box_top, KEEN_BOX_TOP, touch_row0)
    TileOf(box_top, KEEN_BOX_BOTTOM, touch_row1)
    lda touch_row0
    sta t_row
touch_row:
    lda touch_col0
    sta t_col
touch_cell:
    jsr tile_attr_at              // X = tile
    lda TILE_BEHAVIOUR, x
    beq touch_next
    jsr touch_behaviour
    lda play_result
    bne touch_done
touch_next:
    lda t_col
    cmp touch_col1
    inc t_col
    bcc touch_cell
    lda t_row
    cmp touch_row1
    inc t_row
    bcc touch_row
touch_done:
    rts

// A = behaviour of tile (t_col, t_row).
touch_behaviour:
    cmp #BEH_KILLS
    bne !+
#if !GODMODE
    lda #RESULT_DIED
    sta play_result
#endif
    rts
!:  cmp #BEH_EXIT
    bne !+
    lda #RESULT_EXIT
    sta play_result
    rts
!:  cmp #BEH_POINTS500
    bcc touch_ignore              // doors are handled by door_blocked
    cmp #BEH_POINTS5000 + 1
    bcs !+
    sec
    sbc #BEH_POINTS500
    tax
    lda points_mid, x
    ldy points_low, x
    jsr add_score
    lda #SND_GOTBONUSSND
    jsr sound_play
    jmp collect
!:  cmp #BEH_EVERCLEAR + 1
    bcs !+
    sec
    sbc #BEH_JOYSTICK
    tax
    lda bit_table, x
    ora ship_parts
    sta ship_parts
    lda #SND_GOTPARTSND
    jsr sound_play
    jmp collect
!:  cmp #BEH_RAYGUN
    bne !+
    lda ammo
    clc
    adc #RAYGUN_SHOTS
    sta ammo
    lda #SND_GOTITEMSND
    jsr sound_play
    jmp collect
!:  cmp #BEH_POGO
    bne !+
    lda #1
    sta p_has_pogo
    lda #SND_GOTITEMSND
    jsr sound_play
    jmp collect
!:  cmp #BEH_KEY1
    bcc touch_ignore
    cmp #BEH_KEY4 + 1
    bcs touch_ignore
    sec
    sbc #BEH_KEY1
    tax
    lda bit_table, x
    ora keycards
    sta keycards
    lda #SND_GETCARDSND
    jsr sound_play
    jmp collect
touch_ignore:
    rts

// Points per behaviour 6-10: 500, 100, 200, 1000, 5000 as BCD (middle, low byte).
points_mid: .byte $05, $01, $02, $10, $50
points_low: .byte $00, $00, $00, $00, $00
bit_table:  .byte 1, 2, 4, 8

// Remove the item at (t_col, t_row): replace it with an empty neighbour or the
// level's background tile.
collect:
    lda t_col
    sta mt_col
    lda t_row
    sta mt_row
    jsr empty_neighbour
    jmp set_map_tile

// A = an empty tile next to (mt_col, mt_row), else LVL_BG_TILE.
empty_neighbour:
    lda mt_col
    sta t_col
    lda mt_row
    sta t_row
    dec t_col
    jsr empty_at
    bcs found_empty
    inc t_col
    inc t_col
    jsr empty_at
    bcs found_empty
    dec t_col
    dec t_row
    jsr empty_at
    bcs found_empty
    lda LVL_BG_TILE
    rts
found_empty:
    txa
    rts

// C set and X = tile if (t_col, t_row) has no behaviour and no blocking.
empty_at:
    jsr tile_attr_at
    and #%00011111
    bne !+
    lda TILE_BEHAVIOUR, x
    bne !+
    sec
    rts
!:  clc
    rts

// Score: add A (middle BCD byte, hundreds) and Y (low BCD byte) to the 6-digit score.
add_score:
    sed
    sty zp_tmp0
    clc
    adc #0                        // keep A
    sta zp_tmp1
    lda score
    adc zp_tmp0
    sta score
    lda score + 1
    adc zp_tmp1
    sta score + 1
    lda score + 2
    adc #0
    sta score + 2
    cld
    // extra life every 20000: compare the ten-thousands byte
    lda score + 2
    cmp next_life
    bcc !+
    inc lives
    lda #SND_EXTRAMANSND
    jsr sound_play
    sed
    clc
    lda next_life
    adc #$02
    sta next_life
    cld
!:  rts

// Called by player_move_x when Keen is blocked: open a door in the blocking column
// if Keen has the matching keycard. C set = door opened (not blocked any more).
door_blocked:
    lda t_row
    sta door_row
!:  jsr tile_attr_at
    lda TILE_BEHAVIOUR, x
    cmp #BEH_DOOR1
    bcc door_next
    cmp #BEH_DOOR4 + 1
    bcs door_next
    sec
    sbc #BEH_DOOR1
    tax
    lda bit_table, x
    and keycards
    beq door_next
    jmp open_door
door_next:
    lda t_row
    cmp t_end
    inc t_row
    bcc !-
    lda door_row
    sta t_row
    clc
    rts

// Remove the whole door in column t_col around row t_row (all tiles with door behaviour).
open_door:
    lda #SND_DOOROPENSND
    jsr sound_play
    ldx t_row
    stx door_scan
    // find the top of the door
!:  dec door_scan
    lda door_scan
    sta t_row
    jsr tile_attr_at
    lda TILE_BEHAVIOUR, x
    cmp #BEH_DOOR1
    bcc !+
    cmp #BEH_DOOR4 + 1
    bcc !-
!:  inc door_scan
    // remove downwards while the tiles are door tiles
!:  lda door_scan
    sta t_row
    jsr tile_attr_at
    lda TILE_BEHAVIOUR, x
    cmp #BEH_DOOR1
    bcc door_opened
    cmp #BEH_DOOR4 + 1
    bcs door_opened
    lda t_col
    sta mt_col
    lda door_scan
    sta mt_row
    lda LVL_BG_TILE
    jsr set_map_tile
    inc door_scan
    jmp !-
door_opened:
    lda door_row
    sta t_row
    sec
    rts

.segment Vars
score:      .fill 3, 0            // BCD, low byte first: 6 digits
next_life:  .byte 0               // BCD ten-thousands of the next extra life
lives:      .byte 0
ammo:       .byte 0
ship_parts: .byte 0               // bits: joystick, battery, vacuum, everclear
keycards:   .byte 0               // bits: doors 1-4
levels_done: .fill 3, 0           // bit per level 1-16 (and 17-24 spare)
touch_col0: .byte 0
touch_col1: .byte 0
touch_row0: .byte 0
touch_row1: .byte 0
door_row:   .byte 0
door_scan:  .byte 0
