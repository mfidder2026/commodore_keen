// M7 scenario: the real game flow (title, map, level, back to the map) with a scripted
// joystick (build/generated/gen_script.asm). When the script runs out, the state is
// saved as STATS and VICE exits with code 0.

#import "gen_script.asm"
#import "script_input.asm"

.segment Code

flow_test:
    jsr script_start
    jmp game_main

flow_won:
    lda #1
    sta ft_stats + 13
    // fall through
script_finished:
    ldx #2
!:  lda levels_done, x
    sta ft_stats, x
    lda score, x
    sta ft_stats + 3, x
    dex
    bpl !-
    lda lives
    sta ft_stats + 6
    lda p_x
    sta ft_stats + 7
    lda p_x + 1
    sta ft_stats + 8
    lda p_y
    sta ft_stats + 9
    lda p_y + 1
    sta ft_stats + 10
    lda map_mode
    sta ft_stats + 11
    lda current_level
    sta ft_stats + 12
    lda ship_parts
    sta ft_stats + 14
    lda #<ft_stats
    sta save_from
    lda #>ft_stats
    sta save_from + 1
    lda #<ft_stats_end
    sta save_to
    lda #>ft_stats_end
    sta save_to + 1
    lda #ft_name_end - ft_name
    ldx #<ft_name
    ldy #>ft_name
    jsr kernal_save
    lda #0
    sta $d7ff
    jmp *

ft_name:
    .text "STATS"
ft_name_end:

record_tick:
    rts

.segment Vars
// levels done (3), score (3), lives, keen x (2), keen y (2), map mode, current level
ft_stats:    .fill 15, 0           // ..., won (the end reached), ship parts
ft_stats_end:
