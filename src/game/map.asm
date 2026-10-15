// World map (level 80): Keen walks in four directions; fire enters a level, takes the
// ship home or is ignored. Codes in the map's sprite plane:
//   1-16    level entrances           20     the ship (needs all four parts)
//   $8000+n barrier until level n is done
//   38, 41, 46 teleporters. Destinations are a guess (no source): 38 -> 41 -> 46 -> 38.
// Done levels get a MARK sprite on their entrance.

.const MAP_LEVEL      = 80
.const MAP_SPEED      = 24        // 1.5 px per tick (estimate)
.const MAP_BOX_LEFT   = 3         // only Keen's feet collide on the map: forgiving
.const MAP_BOX_RIGHT  = 8         // in narrow passages (the full sprite is 16 x 16)
.const MAP_BOX_TOP    = 8
.const MAP_BOX_BOTTOM = 15
.const MAX_MAP_SPOTS  = 48        // the map has 41 (entrances can be 2x2 tiles)
.const MAX_BARRIERS   = 8
.const SHIP_CODE      = 20
.const ALL_PARTS      = %00001111

.const MAP_RESULT_LEVEL = 1       // map_run results
.const MAP_RESULT_SHIP  = 2
.const MAP_RESULT_QUIT  = 3

.segment Code

// Load the map and place Keen (start position on a new game, else where he left it).
map_enter:
    lda #MAP_LEVEL
    sta current_level
    jsr load_level
    jsr level_init
    jsr anim_init
    jsr map_collect_spots
    lda map_keen_x + 1
    ora map_keen_y + 1
    bne !+
    jsr player_init               // first time: the start code (255)
    lda LVL_START_X
    sta p_x + 1
    lda #0
    sta p_x
    lda LVL_START_Y
    sta p_y + 1
    lda #0
    sta p_y
    jmp !++
!:  lda map_keen_x
    sta p_x
    lda map_keen_x + 1
    sta p_x + 1
    lda map_keen_y
    sta p_y
    lda map_keen_y + 1
    sta p_y + 1
!:  lda #1
    sta map_mode
    sta teleport_lock             // standing on something at the start: no teleport yet
    lda #0
    sta p_facing
    sta map_dir
    sta spr_enable
    jsr camera_center
    jsr scroll_init
    rts

// Entrances, teleporters, ship and barriers from the map's actor list.
map_collect_spots:
    lda #0
    sta spot_count
    sta barrier_count
    lda #<LVL_ACTORS
    sta zp_ptr0
    lda #>LVL_ACTORS
    sta zp_ptr0 + 1
    ldx LVL_ACTOR_COUNT
    beq spots_done
spot_loop:
    ldy #1
    lda (zp_ptr0), y
    bmi barrier                   // $80xx: barrier for level xx
    bne spot_next
    dey
    lda (zp_ptr0), y              // code
    ldy spot_count
    cpy #MAX_MAP_SPOTS
    bcs spot_next
    sta spot_code, y
    sty zp_tmp0
    ldy #2
    lda (zp_ptr0), y
    ldy zp_tmp0
    sta spot_x, y
    ldy #3
    lda (zp_ptr0), y
    ldy zp_tmp0
    sta spot_y, y
    inc spot_count
    jmp spot_next
barrier:
    ldy barrier_count
    cpy #MAX_BARRIERS
    bcs spot_next
    sty zp_tmp0
    ldy #0
    lda (zp_ptr0), y
    ldy zp_tmp0
    sta barrier_level, y
    ldy #2
    lda (zp_ptr0), y
    ldy zp_tmp0
    sta barrier_x, y
    ldy #3
    lda (zp_ptr0), y
    ldy zp_tmp0
    sta barrier_y, y
    inc barrier_count
spot_next:
    clc
    lda zp_ptr0
    adc #4
    sta zp_ptr0
    bcc !+
    inc zp_ptr0 + 1
!:  dex
    bne spot_loop
spots_done:
    rts

// C set if level A is done.
level_is_done:
    sec
    sbc #1
    pha
    lsr
    lsr
    lsr
    tax
    pla
    and #7
    tay
    lda levels_done, x
    and bit_mask, y
    beq !+
    sec
    rts
!:  clc
    rts

// Mark level A as done.
mark_level_done:
    sec
    sbc #1
    pha
    lsr
    lsr
    lsr
    tax
    pla
    and #7
    tay
    lda levels_done, x
    ora bit_mask, y
    sta levels_done, x
    rts

bit_mask: .byte 1, 2, 4, 8, 16, 32, 64, 128

// Called by tile_attr_at in map mode: A = attribute; returns it, or solid when
// (t_col, t_row) holds a barrier whose level is not done yet. Keeps X and Y.
barrier_attr:
    sta zp_tmp2
    stx zp_tmp3
    tya
    pha
    ldy barrier_count
    beq barrier_open
!:  dey
    lda barrier_x, y
    cmp t_col
    bne barrier_next
    lda barrier_y, y
    cmp t_row
    bne barrier_next
    lda barrier_level, y
    jsr level_is_done
    bcs barrier_next
    pla
    tay
    ldx zp_tmp3
    lda #ATTR_TOP_MASK & 1 | BLOCK_RIGHT | BLOCK_BOTTOM | BLOCK_LEFT
    rts
barrier_next:
    tya
    bne !-
barrier_open:
    pla
    tay
    ldx zp_tmp3
    lda zp_tmp2
    rts

// One tick on the map. Returns map_result (0 = keep walking).
map_tick:
    jsr input_read
    lda #0
    sta map_result
    lda joy_new
    and #KEY_STOP
    beq !+
    lda #MAP_RESULT_QUIT          // RUN/STOP: status screen
    sta map_result
    rts
!:  jsr map_move
    jsr camera_follow
    jsr map_spots
    rts

// Move Keen with the joystick (diagonals allowed), with tile collision.
map_move:
    lda p_x
    sta o_x
    lda p_x + 1
    sta o_x + 1
    lda p_y
    sta o_y
    lda p_y + 1
    sta o_y + 1
    lda #MAP_BOX_LEFT
    sta o_box_l
    lda #MAP_BOX_RIGHT
    sta o_box_r
    lda #MAP_BOX_TOP
    sta o_box_t
    lda #MAP_BOX_BOTTOM
    sta o_box_b
    jsr box16_from_box
    lda #0
    sta o_vx
    sta o_vy
    sta map_moving
    lda joy
    and #JOY_LEFT
    beq !+
    lda #(-MAP_SPEED) & $ff
    sta o_vx
    lda #2
    sta map_dir
!:  lda joy
    and #JOY_RIGHT
    beq !+
    lda #MAP_SPEED
    sta o_vx
    lda #0
    sta map_dir
!:  lda o_vx
    beq !+
    inc map_moving
    jsr actor_walk
!:  lda joy
    and #JOY_UP
    beq !+
    lda #(-MAP_SPEED) & $ff
    sta o_vy
    lda #3
    sta map_dir
!:  lda joy
    and #JOY_DOWN
    beq !+
    lda #MAP_SPEED
    sta o_vy
    lda #1
    sta map_dir
!:  lda o_vy
    beq !+
    inc map_moving
    jsr actor_walk_y
!:  lda o_x
    sta p_x
    lda o_x + 1
    sta p_x + 1
    lda o_y
    sta p_y
    lda o_y + 1
    sta p_y + 1
    // sprite: MAPKEEN R/D/L/U 1-4, animated while moving
    lda map_moving
    beq !+
    inc p_anim
!:  lda p_anim
    lsr
    lsr
    lsr
    and #3
    sta zp_tmp0
    lda map_dir
    asl
    asl
    clc
    adc zp_tmp0
    adc #SPR_MAPKEENR1
    sta p_sprite
    rts

// Vertical move by o_vy with tile collision (like actor_walk). C set if blocked.
actor_walk_y:
    ldx #0
    lda o_vy
    bpl !+
    dex
!:  clc
    adc o_y
    sta new_y
    txa
    adc o_y + 1
    sta new_y + 1
    bpl !+
    sec
    rts
!:  PixelsOf(o_x, box_left)
    PixelsOf(new_y, box_top)
    lda o_box_l
    jsr tile_of_left
    sta t_col
    lda o_box_r
    jsr tile_of_left
    sta t_end
    lda o_vy
    bmi !+
    lda o_box_b
    jsr tile_of_top
    sta t_row
    lda #ATTR_TOP_MASK
    jmp walk_y_check
!:  lda o_box_t
    jsr tile_of_top
    sta t_row
    lda #BLOCK_BOTTOM
