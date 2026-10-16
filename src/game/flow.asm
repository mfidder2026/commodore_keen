// Game flow: title screen, world map, levels, status screen, game over, the end.

.segment Code

game_main:
    jsr title_screen
    jsr game_new
    lda #0
    sta map_keen_x
    sta map_keen_x + 1
    sta map_keen_y
    sta map_keen_y + 1
map_reenter:
    jsr map_enter
map_frame:
    jsr wait_frame
    jsr frames_to_ticks           // NTSC: 5 ticks per 6 frames
    cmp #MAX_TICKS_PER_FRAME + 1
    bcc !+
    lda #MAX_TICKS_PER_FRAME
!:  sta ticks_due
    tax                           // sta does not set Z: test the tick count
    beq map_output
!:  jsr map_tick
    lda map_result
    bne map_event
    dec ticks_due
    bne !-
map_output:
    jsr scroll_update
    jsr player_draw
    jsr map_draw_marks
    jsr anim_update
    jsr render_step
    jmp map_frame

map_event:
    lda p_x                       // remember where Keen stands
    sta map_keen_x
    lda p_x + 1
    sta map_keen_x + 1
    lda p_y
    sta map_keen_y
    lda p_y + 1
    sta map_keen_y + 1
    lda map_result
    cmp #MAP_RESULT_QUIT
    bne !+
    jsr status_screen
    jsr text_end
    jmp map_frame
!:  cmp #MAP_RESULT_SHIP
    bne enter_level
    lda ship_parts
    cmp #ALL_PARTS
    bne !+
    jsr the_end
    jmp game_main
!:  jsr text_begin
    lda #11
    ldx #<need_parts_text
    ldy #>need_parts_text
    lda #11
    jsr print_centred
    jsr wait_fire
    jsr text_end
    jmp map_frame

enter_level:
    lda #0
    sta map_mode
    lda map_spot_code
    sta entered_level
    jsr play_level
    cmp #RESULT_EXIT
    bne !+
    lda entered_level
    jsr mark_level_done
    jmp map_reenter
!:  lda lives                     // died (a life was taken in death_sequence)
    jne map_reenter
    jsr game_over
    jmp game_main

// ---------------------------------------------------------------------------------
title_screen:
    jsr text_begin
    lda #7
    sta text_colour
    lda #4
    ldx #<title_text
    ldy #>title_text
    jsr print_centred
    lda #1
    sta text_colour
    lda #6
    ldx #<subtitle_text
    ldy #>subtitle_text
    jsr print_centred
    lda #15
    sta text_colour
    lda #11
    ldx #<disclaimer1
    ldy #>disclaimer1
    jsr print_centred
    lda #12
    ldx #<disclaimer2
    ldy #>disclaimer2
    jsr print_centred
    lda #13
    ldx #<disclaimer3
    ldy #>disclaimer3
    jsr print_centred
    lda #14
    sta text_colour
    lda #16
    ldx #<keys_text
    ldy #>keys_text
    jsr print_centred
    jsr print_controls
    lda #1
    sta text_colour
    lda #23
    ldx #<press_fire_text
    ldy #>press_fire_text
    jsr print_centred
#if INPUTSCRIPT
    rts                           // tests start straight away
#else
    // F1 switches the control layout, fire (or space) starts
!:  jsr wait_frame
    jsr input_read
    jsr read_f1
    beq title_fire
    lda ctrl_alt
    eor #1
    sta ctrl_alt
    jsr print_controls
!:  jsr wait_frame                // wait until F1 is released
    jsr read_f1
    bne !-
title_fire:
    lda joy_new
    and #JOY_FIRE | KEY_SPACE
    beq !--
    rts
#endif

// Rows 18-21: the current control layout.
print_controls:
    lda #14
    sta text_colour
    lda ctrl_alt
    asl
    asl
    asl                           // 4 lines of 2 bytes per layout
    tax
    lda #18
    sta zp_tmp3
!:  stx controls_index
    lda control_lines, x
    pha
    lda control_lines + 1, x
    tay
    pla
    tax
    lda zp_tmp3
    jsr print_centred
    inc zp_tmp3
    ldx controls_index
    inx
    inx
    txa
    and #7
    bne !-
    rts

// Keyboard: F1 is row 0, column 4. Returns Z clear (bne) while pressed.
read_f1:
    lda #%11111110
    sta $dc00
    lda $dc01
    eor #$ff
    and #%00010000
    tax
    lda #$ff
    sta $dc00
    txa
    rts

// Status (RUN/STOP): score, lives, ammo, pogo, ship parts, keycards. Fire continues.
status_screen:
    jsr text_begin
    lda #7
    sta text_colour
    lda #3
    ldx #<status_title
    ldy #>status_title
    jsr print_centred
    lda #1
    sta text_colour
    lda #10
    sta text_x
    lda #6
    sta text_y
    ldx #<score_label
    ldy #>score_label
    jsr print
    lda #22
    sta text_x
    jsr print_score
    lda #10
    sta text_x
    lda #8
    sta text_y
    ldx #<keens_label
    ldy #>keens_label
    jsr print
    lda #22
    sta text_x
    lda lives
    jsr print_number
    lda #10
    sta text_x
    lda #10
    sta text_y
    ldx #<raygun_label
    ldy #>raygun_label
    jsr print
    lda #22
    sta text_x
    lda ammo
    jsr print_number
    lda #10
    sta text_x
    lda #12
    sta text_y
    ldx #<pogo_label
    ldy #>pogo_label
    jsr print
    lda #22
    sta text_x
    ldx #<no_text
    ldy #>no_text
    lda p_has_pogo
    beq !+
    ldx #<yes_text
    ldy #>yes_text
