// Eight-way scroll engine: double-buffered screen RAM, colour RAM rewritten at the swap.
//
// cam_x/cam_y is the camera the game wants (top-left visible pixel, world coordinates).
// The visible window is 38 x 24 characters (304 x 192 pixels); screen RAM holds 40 x 25.
// One map tile is 2 x 2 characters. Screen column 0 shows world character column front_cx.
//
// Per frame (main loop): scroll_update decides what to show; render_step renders the
// back buffer row by row in the remaining time. The raster IRQ swaps buffers when the
// back buffer is ready and rewrites colour RAM from the new screen, ahead of the beam.

.const ROWS = 25
.const COLS = 40
.const TILES_PER_ROW = 20

.segment Code

// Render the whole front buffer for the current cam_x/cam_y (level start, no timing).
scroll_init:
    jsr clamp_camera
    jsr shown_from_camera
    lda cam_x
    sta prev_cam_x
    lda cam_x + 1
    sta prev_cam_x + 1
    lda cam_y
    sta prev_cam_y
    jsr camera_coarse             // -> want_cx, want_cy
    lda #0
    sta swap_req
    sta back_ready
    sta render_row_no
    lda #1                        // front B for now, so render_row writes screen A
    sta front_buf
    lda want_cx
    sta target_cx
    sta front_cx
    lda want_cx + 1
    sta target_cx + 1
    sta front_cx + 1
    lda want_cy
    sta target_cy
    sta front_cy
!:  jsr render_row
    lda render_row_no
    cmp #ROWS
    bne !-
    lda #0
    sta front_buf
    lda #$ff                      // no back buffer target yet
    sta target_cx + 1
    lda #D018_SCREEN_A
    sta $d018
    jsr colour_screen_a
    jsr shown_from_camera
    lda shown_d016
    sta $d016
    lda shown_d011
    sta $d011
    rts

// Keep cam_x/cam_y inside the level.
clamp_camera:
    lda cam_x + 1
    bpl !+
    lda #0
    sta cam_x
    sta cam_x + 1
!:  lda cam_max_x
    cmp cam_x
    lda cam_max_x + 1
    sbc cam_x + 1
    bcs !+
    lda cam_max_x
    sta cam_x
    lda cam_max_x + 1
    sta cam_x + 1
!:  lda cam_y + 1
    bpl !+
    lda #0
    sta cam_y
    sta cam_y + 1
!:  lda cam_max_y
    cmp cam_y
    lda cam_max_y + 1
    sbc cam_y + 1
    bcs !+
    lda cam_max_y
    sta cam_y
    lda cam_max_y + 1
    sta cam_y + 1
!:  rts

// want_cx = cam_x >> 3 (16 bit), want_cy = cam_y >> 3 (8 bit).
camera_coarse:
    lda cam_x + 1
    sta want_cx + 1
    lda cam_x
    lsr want_cx + 1
    ror
    lsr want_cx + 1
    ror
    lsr want_cx + 1
    ror
    sta want_cx
    lda cam_y + 1
    sta zp_tmp0
    lda cam_y
    lsr zp_tmp0
    ror
    lsr zp_tmp0
    ror
    lsr zp_tmp0
    ror
    sta want_cy
    rts

// Fine scroll registers for shown_x/shown_y: scroll = 7 - (position and 7).
shown_from_camera:
    lda cam_x
    sta shown_x
    lda cam_x + 1
    sta shown_x + 1
    lda cam_y
    sta shown_y
    lda cam_y + 1
    sta shown_y + 1
shown_registers:
    lda shown_x
    and #7
    eor #7
    ora #%00010000                // multicolour on, 38 columns
    sta shown_d016
    lda shown_y
    and #7
    eor #7
    ora #%00010000                // display on, 24 rows
    sta shown_d011
    rts

// Called once per frame by the main loop after the game moved the camera.
scroll_update:
    jsr clamp_camera
    jsr camera_coarse
    lda swap_req
    bne scroll_wait_swap          // a swap is pending for this frame: change nothing
    lda want_cx
    cmp front_cx
    bne need_other
    lda want_cx + 1
    cmp front_cx + 1
    bne need_other
    lda want_cy
    cmp front_cy
    bne need_other
    // Camera inside the front buffer: show it, and prepare the next coarse step.
    jsr shown_from_camera
    jsr predict_target
    jmp scroll_done

need_other:
    lda back_ready
    beq !+
    lda want_cx                   // back buffer ready for exactly this position?
    cmp target_cx
    bne !+
    lda want_cx + 1
    cmp target_cx + 1
    bne !+
    lda want_cy
    cmp target_cy
    bne !+
    jsr shown_from_camera
    lda front_buf                 // the fast colour code must read the incoming buffer
    eor #1
    jsr colour_fast_target
    lda #1
    sta swap_req                  // IRQ swaps and applies the fine scroll together
    jmp scroll_done
!:  jsr start_render_want         // (re)start rendering if not already doing this target
    jsr clamp_shown_to_front      // meanwhile show the nearest position the front allows
scroll_done:
    lda cam_x
    sta prev_cam_x
    lda cam_x + 1
    sta prev_cam_x + 1
    lda cam_y
    sta prev_cam_y
scroll_wait_swap:
    rts

// Predict the next coarse position from the movement direction and the fine offset.
predict_target:
    lda want_cx
    sta pred_cx
    lda want_cx + 1
    sta pred_cx + 1
    lda want_cy
    sta pred_cy
    // horizontal
    lda cam_x
    cmp prev_cam_x
    lda cam_x + 1
    sbc prev_cam_x + 1
    bvc !+
    eor #$80
!:  bmi pred_left
    lda cam_x
    cmp prev_cam_x
    bne pred_right_check
    lda cam_x + 1
    cmp prev_cam_x + 1
    beq pred_vertical
pred_right_check:
    lda cam_x
    and #7
    cmp #4
    bcc pred_vertical
    inc pred_cx
    bne pred_vertical
    inc pred_cx + 1
    jmp pred_vertical
pred_left:
    lda cam_x
    and #7
    cmp #4
    bcs pred_vertical
    lda pred_cx
    bne !+
    dec pred_cx + 1
!:  dec pred_cx
pred_vertical:
    lda cam_y
    cmp prev_cam_y
    beq pred_apply
    bcc pred_up
    lda cam_y
    and #7
    cmp #4
    bcc pred_apply
    inc pred_cy
    jmp pred_apply
pred_up:
    lda cam_y
    and #7
    cmp #4
    bcs pred_apply
    dec pred_cy
pred_apply:
    lda pred_cx
    cmp front_cx
    bne !+
    lda pred_cx + 1
    cmp front_cx + 1
    bne !+
    lda pred_cy
    cmp front_cy
    beq pred_none
!:  lda pred_cx
    sta want2_cx
    lda pred_cx + 1
    sta want2_cx + 1
    lda pred_cy
    sta want2_cy
    jmp start_render_at
pred_none:
    rts

start_render_want:
    lda want_cx
    sta want2_cx
    lda want_cx + 1
    sta want2_cx + 1
    lda want_cy
    sta want2_cy
// Start rendering want2 into the back buffer unless that is already done or under way.
start_render_at:
    lda want2_cx
    cmp target_cx
    bne restart
    lda want2_cx + 1
    cmp target_cx + 1
    bne restart
    lda want2_cy
    cmp target_cy
    bne restart
    lda back_ready
    bne already                   // done
    lda render_row_no
    cmp #ROWS
    bcc already                   // under way
restart:
    lda want2_cx
    sta target_cx
    lda want2_cx + 1
    sta target_cx + 1
    lda want2_cy
    sta target_cy
    lda #0
    sta render_row_no
    sta back_ready
already:
    rts

// Show the camera position closest to cam that the front buffer can display.
clamp_shown_to_front:
    jsr shown_from_camera
    // x range: front_cx*8 .. front_cx*8+7
    lda front_cx
    sta zp_tmp0
    lda front_cx + 1
    asl zp_tmp0
    rol
    asl zp_tmp0
    rol
    asl zp_tmp0
    rol
    sta zp_tmp1                   // zp_tmp0/1 = front_cx * 8
    lda shown_x
    cmp zp_tmp0
    lda shown_x + 1
    sbc zp_tmp1
    bcs !+
    lda zp_tmp0                   // below range
    sta shown_x
    lda zp_tmp1
    sta shown_x + 1
    jmp clamp_y
!:  clc
    lda zp_tmp0
    adc #7
    sta zp_tmp0
    bcc !+
    inc zp_tmp1
!:  lda zp_tmp0
    cmp shown_x
    lda zp_tmp1
    sbc shown_x + 1
    bcs clamp_y
    lda zp_tmp0                   // above range
    sta shown_x
    lda zp_tmp1
    sta shown_x + 1
clamp_y:
    lda front_cy
    sta zp_tmp0
    lda #0
    asl zp_tmp0
    rol
    asl zp_tmp0
    rol
    asl zp_tmp0
    rol
    sta zp_tmp1
    lda shown_y
    cmp zp_tmp0
    lda shown_y + 1
    sbc zp_tmp1
    bcs !+
    lda zp_tmp0
    sta shown_y
    lda zp_tmp1
    sta shown_y + 1
    jmp shown_registers
!:  clc
    lda zp_tmp0
    adc #7
    sta zp_tmp0
    bcc !+
    inc zp_tmp1
!:  lda zp_tmp0
    cmp shown_y
    lda zp_tmp1
    sbc shown_y + 1
    bcs !+
    lda zp_tmp0
    sta shown_y
    lda zp_tmp1
    sta shown_y + 1
!:  jmp shown_registers

// Render rows into the back buffer until it is complete or a new frame has started.
render_step:
    lda zp_frame
    sta render_frame
!:  lda swap_req
    bne render_stop               // back buffer is about to be shown
    lda render_row_no
    cmp #ROWS
    bcs render_stop
    jsr render_row
    lda render_row_no
    cmp #ROWS
    bne !+
    lda #1
    sta back_ready
    jmp render_stop
!:  lda zp_frame
    cmp render_frame
    beq !--
render_stop:
    rts

// Render row render_row_no of the back buffer for target_cx/target_cy. ~800 cycles.
render_row:
    // world character row and tile row
    clc
    lda target_cy
    adc render_row_no
    sta zp_tmp2                   // world char row (max 2*128+24 < 512: carry handled below)
    lda #0
    adc #0
    lsr
    lda zp_tmp2
    ror                           // tile row = char row >> 1 (9-bit safe)
    tax
    lda target_cx + 1
    lsr
    lda target_cx
    ror                           // tile column = cx >> 1
    clc
    adc map_row_lo, x
    sta zp_map
    lda map_row_hi, x
    adc #0
    sta zp_map + 1
    // destination row in the back buffer
    ldx render_row_no
    lda front_buf
    beq !+
    lda row_lo, x                 // front is B: render into A
    sta zp_dst
    lda row_hi_a, x
    sta zp_dst + 1
    jmp fetch
!:  lda row_lo, x
    sta zp_dst
    lda row_hi_b, x
    sta zp_dst + 1
fetch:
    .for (var k = 0; k < TILES_PER_ROW; k++) {
        ldy #k
        lda (zp_map), y
        sta zp_tiles + k
    }
    inc render_row_no
    lda target_cx
    and #1
    sta zp_tmp3
    lda zp_tmp2
    and #1
    asl
    ora zp_tmp3                   // bit 1: bottom half, bit 0: odd column
    tax
    lda row_variant_lo, x
    sta zp_ptr0
    lda row_variant_hi, x
    sta zp_ptr0 + 1
    ldy #0
    jmp (zp_ptr0)