walk_y_check:
    sta c_tmp + 2
    jsr row_blocked
    beq !+
    sec
    rts
!:  lda new_y
    sta o_y
    lda new_y + 1
    sta o_y + 1
    clc
    rts

// Entrances, teleporters and the ship under Keen's centre.
map_spots:
    // centre tile of Keen
    PixelsOf(p_x, box_left)
    PixelsOf(p_y, box_top)
    lda #6
    jsr tile_of_left
    sta map_tx
    lda #12
    jsr tile_of_top
    sta map_ty
    ldy spot_count
    beq no_spot
!:  dey
    lda spot_x, y
    cmp map_tx
    bne spot_other
    lda spot_y, y
    cmp map_ty
    beq on_spot
spot_other:
    tya
    bne !-
no_spot:
    lda #0
    sta teleport_lock
    rts
on_spot:
    lda spot_code, y
    cmp #38
    beq teleport
    cmp #41
    beq teleport
    cmp #46
    beq teleport
    sta map_spot_code
    lda joy_new
    and #JOY_FIRE
    beq spot_done
    lda map_spot_code
    cmp #SHIP_CODE
    bne !+
    lda #MAP_RESULT_SHIP
    sta map_result
    rts
!:  cmp #17
    bcs spot_done
    jsr level_is_done             // done levels cannot be entered again
    bcs spot_done
    lda #MAP_RESULT_LEVEL
    sta map_result
spot_done:
    rts

teleport:
    ldx teleport_lock
    bne spot_done                 // arrived here by teleport: walk off first
    ldx #41
    cmp #38
    beq !+
    ldx #46
    cmp #41
    beq !+
    ldx #38
!:  stx zp_tmp0
    // find the destination spot
    ldy spot_count
!:  dey
    bmi spot_done
    lda spot_code, y
    cmp zp_tmp0
    bne !-
    lda spot_x, y
    sta p_x + 1
    lda #0
    sta p_x
    lda spot_y, y
    sta p_y + 1
    lda #0
    sta p_y
    lda #1
    sta teleport_lock
    rts

// MARK sprites on the entrances of done levels that are on screen (sprites 2-7).
map_draw_marks:
    lda #2
    sta next_hw
    lda spr_enable
    and #%00000011
    sta spr_enable
    lda spr_x_msb
    and #%00000011
    sta spr_x_msb
    jsr camera_tile_range
    ldy spot_count
    beq marks_done
mark_loop:
    dey
    sty zp_tmp3
    lda spot_code, y
    beq mark_next
    cmp #17
    bcs mark_next
    jsr level_is_done
    bcc mark_next
    ldy zp_tmp3
    lda spot_x, y
    cmp view_tx0
    bcc mark_next
    cmp view_tx1
    bcs mark_next
    lda spot_y, y
    cmp view_ty0
    bcc mark_next
    cmp view_ty1
    bcs mark_next
    // use the actor drawing routine with a temporary actor slot 47
    ldx #MAX_ACTORS - 1
    lda spot_x, y
    sta act_x_hi, x
    lda #0
    sta act_x_lo, x
    lda spot_y, y
    sta act_y_hi, x
    lda #0
    sta act_y_lo, x
    lda #SPR_MARK
    sta act_sprite, x
    stx cur_actor
    jsr draw_actor
    lda next_hw
    cmp #8
    bcs marks_done
mark_next:
    ldy zp_tmp3
    bne mark_loop
marks_done:
    rts

.segment Vars
map_mode:      .byte 0
map_result:    .byte 0
map_dir:       .byte 0            // 0 right, 1 down, 2 left, 3 up
map_moving:    .byte 0
map_tx:        .byte 0
map_ty:        .byte 0
map_spot_code: .byte 0
teleport_lock: .byte 0
map_keen_x:    .word 0
map_keen_y:    .word 0
spot_count:    .byte 0
spot_code:     .fill MAX_MAP_SPOTS, 0
spot_x:        .fill MAX_MAP_SPOTS, 0
spot_y:        .fill MAX_MAP_SPOTS, 0
barrier_count: .byte 0
barrier_level: .fill MAX_BARRIERS, 0
barrier_x:     .fill MAX_BARRIERS, 0
barrier_y:     .fill MAX_BARRIERS, 0
