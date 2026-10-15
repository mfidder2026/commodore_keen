// Memory layout. All segments are defined here; keep docs/memorymap.md in sync.
// M0: only the BASIC stub and code are in use.

.const VIC_BANK_BASE = $c000       // VIC-II looks at bank 3 ($c000-$ffff)
.const SCREEN_A      = $c000
.const SCREEN_B      = $c400
.const CHARSET       = $c800

.segmentdef Basic [start=$0801]
.segmentdef Code  [startAfter="Basic", max=$4fff]
.segmentdef Vars  [start=$0200, max=$07ff, virtual]

.file [name="commander-keen-c64.prg", segments="Basic,Code"]
