//
// Copyright (c) 2002 - 2020 Magnus Lind.
//
// This software is provided 'as-is', without any express or implied warranty.
// In no event will the authors be held liable for any damages arising from
// the use of this software.
//
// Permission is granted to anyone to use this software for any purpose,
// including commercial applications, and to alter it and redistribute it
// freely, subject to the following restrictions:
//
//   1. The origin of this software must not be misrepresented; you must not
//   claim that you wrote the original software. If you use this software in a
//   product, an acknowledgment in the product documentation would be
//   appreciated but is not required.
//
//   2. Altered source versions must be plainly marked as such, and must not
//   be misrepresented as being the original software.
//
//   3. This notice may not be removed or altered from any distribution.
//
//   4. The names of this software and/or it's copyright holders may not be
//   used to endorse or promote products derived from this software without
//   specific prior written permission.
//
// -------------------------------------------------------------------
// ALTERED SOURCE VERSION: exodecrunch.asm from Exomizer 3.1.0 (64tass syntax),
// ported to KickAssembler syntax for Commodore Keen. Only the default
// configuration is kept (backwards decrunching, bit stream -P39, get_bits not
// inlined); get_crunched_byte reads the loaded file backwards from exo_end.
// -------------------------------------------------------------------
// Known quirk (original): can't handle a sequence reference that ends at $ffff.

.label zp_len_lo   = $9e
.label zp_len_hi   = $9f
.label zp_src_lo   = $ae
.label zp_src_hi   = zp_src_lo + 1
.label zp_bits_hi  = $a7
.label zp_ro_state = $a8
.label zp_bitbuf   = $fd
.label zp_dest_lo  = zp_bitbuf + 1    // dest addr lo
.label zp_dest_hi  = zp_bitbuf + 2    // dest addr hi

.const ENCODED_ENTRIES = 52

.segment Code

// Decrunch a file loaded by the KERNAL: X/Y = end address + 1 (as LOAD returns it).
exo_decrunch_loaded:
    stx exo_byte + 1
    sty exo_byte + 2
    jmp exo_decrunch

// Reads one crunched byte into A, backwards. Preserves X, Y, C and V.
get_crunched_byte:
    lda exo_byte + 1
    bne !+
    dec exo_byte + 2
!:  dec exo_byte + 1
exo_byte:
    lda $ffff                     // SMC: current read address
    rts

.macro mac_refill_bits() {
    pha
    jsr get_crunched_byte
    rol
    sta zp_bitbuf
    pla
}

get_bits:
    adc #$80                      // needs c=0, affects v
    asl
    bpl gb_skip
gb_next:
    asl zp_bitbuf
    bne gb_ok
    mac_refill_bits()
gb_ok:
    rol
    bmi gb_next
gb_skip:
    bvs gb_get_hi
    rts
gb_get_hi:
    sec
    sta zp_bits_hi
    jmp get_crunched_byte

// jsr this label to decrunch; the decimal flag must be clear.
exo_decrunch:
    ldx #3
init_zp:
    jsr get_crunched_byte
    sta zp_bitbuf - 1, x
    dex
    bne init_zp
// calculate tables (64 bytes) + get_bits; x must be 0 here
    ldy #0
    clc
table_gen:
    tax
    tya
    and #$0f
    sta tabl_lo, y
    beq shortcut                  // start a new sequence
    txa
    adc tabl_lo - 1, y
    sta tabl_lo, y
    lda zp_len_hi
    adc tabl_hi - 1, y
shortcut:
    sta tabl_hi, y
    lda #$01
    sta zp_len_hi
    lda #$78                      // %01111000
    jsr get_bits
    lsr
    tax
    beq rolled
    php
rolle:
    asl zp_len_hi
    sec
    ror
    dex
    bne rolle
    plp
rolled:
    ror
    sta tabl_bi, y
    bmi no_fixup_lohi
    lda zp_len_hi
    stx zp_len_hi
    .byte $24                     // bit zp: skips the next instruction
no_fixup_lohi:
    txa
    iny
    cpy #ENCODED_ENTRIES
    bne table_gen
// prepare for main decruncher
    ror zp_ro_state
    sec
    ldy zp_dest_lo
    stx zp_dest_lo
    stx zp_bits_hi
// copy one literal byte to destination
literal_start1:
    tya
    bne no_hi_decr
    dec zp_dest_hi
    dec zp_src_hi
no_hi_decr:
    dey
    jsr get_crunched_byte
    sta (zp_dest_lo), y
// fetch sequence length index; x = length index + 1 or 0 for a literal byte
next_round:
    ror zp_ro_state
    dex
    lda zp_bitbuf
no_literal1:
    asl
    bne nofetch8
    jsr get_crunched_byte
    rol
nofetch8:
    inx
    bcc no_literal1
    sta zp_bitbuf
    beq literal_start1            // literal byte
    cpx #$11
    bcs exit_or_lit_seq           // decrunch done or literal sequence
// calculate length of sequence (zp_len)
    lda tabl_bi - 1, x
    jsr get_bits
    adc tabl_lo - 1, x
    sta zp_len_lo
    lda zp_bits_hi
    adc tabl_hi - 1, x            // c = 0 after this
    sta zp_len_hi
    ldx zp_len_lo
    lda #0
// reuse latest offset or not
    bit zp_ro_state
    bmi test_reuse
no_reuse:
    sta zp_bits_hi
    lda #$e1
    cpx #$03
    bcs gbnc2_next
    lda tabl_bit - 1, x
gbnc2_next:
    asl zp_bitbuf
    bne gbnc2_ok
    tax
    jsr get_crunched_byte
    rol
    sta zp_bitbuf
    txa
gbnc2_ok:
    rol
    bcs gbnc2_next
    tax
// calculate absolute offset (zp_src)
    lda tabl_bi, x
    jsr get_bits
    adc tabl_lo, x
    sta zp_src_lo
    lda zp_bits_hi
    adc tabl_hi, x
    adc zp_dest_hi
    sta zp_src_hi
    ldx zp_len_lo
// main copy loop
copy_next:
    tya
    bne copy_skip_hi
    dec zp_dest_hi
    dec zp_src_hi
copy_skip_hi:
    dey
    bcs get_literal_byte
    lda (zp_src_lo), y
literal_byte_gotten:
    sta (zp_dest_lo), y
    dex
    bne copy_next
    lda zp_len_hi
    stx zp_bits_hi
    beq next_round
copy_next_hi:
    dec zp_len_hi
    jmp copy_next
// test for offset reuse
test_reuse:
    bvs no_reuse
    asl zp_bitbuf
    bne gbnc1_ok
    pha
    jsr get_crunched_byte
    rol
    sta zp_bitbuf
    pla
gbnc1_ok:
    rol
    beq no_reuse                  // bit == 0 => C=0, no reuse
    bne copy_next                 // bit != 0 => C=0, reuse previous offset
// exit or literal sequence handling
exit_or_lit_seq:
    beq decr_exit
    jsr get_crunched_byte
    sta zp_len_hi
    jsr get_crunched_byte
    tax
    bcs copy_next
decr_exit:
    rts
get_literal_byte:
    jsr get_crunched_byte
    bcs literal_byte_gotten
// static table for bits+offset for lengths 1 and 2: %10001100, %11100010
tabl_bit:
    .byte $8c, $e2

.segment Vars
// 156-byte table area; may be clobbered between decrunches.
decrunch_table:
tabl_bi: .fill ENCODED_ENTRIES, 0
tabl_lo: .fill ENCODED_ENTRIES, 0
tabl_hi: .fill ENCODED_ENTRIES, 0
