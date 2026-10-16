// Playing one level: load, set up, run the frame loop, death and exit.

.const MAX_TICKS_PER_FRAME = 2    // catch up at most this many lost frames
.const DEATH_TICKS     = 75       // 1.5 s death animation

.segment Code

// A = level number. Returns with play_result: RESULT_EXIT or RESULT_DIED (map/level
// file needs reloading because collected items changed the map in memory).
play_level:
    sta current_level
    ldx #0
    stx map_mode
    jsr load_level
    jsr level_init
    jsr anim_init
    lda #0
    sta spr_enable
    jsr items_level_start
    jsr actors_init
    jsr player_init
    jsr camera_center
    jsr scroll_init
    jsr wait_frame
    lda #0
    sta play_result
    sta perf_max_frames
    sta perf_lost
    sta perf_lost + 1
    sta perf_tick_max
    sta perf_tick_max + 1
    sta perf_out_max
    sta perf_out_max + 1

play_loop:
    jsr wait_frame                // A = frames since the last iteration
    jsr perf_count
    jsr frames_to_ticks           // NTSC: 5 ticks per 6 frames
    cmp #MAX_TICKS_PER_FRAME + 1
    bcc !+
    lda #MAX_TICKS_PER_FRAME
!:  sta ticks_due
    tax                           // sta does not set Z: test the tick count
    beq play_output
!:
#if INPUTSCRIPT
    TimerRead(perf_t0)
#endif
    jsr game_tick
#if INPUTSCRIPT
    TimerRead(perf_t1)
    TimerMax(perf_t0, perf_t1, perf_tick_max)
#endif
    lda play_result
    bne play_done
    dec ticks_due
    bne !-
play_output:
    jsr frame_output
    jmp play_loop
play_done:
    cmp #RESULT_EXIT
    bne !+
    lda #SND_LVLDONESND
    jsr sound_play
    lda #RESULT_EXIT
!:  cmp #RESULT_DIED
    bne !+
    jsr death_sequence
!:  lda #0
    sta spr_enable
    lda play_result
    rts

// Frame statistics (read by tests): longest iteration in frames, frames lost in total.
// In: A = frames since the last iteration. Keeps A.
perf_count:
    pha
#if INPUTSCRIPT
    ldx perf_iterations + 1       // test builds: frames of the first 32 iterations
    bne !+
    ldx perf_iterations
    cpx #32
    bcs !+
    sta perf_history, x
!:
#endif
    inc perf_iterations
    bne !+
    inc perf_iterations + 1
!:  pla
    pha
    cmp perf_max_frames
    bcc !+
    sta perf_max_frames
    lda perf_iterations           // remember when the longest iteration happened
    sta perf_max_at
    lda perf_iterations + 1
    sta perf_max_at + 1
    pla
    pha
!:  sec
    sbc #1
    clc
    adc perf_lost
    sta perf_lost
    bcc !+
    inc perf_lost + 1
!:  pla
    rts

// Per displayed frame: camera, scrolling, sprites, tile animation, background render.
frame_output:
#if INPUTSCRIPT
    TimerRead(perf_t0)
#endif
    jsr scroll_update
    jsr player_draw
    jsr actors_draw
    jsr anim_update
#if INPUTSCRIPT
    TimerRead(perf_t1)
    TimerMax(perf_t0, perf_t1, perf_out_max)
#endif
    jmp render_step

game_tick:
    jsr input_read
    lda joy_new
    and #KEY_STOP
    beq !+
    jsr status_screen             // RUN/STOP: status and pause
    jsr text_end
!:    jsr player_update
    jsr player_touch
    jsr actors_update
    jsr camera_follow             // per tick: actor activation depends on the camera
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
#if !GODMODE
    lda #RESULT_DIED
    sta play_result
#endif
!:  rts

// Keen's death: the death sprite flies up off the screen (like the original), then
// one life is lost.
death_sequence:
    lda #SND_KEENDIESND
    jsr sound_play
    lda #DEATH_TICKS
    sta ticks_due
!:  jsr wait_frame
    lda ticks_due
    and #8
    lsr
    lsr
    lsr                           // alternate KEENISDEAD1/2 every 8 ticks
    clc
    adc #SPR_KEENISDEAD1
    sta p_sprite
    sec                           // move up 2 px per tick
    lda p_y
    sbc #32
    sta p_y
    bcs !+
    dec p_y + 1
!:  jsr scroll_update
    jsr player_draw
    jsr anim_update
    dec ticks_due
    bne !--
    dec lives
    rts

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
perf_max_frames: .byte 0
perf_lost:     .word 0
perf_tick_max: .word 0              // test builds: longest game tick in cycles
perf_out_max:  .word 0              // test builds: longest frame output without rendering
perf_t0:       .word 0
perf_iterations: .word 0
perf_max_at:   .word 0             // iteration number of the longest one
perf_history:  .fill 32, 0
perf_t1:       .word 0
