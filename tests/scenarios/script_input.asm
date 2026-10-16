// Scripted joystick for test builds: input_script holds (ticks, joystick bits) pairs,
// ended by 0. Any length (16-bit pointer). When the script ends, script_finished runs
// (defined by the scenario).

.label zp_script = $64            // 2 bytes, test builds only

.segment Code

script_start:
    lda #<input_script
    sta zp_script
    lda #>input_script
    sta zp_script + 1
    lda #0
    sta script_left
    rts

script_input:
    lda script_left
    bne !+
    ldy #0
    lda (zp_script), y
    beq script_end
    sta script_left
    iny
    lda (zp_script), y
    sta script_joy
    clc
    lda zp_script
    adc #2
    sta zp_script
    bcc !+
    inc zp_script + 1
!:  dec script_left
    lda script_joy
    sta joy
    rts
script_end:
    lda #0
    sta joy
    jmp script_finished

.segment Vars
script_left: .byte 0
script_joy:  .byte 0
