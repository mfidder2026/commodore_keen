// Input: joystick in port 2 plus space and RUN/STOP, read directly from CIA1.
// Result in `joy` (1 = pressed), `joy_new` = pressed since the previous tick.
// Test builds (INPUTSCRIPT) replay a scripted table instead.

.const JOY_UP    = %00000001
.const JOY_DOWN  = %00000010
.const JOY_LEFT  = %00000100
.const JOY_RIGHT = %00001000
.const JOY_FIRE  = %00010000
.const KEY_SPACE = %00100000
.const KEY_STOP  = %01000000

.segment Code

input_read:
    lda joy
    sta joy_prev
#if INPUTSCRIPT
    jsr script_input
#else
    lda #$ff
    sta $dc02                     // port A outputs (keyboard rows / joystick 2)
    lda #$00
    sta $dc03                     // port B inputs
    lda #$ff
    sta $dc00                     // no keyboard row selected: port A reads joystick 2
    lda $dc00
    eor #$ff
    and #%00011111
    sta joy
    lda #%01111111                // keyboard row 7: space = bit 4, RUN/STOP = bit 7
    sta $dc00
    lda $dc01
    eor #$ff
    tax
    and #%00010000
    beq !+
    lda joy
    ora #KEY_SPACE
    sta joy
!:  txa
    and #%10000000
    beq !+
    lda joy
    ora #KEY_STOP
    sta joy
!:  lda #$ff
    sta $dc00
#endif
    lda joy_prev
    eor #$ff
    and joy
    sta joy_new
    rts

// Alternative layout (ctrl_alt = 1), in levels only: fire jumps, down + fire shoots,
// pogo only with space. Turns the joystick into the standard bits (up = jump, fire =
// shoot) so the game logic stays the same; down is dropped (no down+fire pogo).
remap_controls:
    lda ctrl_alt
    beq remap_done
    lda joy
    and #JOY_LEFT | JOY_RIGHT | KEY_SPACE | KEY_STOP
    sta zp_tmp0
    lda joy
    and #JOY_FIRE
    beq remap_store
    lda joy
    and #JOY_DOWN
    beq remap_jump
    lda #JOY_FIRE                 // down + fire: shoot
    jmp remap_add
remap_jump:
    lda #JOY_UP                   // fire alone: jump
remap_add:
    ora zp_tmp0
    sta zp_tmp0
remap_store:
    lda zp_tmp0
    sta joy
    lda remap_prev
    eor #$ff
    and joy
    sta joy_new
    lda joy
    sta remap_prev
remap_done:
    rts

.segment Vars
ctrl_alt:   .byte 0               // 0 = up jumps (standard), 1 = fire jumps
remap_prev: .byte 0
.segment Code
