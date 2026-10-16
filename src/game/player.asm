// Keen: walking, jumping, pogo, collision with tiles, animation, camera.
// Constants: game/physics.asm. Collision box: KEEN_BOX_* inside the 16 x 24 sprite.
//
// Tile sides (tileinfo): moving right into a tile tests its left side (BLOCK_LEFT),
// moving left its right side, falling onto it its top (bits 0-1), rising into it its
// bottom side.

.const ATTR_TOP_MASK = %00000011
.const BLOCK_RIGHT   = %00000100
.const BLOCK_BOTTOM  = %00001000
.const BLOCK_LEFT    = %00010000

.segment Code

// Place Keen on the start tile of the level (sprite feet on the tile's bottom).
player_init:
    lda LVL_START_X               // x = tile * 16 px * 16 subpx = tile * 256
    sta p_x + 1
    lda #0
    sta p_x
    // Measured in the original: Keen's sprite top starts 8 px below the start tile
    // (level 1: start tile row 15, feet at y = 271 on row 17).
    lda LVL_START_Y
    sta p_y + 1
    lda #128
    sta p_y
    lda #0
    sta p_vx
    sta p_vy
    sta p_ground
    sta p_facing
    sta p_anim
    sta p_pogo
    rts

// One game tick.
player_update:
    lda p_frozen
    beq !+
    dec p_frozen                  // frozen by ice: no control, slide to a stop
    lda #0
    sta p_vx
    jsr gravity
    jmp !++
!:  jsr player_controls
    jsr player_fire
!:  jsr player_move_x
    jsr player_move_y
    jsr player_animate
    rts

player_controls:
    // pogo on/off: space, or down + fire
    lda joy_new
    and #KEY_SPACE
    bne pogo_toggle
    lda joy
    and #JOY_DOWN
    beq !+
    lda joy_new
    and #JOY_FIRE
    beq !+
pogo_toggle:
    lda p_has_pogo
    beq !+
    lda p_pogo
    eor #1
    sta p_pogo
!:
    // horizontal: accelerate towards the wanted speed
    lda joy
    and #JOY_LEFT
    beq !+
    lda #1
    sta p_facing
    lda #(-WALK_SPEED) & $ff
    jmp accelerate
!:  lda joy
    and #JOY_RIGHT
    beq !+
    lda #0
    sta p_facing
    lda #WALK_SPEED
    jmp accelerate
!:  lda #0
accelerate:
    sta c_tmp                     // wanted speed (signed)
    ldx p_ground
    lda accel_table, x
    sta c_tmp + 1
    lda c_tmp
    bne !+
    lda friction_table, x         // no input: friction instead of acceleration
    sta c_tmp + 1
!:  lda p_vx
    sec
    sbc c_tmp
    beq vx_done                   // already at the wanted speed
    bvc !+
    eor #$80
!:  bmi vx_up                     // vx < wanted
    lda p_vx                      // vx > wanted: decrease, not below wanted
    sec
    sbc c_tmp + 1
    bvs vx_clamp_low
    sta p_vx
    sec
    sbc c_tmp
    bvc !+
    eor #$80
!:  bpl vx_done
vx_clamp_low:
    lda c_tmp
    sta p_vx
    jmp vx_done
vx_up:
    lda p_vx
    clc
    adc c_tmp + 1
    bvs vx_clamp_high
    sta p_vx
    sec
    sbc c_tmp
    bvc !+
    eor #$80
!:  bmi vx_done
vx_clamp_high:
    lda c_tmp
    sta p_vx
vx_done:
    // jumping and pogo bouncing start from the ground
    lda p_ground
    beq gravity
    lda p_pogo
    beq !+
    lda joy                       // pogo bounces by itself; holding up bounces higher
    and #JOY_UP
    beq pogo_low
    lda #(-POGO_HIGH_SPEED) & $ff
    jmp launch
pogo_low:
    lda #(-POGO_SPEED) & $ff
    jmp launch
!:  lda joy
    and #JOY_UP
    beq gravity
    lda #(-JUMP_SPEED) & $ff
launch:
    sta p_vy
    lda #0
    sta p_ground
    lda p_pogo
    beq !+
    lda #SND_POGOJUMPSND
    jsr sound_play
    rts
!:
    lda #SND_KEENJUMPSND
    jsr sound_play
    rts
gravity:
    lda p_vy
    clc
    adc #GRAVITY
    bmi !+                        // still rising
    cmp #MAX_FALL
    bcc !+
    lda #MAX_FALL
!:  sta p_vy
    rts

accel_table:    .byte AIR_ACCEL, WALK_ACCEL
friction_table: .byte AIR_FRICTION, WALK_FRICTION

// x in pixels: box_left = (pos >> 4)
.macro PixelsOf(src, dst) {
    lda src + 1
    sta dst + 1
    lda src
    lsr dst + 1
    ror
    lsr dst + 1
    ror
    lsr dst + 1
    ror
    lsr dst + 1
    ror
    sta dst
}

// dst = (pixel value + offset) >> 4, as a tile number (fits 8 bits inside a level)
.macro TileOf(src, offset, dst) {
    clc
    lda src
    adc #offset
    sta c_tmp
    lda src + 1
    adc #0
    lsr
    ror c_tmp
    lsr
    ror c_tmp
    lsr
    ror c_tmp
    lsr
    ror c_tmp
    lda c_tmp
    sta dst
}

// A = attribute of tile (t_col, t_row); X = C64 tile number.
// Left/right of the map: solid. Above or below the map: empty.
tile_attr_at:
    lda t_row
    cmp level_height
    bcs tile_empty
    lda t_col
    cmp level_width
    bcs tile_solid
    ldx t_row
    lda map_row_lo, x
    sta c_tmp
    lda map_row_hi, x
    sta c_tmp + 1
    ldy t_col
    lda (c_tmp), y
    tax
    // Closed doors (behaviour 2-5) block on all sides; tileinfo only marks top/bottom.
    lda TILE_BEHAVIOUR, x
    sec
    sbc #2
    cmp #4
    bcc door_tile
    lda TILE_ATTR, x
    ldy map_mode                  // on the world map: barriers until their level is done
    bne !+
    rts
!:  jmp barrier_attr
door_tile:
    lda TILE_ATTR, x
    ora #ATTR_TOP_MASK & 1 | BLOCK_RIGHT | BLOCK_BOTTOM | BLOCK_LEFT
    rts
tile_empty:
    ldx LVL_BG_TILE               // a tile without behaviour
    lda #0
    rts
tile_solid:
    ldx LVL_BG_TILE
    lda #ATTR_TOP_MASK | BLOCK_RIGHT | BLOCK_BOTTOM | BLOCK_LEFT
    rts

// Does any tile in column t_col, rows t_row..t_end have one of the bits in c_tmp + 2?
// Out: Z clear (bne) if blocked.
column_blocked:
    lda t_row
    pha
!:  jsr tile_attr_at
    and c_tmp + 2
    bne !+
    lda t_row
    cmp t_end
    inc t_row
    bcc !-
    lda #0                        // sets Z: not blocked
!:  tax
    pla
    sta t_row
    txa
    rts

// Does any tile in row t_row, columns t_col..t_end have one of the bits in c_tmp + 2?
row_blocked:
    lda t_col
    pha
!:  jsr tile_attr_at
    and c_tmp + 2
    bne !+
    lda t_col
    cmp t_end
    inc t_col
    bcc !-
    lda #0
!:  tax
    pla
    sta t_col
    txa
    rts

player_move_x:
    lda p_vx
    bne !+
    rts
!:  // new_x = p_x + vx (sign extended)
    ldx #0
    lda p_vx
    bpl !+
    dex
!:  clc
    adc p_x
    sta new_x
    txa
    adc p_x + 1
    sta new_x + 1
    bpl !+
    lda #0                        // left edge of the world
    sta new_x
    sta new_x + 1
    sta p_vx
!:  PixelsOf(new_x, box_left)
    PixelsOf(p_y, box_top)
    TileOf(box_top, KEEN_BOX_TOP, t_row)
    TileOf(box_top, KEEN_BOX_BOTTOM, t_end)
    lda p_vx
    bmi move_left
    TileOf(box_left, KEEN_BOX_RIGHT, t_col)
    lda #BLOCK_LEFT
    sta c_tmp + 2
    jsr column_blocked
    beq store_x
    jsr door_blocked              // a door Keen has the keycard for opens
    bcs store_x
    // stop at the tile's left side: left = col * 16 - KEEN_BOX_RIGHT - 1
    lda t_col
    jsr times16
    sec
    lda c_tmp
    sbc #KEEN_BOX_RIGHT + 1
    sta box_left
    lda c_tmp + 1
    sbc #0
    sta box_left + 1
    jmp blocked_x
move_left:
    TileOf(box_left, KEEN_BOX_LEFT, t_col)
    lda #BLOCK_RIGHT
    sta c_tmp + 2
    jsr column_blocked
    beq store_x
    jsr door_blocked
    bcs store_x
    // stop at the tile's right side: left = (col + 1) * 16 - KEEN_BOX_LEFT
    ldx t_col
    inx
    txa
    jsr times16
    sec
    lda c_tmp
    sbc #KEEN_BOX_LEFT
    sta box_left
    lda c_tmp + 1
    sbc #0
    sta box_left + 1
blocked_x:
    lda #0
    sta p_vx
    jsr pixels_to_new_x
store_x:
    lda new_x
    sta p_x
    lda new_x + 1
    sta p_x + 1
    rts

player_move_y:
    // new_y = p_y + vy
    ldx #0
    lda p_vy
    bpl !+
    dex
!:  clc
    adc p_y
    sta new_y
    txa
    adc p_y + 1
    sta new_y + 1
    PixelsOf(p_x, box_left)
    TileOf(box_left, KEEN_BOX_LEFT, t_col)
    TileOf(box_left, KEEN_BOX_RIGHT, t_end)
    lda p_vy
    bpl !+
    jmp move_up
!:  // Falling (or standing): the row holding the pixel just below the new feet.
    PixelsOf(new_y, box_top)
    TileOf(box_top, KEEN_BOX_BOTTOM + 1, t_row)
    // land only if the old feet were above that row
    PixelsOf(p_y, box_bottom)
    TileOf(box_bottom, KEEN_BOX_BOTTOM, c_tmp + 3)
    lda c_tmp + 3
    cmp t_row
    bcs in_air                    // old feet already in or below that row
    lda #ATTR_TOP_MASK
    sta c_tmp + 2
    jsr row_blocked
    beq in_air
    // land: bottom = row * 16 - 1, so top = row * 16 - KEEN_BOX_BOTTOM - 1
    lda t_row
    jsr times16
    sec
    lda c_tmp
    sbc #KEEN_BOX_BOTTOM + 1
    sta box_top
    lda c_tmp + 1
    sbc #0
    sta box_top + 1
    jsr pixels_to_new_y
    lda p_vy                      // landing after a real fall: sound
    cmp #24
    bcc !+
    lda p_pogo
    bne !+
    lda #SND_KEENLANDSND
    jsr sound_play
!:  lda #0
    sta p_vy
    lda #1
    sta p_ground
    jmp store_y
in_air:
    lda #0
    sta p_ground
    jmp store_y
