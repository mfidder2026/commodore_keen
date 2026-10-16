// M4 scenario: replay scripted joystick input in level 1 and record Keen's position
// every tick. The recording is saved as STATS; test_player.py compares it with the
// movement measured in the original game.
//
// Script: wait 20 ticks, walk right 86 ticks, stand 74 ticks, jump (hold up) 70 ticks,
// stand 30 ticks. The jump happens near x = 258, where the measurement in the original
// was taken (open above, a platform with its top at y = 240 to land on).

.const RECORD = $9400              // free in level 1 (its map ends at $75d8)              // 4 bytes per tick: x lo/hi, y lo/hi (1/16 px)
.const RECORD_TICKS = 280

.segment Code

player_test:
    lda #0
    sta script_pos
    sta script_left
    sta record_count
    sta record_count + 1
    lda #1
    jmp play_level                 // never returns: record_tick ends the test

// Script entries: ticks, joystick bits. 0 ticks ends the script.
input_script:
    .byte 20, 0
    .byte 86, JOY_RIGHT
    .byte 74, 0
    .byte 70, JOY_UP
    .byte 30, 0
    .byte 0

script_input:
    lda script_left
    bne !+
    ldx script_pos
    lda input_script, x
    beq script_end
    sta script_left
    lda input_script + 1, x
    sta script_joy
    inx
    inx
    stx script_pos
!:  dec script_left
    lda script_joy
    sta joy
    rts
script_end:
    lda #0
    sta joy
    rts

record_tick:
    lda record_count
    asl
    sta zp_ptr1
    lda record_count + 1
    rol
    sta zp_ptr1 + 1
    asl zp_ptr1
    rol zp_ptr1 + 1               // * 4
    clc
    lda zp_ptr1 + 1
    adc #>RECORD
    sta zp_ptr1 + 1
    ldy #0
    lda p_x
    sta (zp_ptr1), y
    iny
    lda p_x + 1
    sta (zp_ptr1), y
    iny
    lda p_y
    sta (zp_ptr1), y
    iny
    lda p_y + 1
    sta (zp_ptr1), y
    inc record_count
    bne !+
    inc record_count + 1
!:  lda record_count
    cmp #<RECORD_TICKS
    bne !+
    lda record_count + 1
    cmp #>RECORD_TICKS
    bne !+
    jmp record_done
!:  rts

record_done:
    lda #<RECORD
    sta save_from
    lda #>RECORD
    sta save_from + 1
    lda #<(RECORD + RECORD_TICKS * 4)
    sta save_to
    lda #>(RECORD + RECORD_TICKS * 4)
    sta save_to + 1
    lda #record_name_end - record_name
    ldx #<record_name
    ldy #>record_name
    jsr kernal_save
    lda #0
    sta $d7ff
    jmp *

record_name:
    .text "STATS"
record_name_end:

.segment Vars
script_pos:   .byte 0
script_left:  .byte 0
script_joy:   .byte 0
record_count: .word 0
