// Level setup after loading: character set, colours, map row pointers, tile animation.

.segment Code

// Prepare the loaded level in LEVEL_BASE for display.
level_init:
    // Character set to $c800.
    ldx #0
!:
    .for (var p = 0; p < 8; p++) {
        lda LVL_CHARSET + p * $100, x
        sta CHARSET + p * $100, x
    }
    inx
    bne !-

    lda LVL_COLOURS
    sta $d021
    lda LVL_COLOURS + 1
    sta $d022
    lda LVL_COLOURS + 2
    sta $d023
    lda #0
    sta $d020

    lda LVL_WIDTH
    sta level_width
    lda LVL_HEIGHT
    sta level_height

    // Map row pointers for rows 0..height (one extra row: the renderer may read it).
    lda #<LVL_MAP
    sta zp_ptr0
    lda #>LVL_MAP
    sta zp_ptr0 + 1
    ldx #0
!:  lda zp_ptr0
    sta map_row_lo, x
    lda zp_ptr0 + 1
    sta map_row_hi, x
    clc
    lda zp_ptr0
    adc level_width
    sta zp_ptr0
    bcc !+
    inc zp_ptr0 + 1
!:  cpx level_height
    inx
    bcc !--

    // Camera limits: the visible window is 304 x 192 pixels.
    // max_x = width * 16 - 304, max_y = height * 16 - 192
    lda level_width
    sta cam_max_x
    lda #0
    sta cam_max_x + 1
    .for (var i = 0; i < 4; i++) {
        asl cam_max_x
        rol cam_max_x + 1
    }
    sec
    lda cam_max_x
    sbc #<304
    sta cam_max_x
    lda cam_max_x + 1
    sbc #>304
    sta cam_max_x + 1
    lda level_height
    sta cam_max_y
    lda #0
    sta cam_max_y + 1
    .for (var i = 0; i < 4; i++) {
        asl cam_max_y
        rol cam_max_y + 1
    }
    sec
    lda cam_max_y
    sbc #192
    sta cam_max_y
    lda cam_max_y + 1
    sbc #0
    sta cam_max_y + 1

    lda #0
    sta anim_timer
    sta anim_phase
    rts

// Animate tiles: every ANIM_TICKS frames copy the next frame of each animation
// group into its 4 dedicated characters (32 bytes per group).
.const ANIM_TICKS = 8

anim_update:
    dec anim_timer
    bpl anim_done
    lda #ANIM_TICKS - 1
    sta anim_timer
    inc anim_phase
    ldx #0                        // group index * 4
anim_group:
    cpx LVL_ANIM_COUNT_X4
    bcs anim_done
    // destination: CHARSET + first_char * 8
    lda LVL_ANIMS, x
    sta zp_ptr1
    lda #0
    sta zp_ptr1 + 1
    asl zp_ptr1
    rol zp_ptr1 + 1
    asl zp_ptr1
    rol zp_ptr1 + 1
    asl zp_ptr1
    rol zp_ptr1 + 1
    clc
    lda zp_ptr1 + 1
    adc #>CHARSET
    sta zp_ptr1 + 1
    // source: frame data + (phase mod frames) * 32
    lda anim_phase
    ldy LVL_ANIMS + 1, x          // frame count: 2 or 4
    cpy #4
    beq !+
    and #1
    jmp !++
!:  and #3
!:  asl
    asl
    asl
    asl
    asl                           // * 32 (max 96)
    clc
    adc LVL_ANIMS + 2, x
    sta zp_ptr0
    lda LVL_ANIMS + 3, x
    adc #0
    sta zp_ptr0 + 1
    ldy #31
!:  lda (zp_ptr0), y
    sta (zp_ptr1), y
    dey
    bpl !-
    inx
    inx
    inx
    inx
    jmp anim_group
anim_done:
    rts

.label LVL_ANIM_COUNT_X4 = anim_count_x4

// Must be called after level_init; anim_count_x4 = number of groups * 4.
anim_init:
    lda LVL_ANIM_COUNT
    asl
    asl
    sta anim_count_x4
    rts

.segment Vars
level_width:    .byte 0
level_height:   .byte 0
cam_max_x:      .word 0
cam_max_y:      .word 0
anim_timer:     .byte 0
anim_phase:     .byte 0
anim_count_x4:  .byte 0
map_row_lo:     .fill 129, 0
map_row_hi:     .fill 129, 0
