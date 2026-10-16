# Status

Last update: 16 October 2026 (night session).

## Milestones

| Milestone | Status | Proven by |
| --- | --- | --- |
| M0 Toolchain | done, except the C64U deploy test (C64 was off) | `test_toolchain.py`, `test_vice.py` |
| M1 Converter: reading | done | `test_original.py`, DOSBox comparison (`-m dosbox`) |
| M2 Converter: C64 assets | done; previews in `build/assets/preview_*.png` still need your approval | `test_c64.py` |
| M3 Scroll engine | done in VICE; C64U not tested | `test_scroll.py` (pixel-exact, 0 lost frames) |
| M4 Keen | done; physics measured in DOSBox, **not yet checked against the source** | `test_player.py`, `test_collision.py` |
| M5 Tiles and items | done | `test_level.py` (level 1 start to exit in VICE), `test_items.py` |
| M6 Enemies | done; **behaviour is an estimate** | `test_actors.py`, frame rate test |
| M7 Map and flow | done; full playthrough proven for part of the levels only (see below) | `test_flow.py` |
| M8 Sound | effects done; **no music** (needs tunes with permission) | `test_sound.py` |
| M9 Polish | partly: sfx main program, README, three engine bugs fixed (raster IRQ line, zero page, SID read) | — |
| M10 NTSC | done in VICE: detection, equal game speed (5 ticks per 6 frames), sound tempo and pitch, faster colour update. Not on a real NTSC machine | `test_scroll.py` and the frame rate test on PAL and NTSC |

## NTSC

The first colour RAM update (17,800 cycles) was longer than an NTSC frame. The update is now generated at startup as unrolled code at `$A600` (14,500-14,900 cycles, PAL benefits too), and scrolling on NTSC is pixel-exact without lost frames in the scroll test. With many enemies (level 14) NTSC drops to 20 fps for a moment now and then (PAL stays at 25 fps or more); see docs/budget.md.

## Waiting on your decision or approval

1. **Reconstructed source (K1n9_Duk3)**: download it from the Keen modding forum into `reference/keen13-src/`. Physics (docs/physics.md), enemy behaviour (docs/actors.md) and the world map's teleporter destinations are estimates or guesses until they are checked against it.
2. **Music**: choose SID tunes (CC0/CC-BY or with the composer's permission); record them in docs/credits.md.
3. **C64 Ultimate**: `python tools/deploy.py` with `C64U_HOST`; play-test the controls (M4 acceptance: "lekker spelen").
4. **Graphics**: approve the converted levels (build/assets/preview_lNN.png) or point out levels to touch up. The colours are limited by the C64 (3 shared colours per level plus 1 own colour per character).
5. **Fastloader**: a Krill loader would make loading much faster; that is a download that needs your approval.

## Known limitations and deviations

- Loading uses the KERNAL: about 30-40 s from a real 1541 at startup, 5-10 s per level.
- Enemies: 8 hardware sprites, no multiplexer; with more on screen they flicker.
- Animated tiles all run in phase; foreground tiles are not drawn in front of sprites.
- Yorp statues (message tiles), light switches and in-level teleporters are not implemented.
- Short jumps are not possible (jump height is fixed); not yet compared with the original.
- Highscores are not saved; no option for the alternative control layout yet.
- The map Keen collides only with his feet (more forgiving than the full sprite).

## Playability evidence

`tools/bot_all.py` lets a simple bot (walk right, jump at obstacles) play every level in py65 with the real game code. It finishes levels 1, 2, 5 and 6; the others need routes to the left, keycards, the pogo stick or getting past enemies, which this bot cannot do. That does not mean those levels are unbeatable, but it is not proven yet.
