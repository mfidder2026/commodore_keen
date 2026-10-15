// Zero page allocation. Every zero page variable is declared here, nowhere else.
// The game owns $02-$7f. The KERNAL (used only while loading) keeps $90-$ff.

.label zp_frame      = $02         // frame counter, incremented by the raster IRQ
.label zp_ptr0       = $03         // general purpose pointer (2 bytes)
.label zp_ptr1       = $05         // general purpose pointer (2 bytes)
.label zp_map        = $07         // map pointer for the renderer (2 bytes)
.label zp_dst        = $09         // screen pointer for the renderer (2 bytes)
.label zp_tmp0       = $0b
.label zp_tmp1       = $0c
.label zp_tmp2       = $0d
.label zp_tmp3       = $0e
.label zp_irq_ptr    = $0f         // pointer used only inside the IRQ (2 bytes)
.label zp_tiles      = $11         // 20 tile numbers of the row being rendered ($11-$24)
.label zp_game       = $30         // $30-$7f: game logic (see game/*.asm)
