// Level scenario (M5, M6): play a level with a scripted joystick
// (build/generated/gen_script.asm: SCRIPT_LEVEL and input_script).
// When the script runs out, the level is ended with RESULT_QUIT.
// Saves the outcome as STATS and exits VICE with code 0 (exit reached or script done)
// or 1 (Keen died).

#import "gen_script.asm"
#import "script_input.asm"

.segment Code

level_test:
    jsr timer_init
    jsr game_new
    jsr script_start
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
    lda perf_max_frames
    sta lt_stats + 8
    lda perf_lost
    sta lt_stats + 9
    lda perf_lost + 1
    sta lt_stats + 10
    lda perf_tick_max
    sta lt_stats + 11
    lda perf_tick_max + 1
    sta lt_stats + 12
    lda perf_out_max
    sta lt_stats + 13
    lda perf_out_max + 1
    sta lt_stats + 14
    lda perf_max_at
    sta lt_stats + 15
    lda perf_max_at + 1
    sta lt_stats + 16
    ldx #31
!:  lda perf_history, x
    sta lt_history, x
    dex
    bpl !-
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
    cmp #RESULT_DIED
    bne !+
    lda #1
    sta $d7ff
!:  lda #0
    sta $d7ff
    jmp *

lt_name:
    .text "STATS"
lt_name_end:

script_finished:
    lda #RESULT_QUIT              // checked by play_loop after this tick
    sta play_result
    rts

record_tick:
    rts

.segment Vars
// result, score (3, BCD), lives, ammo, ship parts, keycards, max frames per
// iteration, lost frames (2)
lt_stats:    .fill 17, 0
lt_history:  .fill 32, 0          // frames per iteration, first 32 iterations
lt_stats_end:
