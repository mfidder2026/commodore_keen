// Commander Keen C64 - entry point.
// An unofficial, non-commercial fan port. Not affiliated with id Software.

#import "memory.asm"
#import "zp.asm"
#import "sprites.asm"            // generated: build/generated/sprites.asm
#import "engine/system.asm"
#import "engine/exodecrunch.asm"
#import "engine/irq.asm"
#import "engine/level.asm"
#import "engine/scroll.asm"
#import "engine/sprites.asm"
#import "engine/timing.asm"

.encoding "petscii_upper"

.const DEMO_SPEED = 2

.segment Basic
    BasicUpstart2(start)

.segment Code
start:
    sei
    lda #0
    sta $d020
    sta $d021
    sta $d015
    // Variables live in a virtual segment at $a000-$bfff: clear it (RAM under BASIC ROM).
    lda #$36
    sta $01
    lda #0
    tax
!:
    .for (var p = $a0; p < $c0; p++) {
        sta p * $100, x
    }
    inx
    beq !+
    jmp !-
!:
    lda #<irq_nothing
    sta irq_hook_vector
    lda #>irq_nothing
    sta irq_hook_vector + 1
    jsr system_init
    jsr sprites_init
    jsr load_sprite_bank
#if SCROLLTEST
    jmp scroll_test
#else
    jmp scroll_demo
#endif

// M3 demo: scroll through a level with the joystick in port 2; fire loads the next level.
scroll_demo:
    lda #0
    sta demo_level_index
demo_load:
    ldx demo_level_index
    lda demo_levels, x
    jsr load_level
    jsr level_init
    jsr anim_init
    lda #0
    sta cam_x
    sta cam_x + 1
    sta cam_y
    sta cam_y + 1
    jsr scroll_init
demo_loop:
    jsr wait_frame
    lda $dc00
    sta zp_tmp3
    lsr zp_tmp3                   // bit 0: up
    bcs !+
    lda cam_y
    sec
    sbc #DEMO_SPEED
    sta cam_y
    bcs !+
    dec cam_y + 1
!:  lsr zp_tmp3                   // bit 1: down
    bcs !+
    lda cam_y
    clc
    adc #DEMO_SPEED
    sta cam_y
    bcc !+
    inc cam_y + 1
!:  lsr zp_tmp3                   // bit 2: left
    bcs !+
    lda cam_x
    sec
    sbc #DEMO_SPEED
    sta cam_x
    bcs !+
    dec cam_x + 1
!:  lsr zp_tmp3                   // bit 3: right
    bcs !+
    lda cam_x
    clc
    adc #DEMO_SPEED
    sta cam_x
    bcc !+
    inc cam_x + 1
!:  lsr zp_tmp3                   // bit 4: fire
    bcs demo_frame
!:  lda $dc00                     // wait for release
    and #$10
    beq !-
    inc demo_level_index
    lda demo_level_index
    cmp #demo_levels_end - demo_levels
    bcc !+
    lda #0
    sta demo_level_index
!:  jmp demo_load
demo_frame:
    jsr scroll_update
    jsr anim_update
    jsr render_step
    jmp demo_loop

demo_levels:
    .byte 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 80, 81, 90
demo_levels_end:

#if SCROLLTEST
#import "../tests/scenarios/m3_scroll.asm"
#endif

.segment Vars
demo_level_index: .byte 0
