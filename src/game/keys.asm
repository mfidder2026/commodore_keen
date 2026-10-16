// Keyboard as a second joystick: W A S D for the directions, RETURN for fire. Called
// from input_read; the bits are added to `joy`.
//
// Keyboard matrix (C64-Wiki, "Keyboard", Keyboard Matrix): a row is selected by a 0 bit
// in CIA1 port A ($DC00), the pressed keys of that row read as 0 bits in port B ($DC01).
// Joystick 2 shares the port A lines, so joystick and keys at the same time can show
// ghost keys; either one on its own reads correctly.
//
// Imported after the rest of the game code: inserting code before actors.asm shifts its
// page alignment, which costs a frame now and then in level 14 (docs/budget.md).

.const KB_ROWS   = 3              // keyboard rows scanned (PA0-PA2)
.const KEY_COUNT = 5              // keys in the key_* table

.segment Code

// Keyboard rows 0-2 (port A bits 0-2 low) into kb_rows, 1 bits = pressed. ~90 cycles.
keys_scan:
    ldx #KB_ROWS - 1
!:  lda kb_select, x
    sta $dc00
    lda $dc01
    eor #$ff
    sta kb_rows, x
    dex
    bpl !-
    lda #$ff
    sta $dc00                     // no row selected again: port A reads joystick 2
    rts

// Add the keys in kb_rows to `joy` as joystick bits (table key_*). ~100 cycles.
keys_decode:
    ldx #KEY_COUNT - 1
!:  ldy key_row, x
    lda kb_rows, y
    and key_mask, x
    beq keys_next
    lda joy
    ora key_joy, x
    sta joy
keys_next:
    dex
    bpl !-
    rts

kb_select: .byte %11111110, %11111101, %11111011    // rows PA0, PA1, PA2
//                 W         A          S          D          RETURN
key_row:   .byte 1,         1,         1,         2,         0
key_mask:  .byte %00000010, %00000100, %00100000, %00000100, %00000010
key_joy:   .byte JOY_UP,    JOY_LEFT,  JOY_DOWN,  JOY_RIGHT, JOY_FIRE

.segment Vars
kb_rows:    .fill KB_ROWS, 0      // keyboard rows 0-2, 1 = pressed
.segment Code
