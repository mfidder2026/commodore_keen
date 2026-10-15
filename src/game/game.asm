// Playing one level: load, set up, run the frame loop.

.const MAX_TICKS_PER_FRAME = 2    // catch up at most this many lost frames
.const RESULT_DIED     = 1
.const RESULT_EXIT     = 2
.const RESULT_QUIT     = 3

.segment Code

// A = level number. Loads and starts it; returns when the level ends (play_result).
play_level:
    sta current_level
    jsr load_level
    jsr level_init
    jsr anim_init
level_restart:
    lda #0
    sta spr_enable
    jsr player_init
    jsr camera_center
    jsr scroll_init
    jsr wait_frame
    lda #0
    sta play_result

play_loop:
    jsr wait_frame                // A = frames since the last iteration
    cmp #MAX_TICKS_PER_FRAME + 1
    bcc !+
    lda #MAX_TICKS_PER_FRAME
!:  sta ticks_due
!:  jsr game_tick
    lda play_result
    bne play_done
    dec ticks_due
    bne !-
    jsr camera_follow
    jsr scroll_update
    jsr player_draw
    jsr anim_update
    jsr render_step
    jmp play_loop
play_done:
    lda play_result
    cmp #RESULT_DIED
    bne !+
    jmp level_restart             // M5 adds lives; for now: try again
!:  rts


game_tick:
    jsr input_read
    jsr player_update
    jsr check_fell_out
#if INPUTSCRIPT
    jsr record_tick
#endif
    rts

// Below the bottom of the map: dead.
check_fell_out:
    lda p_y + 1                   // p_y / 256 = tile row of the sprite top
    cmp level_height
    bcc !+
    lda #RESULT_DIED
    sta play_result
!:  rts

// Camera centred on Keen (start of a level).
camera_center:
    lda p_x + 1                   // px = p_x / 16; cam_x = px - 144
    sta cam_x + 1
    lda p_x
    lsr cam_x + 1
    ror
    lsr cam_x + 1
    ror
    lsr cam_x + 1
    ror
    lsr cam_x + 1
    ror
    sec
    sbc #144
    sta cam_x
    lda cam_x + 1
    sbc #0
    sta cam_x + 1
    lda p_y + 1
    sta cam_y + 1
    lda p_y
    lsr cam_y + 1
    ror
    lsr cam_y + 1
    ror
    lsr cam_y + 1
    ror
    lsr cam_y + 1
    ror
    sec
    sbc #80
    sta cam_y
    lda cam_y + 1
    sbc #0
    sta cam_y + 1
    jmp clamp_camera

.segment Vars
current_level: .byte 0
play_result:   .byte 0
ticks_due:     .byte 0
