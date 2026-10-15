// Enemies, Keen's raygun shots and enemy shots.
//
// Actor codes in the level's sprite plane (Keen 1): 1 Yorp, 2 Garg, 3 Vorticon,
// 4 Butler robot, 5 Tank robot, 6-9 ice cannons, 10 Vorticon commander (level 16).
// BEHAVIOUR AND SPEEDS ARE ESTIMATES from playing the original, not yet checked against
// the reconstructed source (docs/actors.md). Positions in 1/16 px like Keen.

.const MAX_ACTORS   = 48
.const T_NONE       = 0
.const T_YORP       = 1
.const T_GARG       = 2
.const T_VORT       = 3
.const T_BUTLER     = 4
.const T_TANK       = 5
.const T_ICECANNON  = 6           // codes 6-9 -> one type, direction in act_dir
.const T_COMMANDER  = 10
.const T_KEENSHOT   = 11
.const T_TANKSHOT   = 12
.const T_ICESHOT    = 13
.const T_SPLASH     = 14
.const T_COUNT      = 15

// states
.const S_WALK       = 0
.const S_LOOK       = 1           // Yorp looking around / Garg before charging
.const S_STUNNED    = 2
.const S_DEAD       = 3
.const S_CHARGE     = 4

// speeds (1/16 px per tick) - estimates
.const YORP_SPEED   = 12
.const GARG_SPEED   = 16
.const GARG_CHARGE  = 48
.const VORT_SPEED   = 24
.const VORT_JUMP    = 64
.const BUTLER_SPEED = 32
.const TANK_SPEED   = 16
.const SHOT_SPEED   = 112         // Keen's raygun: 7 px per tick
.const TANKSHOT_SPEED = 80
.const ICE_SPEED    = 40
.const VORT_HP      = 4
.const COMMANDER_HP = 10
.const TANK_FIRE_TICKS = 100
.const ICE_FIRE_TICKS  = 120
.const STUN_TICKS   = 150
.const FREEZE_TICKS = 100

.const ACTIVE_MARGIN = 96         // px outside the view in which actors still move

.segment Code

// Build the actor table from the level's actor list.
actors_init:
    ldx #MAX_ACTORS - 1
    lda #T_NONE
!:  sta act_type, x
    dex
    bpl !-
    lda #0
    sta shot_cooldown
    sta shoot_pose
    sta p_frozen
    sta draw_rotate
    lda #$a5
    sta rng
    lda LVL_ACTOR_COUNT
    sta zp_tmp3
    jeq actors_init_done
    lda #<LVL_ACTORS
    sta zp_ptr0
    lda #>LVL_ACTORS
    sta zp_ptr0 + 1
    ldx #0                        // actor slot
actor_from_list:
    ldy #1
    lda (zp_ptr0), y              // code hi: only codes < 256
    bne skip_entry
    dey
    lda (zp_ptr0), y
    beq skip_entry
    cmp #T_COMMANDER + 1
    bcs skip_entry
    cmp #T_ICECANNON
    bcc !+
    cmp #T_COMMANDER
    beq !+
    sec
    sbc #T_ICECANNON              // ice cannon direction 0-3
    sta act_dir, x
    lda #T_ICECANNON
!:  sta act_type, x
    ldy #2                        // x tile -> x * 256 (1/16 px)
    lda (zp_ptr0), y
    sta act_x_hi, x
    lda #0
    sta act_x_lo, x
    ldy #3
    lda (zp_ptr0), y
    sta act_y_hi, x
    lda #0
    sta act_y_lo, x
    sta act_vx, x
    sta act_vy, x
    sta act_state, x
    sta act_timer, x
    sta act_ground, x
    lda act_type, x
    cmp #T_ICECANNON
    beq !+
    lda #1                        // start walking left (towards Keen at the level start?)
    sta act_dir, x
!:  lda #VORT_HP
    ldy act_type, x
    cpy #T_COMMANDER
    bne !+
    lda #COMMANDER_HP
!:  sta act_hp, x
    // The sprite top starts at the marker tile's top; gravity puts the actor on the
    // floor (in the levels the floor is 2 rows below the marker, 1 for the Butler).
    inx
    cpx #MAX_ACTORS - 8           // keep slots for shots
    bcs actors_init_done
skip_entry:
    clc
    lda zp_ptr0
    adc #4
    sta zp_ptr0
    bcc !+
    inc zp_ptr0 + 1
!:  dec zp_tmp3
    bne actor_from_list
actors_init_done:
    rts

// One tick for all actors near the camera.
actors_update:
    lda shot_cooldown
    beq !+
    dec shot_cooldown
!:  jsr camera_tile_range
    ldx #MAX_ACTORS - 1
actor_loop:
    lda act_type, x
    beq actor_next
    stx cur_actor
    jsr actor_near_camera
    bcc actor_next_x
    jsr actor_load
    ldx cur_actor
    lda act_type, x
    asl
    tay
    lda update_table, y
    sta zp_ptr1
    lda update_table + 1, y
    sta zp_ptr1 + 1
    jsr call_ptr1
    ldx cur_actor
    lda act_type, x
    beq actor_next_x              // removed itself
    jsr actor_store
    jsr actor_touch_keen
