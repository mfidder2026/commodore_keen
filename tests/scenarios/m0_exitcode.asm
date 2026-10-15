// M0 scenario: proves the headless test loop works.
// Waits 50 PAL frames on the raster, then reports the result to the VICE debug
// cartridge: writing a value to $d7ff makes VICE exit with that value as exit code.

.const DEBUG_CART_EXIT = $d7ff
.const RASTER          = $d012
.const FRAMES          = 50

BasicUpstart2(start)

start:
    sei
    ldx #FRAMES
wait_frame:
    lda RASTER
    cmp #$ff                        // wait until raster line $ff ...
    bne wait_frame
wait_leave:
    lda RASTER
    cmp #$ff                        // ... and until it has passed
    beq wait_leave
    dex
    bne wait_frame

    lda #0                          // 0 = pass
    sta DEBUG_CART_EXIT
    jmp *
