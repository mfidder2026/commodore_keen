// Changing a map tile while the level is shown (items, doors).
// The map is updated, the visible front buffer and colour RAM are patched directly,
// and so is the back buffer when it holds (or is being rendered for) a position.

.segment Code

// Replace tile (mt_col, mt_row) with C64 tile A.
set_map_tile:
    sta mt_tile
    php
    sei                           // no buffer swap halfway through
    ldx mt_row
    lda map_row_lo, x
    sta zp_ptr0
    lda map_row_hi, x
    sta zp_ptr0 + 1
    ldy mt_col
    lda mt_tile
    sta (zp_ptr0), y

    // front buffer + colour RAM
    lda front_cx
    sta mt_cx
    lda front_cx + 1
    sta mt_cx + 1
    lda front_cy
    sta mt_cy
    lda front_buf
    sta mt_buf
    lda #1
    sta mt_colour
    jsr patch_buffer
    // back buffer, if it has a target
    lda target_cx + 1
    cmp #$ff
    beq !+
    lda target_cx
    sta mt_cx
    lda target_cx + 1
    sta mt_cx + 1
    lda target_cy
    sta mt_cy
    lda front_buf
    eor #1
    sta mt_buf
    lda #0
    sta mt_colour
    jsr patch_buffer
!:  plp
    rts

// Write the 4 characters of mt_tile into buffer mt_buf showing (mt_cx, mt_cy).
patch_buffer:
    lda #0
    sta mt_quad
patch_quad:
    // column = mt_col * 2 + (quad & 1) - mt_cx  (16 bit)
    lda mt_col
    asl
    sta zp_tmp0
    lda #0
    rol
    sta zp_tmp1
    lda mt_quad
    and #1
    clc
    adc zp_tmp0
    sta zp_tmp0
    bcc !+
    inc zp_tmp1
!:  sec
    lda zp_tmp0
    sbc mt_cx
    sta zp_tmp0
    lda zp_tmp1
    sbc mt_cx + 1
    bne patch_next                // outside (negative or >= 256)
    lda zp_tmp0
    cmp #COLS
    bcs patch_next
    // row = mt_row * 2 + (quad >> 1) - mt_cy
    lda mt_quad
    lsr
    sta zp_tmp1
    lda mt_row
    asl
    clc
    adc zp_tmp1
    sec
    sbc mt_cy
    bcc patch_next                // above the buffer
    cmp #ROWS
    bcs patch_next
    tax
    // screen address = base + row_lo[row] + column
    lda row_lo, x
    clc
    adc zp_tmp0
    sta zp_ptr1
    lda mt_buf
    beq !+
    lda row_hi_b, x
    jmp !++
!:  lda row_hi_a, x
!:  adc #0
    sta zp_ptr1 + 1
    // character of this quadrant
    ldx mt_tile
    lda mt_quad
    beq q0
    cmp #1
    beq q1
    cmp #2
    beq q2
    lda TILE_BR, x
    jmp have_char
q0: lda TILE_TL, x
    jmp have_char
q1: lda TILE_TR, x
    jmp have_char
q2: lda TILE_BL, x
have_char:
    ldy #0
    sta (zp_ptr1), y
    ldx mt_colour
    beq patch_next
    tax
    lda LVL_CHAR_COLOUR, x
    pha
    lda zp_ptr1 + 1               // colour RAM = $d800 + (address - screen base)
    and #%00000011
    ora #>COLOUR_RAM
    sta zp_ptr1 + 1
    pla
    sta (zp_ptr1), y
patch_next:
    inc mt_quad
    lda mt_quad
    cmp #4
    beq !+
    jmp patch_quad
!:  rts

.segment Vars
mt_col:    .byte 0
mt_row:    .byte 0
mt_tile:   .byte 0
mt_cx:     .word 0
mt_cy:     .byte 0
mt_buf:    .byte 0
mt_colour: .byte 0
mt_quad:   .byte 0