actor_next_x:
    ldx cur_actor
actor_next:
    dex
    bpl actor_loop
    rts

call_ptr1:
    jmp (zp_ptr1)

update_table:
    .word actor_nothing, yorp_update, garg_update, vort_update, butler_update
    .word tank_update, icecannon_update, actor_nothing, actor_nothing, actor_nothing
    .word vort_update, keenshot_update, enemyshot_update, enemyshot_update, splash_update

actor_nothing:
    rts

// Tile range in which actors are active (camera view plus ACTIVE_TILES) and visible.
// Computed once per tick; act_x_hi / act_y_hi are tile coordinates already
// (position in 1/16 px divided by 256 = pixels / 16).
.const ACTIVE_TILES = 6

camera_tile_range:
    lda cam_x + 1                 // cam tile x = cam_x >> 4
    sta zp_tmp1
    lda cam_x
    .for (var i = 0; i < 4; i++) {
        lsr zp_tmp1
        ror
    }
    sta view_tx0
    clc
    adc #19                       // 304 px = 19 tiles
    sta view_tx1
    lda view_tx0
    sec
    sbc #ACTIVE_TILES + 2         // actors are up to 2 tiles wide to the left of their x
    bcs !+
    lda #0
!:  sta act_tx0
    lda view_tx1
    clc
    adc #ACTIVE_TILES
    bcc !+
    lda #$ff
!:  sta act_tx1
    lda cam_y + 1
    sta zp_tmp1
    lda cam_y
    .for (var i = 0; i < 4; i++) {
        lsr zp_tmp1
        ror
    }
    sta view_ty0
    clc
    adc #12                       // 192 px = 12 tiles
    sta view_ty1
    lda view_ty0
    sec
    sbc #ACTIVE_TILES + 2
    bcs !+
    lda #0
!:  sta act_ty0
    lda view_ty1
    clc
    adc #ACTIVE_TILES
    bcc !+
    lda #$ff
!:  sta act_ty1
    rts

// C set if actor X lies in the active tile range. Shots are always active.
actor_near_camera:
    lda act_type, x
    cmp #T_KEENSHOT
    bcs near
    lda act_x_hi, x
    cmp act_tx0
    bcc far
    cmp act_tx1
    bcs far
    lda act_y_hi, x
    cmp act_ty0
    bcc far
    cmp act_ty1
    bcs far
near:
    sec
    rts
far:
    clc
    rts

// Copy actor cur_actor into the zero page work area (o_*), and back.
actor_load:
    lda act_x_lo, x
    sta o_x
    lda act_x_hi, x
    sta o_x + 1
    lda act_y_lo, x
    sta o_y
    lda act_y_hi, x
    sta o_y + 1
    lda act_vx, x
    sta o_vx
    lda act_vy, x
    sta o_vy
    lda act_ground, x
    sta o_ground
    lda act_type, x
    tay
    lda box_left_tab, y
    sta o_box_l
    lda box_right_tab, y
    sta o_box_r
    lda box_top_tab, y
    sta o_box_t
    lda box_bottom_tab, y
    sta o_box_b
    lda box_l16_lo, y
    sta o_bl16
    lda box_l16_hi, y
    sta o_bl16 + 1
    lda box_r16_lo, y
    sta o_br16
    lda box_r16_hi, y
    sta o_br16 + 1
    lda box_t16_lo, y
    sta o_bt16
    lda box_t16_hi, y
    sta o_bt16 + 1
    lda box_b16_lo, y
    sta o_bb16
    lda box_b16_hi, y
    sta o_bb16 + 1
    rts

actor_store:
    ldx cur_actor
    lda o_x
    sta act_x_lo, x
    lda o_x + 1
    sta act_x_hi, x
    lda o_y
    sta act_y_lo, x
    lda o_y + 1
    sta act_y_hi, x
    lda o_vx
    sta act_vx, x
    lda o_vy
    sta act_vy, x
    lda o_ground
    sta act_ground, x
    rts

// Collision boxes per type (pixels inside the sprite), from EGAHEAD hitboxes.
//                         none yorp garg vort butl tank ice  -  -  -  cmdr shot tshot ice splash
.var box_l = List().add(0,   4,   4,   2,   3,   0,  0,  0, 0, 0,  2,   2,   2,   2,   0)
.var box_r = List().add(0,  11,  19,  21,  12,  15,  0,  0, 0, 0, 21,  13,  13,  13,   0)
.var box_t = List().add(0,   4,   4,   1,   3,   0,  0,  0, 0, 0,  1,   2,   2,   2,   0)
.var box_b = List().add(0,  23,  31,  31,  15,  23,  0,  0, 0, 0, 31,   5,   5,  13,   0)
box_left_tab:   .fill box_l.size(), box_l.get(i)
box_right_tab:  .fill box_r.size(), box_r.get(i)
box_top_tab:    .fill box_t.size(), box_t.get(i)
box_bottom_tab: .fill box_b.size(), box_b.get(i)
// the same in 1/16 px; the bottom one pixel lower (the pixel below the feet)
box_l16_lo:     .fill box_l.size(), <(box_l.get(i) * 16)
box_l16_hi:     .fill box_l.size(), >(box_l.get(i) * 16)
box_r16_lo:     .fill box_r.size(), <(box_r.get(i) * 16)
box_r16_hi:     .fill box_r.size(), >(box_r.get(i) * 16)
box_t16_lo:     .fill box_t.size(), <(box_t.get(i) * 16)
box_t16_hi:     .fill box_t.size(), >(box_t.get(i) * 16)
box_b16_lo:     .fill box_b.size(), <((box_b.get(i) + 1) * 16)
box_b16_hi:     .fill box_b.size(), >((box_b.get(i) + 1) * 16)

// o_bl16 .. o_bb16 from o_box_* (for callers that set the box themselves, the map).
box16_from_box:
    ldx #3
!:  lda o_box_l, x
    sta zp_tmp0
    lda #0
    .for (var i = 0; i < 4; i++) {
        asl zp_tmp0
        rol
    }
    sta zp_tmp1
    txa
    asl
    tay
    lda zp_tmp0
    sta o_bl16, y
    lda zp_tmp1
    sta o_bl16 + 1, y
    dex
    bpl !-
    clc                           // bottom: one pixel lower
    lda o_bb16
    adc #16
    sta o_bb16
    bcc !+
    inc o_bb16 + 1
!:  rts

// ---------------------------------------------------------------------------------
// Movement with tile collision for the current actor (o_*).
// actor_walk: horizontal move by o_vx; C set if a wall or the map edge stopped it.
// Tile numbers are the high bytes of positions in 1/16 px.
actor_walk:
    lda o_vx
    bne !+
    clc
    rts
!:  ldx #0
    lda o_vx
    bpl !+
    dex
!:  clc
    adc o_x
    sta new_x
    txa
    adc o_x + 1
    sta new_x + 1
    bpl !+
    sec                           // left edge of the world
    rts
!:  clc                           // rows of the box
    lda o_y
    adc o_bt16
    lda o_y + 1
    adc o_bt16 + 1
    sta t_row
    sec                           // bottom row: (y - 16 + (bottom + 1) * 16) >> 8
    lda o_y
    sbc #16
    tax
    lda o_y + 1
    sbc #0
    tay
    clc
    txa
    adc o_bb16
    tya
    adc o_bb16 + 1
    sta t_end
    lda o_vx
    bmi !+
    clc                           // moving right: column of the right edge
    lda new_x
    adc o_br16
    lda new_x + 1
    adc o_br16 + 1
    sta t_col
    lda #BLOCK_LEFT
    jmp walk_check
!:  clc                           // moving left: column of the left edge
    lda new_x
    adc o_bl16
    lda new_x + 1
    adc o_bl16 + 1
    sta t_col
    lda #BLOCK_RIGHT
walk_check:
    sta c_tmp + 2
    jsr column_blocked
    beq !+
    sec
    rts
!:  lda new_x
    sta o_x
    lda new_x + 1
    sta o_x + 1
    clc
    rts

// A = (box_left + A) >> 4 / (box_top + A) >> 4
tile_of_left:
    clc
    adc box_left
    sta c_tmp
    lda box_left + 1
    adc #0
    jmp shift4
tile_of_top:
    clc
    adc box_top
    sta c_tmp
    lda box_top + 1
    adc #0
shift4:
    lsr
    ror c_tmp
    lsr
    ror c_tmp
    lsr
    ror c_tmp
    lsr
    ror c_tmp
    lda c_tmp
    rts

// Gravity and vertical movement: lands on tiles with a top side.
actor_fall:
    lda o_vy
    clc
    adc #GRAVITY
    bmi !+
    cmp #MAX_FALL
    bcc !+
    lda #MAX_FALL
!:  sta o_vy
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
    lda #0
    sta o_ground
    lda o_vy
    bmi fall_store                // rising: no ceiling check for actors
    // probe row: the pixel below the new feet; old feet row: the pixel of the old feet
    clc
    lda new_y
    adc o_bb16
    lda new_y + 1
    adc o_bb16 + 1
    sta t_row
    sec
    lda o_y
    sbc #16                       // old feet pixel = probe position of the old y - 1 px
    tax
    lda o_y + 1
    sbc #0
    tay
    clc
    txa
    adc o_bb16
    tya
    adc o_bb16 + 1
    cmp t_row
    bcs fall_store                // the feet were already in that row
    clc                           // columns of the box
    lda o_x
    adc o_bl16
    lda o_x + 1
    adc o_bl16 + 1
    sta t_col
    clc
    lda o_x
    adc o_br16
    lda o_x + 1
    adc o_br16 + 1
    sta t_end
    lda #ATTR_TOP_MASK
    sta c_tmp + 2
    jsr row_blocked
    beq fall_store
    // land: y = row * 256 - (bottom + 1) * 16, so the feet end just above the row
    sec
    lda #0
    sbc o_bb16
    sta new_y
    lda t_row
    sbc o_bb16 + 1
    sta new_y + 1
    lda #0
    sta o_vy
    lda #1
    sta o_ground
fall_store:
    lda new_y
    sta o_y
    lda new_y + 1
    sta o_y + 1
    rts

// Walk in act_dir at speed A; turn around at walls and, if C was set on entry, at ledges.
walker:
    pha
    ldx cur_actor
    lda act_dir, x
    beq !+
    pla
    eor #$ff
    clc
    adc #1
    jmp !++
!:  pla
!:  sta o_vx
    lda o_ground
    beq !+                        // in the air: keep going
    jsr actor_walk
    bcc !+
    ldx cur_actor                 // hit a wall: turn around
    lda act_dir, x
    eor #1
    sta act_dir, x
!:  jmp actor_fall

// Face Keen: act_dir = 1 if Keen is to the left.
face_keen:
    ldx cur_actor
    lda p_x
    cmp o_x
    lda p_x + 1
    sbc o_x + 1
    lda #0
    bcs !+
    lda #1
!:  sta act_dir, x
    rts

// Simple pseudo-random generator (8 bit, xorshift-like), deterministic.
random:
    lda rng
    asl
    bcc !+
    eor #$1d
!:  sta rng
    rts

// ---------------------------------------------------------------------------------
yorp_update:
    ldx cur_actor
    lda act_state, x
    cmp #S_DEAD
    bne !+
    lda #SPR_YORPCORPSE2
    sta act_sprite, x
    jmp actor_fall
!:  cmp #S_STUNNED
    bne !+
    dec act_timer, x
    bne yorp_stunned_frame
    lda #S_WALK
    sta act_state, x
yorp_stunned_frame:
    lda act_timer, x
    and #8
    lsr
    lsr
    lsr
    clc
    adc #SPR_YORPSTUN1
    sta act_sprite, x
    lda #0
    sta o_vx
    jmp actor_fall
!:  cmp #S_LOOK
    bne yorp_walk
    dec act_timer, x
    bne !+
    lda #S_WALK
    sta act_state, x
    jsr face_keen
!:  ldx cur_actor
    lda act_timer, x
    lsr
    lsr
    lsr
    and #3
    clc
    adc #SPR_YORPSTAND1
    sta act_sprite, x
    lda #0
    sta o_vx
    jmp actor_fall
yorp_walk:
    jsr random
    cmp #3                        // now and then: stop and look around
    bcs !+
    ldx cur_actor
    lda #S_LOOK
    sta act_state, x
    lda #64
    sta act_timer, x
    jmp actor_fall
!:  cmp #8                        // now and then: hop
    bcs !+
    lda o_ground
    beq !+
    lda #(-40) & $ff
    sta o_vy
!:  ldx cur_actor
    inc act_timer, x
    lda act_timer, x
    lsr
    lsr
    lsr
    and #1
    ldy act_dir, x
    beq !+
    clc
    adc #SPR_YORPLEFT1 - SPR_YORPRIGHT1
!:  clc
    adc #SPR_YORPRIGHT1
    sta act_sprite, x
    lda #YORP_SPEED
    jmp walker

garg_update:
    ldx cur_actor
    lda act_state, x
    cmp #S_DEAD
    bne !+
    lda #SPR_GARGCORPSE2
    sta act_sprite, x
    jmp actor_fall
!:  cmp #S_LOOK
    bne garg_walking
    dec act_timer, x
    bne !+
    lda #S_CHARGE                 // looked around: charge towards Keen
    sta act_state, x
    jsr face_keen
!:  ldx cur_actor
    lda act_timer, x
    lsr
    lsr
    lsr
    and #3
    clc
    adc #SPR_GARGSTAND1
    sta act_sprite, x
    lda #0
    sta o_vx
    jmp actor_fall
garg_walking:
    // Keen on (about) the same height: look, then charge
    lda act_state, x
    cmp #S_CHARGE
    beq garg_move
    lda p_y + 1
    sec
    sbc o_y + 1
    clc
    adc #1
    cmp #3                        // within one tile vertically
    bcs garg_move
    jsr random
    cmp #24
    bcs garg_move
    ldx cur_actor
    lda #S_LOOK
    sta act_state, x
    lda #32
    sta act_timer, x
    jmp actor_fall
garg_move:
    ldx cur_actor
    inc act_timer, x
    lda act_timer, x
    lsr
    lsr
    lsr
    and #1
    ldy act_dir, x
    beq !+
    clc
    adc #SPR_GARGLEFT1 - SPR_GARGRIGHT1
!:  clc
    adc #SPR_GARGRIGHT1
    sta act_sprite, x
    lda act_state, x
    cmp #S_CHARGE
    bne !+
    lda o_ground                  // a charge ends at a wall
    beq garg_charge
    lda act_dir, x
    sta zp_tmp2
    lda #GARG_CHARGE
    jsr walker
    ldx cur_actor
    lda act_dir, x
    cmp zp_tmp2
    beq garg_end
    lda #S_WALK
    sta act_state, x
garg_end:
    rts
garg_charge:
    lda #GARG_CHARGE
    jmp walker
!:  lda #GARG_SPEED
    jmp walker

vort_update:
    ldx cur_actor
    lda act_state, x
    cmp #S_DEAD
    bne vort_alive
    // dying: frames VORTDIE1-6, then stays down
    lda act_timer, x
    cmp #6 * 6
    bcs !+
    inc act_timer, x
!:  lsr
    ldy #0
!:  cmp #3
    bcc !+
    sbc #3
    iny
    bne !-
!:  cpy #6
    bcc !+
    ldy #5
