// Cycle measurement with CIA2 timer A (free-running from $ffff, counting down).
// Only used by test builds and for docs/budget.md; costs nothing otherwise.

.segment Code

timer_init:
    lda #$ff
    sta $dd04
    sta $dd05
    lda #%00010001                // force load, start, continuous
    sta $dd0e
    rts

// Reads the timer into timer_now (16 bit). ~20 cycles.
.macro TimerRead(dest) {
    lda $dd05
    sta dest + 1
    lda $dd04
    sta dest
    lda $dd05                     // high byte changed meanwhile: read again
    cmp dest + 1
    beq !+
    sta dest + 1
    lda $dd04
    sta dest
!:
}

// max = max(max, start - end) for a down-counting timer.
.macro TimerMax(start, end, max) {
    sec
    lda start
    sbc end
    sta zp_tmp0
    lda start + 1
    sbc end + 1
    sta zp_tmp1
    lda max
    cmp zp_tmp0
    lda max + 1
    sbc zp_tmp1
    bcs !+
    lda zp_tmp0
    sta max
    lda zp_tmp1
    sta max + 1
!:
}
