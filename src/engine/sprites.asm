// Hardware sprite shadow registers, written to the VIC by the raster IRQ.
// The game fills spr_* during the frame; sprites_apply copies them at line IRQ_LINE.

.segment Code

sprites_init:
    lda #$ff
    sta $d01c                     // all sprites multicolour
    lda #0
    sta $d01b                     // sprites in front of characters
    sta $d017
    sta $d01d
    sta spr_enable
    lda #SPRITE_MC0
    sta $d025
    lda #SPRITE_MC1
    sta $d026
    rts

// ~260 cycles.
sprites_apply:
    ldx #7
!:  txa
    asl
    tay
    lda spr_x, x
    sta $d000, y
    lda spr_y, x
    sta $d001, y
    lda spr_col, x
    sta $d027, x
    lda spr_ptr, x
    sta SCREEN_A + $3f8, x
    sta SCREEN_B + $3f8, x
    dex
    bpl !-
    lda spr_x_msb
    sta $d010
    lda spr_enable
    sta $d015
    rts

.segment Vars
spr_x:      .fill 8, 0
spr_x_msb:  .byte 0
spr_y:      .fill 8, 0
spr_ptr:    .fill 8, 0
spr_col:    .fill 8, 0
spr_enable: .byte 0
