// Commander Keen C64 - entry point.
// M0: empty program that shows the title and the unofficial fan port disclaimer.

#import "memory.asm"
#import "zp.asm"

.const BORDER     = $d020
.const BACKGROUND = $d021
.const SCREEN     = $0400
.const COLOR_RAM  = $d800

.segment Basic
    BasicUpstart2(start)

.segment Code
start:
    sei
    lda #0
    sta BORDER
    sta BACKGROUND
    sta zp_frame

    ldx #0
clear:
    lda #' '
    sta SCREEN, x
    sta SCREEN + $100, x
    sta SCREEN + $200, x
    sta SCREEN + $2e8, x
    lda #1                          // white
    sta COLOR_RAM, x
    sta COLOR_RAM + $100, x
    sta COLOR_RAM + $200, x
    sta COLOR_RAM + $2e8, x
    inx
    bne clear

    ldx #title_len - 1
copy_title:
    lda title, x
    sta SCREEN + 10 * 40 + (40 - title_len) / 2, x
    dex
    bpl copy_title

    ldx #disclaimer_len - 1
copy_disclaimer:
    lda disclaimer, x
    sta SCREEN + 13 * 40 + (40 - disclaimer_len) / 2, x
    dex
    bpl copy_disclaimer

    cli
idle:
    jmp idle

.encoding "screencode_upper"
title:
    .text "COMMANDER KEEN C64"
.label title_len = * - title
disclaimer:
    .text "UNOFFICIAL NON-COMMERCIAL FAN PORT"
.label disclaimer_len = * - disclaimer