!:  tya
    clc
    adc #SPR_VORTDIE1
    sta act_sprite, x
    jmp actor_fall
vort_alive:
    lda o_ground
    beq vort_air
    jsr random
    cmp #10                       // jump now and then, towards Keen
    bcs vort_walk
    jsr face_keen
    lda #(-VORT_JUMP) & $ff
    sta o_vy
vort_air:
    ldx cur_actor
    lda #SPR_VORTJUMPR
    ldy act_dir, x
    beq !+
    lda #SPR_VORTJUMPL
!:  sta act_sprite, x
    lda act_dir, x
    beq !+
    lda #(-VORT_SPEED) & $ff
    jmp !++
!:  lda #VORT_SPEED
!:  sta o_vx
    jsr actor_walk
    jmp actor_fall
vort_walk:
    ldx cur_actor
    inc act_timer, x
    lda act_timer, x
    lsr
    lsr
    lsr
    and #3
    ldy act_dir, x
    bne !+
    clc
    adc #SPR_VORTRIGHT1 - SPR_VORTLEFT1
!:  clc
    adc #SPR_VORTLEFT1
    sta act_sprite, x
    lda #VORT_SPEED
    jmp walker

butler_update:
    ldx cur_actor
    inc act_timer, x
    lda act_timer, x
    lsr
    lsr
    and #3
    ldy act_dir, x
    bne !+
    clc
    adc #SPR_CANRIGHT1 - SPR_CANLEFT1
!:  clc
    adc #SPR_CANLEFT1
    sta act_sprite, x
    lda #BUTLER_SPEED
    jmp walker

tank_update:
    ldx cur_actor
    inc act_timer, x
    lda act_timer, x
    cmp #TANK_FIRE_TICKS
    bcc !+
    lda #0
    sta act_timer, x
    jsr face_keen
    jsr tank_fire
    ldx cur_actor
!:  lda act_timer, x
    lsr
    lsr
    and #3
    ldy act_dir, x
    bne !+
    clc
    adc #SPR_TANKRIGHT1 - SPR_TANKLEFT1
!:  clc
    adc #SPR_TANKLEFT1
    sta act_sprite, x
    lda #TANK_SPEED
    jmp walker

tank_fire:
    jsr free_slot
    bcc !+
    lda #T_TANKSHOT
    sta act_type, y
    ldx cur_actor
    lda act_dir, x
    sta act_dir, y
    lda o_x
    sta act_x_lo, y
    lda o_x + 1
    sta act_x_hi, y
    clc                           // 8 px down from the tank's top
    lda o_y
    adc #128
    sta act_y_lo, y
    lda o_y + 1
    adc #0
    sta act_y_hi, y
    lda act_dir, y
    beq tank_shot_right
    lda #(-TANKSHOT_SPEED) & $ff
    jmp tank_shot_vx
tank_shot_right:
    lda #TANKSHOT_SPEED
tank_shot_vx:
    sta act_vx, y
    lda #0
    sta act_vy, y
    lda #SPR_TANKSHOT
    sta act_sprite, y
!:  rts

// Ice cannons are invisible; they launch ice in their direction (act_dir 0-3).
icecannon_update:
    ldx cur_actor
    lda #$ff
    sta act_sprite, x             // nothing to draw
    inc act_timer, x
    lda act_timer, x
    cmp #ICE_FIRE_TICKS
    bcc !+
    lda #0
    sta act_timer, x
    jsr free_slot
    bcc !+
    lda #T_ICESHOT
    sta act_type, y
    lda o_x
    sta act_x_lo, y
    lda o_x + 1
    sta act_x_hi, y
    lda o_y
    sta act_y_lo, y
    lda o_y + 1
    sta act_y_hi, y
    ldx cur_actor
    lda act_dir, x
    tax
    lda ice_vx, x
    sta act_vx, y
    lda ice_vy, x
    sta act_vy, y
    lda #SPR_ICESHOT
    sta act_sprite, y
!:  rts

// directions 0-3: up-right, up-left, down-right, down-left
ice_vx: .byte ICE_SPEED, (-ICE_SPEED) & $ff, ICE_SPEED, (-ICE_SPEED) & $ff
ice_vy: .byte (-ICE_SPEED) & $ff, (-ICE_SPEED) & $ff, ICE_SPEED, ICE_SPEED

// Y = a free actor slot (C set), or C clear if none.
free_slot:
    ldy #MAX_ACTORS - 1
!:  lda act_type, y
    beq !+
    dey
    bpl !-
    clc
    rts
!:  lda #0
    sta act_state, y
    sta act_timer, y
    sta act_ground, y
    sec
    rts

// Shots fly straight; a blocking tile turns them into a splash.
keenshot_update:
enemyshot_update:
    // move x
    ldx #0
    lda o_vx
    bpl !+
    dex
!:  clc
    adc o_x
    sta o_x
    txa
    adc o_x + 1
    sta o_x + 1
    // move y (ice)
    ldx #0
    lda o_vy
    bpl !+
    dex
