// Fast colour RAM update, generated at startup into RAM (COLOUR_CODE, $A600).
//
// Five blocks, one per group of six rows (rows 0-5, 6-11, 12-17, 18-23, 24). A block
// handles the 40 characters of one row with Y = row offset inside the group:
//     ldx SCREEN + group*240 + k, y   / lda LVL_CHAR_COLOUR, x / sta $d800 + group*240 + k, y
// That is 13 cycles per character (16.5 for the looped version), fast enough to stay
// ahead of the beam on NTSC too. The screen high bytes are patched to the back buffer
// before each swap (colour_fast_target), outside the IRQ.

.const COLOUR_CODE  = $a600
.const GROUP_BYTES  = 40 * 9 + 1  // 40 cells of 9 bytes, rts
.const GROUPS       = 5

.segment Code

// Write the five blocks (screen A as target).
colour_fast_init:
    lda #<COLOUR_CODE
    sta zp_ptr0
    lda #>COLOUR_CODE
    sta zp_ptr0 + 1
    lda #0
    sta cf_group
cf_group_loop:
    // address of the first cell of the group: group * 240
    ldx cf_group
    lda cf_group_lo, x
    sta cf_cell
    lda cf_group_hi, x
    sta cf_cell + 1
    lda #40
    sta cf_count
cf_cell_loop:
    ldy #0
    lda #$be                      // ldx abs,y
    sta (zp_ptr0), y
    iny
    lda cf_cell
    sta (zp_ptr0), y
    iny
    lda cf_cell + 1
    clc
    adc #>SCREEN_A
    sta (zp_ptr0), y
    iny
    lda #$bd                      // lda abs,x
    sta (zp_ptr0), y
    iny
    lda #<LVL_CHAR_COLOUR
    sta (zp_ptr0), y
    iny
    lda #>LVL_CHAR_COLOUR
    sta (zp_ptr0), y
    iny
    lda #$99                      // sta abs,y
    sta (zp_ptr0), y
    iny
    lda cf_cell
    sta (zp_ptr0), y
    iny
    lda cf_cell + 1
    clc
    adc #>COLOUR_RAM
    sta (zp_ptr0), y
    clc
    lda zp_ptr0
    adc #9
    sta zp_ptr0
    bcc !+
    inc zp_ptr0 + 1
!:  inc cf_cell
    bne !+
    inc cf_cell + 1
!:  dec cf_count
    bne cf_cell_loop
    ldy #0
    lda #$60                      // rts
    sta (zp_ptr0), y
    inc zp_ptr0
    bne !+
    inc zp_ptr0 + 1
!:  inc cf_group
    lda cf_group
    cmp #GROUPS
    bne cf_group_loop
    lda #0
    sta cf_buffer
    rts

cf_group_lo: .fill GROUPS, <(i * 240)
cf_group_hi: .fill GROUPS, >(i * 240)

// Point the generated code at screen A (A = 0) or screen B (A = 1).
colour_fast_target:
    cmp cf_buffer
    beq cf_target_done
    sta cf_buffer
    lda #<(COLOUR_CODE + 2)       // high byte of the first ldx operand
    sta zp_ptr0
    lda #>(COLOUR_CODE + 2)
    sta zp_ptr0 + 1
    ldx #GROUPS
cf_patch_group:
    ldy #40
cf_patch_cell:
    sty cf_count
    ldy #0
    lda (zp_ptr0), y
    eor #>(SCREEN_A ^ SCREEN_B)   // $c0-$c3 <-> $c4-$c7
    sta (zp_ptr0), y
    clc
    lda zp_ptr0
    adc #9
    sta zp_ptr0
    bcc !+
    inc zp_ptr0 + 1
!:  ldy cf_count
    dey
    bne cf_patch_cell
    inc zp_ptr0                   // skip the rts
    bne !+
    inc zp_ptr0 + 1
!:  dex
    bne cf_patch_group
cf_target_done:
    rts

// Run the update (from the IRQ). Rows from the top, group by group. ~13,400 cycles.
colour_fast:
    .for (var g = 0; g < GROUPS; g++) {
        .for (var r = 0; r < 6; r++) {
            .if (g * 6 + r < 25) {
                ldy #r * 40
                jsr COLOUR_CODE + g * GROUP_BYTES
            }
        }
    }
    rts

.segment Vars
cf_group:  .byte 0
cf_count:  .byte 0
cf_cell:   .word 0
cf_buffer: .byte 0
