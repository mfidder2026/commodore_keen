// M5 scenario: play a level from start to exit with the input found by tools/bot.py
// (build/generated/gen_script.asm). Saves the outcome as STATS and exits VICE with
// code 0 when the exit was reached, 1 otherwise.

#import "gen_script.asm"

.segment Code

level_test:
    jsr game_new
    lda #0
    sta script_pos
    sta script_left
    lda #SCRIPT_LEVEL
    jsr play_level
    sta lt_stats                  // play_result
    ldx #2
!:  lda score, x
    sta lt_stats + 1, x
    dex
    bpl !-
    lda lives
    sta lt_stats + 4
    lda ammo
    sta lt_stats + 5
    lda ship_parts
    sta lt_stats + 6
    lda keycards
    sta lt_stats + 7
    lda #<lt_stats
    sta save_from
    lda #>lt_stats
    sta save_from + 1
    lda #<lt_stats_end
    sta save_to
    lda #>lt_stats_end
    sta save_to + 1
    lda #lt_name_end - lt_name
    ldx #<lt_name
    ldy #>lt_name
    jsr kernal_save
    lda lt_stats
    cmp #RESULT_EXIT
    beq !+
    lda #1
    sta $d7ff
!:  lda #0
    sta $d7ff
    jmp *

lt_name:
    .text "STATS"
lt_name_end:

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
    rts

.segment Vars
script_pos:  .byte 0
script_left: .byte 0
script_joy:  .byte 0
lt_stats:    .fill 8, 0           // result, score (3, BCD), lives, ammo, ship parts, keycards
lt_stats_end:
