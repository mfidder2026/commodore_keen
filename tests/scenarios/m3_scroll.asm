// M3 scenario: scroll level 1 along a fixed path, then report via the debug cartridge.
// Path (per frame): 180 frames right 3 px, 120 frames left 2 px and down 1 px,
// 60 frames up-right 1 px each, then hold for 50 frames so the last swap settles.
// test_stats (dumped by the VICE monitor) holds the measurements; see test_scroll.py.

.segment Code

scroll_test:
    jsr timer_init
    lda #1
    jsr load_level
    jsr level_init
    jsr anim_init
    lda #0
    sta cam_x
    sta cam_x + 1
    sta cam_y
    sta cam_y + 1
    jsr scroll_init
    lda #0
    ldx #test_stats_end - test_stats - 1
!:  sta test_stats, x
    dex
    bpl !-
    // One-off measurements: a row render and a full colour RAM update.
    sei
    lda #0
    sta render_row_no
    TimerRead(tm_start)
    jsr render_row
    TimerRead(tm_end)
    TimerMax(tm_start, tm_end, stat_row_cycles)
    TimerRead(tm_start)
    jsr colour_screen_a
    TimerRead(tm_end)
    TimerMax(tm_start, tm_end, stat_colour_cycles)
    jsr scroll_init               // undo the test row render
    cli
    jsr wait_frame

test_loop:
    jsr wait_frame                // A = frames since the last iteration
    sec
    sbc #1                        // frames the main loop did not get to (lost frames)
    clc
    adc stat_lost_frames
    sta stat_lost_frames

    jsr test_move_camera
    bcc !+
    jmp test_finish
!:  jsr scroll_update
    // frames where the screen could not follow the camera
    lda shown_x
    cmp cam_x
    bne !+
    lda shown_y
    cmp cam_y
    beq !++
!:  inc stat_lag_frames
!:  jsr anim_update
    TimerRead(tm_start)
    jsr render_step
    TimerRead(tm_end)
    TimerMax(tm_start, tm_end, stat_max_render_step)
    inc test_step
    bne !+
    inc test_step + 1
!:  jmp test_loop

test_finish:
    lda cam_x
    sta stat_cam_x
    lda cam_x + 1
    sta stat_cam_x + 1
    lda cam_y
    sta stat_cam_y
    lda cam_y + 1
    sta stat_cam_y + 1
    lda shown_x
    sta stat_shown_x
    lda shown_x + 1
    sta stat_shown_x + 1
    lda shown_y
    sta stat_shown_y
    lda shown_y + 1
    sta stat_shown_y + 1
    lda front_cx
    sta stat_front_cx
    lda front_cy
    sta stat_front_cy
test_done:
    lda #<test_stats
    sta save_from
    lda #>test_stats
    sta save_from + 1
    lda #<test_stats_end
    sta save_to
    lda #>test_stats_end
    sta save_to + 1
    lda #stats_name_end - stats_name
    ldx #<stats_name
    ldy #>stats_name
    jsr kernal_save
    lda #0
    sta $d7ff                     // debug cartridge: exit VICE with code 0
    jmp *

stats_name:
    .text "STATS"
stats_name_end:

// Moves the camera one step along the path; C set when the path is finished.
.macro StepBelow(value, target) {   // branch to target if test_step < value
    lda test_step
    cmp #<value
    lda test_step + 1
    sbc #>value
    bcc target
}

test_move_camera:
    StepBelow(180, phase1)
    StepBelow(300, phase2)
    StepBelow(360, phase3)
    StepBelow(410, phase_hold)
    sec
    rts
phase1:
    lda #3                        // right 3
    jsr cam_add_x
    clc
    rts
phase2:
    lda #$fe                      // left 2, down 1
    jsr cam_add_x
    lda #1
    jsr cam_add_y
    clc
    rts
phase3:
    lda #1                        // right 1, up 1
    jsr cam_add_x
    lda #$ff
    jsr cam_add_y
phase_hold:
    clc
    rts

// cam_x += signed A
cam_add_x:
    ldx #0
    cmp #$80
    bcc !+
    dex
!:  clc
    adc cam_x
    sta cam_x
    txa
    adc cam_x + 1
    sta cam_x + 1
    rts

cam_add_y:
    ldx #0
    cmp #$80
    bcc !+
    dex
!:  clc
    adc cam_y
    sta cam_y
    txa
    adc cam_y + 1
    sta cam_y + 1
    rts

.segment Vars
test_step:          .word 0
tm_start:            .word 0
tm_end:              .word 0
test_stats:
stat_lost_frames:   .byte 0
stat_lag_frames:    .byte 0
stat_max_render_step: .word 0
stat_cam_x:         .word 0
stat_cam_y:         .word 0
stat_shown_x:       .word 0
stat_shown_y:       .word 0
stat_front_cx:      .word 0
stat_front_cy:      .byte 0
stat_row_cycles:    .word 0
stat_colour_cycles: .word 0
test_stats_end:
