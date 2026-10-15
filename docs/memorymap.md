# Memory map

Source of truth: `src/memory.asm` (segments) and `src/zp.asm` (zero page). The target layout is in PLAN.md under "Geheugenkaart".

## In use (M0)

| Address | Content | Segment |
| --- | --- | --- |
| `$0002` | `zp_frame`, frame counter | zp.asm |
| `$0003–$0004` | `zp_ptr0`, general purpose pointer | zp.asm |
| `$0801–` | BASIC stub with the `SYS` line | Basic |
| after the stub, up to `$4fff` | engine and game code | Code |

M0 still uses the default VIC bank 0 with screen RAM at `$0400`. The switch to bank 3 (`$c000`) comes in M3.

## Open point

The KERNAL also uses zero page during level loading. Before M3, decide which zero page addresses to save and restore around a KERNAL LOAD, or reserve them up front.