row_variant_lo: .byte <row_top_even, <row_top_odd, <row_bottom_even, <row_bottom_odd
row_variant_hi: .byte >row_top_even, >row_top_odd, >row_bottom_even, >row_bottom_odd

// Even column: 20 tiles, 40 cells. 27 cycles per tile.
.macro RowEven(left, right) {
    .for (var k = 0; k < TILES_PER_ROW; k++) {
        ldx zp_tiles + k
        lda left, x
        sta (zp_dst), y
        iny
        lda right, x
        sta (zp_dst), y
        iny
    }
    rts
}

// Odd column: right half of tile 0, then tiles 1..19: 39 cells.
.macro RowOdd(left, right) {
    ldx zp_tiles
    lda right, x
    sta (zp_dst), y
    iny
    .for (var k = 1; k < TILES_PER_ROW; k++) {
        ldx zp_tiles + k
        lda left, x
        sta (zp_dst), y
        iny
        lda right, x
        sta (zp_dst), y
        iny
    }
    rts
}

row_top_even:    RowEven(TILE_TL, TILE_TR)
row_top_odd:     RowOdd(TILE_TL, TILE_TR)
row_bottom_even: RowEven(TILE_BL, TILE_BR)
row_bottom_odd:  RowOdd(TILE_BL, TILE_BR)

row_lo:   .fill ROWS, <(i * COLS)
row_hi_a: .fill ROWS, >(SCREEN_A + i * COLS)
row_hi_b: .fill ROWS, >(SCREEN_B + i * COLS)

// Colour RAM from screen RAM via the per-character colour table, row by row from the
// top, two cells per loop: about 620 cycles per row, faster than the beam (504 per row
// plus a head start of ~110 lines from the IRQ at line 251).
.macro ColourFromScreen(screen) {
    .for (var r = 0; r < ROWS; r++) {
        ldy #COLS - 2
    !:  ldx screen + r * COLS + 1, y
        lda LVL_CHAR_COLOUR, x
        sta COLOUR_RAM + r * COLS + 1, y
        ldx screen + r * COLS, y
        lda LVL_CHAR_COLOUR, x
        sta COLOUR_RAM + r * COLS, y
        dey
        dey
        bpl !-
    }
    rts
}

colour_screen_a: ColourFromScreen(SCREEN_A)     // level start (not time critical)

// Called from the raster IRQ when swap_req is set.
do_swap:
    lda front_buf
    eor #1
    sta front_buf
    beq !+
    lda #D018_SCREEN_B
    sta $d018
    lda shown_d016
    sta $d016
    lda shown_d011
    sta $d011
    jsr colour_fast
    jmp !++
!:  lda #D018_SCREEN_A
    sta $d018
    lda shown_d016
    sta $d016
    lda shown_d011
    sta $d011
    jsr colour_fast
!:  lda target_cx
    sta front_cx
    lda target_cx + 1
    sta front_cx + 1
    lda target_cy
    sta front_cy
    lda #0
    sta back_ready
    sta swap_req
    lda #ROWS
    sta render_row_no             // nothing rendering; scroll_update starts the next one
    lda #$ff                      // forget the old target so it is rendered again if needed
    sta target_cx + 1
    rts

.segment Vars
cam_x:          .word 0
cam_y:          .word 0
prev_cam_x:     .word 0
prev_cam_y:     .word 0
shown_x:        .word 0
shown_y:        .word 0
shown_d011:     .byte 0
shown_d016:     .byte 0
front_cx:       .word 0
front_cy:       .byte 0
want_cx:        .word 0
want_cy:        .byte 0
want2_cx:       .word 0
want2_cy:       .byte 0
pred_cx:        .word 0
pred_cy:        .byte 0
target_cx:      .word 0
target_cy:      .byte 0
front_buf:      .byte 0
back_ready:     .byte 0
swap_req:       .byte 0
render_row_no:  .byte 0
render_frame:   .byte 0