move_up:
    lda #0
    sta p_ground
    PixelsOf(new_y, box_top)
    TileOf(box_top, KEEN_BOX_TOP, t_row)
    PixelsOf(p_y, box_bottom)
    TileOf(box_bottom, KEEN_BOX_TOP, c_tmp + 3)
    lda t_row
    cmp c_tmp + 3
    bcs store_y                   // still in the same row
    lda #BLOCK_BOTTOM
    sta c_tmp + 2
    jsr row_blocked
    beq store_y
    // bump the head: top = (row + 1) * 16 - KEEN_BOX_TOP
    ldx t_row
    inx
    txa
    jsr times16
    sec
    lda c_tmp
    sbc #KEEN_BOX_TOP
    sta box_top
    lda c_tmp + 1
    sbc #0
    sta box_top + 1
    jsr pixels_to_new_y
    lda #0
    sta p_vy
    lda #SND_BUMPHEADSND
    jsr sound_play
store_y:
    lda new_y
    sta p_y
    lda new_y + 1
    sta p_y + 1
    rts

// c_tmp/c_tmp+1 = A * 16
times16:
    sta c_tmp
    lda #0
    asl c_tmp
    rol
    asl c_tmp
    rol
    asl c_tmp
    rol
    asl c_tmp
    rol
    sta c_tmp + 1
    rts

// new_x = box_left * 16
pixels_to_new_x:
    lda box_left
    sta new_x
    lda box_left + 1
    .for (var i = 0; i < 4; i++) {
        asl new_x
        rol
    }
    sta new_x + 1
    rts

// new_y = box_top * 16
pixels_to_new_y:
    lda box_top
    sta new_y
    lda box_top + 1
    .for (var i = 0; i < 4; i++) {
        asl new_y
        rol
    }
    sta new_y + 1
    rts

// Choose Keen's sprite: pogo, jump frames by vertical speed, walk cycle, standing.
player_animate:
    lda p_frozen
    beq !+
    and #16                       // KEENSICLE1/2 while frozen
    lsr
    lsr
    lsr
    lsr
    clc
    adc #SPR_KEENSICLE1
    sta p_sprite
    rts
!:  lda shoot_pose
    beq !+
    lda p_ground
    beq !+
    lda #SPR_KEENSHOOTR
    ldx p_facing
    beq shoot_frame
    lda #SPR_KEENSHOOTL
shoot_frame:
    sta p_sprite
    rts
!:  lda p_pogo
    beq not_pogo
    lda p_ground
    eor #1                        // POGOR1 (compressed) on the ground, POGOR2 in the air
    clc
    adc #SPR_KEENPOGOR1
    ldx p_facing
    beq !+
    clc
    adc #SPR_KEENPOGOL1 - SPR_KEENPOGOR1
!:  sta p_sprite
    rts
not_pogo:
    lda p_ground
    bne on_ground
    // in the air: frames 1-3 rising (fast to slow), 4-6 falling (slow to fast)
    lda p_vy
    bmi rising
    lsr
    lsr
    lsr
    lsr
    lsr                           // vy 0..80 -> 0..2
    clc
    adc #3
    jmp jump_frame
rising:
    cmp #(-48) & $ff
    bcc rising_fast
    cmp #(-16) & $ff
    bcc rising_mid
    lda #2
    jmp jump_frame
rising_fast:
    lda #0
    jmp jump_frame
rising_mid:
    lda #1
jump_frame:
    clc
    adc #SPR_KEENJUMPR1
    ldx p_facing
    beq !+
    clc
    adc #SPR_KEENJUMPL1 - SPR_KEENJUMPR1
!:  sta p_sprite
    rts
on_ground:
    lda p_vx
    bne walking
    lda #0
    sta p_anim
    lda #SPR_KEENWALKR1
    jmp face
walking:
    inc p_anim
    lda p_anim
    cmp #WALK_FRAME_TICKS * 4
    bcc !+
    lda #0
    sta p_anim
!:  ldx #0                        // frame = anim / WALK_FRAME_TICKS
!:  cmp #WALK_FRAME_TICKS
    bcc !+
    sbc #WALK_FRAME_TICKS
    inx
    bne !-
