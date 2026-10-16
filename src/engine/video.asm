// PAL/NTSC: detection, and the game running at 50 ticks per second on both.
// PAL: one tick per frame (50 Hz). NTSC: 5 ticks per 6 frames (60 Hz). Physics, timers
// and sound data are all per 50 Hz tick, so nothing else needs NTSC tables.

.segment Code

// Highest raster line of a frame: PAL 311 ($137), NTSC 262 ($106) or 261 (old NTSC).
// Sets is_ntsc. Call with interrupts off.
video_detect:
    lda #0
    sta zp_tmp0                   // highest low byte seen while the raster MSB was set
!:  bit $d011                     // wait for the bottom part of the frame (MSB set)
    bpl !-
!:  lda $d012
    cmp zp_tmp0
    bcc !+
    sta zp_tmp0
!:  bit $d011
    bmi !--
    lda #0
    ldx zp_tmp0
    cpx #$20                      // PAL reaches $37, NTSC only $05/$06
    bcs !+
    lda #1
!:  sta is_ntsc
    rts

// Frames since the last iteration (A, from wait_frame) -> game ticks (A).
frames_to_ticks:
    ldx is_ntsc
    bne !+
    rts                           // PAL: one tick per frame
!:  tax                           // NTSC: ticks = (acc + 5 * frames) / 6
!:  lda tick_acc
    clc
    adc #5
    sta tick_acc
    dex
    bne !-
    lda #0
!:  ldx tick_acc
    cpx #6
    bcc !+
    tax
    lda tick_acc
    sec
    sbc #6
    sta tick_acc
    txa
    clc
    adc #1
    jmp !-
!:  rts

.segment Vars
is_ntsc:  .byte 0
tick_acc: .byte 0
