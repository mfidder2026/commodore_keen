# Commodore Keen — instructies voor Claude Code

## Doel
Commodore Keen: Commander Keen 1 (episode 1) als onofficiële fanport voor de stock PAL C64, in 6502-assembly.
PLAN.md bevat ontwerp, mijlpalen en acceptatiecriteria. Lees het bij elke nieuwe sessie.

## Harde regels
- Doelmachine: stock PAL C64, 64 KB, 1541. Geen REU, geen turbo. NTSC pas in de laatste mijlpaal.
- Besturing: joystick met één knop in poort 2 (indeling in PLAN.md). Muziek en effecten op de SID.
- Commit nooit iets uit data/original/, reference/ of build/. Er komt geen id-data in git.
- Gebruik geen SID-tune zonder vastgelegde toestemming of licentie in docs/credits.md.
- Werk één mijlpaal tegelijk af. Klaar = alle acceptatiecriteria aantoonbaar gehaald.
- Gedrag van Keen en vijanden komt uit reference/keen13-src. Gok niet; noem bestand en functie.
- Hardwarefeiten (VIC-II, SID, CIA) haal je uit documentatie, niet uit je geheugen.

## Commando's
- python tools/build.py    bouwt build/commodore-keen.d64
- python tools/test.py     pytest, py65-tests en VICE-scenario's
- python tools/run.py      start de build in VICE
- python tools/deploy.py   start de build op de C64 Ultimate (env C64U_HOST, optioneel C64U_PASSWORD)
- python -m tools.convert  decodeert data/original/ naar build/original/ (PNG's, summary.json)
- python tools/test.py -m dosbox   vergelijkt de converter met Keen 1 in DOSBox (traag, opent een venster)

Renders, schermafbeeldingen en andere afgeleide id-data blijven in build/; tests slaan alleen
aantallen en hashes op. Uitzondering (16 oktober 2026, goedgekeurd): de README-schermafbeeldingen in
docs/screenshots/ (python tools/screenshots.py). De speelbare .d64 gaat alleen als bestand bij een
GitHub-release (https://github.com/mfidder2026/commodore_keen), nooit in git. Formaten en bevindingen staan in docs/formats.md.

Hulpmiddelen (tools/):
- bot.py / planner.py / episode.py: invoer zoeken die een level of het hele spel uitspeelt,
  met de echte 6502-code in py65 (deterministisch, speelt identiek af in VICE)
- hangcheck.py / pcsample.py / vicemon.py: VICE binary monitor; waar hangt of wacht de CPU
- longbranch.py: maakt te verre branches lang (jeq/jne/... uit src/macros.asm)
- dosbox_capture.py / measure_keen.py: het origineel meten in DOSBox

Valkuilen die al eens misgingen:
- $D011 nooit read-modify-write zonder `and #$7f` (bit 7 = raster-MSB, schrijven verzet de IRQ-lijn).
- `sta` zet geen vlaggen: test een waarde opnieuw (tax/lda) voor beq/bne.
- KickAssembler: .const vóór gebruik definiëren; gegenereerde tabellen in een echt segment importeren.
- SID-registers zijn alleen-schrijven; KERNAL SAVE overschrijft geen bestaand bestand.

Tools staan in de gedeelde map `../c64` (java, kick, vice, dosbox). Volgorde: omgevingsvariabele
(JAVA, KICKASS_JAR, VICE_DIR, DOSBOX, EXOMIZER), dan C64_TOOLS (standaard ../c64), dan `.tools/`,
dan het PATH. Zie tools/toolchain.py en docs/toolchain.md.

## Codeconventies (KickAssembler)
- Geheugenindeling alleen via segmenten in src/memory.asm; werk docs/memorymap.md bij.
- Zero page wordt centraal toegewezen in src/zp.asm.
- Snelheden, sprongen en timers staan in tabellen per tik, nooit als losse getallen in code (nodig voor NTSC).
- Labels en commentaar in het Engels; snake_case voor labels, UPPER_CASE voor constanten.
- Zet bij elke hot loop het aantal cycli in commentaar.
- Zelfmodificerende code alleen met een SMC:-commentaar en een ADR.

## Definition of done per wijziging
- Alle tests groen; nieuwe logica heeft een test.
- Rastertijd gemeten en docs/budget.md bijgewerkt.
- Referentiebeelden in tests/golden/ alleen bijwerken als het beeld bewust verandert.
- Architectuurkeuze gemaakt? Schrijf een ADR in docs/decisions/.

## Als je vastloopt
Stop, beschrijf wat je geprobeerd hebt en welke keuze nodig is, en vraag het mij.