!:  clc
    adc o_y
    sta o_y
    txa
    adc o_y + 1
    sta o_y + 1
    // a solid tile at the shot's centre ends it
    PixelsOf(o_x, box_left)
    PixelsOf(o_y, box_top)
    lda #8
    jsr tile_of_left
    sta t_col
    lda #4
    jsr tile_of_top
    sta t_row
    jsr tile_attr_at
    and #BLOCK_LEFT | BLOCK_RIGHT
    beq !+
    jmp make_splash
!:  // gone off the camera view: remove
    ldx cur_actor
    jsr actor_near_camera
    bcs !+
    ldx cur_actor
    lda #T_NONE
    sta act_type, x
    rts
!:  ldx cur_actor
    lda act_type, x
    cmp #T_KEENSHOT
    bne !+
    jmp keenshot_hits
!:  rts

make_splash:
    ldx cur_actor
    lda #T_SPLASH
    sta act_type, x
    lda #8
    sta act_timer, x
    lda #SPR_SHOTSPLASHR
    ldy o_vx
    bpl !+
    lda #SPR_SHOTSPLASHL
!:  sta act_sprite, x
    rts

splash_update:
    ldx cur_actor
    dec act_timer, x
    bne !+
    lda #T_NONE
    sta act_type, x
!:  rts

// Keen's shot against enemies.
keenshot_hits:
    ldy #MAX_ACTORS - 1
shot_target:
    lda act_type, y
    beq shot_next
    cmp #T_ICECANNON
    beq shot_next
    cmp #T_KEENSHOT
    bcs shot_next
    lda act_state, y
    cmp #S_DEAD
    beq shot_next
    sty other_actor
    jsr shot_overlaps
    ldy other_actor
    bcc shot_next
    // hit
    lda act_type, y
    cmp #T_BUTLER
    beq absorbed
    cmp #T_TANK
    beq absorbed
    cmp #T_VORT
    beq vort_hit
    cmp #T_COMMANDER
    beq vort_hit
kill_it:
    lda #S_DEAD
    sta act_state, y
    lda #0
    sta act_timer, y
    lda #SPR_YORPCORPSE1
    ldx act_type, y
    cpx #T_GARG
    bne !+
    lda #SPR_GARGCORPSE1
!:  sta act_sprite, y
absorbed:
    jmp make_splash
vort_hit:
    lda act_hp, y
    sec
    sbc #1
    sta act_hp, y
    bne absorbed
    jmp kill_it
shot_next:
    dey
    bpl shot_target
    rts

// C set if the current shot (o_x/o_y) overlaps actor other_actor's box.
shot_overlaps:
    ldy other_actor
    lda act_x_hi, y
    sta zp_tmp1
    lda act_x_lo, y
    sta zp_tmp0
    lda act_y_hi, y
    sta zp_tmp3
    lda act_y_lo, y
    sta zp_tmp2
    // shot centre in px
    PixelsOf(o_x, box_left)
    PixelsOf(o_y, box_top)
    clc
    lda box_left
    adc #8
    sta box_left
    bcc !+
    inc box_left + 1
!:  clc
    lda box_top
    adc #4
    sta box_top
    bcc !+
    inc box_top + 1
!:  // target box
    lda act_type, y
    tax
    lda zp_tmp1
    sta box_right + 1
    lda zp_tmp0
    .for (var i = 0; i < 4; i++) {
        lsr box_right + 1
        ror
    }
    sta box_right                 // target px
    lda zp_tmp3
    sta box_bottom + 1
    lda zp_tmp2
    .for (var i = 0; i < 4; i++) {
        lsr box_bottom + 1
        ror
    }
    sta box_bottom                // target py
    jmp point_in_box

// C set if point (box_left, box_top) lies in the box of type X at (box_right, box_bottom).
point_in_box:
    // dx = point x - target x must be in [box_left_tab, box_right_tab]
    sec
    lda box_left
    sbc box_right
    sta zp_tmp0
    lda box_left + 1
    sbc box_right + 1
    bne outside
    lda zp_tmp0
    cmp box_left_tab, x
    bcc outside
    lda box_right_tab, x
    cmp zp_tmp0
    bcc outside
    sec
    lda box_top
    sbc box_bottom
    sta zp_tmp0
    lda box_top + 1
    sbc box_bottom + 1
    bne outside
    lda zp_tmp0
    cmp box_top_tab, x
    bcc outside
    lda box_bottom_tab, x
    cmp zp_tmp0
    bcc outside
    sec
    rts
outside:
    clc
    rts

// Keen's raygun: fire spawns a shot if there is ammo and the gun has cooled down.
player_fire:
    lda joy_new
    and #JOY_FIRE
    beq fire_done
    lda joy
    and #JOY_DOWN                 // down + fire is the pogo
    bne fire_done
    lda shot_cooldown
    bne fire_done
    lda #10
    sta shoot_pose
    lda ammo
    beq fire_done                 // empty: click (sound in M8)
    jsr free_slot
    bcc fire_done
    dec ammo
    lda #8
    sta shot_cooldown
    lda #T_KEENSHOT
    sta act_type, y
    lda #SPR_KEENSHOT
    sta act_sprite, y
    lda p_facing
    sta act_dir, y
    beq !+
    lda #(-SHOT_SPEED) & $ff
    jmp !++