!:  txa
    clc
    adc #SPR_KEENWALKR1
face:
    ldx p_facing
    beq !+
    clc
    adc #SPR_KEENWALKL1 - SPR_KEENWALKR1
!:  sta p_sprite
    rts

// Keep Keen inside the camera margins, and the camera inside the level. Clamping here
// (game logic) rather than only in scroll_update keeps actor activation identical
// whether or not frames are drawn (py65 planning versus the real game).
camera_follow:
    jsr camera_follow_margins
    jmp clamp_camera

camera_follow_margins:
    PixelsOf(p_x, box_left)
    // screen x = px - cam_x
    sec
    lda box_left
    sbc cam_x
    sta c_tmp
    lda box_left + 1
    sbc cam_x + 1
    bmi cam_go_left               // left of the screen
    bne cam_go_right              // >= 256: right of the margin
    lda c_tmp
    cmp #CAM_LEFT_EDGE
    bcc cam_go_left
    cmp #CAM_RIGHT_EDGE + 1
    bcc cam_vertical
cam_go_right:
    sec
    lda box_left
    sbc #CAM_RIGHT_EDGE
    sta cam_x
    lda box_left + 1
    sbc #0
    sta cam_x + 1
    jmp cam_vertical
cam_go_left:
    sec
    lda box_left
    sbc #CAM_LEFT_EDGE
    sta cam_x
    lda box_left + 1
    sbc #0
    sta cam_x + 1
cam_vertical:
    PixelsOf(p_y, box_top)
    sec
    lda box_top
    sbc cam_y
    sta c_tmp
    lda box_top + 1
    sbc cam_y + 1
    bmi cam_go_up
    bne cam_go_down
    lda c_tmp
    cmp #CAM_TOP_EDGE
    bcc cam_go_up
    cmp #CAM_BOTTOM_EDGE + 1
    bcc cam_done
cam_go_down:
    sec
    lda box_top
    sbc #CAM_BOTTOM_EDGE
    sta cam_y
    lda box_top + 1
    sbc #0
    sta cam_y + 1
    rts
cam_go_up:
    sec
    lda box_top
    sbc #CAM_TOP_EDGE
    sta cam_y
    lda box_top + 1
    sbc #0
    sta cam_y + 1
cam_done:
    rts

// Keen's two overlaid sprites (hardware sprites 0 and 1) relative to the shown camera.
// VIC x = 31 + px - shown_x, VIC y = 54 + py - shown_y + piece offset.
player_draw:
    PixelsOf(p_x, box_left)
    PixelsOf(p_y, box_top)
    sec
    lda box_left
    sbc shown_x
    sta c_tmp
    lda box_left + 1
    sbc shown_x + 1
    sta c_tmp + 1
    clc
    lda c_tmp
    adc #31
    sta spr_x
    sta spr_x + 1
    lda c_tmp + 1
    adc #0
    and #1
    sta c_tmp + 1                 // bit 8 of x
    lda spr_x_msb
    and #%11111100
    ldx c_tmp + 1
    beq !+
    ora #%00000011
!:  sta spr_x_msb
    sec
    lda box_top
    sbc shown_y
    clc
    adc #54
    sta c_tmp
    ldx p_sprite
    clc
    adc spr_dy0, x
    sta spr_y
    lda c_tmp
    clc
    adc spr_dy1, x
    sta spr_y + 1
    lda spr_ptr0, x
    sta spr_ptr
    lda spr_ptr1, x
    sta spr_ptr + 1
    lda spr_col0, x
    sta spr_col
    lda spr_col1, x
    sta spr_col + 1
    lda spr_enable                // sprite 0, and sprite 1 for two-piece frames
    and #%11111100
    ora #%00000001
    ldy spr_pieces, x
    cpy #2
    bcc !+
    ora #%00000010
!:  sta spr_enable
    rts
