// PC speaker sound effects on SID voice 1 (pulse wave, like the speaker's square wave).
// Data (SOUNDS file at $B000, tools/convert/export.py): per sound a list of SID
// frequencies per 50 Hz frame, 0 = silence, $FFFF = end. A new sound interrupts the
// current one only with an equal or higher priority (as in the original's sound format).

.const SID        = $d400
.const SOUND_WAVE = %01000001     // pulse + gate

.segment Code

sound_init:
    lda #0
    ldx #$18
!:  sta SID, x
    dex
    bpl !-
    sta snd_active
    lda #$00                      // pulse width 50 %
    sta SID + 2
    lda #$08
    sta SID + 3
    lda #$00                      // attack 0, decay 0
    sta SID + 5
    lda #$f0                      // sustain 15, release 0
    sta SID + 6
    lda #$0f                      // volume 15
    sta SID + $18
    rts

// Load the SOUNDS file to $B000.
load_sounds:
    lda #sounds_name_end - sounds_name
    ldx #<sounds_name
    ldy #>sounds_name
    jsr kernal_load
    bcc !+
    jmp load_failed
!:  jmp exo_decrunch_loaded

sounds_name:
    .text "SOUNDS"
sounds_name_end:

// Start sound A (0-based) unless a sound with a higher priority is playing.
// Keeps X and Y.
sound_play:
    stx snd_save_x
    tax
    lda snd_active
    beq !+
    lda SOUND_PRIORITY, x
    cmp snd_priority
    bcc sound_play_done
!:  lda #0
    sta snd_active                // the IRQ must not read a half-set pointer
    lda SOUND_LO, x
    sta snd_ptr
    lda SOUND_HI, x
    sta snd_ptr + 1
    lda SOUND_PRIORITY, x
    sta snd_priority
    lda #1
    sta snd_active
sound_play_done:
    ldx snd_save_x
    rts

// One frame of sound, from the raster IRQ. ~60 cycles.
sound_tick:
    lda snd_active
    beq sound_off
    lda snd_ptr
    sta zp_irq_ptr
    lda snd_ptr + 1
    sta zp_irq_ptr + 1
    ldy #1
    lda (zp_irq_ptr), y
    tax                           // high byte
    dey
    lda (zp_irq_ptr), y           // low byte
    cpx #$ff
    bne !+
    cmp #$ff
    bne !+
    lda #0                        // end of the sound
    sta snd_active
    beq sound_off
!:  sta SID
    stx SID + 1
    ora SID + 1
    beq sound_silent
    lda #SOUND_WAVE
    sta SID + 4
    jmp sound_next
sound_silent:
    lda #SOUND_WAVE & $fe         // gate off
    sta SID + 4
sound_next:
    clc
    lda snd_ptr
    adc #2
    sta snd_ptr
    bcc !+
    inc snd_ptr + 1
!:  rts
sound_off:
    lda #SOUND_WAVE & $fe
    sta SID + 4
    rts

.segment Vars
snd_active:   .byte 0
snd_priority: .byte 0
snd_ptr:      .word 0
snd_save_x:   .byte 0