!:  lda #SHOT_SPEED
!:  sta act_vx, y
    lda #0
    sta act_vy, y
    lda p_x
    sta act_x_lo, y
    lda p_x + 1
    sta act_x_hi, y
    clc                           // shot at gun height: 9 px below Keen's top
    lda p_y
    adc #9 * 16
    sta act_y_lo, y
    lda p_y + 1
    adc #0
    sta act_y_hi, y
fire_done:
    lda shoot_pose
    beq !+
    dec shoot_pose
!:  rts

// ---------------------------------------------------------------------------------
// Contact between the current actor (o_*) and Keen.
actor_touch_keen:
    ldx cur_actor
    lda act_type, x
    cmp #T_KEENSHOT
    beq touch_none
    cmp #T_SPLASH
    beq touch_none
    cmp #T_ICECANNON
    beq touch_none
    lda act_state, x
    cmp #S_DEAD
    beq touch_none
    // cheap pre-check: within 2 tiles horizontally and 3 vertically of Keen
    lda o_x + 1
    sec
    sbc p_x + 1
    clc
    adc #2
    cmp #5
    bcs touch_none
    lda o_y + 1
    sec
    sbc p_y + 1
    clc
    adc #3
    cmp #7
    bcs touch_none
    jsr boxes_overlap
    bcc touch_none
    ldx cur_actor
    lda act_type, x
    cmp #T_YORP
    beq touch_yorp
    cmp #T_BUTLER
    beq touch_push
    cmp #T_ICESHOT
    beq touch_ice
    // Garg, Vorticon, commander, tank, tank shot: deadly
#if !GODMODE
    lda #RESULT_DIED
    sta play_result
#endif
touch_none:
    rts
touch_yorp:
    lda act_state, x
    cmp #S_STUNNED
    beq touch_none                // a stunned Yorp is harmless
    // Keen falling onto the Yorp's head stuns it
    lda p_vy
    bmi touch_push
    beq touch_push
    lda p_y + 1                   // Keen's top above the Yorp's top - 8 px?
    cmp o_y + 1
    bcs touch_push
    lda #S_STUNNED
    sta act_state, x
    lda #STUN_TICKS
    sta act_timer, x
    lda #(-48) & $ff              // Keen bounces off
    sta p_vy
    rts
touch_push:
    // push Keen away from the actor
    lda p_x
    cmp o_x
    lda p_x + 1
    sbc o_x + 1
    bcc !+
    lda #40
    jmp !++
!:  lda #(-40) & $ff
!:  sta p_vx
    rts
touch_ice:
    lda #FREEZE_TICKS
    sta p_frozen
    lda #T_NONE
    sta act_type, x
    rts

// C set if Keen's box overlaps the current actor's box (o_*, o_box_*).
boxes_overlap:
    PixelsOf(p_x, box_left)       // Keen px
    PixelsOf(p_y, box_top)
    PixelsOf(o_x, box_right)      // actor px
    PixelsOf(o_y, box_bottom)
    // keen.left + 4 <= actor.left + box_r  and  actor.left + box_l <= keen.left + 11
    clc
    lda box_right
    adc o_box_r
    sta zp_tmp0
    lda box_right + 1
    adc #0
    sta zp_tmp1                   // actor right
    clc
    lda box_left
    adc #KEEN_BOX_LEFT
    sta zp_tmp2
    lda box_left + 1
    adc #0
    sta zp_tmp3                   // keen left
    lda zp_tmp0
    cmp zp_tmp2
    lda zp_tmp1
    sbc zp_tmp3
    bcc no_overlap
    clc
    lda box_left
    adc #KEEN_BOX_RIGHT
    sta zp_tmp0
    lda box_left + 1
    adc #0
    sta zp_tmp1                   // keen right
    clc
    lda box_right
    adc o_box_l
    sta zp_tmp2
    lda box_right + 1
    adc #0
    sta zp_tmp3                   // actor left
    lda zp_tmp0
    cmp zp_tmp2
    lda zp_tmp1
    sbc zp_tmp3
    bcc no_overlap
    // vertical
    clc
    lda box_bottom
    adc o_box_b
    sta zp_tmp0
    lda box_bottom + 1
    adc #0
    sta zp_tmp1                   // actor bottom
    clc
    lda box_top
    adc #KEEN_BOX_TOP
    sta zp_tmp2
    lda box_top + 1
    adc #0
    sta zp_tmp3                   // keen top
    lda zp_tmp0
    cmp zp_tmp2
    lda zp_tmp1
    sbc zp_tmp3
    bcc no_overlap
    clc
    lda box_top
    adc #KEEN_BOX_BOTTOM
    sta zp_tmp0
    lda box_top + 1
    adc #0
    sta zp_tmp1                   // keen bottom
    clc
    lda box_bottom
    adc o_box_t
    sta zp_tmp2
    lda box_bottom + 1
    adc #0
    sta zp_tmp3                   // actor top
    lda zp_tmp0
    cmp zp_tmp2
    lda zp_tmp1
    sbc zp_tmp3
    bcc no_overlap
    sec
    rts
no_overlap:
    clc
    rts

