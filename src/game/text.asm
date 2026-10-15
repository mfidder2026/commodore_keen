// Text screens with Keen's font (64 hires characters at $d800, ASCII 32-95):
// title, status, game over, the end. Screen A is used; the level display is rebuilt
// afterwards with scroll_init.

.const TEXT_D016 = %00001000      // 40 columns, no fine scroll, multicolour off
.const TEXT_D011 = %00011011      // 25 rows, display on, YSCROLL 3

.segment Code

// Clear screen A and switch to the font.
text_begin:
    jsr wait_frame
    lda #0
    sta spr_enable
    sta swap_req
    lda #TEXT_D016
    sta shown_d016
    lda #TEXT_D011
    sta shown_d011
    jsr wait_frame                // IRQ has applied the text mode registers
    ldx #0
!:  lda #0                        // screen code 0 = space
    sta SCREEN_A, x
    sta SCREEN_A + $100, x
    sta SCREEN_A + $200, x
    sta SCREEN_A + $2e8, x
    lda #1
    sta COLOUR_RAM, x
    sta COLOUR_RAM + $100, x
    sta COLOUR_RAM + $200, x
    sta COLOUR_RAM + $2e8, x
    inx
    bne !-
    lda #0
    sta $d020
    sta $d021
    lda #D018_FONT_A
    sta $d018
    lda #0
    sta front_buf
    rts

// Back to the level display (charset, colours, both buffers rebuilt for cam_x/cam_y).
text_end:
    lda LVL_COLOURS
    sta $d021
    jsr scroll_init
    jmp wait_frame

// Print the zero-terminated ASCII text at (text_x, text_y) in colour text_colour.
// In: X/Y = text address lo/hi.
print:
    stx zp_ptr0
    sty zp_ptr0 + 1
    ldx text_y
    lda row_lo, x
    clc
    adc text_x
    sta zp_ptr1
    lda row_hi_a, x
    adc #0
    sta zp_ptr1 + 1
    ldy #0
!:  lda (zp_ptr0), y
    beq print_done
    sec
    sbc #32                       // ASCII 32-95 -> font characters 0-63
    sta (zp_ptr1), y
    lda zp_ptr1 + 1               // colour RAM: same offset from $d800
    pha
    and #%00000011
    ora #>COLOUR_RAM
    sta zp_ptr1 + 1
    lda text_colour
    sta (zp_ptr1), y
    pla
    sta zp_ptr1 + 1
    iny
    bne !-
print_done:
    rts

// Print a line centred on row A. X/Y = text.
print_centred:
    sta text_y
    stx zp_ptr0
    sty zp_ptr0 + 1
    ldy #0
!:  lda (zp_ptr0), y
    beq !+
    iny
    bne !-
!:  sty zp_tmp0
    lda #40
    sec
    sbc zp_tmp0
    lsr
    sta text_x
    ldx zp_ptr0
    ldy zp_ptr0 + 1
    jmp print

// Print the 6-digit BCD score at (text_x, text_y).
print_score:
    ldx #2
    ldy #0
!:  lda score, x
    lsr
    lsr
    lsr
    lsr
    ora #'0'
    sta number_text, y
    iny
    lda score, x
    and #$0f
    ora #'0'
    sta number_text, y
    iny
    dex
    bpl !-
    lda #0
    sta number_text, y
    ldx #<number_text
    ldy #>number_text
    jmp print

// Print the byte A (0-255) in decimal at (text_x, text_y).
print_number:
    ldx #0
    ldy #'0' - 1
!:  iny                           // hundreds
    sec
    sbc #100
    bcs !-
    adc #100
    sty number_text
    ldy #'0' - 1
!:  iny                           // tens
    sec
    sbc #10
    bcs !-
    adc #10
    sty number_text + 1
    ora #'0'
    sta number_text + 2
    lda #0
    sta number_text + 3
    // skip leading zeros
    ldx #<number_text
    lda number_text
    cmp #'0'
    bne !+
    inx
    lda number_text + 1
    cmp #'0'
    bne !+
    inx
!:  ldy #>number_text
    jmp print

// Wait for fire (pressed and released) or space.
wait_fire:
!:  jsr wait_frame
    jsr input_read
    lda joy
    and #JOY_FIRE | KEY_SPACE
    bne !-                        // first release
!:  jsr wait_frame
    jsr input_read
    lda joy_new
    and #JOY_FIRE | KEY_SPACE
    beq !-
    rts

.encoding "ascii"
number_text: .fill 8, 0

.segment Vars
text_x:      .byte 0
text_y:      .byte 0
text_colour: .byte 0
