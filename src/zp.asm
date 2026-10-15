// Zero page allocation. Every zero page variable is declared here, nowhere else.
// $00/$01 are the CPU port; the game owns $02-$ff while the KERNAL is banked out.

.label zp_frame      = $02         // frame counter, incremented by the raster IRQ
.label zp_ptr0       = $03         // general purpose pointer (2 bytes)