// ---------------------------------------------------------------------------------
// Draw visible actors into hardware sprites 2-7. When there are more pieces than
// sprites, the starting actor rotates every frame (flicker instead of invisibility).
actors_draw:
    lda #2
    sta next_hw
    lda spr_enable
    and #%00000011
    sta spr_enable
    lda spr_x_msb
    and #%00000011
    sta spr_x_msb
    inc draw_rotate
    lda draw_rotate
    and #63
!:  cmp #MAX_ACTORS
    bcc !+
    sbc #MAX_ACTORS
    jmp !-
!:  tax
    lda #MAX_ACTORS
    sta draw_count                // actors left to look at
draw_loop:
    stx cur_actor
    lda act_type, x
    beq draw_next
    lda act_sprite, x
    cmp #$ff
    beq draw_next
    lda act_x_hi, x               // visible tile range with a margin of 2 tiles
    clc
    adc #2
    cmp view_tx0
    bcc draw_next
    sbc #3
    cmp view_tx1
    bcs draw_next
    lda act_y_hi, x
    clc
    adc #2
    cmp view_ty0
    bcc draw_next
    sbc #3
    cmp view_ty1
    bcs draw_next
    jsr draw_actor
    lda next_hw
    cmp #8
    bcs draw_done
draw_next:
    ldx cur_actor
    inx
    cpx #MAX_ACTORS
    bcc !+
    ldx #0
!:  dec draw_count
    bne draw_loop
draw_done:
    rts

// Pieces of actor cur_actor's sprite, if on screen.
draw_actor:
    // screen x = px - shown_x + 31 (9 bit), skip if outside 0..343
    lda act_x_hi, x
    sta zp_tmp1
    lda act_x_lo, x
    .for (var i = 0; i < 4; i++) {
        lsr zp_tmp1
        ror
    }
    sec
    sbc shown_x
    sta zp_tmp0
    lda zp_tmp1
    sbc shown_x + 1
    sta zp_tmp1
    clc
    lda zp_tmp0
    adc #31
    sta zp_tmp0
    lda zp_tmp1
    adc #0
    sta zp_tmp1
    jmi off_screen                // left of the screen
    cmp #2
    jcs off_screen
    cmp #1
    bne !+
    lda zp_tmp0
    cmp #344 - 256
    jcs off_screen
!:  // screen y = py - shown_y + 54 (must be 30..250)
    lda act_y_hi, x
    sta draw_yhi
    lda act_y_lo, x
    .for (var i = 0; i < 4; i++) {
        lsr draw_yhi
        ror
    }
    sec
    sbc shown_y
    sta zp_tmp2
    lda draw_yhi
    sbc shown_y + 1
    bne off_screen_y
    lda zp_tmp2
    cmp #200
    bcs off_screen_y
    clc
    adc #54 - 32                  // allow 32 px above the view for tall sprites
    sta zp_tmp2
    lda act_sprite, x
    tay
    lda #0
    sta piece
draw_piece:
    ldx next_hw
    cpx #8
    bcs piece_done
    lda zp_tmp0
    sta spr_x, x
    lda zp_tmp1
    beq !+
    lda spr_x_msb
    ora bit_of_sprite, x
    sta spr_x_msb
!:  lda piece
    bne second
    lda zp_tmp2
    clc
    adc spr_dy0, y
    adc #32
    sta spr_y, x
    lda spr_ptr0, y
    sta spr_ptr, x
    lda spr_col0, y
    sta spr_col, x
    jmp piece_on
second:
    lda zp_tmp2
    clc
    adc spr_dy1, y
    adc #32
    sta spr_y, x
    lda spr_ptr1, y
    sta spr_ptr, x
    lda spr_col1, y
    sta spr_col, x
piece_on:
    lda spr_enable
    ora bit_of_sprite, x
    sta spr_enable
    inc next_hw
    inc piece
    lda piece
    cmp spr_pieces, y
    bcc draw_piece
piece_done:
off_screen:
off_screen_y:
    rts

bit_of_sprite: .byte 1, 2, 4, 8, 16, 32, 64, 128

.segment Vars
act_type:    .fill MAX_ACTORS, 0
act_state:   .fill MAX_ACTORS, 0
act_x_lo:    .fill MAX_ACTORS, 0
act_x_hi:    .fill MAX_ACTORS, 0
act_y_lo:    .fill MAX_ACTORS, 0
act_y_hi:    .fill MAX_ACTORS, 0
act_vx:      .fill MAX_ACTORS, 0
act_vy:      .fill MAX_ACTORS, 0
act_timer:   .fill MAX_ACTORS, 0
act_sprite:  .fill MAX_ACTORS, 0
act_hp:      .fill MAX_ACTORS, 0
act_dir:     .fill MAX_ACTORS, 0
act_ground:  .fill MAX_ACTORS, 0
cur_actor:   .byte 0
other_actor: .byte 0
next_hw:     .byte 0
piece:       .byte 0
draw_rotate: .byte 0
draw_yhi:    .byte 0
draw_count:  .byte 0
view_tx0:    .byte 0
view_tx1:    .byte 0
view_ty0:    .byte 0
view_ty1:    .byte 0
act_tx0:     .byte 0
act_tx1:     .byte 0
act_ty0:     .byte 0
act_ty1:     .byte 0
shot_cooldown: .byte 0
shoot_pose:  .byte 0
rng:         .byte 0
