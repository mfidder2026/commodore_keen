// Raster IRQ at IRQ_LINE (below the visible rows): buffer swap with colour RAM update,
// fine scroll, sprites, sound, frame counter.

.segment Code

irq_handler:
    pha
    txa
    pha
    tya
    pha
    lda $01
    pha
    lda #$35                      // I/O visible, whatever the main loop banked in
    sta $01
    lda #$ff
    sta $d019
    lda swap_req
    beq !+
    jsr do_swap                   // also writes $d018/$d016/$d011
    jmp !++
!:  lda shown_d016
    sta $d016
    lda shown_d011
    sta $d011
!:  jsr sprites_apply
    inc zp_frame
    jsr irq_hook
    pla
    sta $01
    pla
    tay
    pla
    tax
    pla
    rti

// Extra per-frame work (sound); replaced by game code later.
irq_hook:
    jmp (irq_hook_vector)

irq_nothing:
    rts

.segment Vars
irq_hook_vector: .word 0
