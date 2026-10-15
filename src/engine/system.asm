// System setup: memory configuration, raster IRQ, KERNAL loading.
// During play: $01 = $35 (RAM everywhere except I/O), KERNAL and BASIC banked out,
// VIC bank 3 ($c000-$ffff), one raster IRQ per frame at IRQ_LINE.

.const IRQ_LINE = 251             // below the last visible text row in 24-row mode

.segment Code

system_init:
    sei
    cld
    lda #$7f
    sta $dc0d                     // no CIA interrupts while playing
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda $dd02                     // VIC bank 3: CIA2 port A bits 0-1 = %00
    ora #%00000011
    sta $dd02
    lda $dd00
    and #%11111100
    sta $dd00
    lda #<nmi_handler
    sta $fffa
    lda #>nmi_handler
    sta $fffb
    jsr irq_on
    cli
    rts

// Install the raster IRQ (I flag must be set by the caller or is set here).
irq_on:
    sei
    lda #<irq_handler
    sta $fffe
    lda #>irq_handler
    sta $ffff
    lda #IRQ_LINE
    sta $d012
    lda $d011
    and #$7f
    sta $d011
    lda #1
    sta $d01a
    lda #$ff
    sta $d019
    rts

nmi_handler:
    rti

// Wait until the raster IRQ has run since the last call (no wait if it already has,
// e.g. because rendering used up the rest of the previous frame).
// Out: A = number of frames since the last call (1 normally, more if frames were lost).
wait_frame:
    lda zp_frame
    cmp last_frame
    beq wait_frame
    sec
    sbc last_frame
    pha
    lda zp_frame
    sta last_frame
    pla
    rts

.segment Vars
last_frame: .byte 0
.segment Code

// Load a file with the KERNAL to the address stored in the file.
// In: A = name length, X/Y = name address lo/hi. Out: C set on error.
kernal_load:
    sta load_len
    stx load_name
    sty load_name + 1
    sei
    lda #0
    sta $d01a                     // raster IRQ off
    sta $d015                     // sprites off
    lda #$ff
    sta $d019
    lda $d011
    and #%11101111                // blank the screen while loading
    sta $d011
    lda #$36                      // KERNAL on, BASIC off, I/O on
    sta $01
    lda #<$ea31
    sta $0314
    lda #>$ea31
    sta $0315
    lda #$81                      // KERNAL's timer IRQ back on
    sta $dc0d
    cli
    lda load_len
    ldx load_name
    ldy load_name + 1
    jsr $ffbd                     // SETNAM
    lda #1
    ldx $ba                       // last used device, 8 if none
    bne !+
    ldx #8
!:  ldy #1                        // load to the address stored in the file
    jsr $ffba                     // SETLFS
    lda #0
    jsr $ffd5                     // LOAD
    php
    sei
    lda #$7f
    sta $dc0d
    lda $dc0d
    lda #$35
    sta $01
    jsr irq_on
    lda $d011
    ora #%00010000
    sta $d011
    plp                           // restores C (error) and I = 0
    rts

// Save memory to a file with the KERNAL (used for test statistics and high scores).
// In: A = name length, X/Y = name address; save_from/save_to = range (save_to exclusive).
kernal_save:
    sta load_len
    stx load_name
    sty load_name + 1
    sei
    lda #0
    sta $d01a
    sta $d015
    lda #$ff
    sta $d019
    lda #$36
    sta $01
    lda #<$ea31
    sta $0314
    lda #>$ea31
    sta $0315
    lda #$81
    sta $dc0d
    cli
    lda load_len
    ldx load_name
    ldy load_name + 1
    jsr $ffbd                     // SETNAM
    lda #1
    ldx $ba
    bne !+
    ldx #8
!:  ldy #0
    jsr $ffba                     // SETLFS
    lda save_from
    sta zp_ptr0
    lda save_from + 1
    sta zp_ptr0 + 1
    lda #zp_ptr0
    ldx save_to
    ldy save_to + 1
    jsr $ffd8                     // SAVE
    php
    sei
    lda #$7f
    sta $dc0d
    lda $dc0d
    lda #$35
    sta $01
    jsr irq_on
    plp
    rts

.segment Vars
save_from: .word 0
save_to:   .word 0
.segment Code

// Load the sprite bank and copy it under I/O and to $e000.
load_sprite_bank:
    lda #sprites_name_end - sprites_name
    ldx #<sprites_name
    ldy #>sprites_name
    jsr kernal_load
    bcc !+
    jmp load_failed
!:  jsr exo_decrunch_loaded       // files on disk are Exomizer-crunched (in place)
    sei
    lda #$34                      // all RAM: $d000-$dfff writable
    sta $01
    ldx #0
!:
    .for (var p = 0; p < 16; p++) {
        lda SPRITE_BANK_LOAD + p * $100, x
        sta $d000 + p * $100, x
    }
    inx
    bne !-
    lda #$35
    sta $01
    ldx #0
copy_high:
    .for (var p = 0; p < 31; p++) {
        lda SPRITE_BANK_LOAD + $1000 + p * $100, x
        sta $e000 + p * $100, x
    }
    inx
    beq !+
    jmp copy_high
!:  ldx #$bf                      // last page: $ff00-$ffbf only, keep the vectors
!:  lda SPRITE_BANK_LOAD + $1000 + 31 * $100, x
    sta $ff00, x
    dex
    cpx #$ff
    bne !-
    cli
    rts

load_failed:
    sei
    lda #2
    sta $d020
    jmp *

sprites_name:
    .text "SPRITES"
sprites_name_end:

// Level file names "L01" .. "L90": the digits are patched in.
load_level:                       // A = level number (1-16, 80, 81, 90)
    ldx #0
!:  cmp #10
    bcc !+
    sbc #10
    inx
    bne !-
!:  ora #'0'
    sta level_name + 2
    txa
    ora #'0'
    sta level_name + 1
    lda #3
    ldx #<level_name
    ldy #>level_name
    jsr kernal_load
    bcs load_failed
    jmp exo_decrunch_loaded

level_name:
    .text "L00"

.segment Vars
load_len:   .byte 0
load_name:  .word 0
