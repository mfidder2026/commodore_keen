# Status

Last update: 16 October 2026.

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
| M9 Polish | partly: sfx main program, README, alternative control layout (F1), engine bugs fixed (raster IRQ line, zero page, SID read, camera clamp) | `test_controls.py` |
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
- Highscores are not saved. The alternative control layout (fire jumps) is chosen with F1 on the title screen.
- Keyboard: W A S D and RETURN act as a second joystick (tested in py65 on the decoding; the CIA scan itself only on paper, from the C64-Wiki matrix). Joystick and keys at the same time can give ghost keys.
- An item touched in the same tick as the exit is now collected before the level ends (level 16: the everclear lies right next to the exit). The original's order is not checked against the source.
- The map Keen collides only with his feet (more forgiving than the full sprite).

## Playability evidence

`tools/planner.py` searches joystick input with the real game code in py65; the routes replay identically in VICE (`tests/scenarios/test_routes.py`).

| Levels | Result |
| --- | --- |
| 1, 2, 3, 5, 6, 7, 8, 9, 10, 11 | finished from a fresh game, replayed in VICE without losing a life |
| 4 | finished with ammunition carried in (a Garg blocks the way otherwise) |
| 13, 14, 16 | finished with the pogo stick (and ammunition) carried in, in py65 |
| 12, 15 | no route found yet (search limit) |

`tools/episode.py` chains the world map and levels 1, 3, 4, 5, 7, 8, 16 with the carried state (raygun shots from levels 1 and 3, the pogo stick from level 5). Levels 1-8 are planned with three ship parts and all lives. **Blocking:** level 16 with the everclear. The everclear (103,10) lies in a one-tile pocket next to the exit (104,9-10); the pocket is only reachable through the open column above the exit, and the corridor to its left is one tile high with deadly tiles. A brute-force test (Keen dropped from every free position above the exit, with many joystick sequences, with and without pogo) always touches the exit before the everclear, so with the C64 version's touch rules the everclear cannot be collected. The original must end the level differently (e.g. only when Keen is fully inside the exit, or on the ground). That rule has to come from the reconstructed source (`reference/keen13-src`, download not yet approved); until then the full playthrough (`tests/scenarios/test_episode.py`) cannot run.
