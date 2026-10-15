# Commander Keen 1 voor de C64 — bouwplan

Oct 15, 2026 · @Fremen

## Samenvatting en haalbaarheid

Commander Keen 1 past goed op de C64: het is een 2D-tegelspel, en soepel scrollend tegelbeeld is precies waar de C64-hardware voor gebouwd is. Een Keen-tegel van 16×16 pixels wordt 2×2 C64-tekens. Je ziet dan vrijwel hetzelfde stuk level als op de pc: 20 tegels breed. Er bestaat nog geen C64-versie, en de spellogica is beschikbaar als gereconstrueerde broncode onder GPL.

| Onderwerp | Besluit |
| --- | --- |
| Naam | Commander Keen C64, een onofficiële, niet-commerciële fanport |
| Doelmachine | Stock PAL C64 met 1541; je C64 Ultimate is testhardware; NTSC als allerlaatste stap |
| Weergave | Multicolor-tekenmodus, soepel scrollen in 8 richtingen, dubbel gebufferd |
| Tegels | 1 Keen-tegel = 2×2 tekens; eigen tekenset per level (max. 256 tekens) |
| Besturing | Joystick met één knop |
| Geluid | Effecten op de SID; gedownloade SID-muziek met toestemming of vrije licentie |
| Data | Python-converter leest jouw eigen Keen 1-sharewarebestanden |
| Spellogica | Vertaald uit de gereconstrueerde Keen 1-3-broncode (GPL) |
| Snelheid (doel) | 50 fps scrollen; 25 fps als ondergrens |
| Release | Kant-en-klare .d64 |
| Inhoud v1.0 | De hele episode 1: wereldkaart, alle levels, eindscherm |

Het grootste risico is grafisch: alle tegels van één level moeten in 256 tekens passen, met maar 4 kleuren per teken. Daarom bouwt Claude Code eerst de converter. Die meet per level hoeveel tekens en kleuren nodig zijn, nog vóór er een regel engine-code is.

## Het origineel en bestaand werk

Keen 1 is uitzonderlijk goed gedocumenteerd: de bestandsformaten zijn uitgezocht en de broncode is tot op de bit gereconstrueerd. Een C64-versie heb ik niet gevonden.

Wat we over het origineel weten:

- Id Software bracht Keen in december 1990 uit; de shareware-episode 1 (‘Marooned on Mars’) is versie 1.31.
- Het was de eerste zijwaarts scrollende EGA-game op de pc. Levels zijn opgebouwd uit tegels van 16×16 pixels, en per frame tekent het spel alleen de tegels die veranderd zijn.
- Episode 1 heeft 611 tegels. Per tegel staan animatie, gedrag en blokkering aan vier zijden in een tabel in het EXE-bestand.
- Levels zijn RLEW-gecomprimeerd en hebben twee lagen van 16-bit woorden: tegels en sprites.
- Tegels en sprites staan in EGALATCH en EGASPRIT, in episode 1 LZW-gecomprimeerd. De geluidseffecten zitten als pc-speakerdata in het EXE-bestand.

Referenties voor de developer:

| Bron | Wat het is | Licentie | Gebruik in dit project |
| --- | --- | --- | --- |
| [Gereconstrueerde Keen 1-3-broncode](https://korben.info/en/commander-keen-source-code-released-35th-anniversary.html) (K1n9\_Duk3, 2025) | C en assembly; met Turbo C++ 1.00 ontstaan bit-identieke EXE's | [GPL](https://feedbagel.com/post/commander-keen-1-3-source-code-reconstructed-and-released-under-gpl-license) | Hoofdreferentie voor fysica, AI en tegelgedrag |
| [Chocolate Keen](https://keenwiki.shikadi.net/wiki/Chocolate_Keen) | Zo trouw mogelijke nabouw van de Keen 1-3-engine | Broncode beschikbaar | Gedrag naast elkaar vergelijken |
| [CloneKeen](https://clonekeen.sourceforge.net/index.html@nav=download) | Kloon in C | GPLv3 | Leesbare tweede bron |
| [Commander Genius](https://build.opensuse.org/projects/games/packages/commandergenius/files/commandergenius.spec?expand=0) | Interpreter voor Keen 1-6 in C++ | GPL-2.0-only | Alleen ter controle, geen code overnemen |
| [ModdingWiki](https://moddingwiki.shikadi.net/wiki/Commander_Keen_1) | Beschrijving van alle bestandsformaten | — | Basis voor de converter |
| [mrcrowbar](https://mrcrowbar.readthedocs.io/en/stable/mrcrowbar.lib.games.keen.html) | Python-klassen voor Keen-formaten, LZW en RLEW | Nog controleren | Startpunt of ter vergelijking voor de converter |
| [Master System-port](https://www.generationamiga.com/2026/07/06/commander-keen-1-gets-a-sega-master-system-port-after-35-years/) (2026) | 8-bit-port van Keen 1 | — | Bewijs dat Keen 1 op 8-bit past |

De maker van de reconstructie zet die zelf niet op GitHub; je haalt hem via het Keen-modforum. Commander Genius gebruiken we alleen om te vergelijken: de GPL-2.0-only-licentie botst met GPLv3-code.

## Doelplatform en tooling

Het spel moet speelbaar zijn op een stock PAL C64 (0,985 MHz, 64 KB, 1541) en draait daarmee ook op je C64 Ultimate. Turbo gebruiken we niet: een platformspel moet op elke C64 even snel aanvoelen. Alles werkt vanaf de commandoregel, zodat Claude Code zelf bouwt, test en op je C64 Ultimate start.

| Rol | Keuze | Waarom |
| --- | --- | --- |
| Assembler | KickAssembler 5.x (Java) | Segmenten voor de geheugenindeling, macro's, labels exporteerbaar naar VICE |
| Converter en tooling | Python 3 met Pillow en pytest | Keen-bestanden lezen, tekensets bouwen, alles testbaar |
| Emulator | [VICE 3.10](https://vice-emu.sourceforge.io/vice_2.html), `x64sc` | Cycle-exact; `-limitcycles`, `-exitscreenshot` en de debug-cartridge maken headless tests mogelijk; `c1541` bouwt de .d64 |
| Referentie-origineel | DOSBox met jouw Keen 1-bestanden | Opnames van het origineel om gedrag mee te vergelijken |
| Unit-tests 6502 | py65 (6502-simulator in Python) | Botsing, fysica en tabellen testen zonder emulator |
| Debugger | VICE-monitor en Retro Debugger | Rastertijd, geheugen en breakpoints live bekijken |
| Handwerk graphics | CharPad en SpritePad | Tekens en sprites na automatische conversie bijwerken |
| Compressie en laden | Exomizer; KERNAL LOAD in v1 | Werkt overal; later een Krill-fastloader voor stock-snelheid |
| Echte hardware | [REST-API van de Ultimate](https://1541u-documentation.readthedocs.io/en/master/_sources/api/api_calls.rst.txt), `POST /v1/runners:run_prg` | Na elke build het spel direct op je C64U starten |
| AI-koppeling (optioneel) | MCP-server [Ultimate64MCP](https://github.com/martijn-devrev/ultimate64mcp) | Claude Code kan zelf programma's starten en geheugen uitlezen op de C64U |

Installeer op je Windows-machine Java 17+, Python 3.11+, VICE 3.10, KickAssembler, Exomizer, DOSBox en Git, allemaal in het PATH. Claude Code controleert in M0 of elk commando werkt en legt de versies vast.

## Architectuur

&#91;embedded content: architectuur · pc-bouwtijd en C64-speltijd\]

De converter op de pc doet het zware omzetwerk: decoderen, kleuren kiezen en tekens ontdubbelen. De C64 laadt per level kant-en-klare data en hoeft alleen nog te scrollen, te tekenen en te spelen.

## Technisch ontwerp

De engine is een klassieke C64-scroller in multicolor-tekenmodus, met per level een eigen tekenset en sprites voor alles wat beweegt. Dit is een eerste ontwerp; Claude Code legt afwijkingen vast in `docs/decisions/` en houdt `docs/memorymap.md` bij.

### Tegels en kleuren

- Eén Keen-tegel van 16×16 pixels wordt 2×2 tekens van 4×8 dikke pixels. Horizontaal halveert de resolutie, verticaal blijft die gelijk.
- Het scherm van 40×25 tekens toont 20 tegels breed, net als het origineel. Tijdens het scrollen staat de 38-kolommenmodus aan.
- Per teken zijn er 4 kleuren: 3 gedeeld over het hele scherm (achtergrond, `$D022`, `$D023`) en 1 eigen kleur uit kleur-RAM. Die eigen kleur moet een van de kleuren 0–7 zijn.
- De converter kiest per level de 3 gedeelde kleuren en ontdubbelt tekens over alle gebruikte tegels heen. Zo past een level binnen 256 tekens, met reserve voor bewegende tegels.

### Scrollen

- Fijn scrollen via `$D016` en `$D011`, grof scrollen elke 8 pixels door naar een tweede scherm-RAM te kopiëren en met `$D018` te wisselen.
- Het kopiëren van scherm-RAM wordt verspreid over de frames vóór de wissel. Kleur-RAM kan niet dubbel gebufferd worden en wordt in het wisselframe bijgewerkt, achter de rasterstraal aan.
- Kleurt elk teken altijd in dezelfde kleur, dan haalt de engine kleur-RAM via een tabel op tekennummer. Dat maakt de kopie eenvoudig en voorspelbaar.

### Sprites

- Keen, vijanden en schoten zijn multicolor-sprites van 12×21 dikke pixels: 3 kleuren plus transparant. Grotere figuren gebruiken 2 of 4 sprites.
- Een sprite-multiplexer laat meer dan 8 sprites per beeld toe, met een harde grens van 8 per rasterlijn.
- Actoren buiten beeld worden niet getekend en, zoals in het origineel, pas actief als ze in de buurt komen.

### Geheugenkaart (eerste versie)

| Adres | Inhoud | Grootte |
| --- | --- | --- |
| `$0002–$00FF` | Zero page: speler, camera, pointers | 254 B |
| `$0200–$07FF` | Variabelen, actortabellen, buffers | 1,5 KB |
| `$0800–$4FFF` | Engine- en spelcode, opzoektabellen | 18 KB |
| `$5000–$8FFF` | Levelkaart, 1 byte per tegel | 16 KB |
| `$9000–$97FF` | Tegeltabel: 4 tekennummers, kleur en eigenschappen | 2 KB |
| `$9800–$BFFF` | Actordata, geluidseffecten, loader | 10 KB |
| `$C000–$C7FF` | Scherm-RAM A en B | 2 KB |
| `$C800–$CFFF` | Tekenset van het huidige level | 2 KB |
| `$D000–$DFFF` | I/O; RAM eronder voor wereldkaart en statusscherm | 4 KB |
| `$E000–$FFF9` | Spritevormen (max. 127) en IRQ-vectoren | 8 KB |

De VIC-II kijkt naar bank 3 (`$C000–$FFFF`). BASIC- en KERNAL-ROM staan tijdens het spelen uit; de KERNAL komt alleen terug bij het laden van een level.

### Framebudget (ontwerp, te meten in M3)

Een PAL-frame duurt 19.656 cycli. Na badlines en sprite-DMA blijven er naar schatting zo'n 17.000 over.

| Taak | Budget per frame (cycli) |
| --- | --- |
| Scherm-RAM kopiëren, verspreid over frames | 2.500 |
| Nieuwe randtegels tekenen | 1.000 |
| Sprite-multiplexer | 2.000 |
| Speler, fysica en botsing | 1.500 |
| Actoren (tot 8 actief) | 3.000 |
| Geluidseffecten | 600 |
| Reserve | 6.400 |

In het wisselframe kost kleur-RAM bijwerken tot ongeveer 8.000 cycli extra; daar is de reserve voor. Lukt 50 fps niet, dan zakt het spel netjes naar 25 fps.

### Spellus en invoer

- Een raster-IRQ op 50 Hz stuurt de lus. De gamelogica draait op een vaste tik; snelheden uit het origineel worden omgerekend naar die tik.
- Invoer: een joystick met één knop in poort 2, plus twee toetsen. Snelheden en sprongen staan in tabellen per tik, zodat de NTSC-versie later alleen andere tabellen nodig heeft.

Op de pc heeft Keen aparte toetsen voor springen en pogo. Op de C64 springt Keen met de joystick omhoog, de gebruikelijke indeling bij C64-platformspellen, zodat de knop vrij is voor schieten:

| Actie | Besturing |
| --- | --- |
| Lopen | Joystick links of rechts |
| Springen | Joystick omhoog |
| Schieten | Knop |
| Pogo aan of uit | Joystick omlaag + knop, of spatiebalk |
| Level binnengaan op de wereldkaart | Knop |
| Status en pauze | RUN/STOP |

Claude Code test in M4 of dit lekker speelt. Een alternatieve indeling, met de knop als springen, komt in het optiemenu.

## Concessies ten opzichte van het origineel

De levels, de besturing van Keen en het gedrag van de vijanden blijven gelijk; de concessies zitten vooral in beeld, geluid en invoer.

| Onderdeel | Origineel (pc) | C64-versie | Waarom |
| --- | --- | --- | --- |
| Resolutie | 320×200, 16 kleuren per pixel vrij | 160×200 dikke pixels; 4 kleuren per teken van 4×8 | Multicolor-tekenmodus van de VIC-II |
| Tegels | 611 tegels in één tegelset | Per level max. 256 tekens; tegels die niet passen worden vereenvoudigd of samengevoegd | Eén tekenset per scherm |
| Graphics | EGA-palet, fijne details van 1 pixel breed | Omgezet naar C64-palet en met de hand bijgewerkt | Horizontale resolutie halveert |
| Sprites | Vrij in grootte en kleur | Multicolor-sprites, 3 kleuren; max. 8 op één rasterlijn | Hardware-sprites van de VIC-II |
| Geluid | Pc-speakereffecten | Dezelfde effecten op de SID | Ander geluidschip; plus gedownloade SID-muziek |
| Besturing | Aparte toetsen voor springen en pogo | Joystick met één knop: omhoog springt, de knop schiet | Joystick met één knop |
| Opslag | Alles op harde schijf | Per level laden van diskette | 64 KB werkgeheugen |
| Opslaan | Spel opslaan op schijf | In v1.0 alleen highscores; savegames daarna | Schrijven naar disk is veel extra werk |

## Data, naam en rechten

De repo bevat geen enkel bestand van id Software: de converter leest jouw eigen Keen 1-sharewarebestanden en maakt de .d64 lokaal. Dat is hetzelfde model als DOOM-NES, en het houdt je code vrij te delen.

- **Sharewarebestanden.** Episode 1 is als shareware vrij te downloaden. Zet de bestanden in `data/original/`; die map staat in `.gitignore`.
- **Delen.** Je publiceert een kant-en-klare .d64, zoals Wolf64 ook deed. Die bevat omgezette Keen-graphics en levels, en dat is juridisch een grijs gebied. Houd het daarom gratis en niet-commercieel, zet er een duidelijke disclaimer bij, en haal het offline als de rechthebbende daarom vraagt.
- **Licentie van je code.** Vertaal je logica uit de gereconstrueerde broncode, dan wordt jouw code een afgeleide en valt die ook onder de GPL. Controleer welke GPL-versie de reconstructie gebruikt, en meng geen code uit bronnen met een onverenigbare versie.
- **Naam.** ‘Commander Keen’ is een merknaam van de rechthebbende. De titel wordt ‘Commander Keen C64’. Zet in de README en op het titelscherm dat het een onofficiële, niet-commerciële fanport is, zonder band met id Software.
- **Muziek.** Alle tunes in de HVSC, de grote SID-verzameling, zijn auteursrechtelijk beschermd; buiten privégebruik heb je toestemming van de componist nodig. Vraag die per tune en zet de componist op het creditscherm, of kies tunes met een vrije licentie, zoals CC0-tunes op [OpenGameArt](https://opengameart.org/content/melodic-adventure-theme-and-rhythmic-variation-c64-style). Bron: [HVSC-copyrightverklaring](https://hafnium.prg.dtu.dk/HVSC/C64Music/DOCUMENTS/HVSC.txt).

## Repostructuur en CLAUDE.md

Exporteer dit document als Markdown naar `PLAN.md` in de repo, en zet de CLAUDE.md hieronder ernaast. Dan werken jij en Claude Code vanuit dezelfde bron.

```
commander-keen-c64/
├── CLAUDE.md
├── PLAN.md                ← dit document, geëxporteerd
├── data/original/         ← jouw Keen 1-sharewarebestanden (niet in git)
├── reference/keen13-src/  ← gereconstrueerde broncode, alleen lezen (niet in git)
├── tools/
│   ├── convert/           ← converter: formaten, tekensets, sprites, geluid
│   └── build.py  test.py  run.py  deploy.py
├── src/
│   ├── engine/            ← scrollen, multiplexer, IRQ, loader
│   ├── game/              ← speler, actoren, tegelgedrag, wereldkaart
│   ├── sound/             ← SID-effecten
│   └── main.asm  memory.asm  zp.asm
├── tests/
│   ├── unit/              ← py65-tests
│   ├── scenarios/         ← invoeropnames voor VICE
│   └── golden/            ← referentieschermafbeeldingen
├── build/                 ← gegenereerde assets en .d64 (niet in git)
└── docs/
    ├── memorymap.md  budget.md  formats.md
    └── decisions/         ← ADR's
```

```markdown
# Commander Keen C64 — instructies voor Claude Code

## Doel
Commander Keen 1 (episode 1) als onofficiële fanport voor de stock PAL C64, in 6502-assembly.
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
- python tools/build.py    bouwt build/commander-keen-c64.d64
- python tools/test.py     pytest, py65-tests en VICE-scenario's
- python tools/run.py      start de build in VICE
- python tools/deploy.py   start de build op de C64 Ultimate (env C64U_HOST)

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
```

## Mijlpalen

Elf mijlpalen, in vaste volgorde; na elke mijlpaal volgt een demo op je C64 Ultimate en jouw akkoord voordat de volgende begint. De converter en de scroll-spike staan bewust vooraan, omdat daar de grootste risico's zitten.

1. **M0 — Toolchain en skelet**
   - Doel: repo, build-, test-, run- en deployscript; een leeg programma start.
   - Klaar als: `build.py` maakt een .d64; een testprogramma geeft via de debug-cartridge een exitcode terug in VICE; `deploy.py` start het op de C64U; alle toolversies staan in `docs/`.
2. **M1 — Converter: het origineel lezen**
   - Doel: alle formaten van episode 1 decoderen: EGA-header en tileinfo uit het EXE, EGALATCH en EGASPRIT (LZW), levels (RLEW) en geluiden.
   - Klaar als: elk level en de wereldkaart worden als PNG gerenderd en kloppen met schermafbeeldingen uit DOSBox; de converter telt 611 tegels; pytest is groen.
3. **M2 — Converter: C64-assets**
   - Doel: per level een tekenset, tegeltabel, kaart en kleurkeuze; sprites omgezet naar multicolor.
   - Klaar als: een rapport per level toont het aantal tekens (doel ≤ 240) en de kleurconflicten; een preview-PNG toont elk level zoals de C64 het tekent; jij keurt de previews van drie levels goed.
4. **M3 — Scroll-engine (spike)**
   - Doel: met de joystick door een omgezet level scrollen in 8 richtingen.
   - Klaar als: 50 fps zonder scheuren of verkeerde kleuren op loopsnelheid, in VICE én op de C64U; de rastertijd per onderdeel staat in `docs/budget.md`.
5. **M4 — Keen: lopen, springen, pogo en botsing**
   - Doel: Keen-fysica uit de reconstructie, botsing via tileinfo, een camera die Keen volgt, de joystickindeling met één knop.
   - Klaar als: sprong- en pogohoogte, loopsnelheid en vallen komen overeen met opnames uit DOSBox; py65-tests dekken de botsingsroutines; jij vindt dat de besturing lekker speelt.
6. **M5 — Tegelgedrag en items**
   - Doel: punten, scheepsonderdelen, sleutelkaarten en deuren, dodelijke en geanimeerde tegels, de uitgang.
   - Klaar als: één level is volledig uit te spelen, van start tot uitgang.
7. **M6 — Vijanden en schieten**
   - Doel: alle vijanden en obstakels van episode 1, zoals Yorps, Gargs en Vorticons, plus het straalpistool en de sprite-multiplexer.
   - Klaar als: het gedrag per type klopt met de reconstructie; nooit meer dan 8 sprites op één rasterlijn; het spel zakt nergens onder 25 fps.
8. **M7 — Wereldkaart en spelverloop**
   - Doel: titelscherm met de naam Commander Keen C64 en disclaimer, wereldkaart, levels in- en uitgaan, levens, score, statusscherm en eindscherm.
   - Klaar als: de hele episode is van begin tot eind uit te spelen in VICE.
9. **M8 — Geluid en muziek**
   - Doel: pc-speakereffecten omgezet naar de SID, plus gedownloade SID-tunes voor titelscherm, wereldkaart en eindscherm. Claude Code verplaatst elke tune met [sidreloc](https://www.linusakesson.net/software/sidreloc/index.php) naar het actorgebied (`$9800–$BFFF`), dat buiten de levels vrij is.
   - Klaar als: elk effect uit het origineel heeft een SID-versie; voor elke tune staan toestemming of licentie in `docs/credits.md` en staat de componist op het creditscherm; effecten kosten in levels minder dan 600 cycli per frame.
10. **M9 — Afwerking en release**
    - Doel: snellere laadtijden met een Krill-variant, eventueel een EasyFlash-.crt, highscores en een optiemenu met de alternatieve besturing.
    - Klaar als: een volledige playthrough op de C64U zonder fouten; een README met bouwinstructies en disclaimer; de kant-en-klare .d64 is klaar om te publiceren.
11. **M10 — NTSC-versie**
    - Doel: het spel ook laten draaien op NTSC-machines, die op 60 Hz lopen en per frame minder rekentijd hebben dan PAL.
    - Klaar als: PAL of NTSC wordt automatisch herkend; spelsnelheid, muziektempo en toonhoogte zijn op beide gelijk; het framebudget is voor NTSC opnieuw gemeten; getest in VICE en op de C64U in NTSC-modus.

## Test- en verificatiestrategie

Claude Code test zonder dat jij hoeft te kijken: de meeste controles draaien headless, en echte hardware komt alleen aan het eind van elke mijlpaal.

| Laag | Wat wordt getest | Hoe |
| --- | --- | --- |
| Converter | Decoderen van formaten, tekenaantallen, kleurkeuze | pytest met vaste referentie-PNG's per level |
| 6502-routines | Botsing, fysica, opzoektabellen, vermenigvuldigen | py65 roept de routine aan en vergelijkt het resultaat met Python |
| Volledig spel | Scrollen, beweging, vijanden | VICE headless met `-limitcycles`; het programma meldt via de debug-cartridge geslaagd of mislukt |
| Beeld | Geen grafische fouten | `-exitscreenshot` na een vaste invoeropname, vergeleken met `tests/golden/` |
| Gedrag | Fysica en AI gelijk aan het origineel | Dezelfde invoer in DOSBox en op de C64 afspelen; posities per tik vergelijken |
| Snelheid | Framebudget | Randkleur per onderdeel in een meetbuild; cycli per frame bijhouden in `docs/budget.md` |
| Hardware | Timing, laden, invoer | Starten op de C64U via de REST-API; jij speelt kort mee en geeft akkoord |

Determinisme maakt dit mogelijk: de gamelogica gebruikt een vaste tik en een eigen pseudo-randomgenerator met vaste seed. Dezelfde invoer geeft dan altijd hetzelfde spelverloop.

## Risico's en open beslissingen

De twee grootste risico's, tekenbudget en kleur-RAM, worden in M2 en M3 al gemeten, zodat er vroeg een terugvaloptie gekozen kan worden.

| Risico | Gevolg | Maatregel |
| --- | --- | --- |
| Een level heeft meer dan 256 unieke tekens nodig | Grafische fouten of ontbrekende tegels | Converter meet het in M2; tegels vereenvoudigen of samenvoegen; desnoods een level in twee tekensets splitsen |
| Kleur-RAM bijwerken kost te veel tijd | Schokkerig of gescheurd scrollen | Terugval: per level één vaste kleur in kleur-RAM (4 kleuren voor het hele level), of 25 fps |
| Te veel sprites op één rasterlijn | Flikkerende vijanden | Multiplexer met prioriteit; Keen altijd zichtbaar; flikkeren boven 8 accepteren |
| Andere tik dan het origineel | Springen en lopen voelen anders | Snelheden omrekenen naar 50 Hz en vergelijken met DOSBox-opnames |
| Een levelkaart is groter dan 16 KB | Past niet in het geheugen | Converter rapporteert de grootte; kaart comprimeren per rij of in delen laden |
| Rechten op graphics en naam | Project moet offline | Geen id-data in de repo; de .d64 gratis en met disclaimer; offline halen als de rechthebbende daarom vraagt |
| GPL-versies botsen | Code mag niet samen verspreid worden | Eén codebron (de reconstructie); licentie controleren in M0 |

Beslissingen van 15 oktober 2026, en wat nog open staat:

- [x] Besturing: joystick met één knop (indeling bij Spellus en invoer).
- [x] Publicatie: een kant-en-klare .d64.
- [x] Naam: Commander Keen C64.
- [x] Muziek: ja, eigen muziek op de SID.
- [x] NTSC: ja, als allerlaatste mijlpaal (M10).
- [ ] Muziek wordt gedownload: kies de tunes en vraag per tune toestemming aan de componist, of kies tunes met een vrije licentie (CC0 of CC-BY).
- [ ] Speelt de joystickindeling lekker? Beoordelen na M4.

## Bronnen

- [Commander Keen 1-3 – ModdingWiki](https://moddingwiki.shikadi.net/wiki/Commander_Keen_1)
- [Commander Keen 1-3 Level format – ModdingWiki](https://moddingwiki.shikadi.net/wiki/Commander_Keen_1-3_Level_format)
- [Keen 1-3 Tileinfo format – ModdingWiki](https://moddingwiki.shikadi.net/wiki/Keen_1-3_Tileinfo_format)
- [Commander Keen EGA Header – ModdingWiki](https://moddingwiki.shikadi.net/wiki/Commander_Keen_EGA_Header)
- [Commander Keen's Adaptive Tile Refresh – Fabien Sanglard](https://fabiensanglard.net/ega/)
- [Gereconstrueerde broncode Keen 1-3 – Korben](https://korben.info/en/commander-keen-source-code-released-35th-anniversary.html)
- [Reconstructie onder GPL – Feedbagel](https://feedbagel.com/post/commander-keen-1-3-source-code-reconstructed-and-released-under-gpl-license)
- [Chocolate Keen – Keen Wiki](https://keenwiki.shikadi.net/wiki/Chocolate_Keen)
- [CloneKeen](https://clonekeen.sourceforge.net/index.html@nav=download)
- [Commander Genius – openSUSE-pakket](https://build.opensuse.org/projects/games/packages/commandergenius/files/commandergenius.spec?expand=0)
- [mrcrowbar Keen-module](https://mrcrowbar.readthedocs.io/en/stable/mrcrowbar.lib.games.keen.html)
- [Commander Keen 1 op de Master System – Generation Amiga](https://www.generationamiga.com/2026/07/06/commander-keen-1-gets-a-sega-master-system-port-after-35-years/)
- [Keen 1 shareware-infokaart – DOS Games Archive](https://archived.software/QmcHirAhxKuJcj9mwawLp1qCFUBiGzt2gSgFPvxQ7ZmZbr/5drH4yE2f8R6KQwbTPaoBm7c8rSNLQ/raw/KEEN-Info-Card.txt)
- [VICE-commandoregelopties](https://vice-emu.sourceforge.io/vice_2.html)
- [Ultimate REST-API](https://1541u-documentation.readthedocs.io/en/master/_sources/api/api_calls.rst.txt)
- [Ultimate64MCP](https://github.com/martijn-devrev/ultimate64mcp)
- [DOOM-NES (model voor converter op eigen data)](https://kedikatstudios.itch.io/doom-nes)