!:  jsr print
    // ship parts
    lda #10
    sta text_x
    lda #14
    sta text_y
    ldx #<parts_label
    ldy #>parts_label
    jsr print
    lda #0
    sta zp_tmp3
part_loop:
    lda #12
    sta text_x
    lda zp_tmp3
    clc
    adc #15
    sta text_y
    ldx zp_tmp3
    lda part_name_lo, x
    pha
    lda part_name_hi, x
    tay
    pla
    tax
    jsr print
    lda #26
    sta text_x
    ldx zp_tmp3
    lda bit_table, x
    and ship_parts
    beq !+
    ldx #<yes_text
    ldy #>yes_text
    jmp !++
!:  ldx #<no_text
    ldy #>no_text
!:  jsr print
    inc zp_tmp3
    lda zp_tmp3
    cmp #4
    bne part_loop
    lda #23
    ldx #<press_fire_text
    ldy #>press_fire_text
    jsr print_centred
    jmp wait_fire

game_over:
    lda #SND_GAMEOVERSND
    jsr sound_play
    jsr text_begin
    lda #2
    sta text_colour
    lda #10
    ldx #<game_over_text
    ldy #>game_over_text
    jsr print_centred
    lda #1
    sta text_colour
    lda #13
    sta text_y
    lda #17
    sta text_x
    jsr print_score
    jmp wait_fire

the_end:
#if FLOWTEST
    jmp flow_won                  // test build: the end reached, save the state
#endif
    jsr text_begin
    lda #7
    sta text_colour
    lda #8
    ldx #<end_text1
    ldy #>end_text1
    jsr print_centred
    lda #1
    sta text_colour
    lda #10
    ldx #<end_text2
    ldy #>end_text2
    jsr print_centred
    lda #11
    ldx #<end_text3
    ldy #>end_text3
    jsr print_centred
    lda #14
    sta text_y
    lda #17
    sta text_x
    jsr print_score
    lda #20
    ldx #<end_text4
    ldy #>end_text4
    jsr print_centred
    jmp wait_fire

.encoding "ascii"
title_text:      .text "COMMODORE KEEN"
                 .byte 0
subtitle_text:   .text "EPISODE ONE: MAROONED ON MARS"
                 .byte 0
disclaimer1:     .text "UNOFFICIAL NON-COMMERCIAL FAN PORT"
                 .byte 0
disclaimer2:     .text "NOT AFFILIATED WITH ID SOFTWARE"
                 .byte 0
disclaimer3:     .text "ORIGINAL GAME (C) 1990 ID SOFTWARE"
                 .byte 0
// All control lines are 30 characters, so switching overwrites the old text.
controls1:       .text "    UP JUMPS, FIRE SHOOTS     "
                 .byte 0
controls2:       .text "   SPACE OR DOWN+FIRE: POGO   "
                 .byte 0
controls3:       .text "  RUN/STOP: STATUS AND PAUSE  "
                 .byte 0
controls4:       .text "F1: OTHER CONTROLS (JOY PORT 2)"
                 .byte 0
alt_controls1:   .text " FIRE JUMPS, DOWN+FIRE SHOOTS "
                 .byte 0
alt_controls2:   .text "         SPACE: POGO          "
                 .byte 0
control_lines:   .word controls1, controls2, controls3, controls4
                 .word alt_controls1, alt_controls2, controls3, controls4
keys_text:       .text "KEYS: W A S D, RETURN = FIRE"
                 .byte 0
press_fire_text: .text "PRESS FIRE"
                 .byte 0
status_title:    .text "STATUS"
                 .byte 0
score_label:     .text "SCORE"
                 .byte 0
keens_label:     .text "KEENS"
                 .byte 0
raygun_label:    .text "RAYGUN"
                 .byte 0
pogo_label:      .text "POGO STICK"
                 .byte 0
parts_label:     .text "SHIP PARTS"
                 .byte 0
yes_text:        .text "YES"
                 .byte 0
no_text:         .text "NO "
                 .byte 0
part1:           .text "JOYSTICK"
                 .byte 0
part2:           .text "BATTERY"
                 .byte 0
part3:           .text "VACUUM CLEANER"
                 .byte 0
part4:           .text "EVERCLEAR"
                 .byte 0
part_name_lo:    .byte <part1, <part2, <part3, <part4
part_name_hi:    .byte >part1, >part2, >part3, >part4
need_parts_text: .text "THE SHIP NEEDS ALL FOUR PARTS"
                 .byte 0
game_over_text:  .text "GAME OVER"
                 .byte 0
end_text1:       .text "THE SHIP IS REPAIRED!"
                 .byte 0
end_text2:       .text "KEEN FLIES HOME TO EARTH"
                 .byte 0
end_text3:       .text "BEFORE HIS PARENTS COME BACK."
                 .byte 0
end_text4:       .text "THE END"
                 .byte 0

.segment Vars
entered_level:  .byte 0
controls_index: .byte 0
