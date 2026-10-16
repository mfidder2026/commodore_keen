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

// One frame of sound, from the raster IRQ. ~60 cycles (NTSC ~110).
// NTSC: every sixth frame is skipped (50 sound steps per second) and the frequency is
// scaled by 985248 / 1022727 = 0.9634 for the faster SID clock.
sound_tick:
    lda is_ntsc
    beq !+
    inc snd_div
    lda snd_div
    cmp #6
    bcc !+
    lda #0
    sta snd_div
    rts
!:  lda snd_active
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
!:  sta snd_freq
    stx snd_freq + 1
    lda is_ntsc
    beq !+
    jsr ntsc_pitch
!:  lda snd_freq
    sta SID
    lda snd_freq + 1
    sta SID + 1
    ora snd_freq                  // SID registers are write-only: test the copy
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

// snd_freq *= 0.9634 (1 - 1/32 - 1/256 - 1/512 = 0.9629)
ntsc_pitch:
    lda snd_freq + 1
    sta snd_tmp + 1
    lda snd_freq
    .for (var i = 0; i < 5; i++) {
        lsr snd_tmp + 1
        ror
    }
    sta snd_tmp                   // v >> 5
    sec
    lda snd_freq
    sbc snd_tmp
    sta snd_freq
    lda snd_freq + 1
    sbc snd_tmp + 1
    sta snd_freq + 1
    lda snd_freq + 1              // v >> 8 (of the reduced value; close enough)
    sta snd_tmp
    lsr
    sta snd_tmp + 1               // v >> 9
    sec
    lda snd_freq
    sbc snd_tmp
    sta snd_freq
    bcs !+
    dec snd_freq + 1
!:  sec
    lda snd_freq
    sbc snd_tmp + 1
    sta snd_freq
    bcs !+
    dec snd_freq + 1
!:  rts

.segment Vars
snd_active:   .byte 0
snd_priority: .byte 0
snd_ptr:      .word 0
snd_save_x:   .byte 0
snd_div:      .byte 0
snd_freq:     .word 0
snd_tmp:      .word 0
