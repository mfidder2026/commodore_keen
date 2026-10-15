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

// Player (game/player.asm). Positions in 1/16 pixel, sprite top-left corner.
.label p_x           = $30         // 2 bytes
.label p_y           = $32         // 2 bytes
.label p_vx          = $34         // signed
.label p_vy          = $35         // signed
.label p_ground      = $36         // 1 = standing on something
.label p_facing      = $37         // 0 = right, 1 = left
.label p_sprite      = $38         // Keen sprite number to show
.label p_anim        = $39         // animation tick counter
.label p_pogo        = $3a         // 1 = on the pogo stick
.label joy           = $3b         // input bits, 1 = pressed (see game/input.asm)
.label joy_prev      = $3c
.label joy_new       = $3d         // pressed this tick
.label c_tmp         = $3e         // collision temporaries ($3e-$4f)
.label box_left      = $40         // collision box in pixels (2 bytes each)
.label box_right     = $42
.label box_top       = $44
.label box_bottom    = $46
.label t_col         = $48         // tile column / row being tested
.label t_row         = $49
.label t_end         = $4a
.label new_x         = $4b         // 2 bytes
.label new_y         = $4d         // 2 bytes
.label p_has_pogo    = $4f

// Current actor work area (game/actors.asm).
.label o_x           = $50         // 2 bytes, 1/16 px
.label o_y           = $52         // 2 bytes
.label o_vx          = $54
.label o_vy          = $55
.label o_ground      = $56
.label o_box_l       = $57
.label o_box_r       = $58
.label o_box_t       = $59
.label o_box_b       = $5a
.label p_frozen      = $5b         // ticks Keen stays frozen (ice)
.label o_bl16        = $5c         // box offsets in 1/16 px (2 bytes each, this order:
.label o_br16        = $5e         // left, right, top, bottom + 1 px)
.label o_bt16        = $60
.label o_bb16        = $62
