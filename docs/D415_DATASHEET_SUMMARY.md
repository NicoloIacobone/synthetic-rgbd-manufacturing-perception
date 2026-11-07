# Intel RealSense Depth Camera D415: dati letti dal datasheet ufficiale

Riepilogo per la verifica manuale. Le sezioni 1–8 contengono solo ciò che è stampato nel datasheet. La sezione 9 elenca ciò che il datasheet **non** dice. La sezione 10 è un confronto con il nostro modello: è un mio ragionamento e **non** fa parte dell'attestazione.

## Documento letto

| Campo | Valore |
|---|---|
| Titolo | Intel® RealSense™ Product Family D400 Series Datasheet (p. 1) |
| Revisione | **Revision 017, September 2023** (p. 1) |
| Numero documento | 337029-017 (p. 1) |
| File | `docs/Intel-RealSense-D400-Series-Datasheet-September-2023.pdf`, 169 pagine, solo locale (escluso da git) |
| SHA-256 | `4f74ae650f1c17ca5cc9e731de322733f9d9f7fee8e1daec7a9e0126e79354b7` |
| Provenienza | Metadati del PDF: creato con Safari il 2026-11-06, titolo `https:/www.realsenseai.com/wp-content/uploads/2023/10/Intel-RealSense-D400-Series-Datasheet-September-2023` |

**Numeri di pagina:** su tutte le pagine tranne la copertina, che non ha piè di pagina, il numero stampato coincide con la pagina del PDF, quindi "p. 41" vale per entrambi. Unica anomalia: il piè di pagina di p. 15 riporta `337029-012` invece di `337029-017`.

## Attestazione e suoi limiti

**Attesto** che ogni valore delle sezioni 1–8 è stato letto il 2026-11-06 da questo file, alla pagina indicata, e che nessuno viene dalla memoria, da altre fonti o dalle revisioni precedenti.

**Metodo:**
- `T` = testo estratto con `pdftotext -layout`, pagina per pagina.
- `T+I` = testo estratto e riscontro a vista sull'immagine della pagina, per escludere colonne scambiate. Pagine viste: 16, 22, 41, 43, 45, 71, 76, 81, 91, 92, 93.

**Limiti:**
- Il PDF non ha firma digitale. L'ufficialità poggia sull'URL nei metadati e sul fatto che lo hai scaricato tu: non l'ho verificata in modo indipendente.
- Questa è la dichiarazione di un assistente AI, non una certificazione di terzi. Le citazioni servono proprio perché tu possa ricontrollare.
- La frase nella colonna "Come stampato" è riportata in inglese, così puoi cercarla nel PDF. In alcune tabelle ho unito parametro e valore in una riga.

## 1. Identità del prodotto

La camera è la **Depth Camera D415**, che contiene il **Depth Module D415**. Per questo i dati delle tabelle "modulo" valgono anche per la camera: il legame è la riga "Depth module" di p. 71.

| Dato | Come stampato | Pagina | Fonte | Metodo |
|---|---|---|---|---|
| Modulo montato nella camera | "Depth module: Intel® RealSense™ Depth module D415" | 71 | Table 3-49 | T+I |
| Componenti | D4 √; Standard Stereo Imagers √; Standard Infrared Projector √; RGB color sensor √; IMU x | 22 | Table 2-2 | T+I |
| Codici prodotto | "Depth Camera D415 — J72476-100 — 82635ASRCDVKHV — 961443 — N/A" | 76 | Table 3-56 | T+I |
| Principio | "uses stereo vision to calculate depth"; "a left imager, right imager, and an optional infrared projector" | 18 | §2.3 | T |

## 2. Geometria stereo e campo visivo

| Dato | Come stampato | Pagina | Fonte | Metodo |
|---|---|---|---|---|
| **Baseline** | "Baseline 55mm" | 71 (anche 41) | Table 3-49, Table 3-11 | T+I |
| **FOV profondità, HD 16:9** | "H:65 / V:40 / D:72" (gradi) | 71 (anche 41) | Table 3-49, Table 3-11 | T+I |
| FOV profondità, VGA 4:3 | "H:50 / V:40 / D:61" | 71 (anche 41) | Table 3-49, Table 3-11 | T+I |
| A che distanza vale il FOV | "Depth FOV specified at 20 cm for D401 and at 2 m for other modules" | 71 (anche 42) | Note 2 | T+I |
| Tolleranza FOV | "can vary from lens to lens and module to module by ~ +/- 3 degrees" | 71 (anche 42) | Note 3 | T+I |
| Da D415 Features | "Depth diagonal field of view over 70°" | 15 | Cap. 1 | T |
| FOV profondità a distanza Z | Depth FOV = HFOV/2 + tan⁻¹{tan(HFOV/2) − B/Z}, con "HFOV = Horizontal Field of View of left imager" | 88 | §4.4 | T |
| Definizione del FOV profondità | "the shared overlap of the individual left and right imagers' fields of view" | 88 | §4.3 | T |

## 3. Sensori IR sinistro e destro

Tutti da **Table 3-12, p. 43** ("Standard Left and Right Imager Properties – D410/D415"), metodo T+I.

| Dato | Come stampato |
|---|---|
| Sensore | OmniVision Technologies OV2740 |
| Pixel attivi | 1920 × 1080 |
| Rapporto | 16:9 |
| Formato | 10-bit RAW |
| Apertura | f/2.0 |
| Focale | 1.88 mm |
| **Filtro** | **None** |
| Fuoco | Fixed |
| **Otturatore** | **Rolling Shutter** |
| **FOV orizzontale** | **71° ± 1°** |
| FOV verticale | 44° ± 1° |
| FOV diagonale | 79° ± 1° |
| Distorsione | <= 1.5% |

Altri dati sui sensori:

| Dato | Come stampato | Pagina | Fonte | Metodo |
|---|---|---|---|---|
| Filtro sulla camera | "Filter: All pass" | 71 | Table 3-49 | T+I |
| Otturatore e FPS | "Dual rolling shutter sensors for up to 90 FPS depth streaming" | 15 | Cap. 1 | T |

## 4. Proiettore IR

Da **Table 3-16, p. 45** ("Standard (D41x) Infrared Projector Parameters"), metodo T+I, salvo dove indicato.

| Dato | Come stampato | Pagina |
|---|---|---|
| Pattern | "Pattern Type: Static" | 45 |
| Sorgente | "Vertical-cavity surface-emitting laser (VCSEL) + Optics" | 45 |
| Controllo | "Laser Controller: PWM" | 45 |
| Potenza ottica | "360 mW average" | 45 |
| **Lunghezza d'onda** | "850 nm ± 10 nm nominal @ 20°C" | 45 |
| Classe laser | "Class 1, IEC 60825-1:2007 Edition 2, IEC 60825-1:2014 Edition 3" | 45 |
| **Campo di proiezione (A)** | H 64°±3°, V 41°±3°, D 72°±3° | 45, Table 3-16 |
| **Campo di proiezione (B)** | "H:67 / V:41 / D:75" | 71 Table 3-49; 41 Table 3-11 |
| Scopo | "projecting a static infrared pattern on the scene to increase texture on low texture scenes" | 45 |
| Potenza impostabile | "Manual Laser Power (mW)", "30 mW steps", min 0, max 360 (T) | 100, Table 4-21 |
| Protezione termica | "if stereo depth module temperature is >60°C, laser power is halved" (T) | 50, Table 3-26 |

**Il datasheet è incoerente con se stesso:** i valori orizzontali e diagonali del campo di proiezione differiscono tra (A) e (B).

## 5. Formati e distanza minima

| Dato | Come stampato | Pagina | Fonte | Metodo |
|---|---|---|---|---|
| **Profondità** | "Z [16 bits]"; 1280 x 720 a 6, 15, 30 FPS | 81 | Table 4-2 | T+I |
| **Immagini sinistra e destra** | "Y8 [8 bits]", "Luminance Left and Right Imager"; 1280 x 720 a 6, 15, 30 FPS | 81 | Table 4-2 | T+I |
| Colore dal sensore sinistro | "UYVY [16 bits]", "Color Stream from Left Imager (D410 & D415)" | 81 | Table 4-2 | T+I |
| RGB | "YUY2 [16 bits]", fino a 1920 x 1080 a 6, 15, 30 FPS | 81 | Table 4-2 | T+I |
| Limite sugli stream | "Streaming of Depth, IR left and IR right concurrently is only supported for calibration" | 84 | Note 5 di Table 4-5 | T |
| **Min-Z, 1280×720** | **450 mm** | 91 | Table 4-11 | T+I |
| Min-Z, altre risoluzioni | 848x480: 310; 640x480: 310; 640x360: 240; 480x270: 180; 424x240: 160 mm | 91 | Table 4-11 | T+I |
| Portata | "Range 0.3 m to over 4 m (varies with lighting conditions)" | 16, seguito di p. 15 | Cap. 1 | T+I |

## 6. Convenzioni della profondità

| Dato | Come stampato | Pagina | Fonte | Metodo |
|---|---|---|---|---|
| Metodo | "correlating points on the left image to the right image and via the shift between a point" | 19 | §2.3 | T |
| **Z, non distanza lungo il raggio** | "a measurement from the parallel plane of the imagers and not the absolute range" | 19 | §2.3 | T |
| **Banda invalida a sinistra** | "This non-overlapped region (at the left edge of the frame) contains no depth data" | 89 | §4.5 | T |
| Larghezza della banda | "Invalid Depth Band (in Pixels) = B ∗ F/Z" | 90 | §4.5 | T |
| Limite della formula | "valid for a base configuration of camera settings"; il firmware predefinito può cambiare la larghezza reale | 90 | §4.5 | T |
| Origine X-Y | "the X-Y center of the left imager" | 97 | §4.8.1 | T |
| Origine Z sulla camera | "referenced from front of the camera cover glass" | 93 | §4.8 | T+I |
| Scarto Z' | "D415 -1.1 mm" | 97 | Table 4-16 | T |

## 7. Qualità della profondità dichiarata

Colonna "D410/D415 (<= 2 Meters and 80% ROI, HD Resolution)".

| Metrica | Valore | Definizione stampata (Table 4-12, p. 92) | Pagina | Metodo |
|---|---|---|---|---|
| **Z-accuracy** | **± 2%** | "difference for valid pixels relative to a ground truth surface" | 92, Table 4-14 | T+I |
| **Fill rate** | **≥ 99%** | "Percentage of pixels that have valid depth values" | 92, Table 4-14 | T+I |
| **RMS Error (Spatial Noise)** | **≤ 2%** | "total spatial noise for each valid pixel relative to a best fit plane" | 92, Table 4-14 | T+I |
| Temporal Noise | ≤ 1% | "total temporal noise for each valid pixel relative to a best fit plane" | 93, Table 4-14 | T+I |
| Lifetime | 4 years | "operating in default settings … up to 16 hours a day [66%]" | 93 | T+I |

**Condizioni di misura, da leggere insieme ai valori:**
- "measured using a texture-less (white) target with default laser power (150mW) and auto exposure enabled" (p. 93, nota 4, T+I).
- "validated at the factory and reflect typical conditions" (p. 93, nota 1, T+I).
- "taken within 80% of this FOV" (p. 91, §4.7, T+I).

## 8. Controlli, meccanica e potenza

| Dato | Come stampato | Pagina | Fonte | Metodo |
|---|---|---|---|---|
| Esposizione manuale | "Control sensor exposure period", 1–166 ms | 100 | Table 4-21 | T |
| Guadagno manuale | "Control sensor digital gain", 16–248, "Gain 1.0 = 16" | 100 | Table 4-21 | T |
| Auto-esposizione | "Exposure and Gain are set based on the environment condition" | 101 | Table 4-21 | T |
| Dimensioni nominali | 99 × 23 × 20 mm (larghezza, altezza, profondità) | 73 | Table 3-51 | T |
| Peso | 64 g, con "+/- 10% from the nominal" | 73, 74 | Table 3-51 e nota | T |
| Temperatura ambiente in funzione | 0–35 °C | 74 | Table 3-55 | T |
| Potenza massima, tutti i componenti | 2961.97 mW; proiettore IR 1296 mW | 113 | Table 7-7 | T |

## 9. Cosa il datasheet NON dice

Ricerca sull'intero testo estratto, senza distinguere maiuscole. **Limite:** il testo dentro le figure non è ricercabile.

| Argomento | Termini cercati | Esito |
|---|---|---|
| Comportamento su metallo o superfici riflettenti | `metal`, `shiny`, `glossy`, `specular`, `reflect` | Nessuna specifica per la D415. `metal` solo in contesti meccanici e termici (p. 40, 67, 114, 119). `specular` solo a p. 72, che confronta D435/D435i/D455 con le varianti "f", **non la D415** |
| Multipath | `multipath`, `multi-path` | Assente |
| Numero, densità o forma dei punti del pattern | `dot`, `density` | Assente |
| Speckle laser, punto caldo del proiettore | `speckle`, `hot spot`, `hotspot` | Assente |
| Disparità, intervallo di ricerca, errore in pixel | `disparity`, `subpixel`, `sub-pixel` | Assente |
| Algoritmo di matching | `SGBM`, `census`, `stereo matching` | Solo una menzione generica a p. 89 |
| Rumore del sensore IR | `noise` | Solo le metriche di profondità (p. 92–93) e una nota sulle emissioni radio (p. 137) |
| Quantità di luce ambiente | `sunlight`, `lux` | Nessun limite per la D415. `Lux` solo per le KPI della D405 (p. 93) |
| Portata ideale | `ideal range`, `working range` | Assente |

## 10. Confronto con il nostro modello

**Questa sezione non fa parte dell'attestazione.** Mette insieme valori del datasheet, file di configurazione del progetto e, dove indicato, altre fonti.

| Voce | Datasheet | Nostro modello | Esito |
|---|---|---|---|
| Baseline | 55 mm (p. 71) | 55 mm (`configs/default.yaml`) | ✅ Coincide |
| Risoluzione profondità | 1280 x 720 (p. 81) | 1280 × 720 | ✅ Coincide |
| Min-Z | 450 mm (p. 91) | 450 mm in configurazione; transizione simulata a 392 mm (f·B/126), misurata tra 0,38 e 0,40 m | ⚠️ Scarto di 58 mm, va in "what did not work" (A-67). Nessun pixel della scena è così vicino |
| Profondità Z, riferita al sensore sinistro | p. 19, 97 | Stessa convenzione | ✅ Coincide |
| Banda invalida | B·F/Z (p. 90) | Prima colonna valida a f·B/z anche dove il margine non illuminato è più largo: SGBM riempie la striscia non illuminata (A-67) | ✅ Coincide, ma il riempimento è un artefatto del matcher |
| Pattern statico, 850 nm | p. 45 | Pattern statico, riflettanza a 848 nm | ✅ Coincide |
| Campo del proiettore | 67/41 (p. 41, 71) o 64/41 (p. 45) | 67° × 41° | ✅ Una delle due versioni, va dichiarato |
| Otturatore rolling | p. 43 | Scena ferma, effetto escluso | ✅ Coerente con la nostra esclusione |
| Formato IR | Sensore 10-bit RAW (p. 43), stream 8 bit Y8 (p. 81) | 8 bit | ✅ Coincide con lo stream, ma il datasheet non dice con quanti bit lavori il matcher interno |
| **Focale** | Sensore 71° ± 1° (p. 43); FOV profondità 65° a 2 m (p. 42) | **fx = 897,25 px, da 71°** (prima 1004,6 px, da 65°) | ✅ Corretta il 6 nov 2026, vedi sotto |
| **Luce ambiente** | Filtro "None" (p. 43), "All pass" (p. 71) | **Solo proiettore, ambiente zero** nella corsa primaria; una prova descrittiva con ambiente (A-70) | ⚠️ Limite dichiarato, vedi sotto |

**Focale. Risolto il 6 nov 2026 per decisione dell'utente: la corsa primaria usa 71° (A-66, PLAN §5.12); quella a 65° resta archiviata come sensibilità descrittiva.** Il motivo è il controllo qui sotto, non i risultati. Le formule di p. 88 e p. 90 usano il FOV del *sensore*, mentre prima avevamo ricavato fx dal FOV della *profondità*.
- Con 71° su 1280 px si ottiene fx = 897,25 px, contro i 1004,6 px di prima (circa il 12% in più).
- La camera reale del dataset ROBI, che **non** è il datasheet, ha fx = 905,9 px (`data/m5/robi/zigzag.json`), pari a un FOV di 70,5°: molto più vicina a 71° che a 65°.
- Il segnale non è univoco. Min-Z 450 mm con 126 px di ricerca richiederebbe fx ≈ 1031 px, che è vicino al nostro valore; il valore 126 però viene da Carfagni, non dal datasheet.
- Il datasheet non si riconcilia da solo: la formula di p. 88 con 71° dà 69,9° a 2 m, non 65°.
- **Effetto:** a 0,9 m, 5 mm valgono ora 0,305 px da noi (0,34 px a 65°) e 0,308 px con la camera ROBI.
- **Risultato misurato a 71°, 460 viste-istanza:** C1 0,717, C2a 0,735, C2b 0,561, C3 0,070, C4 0,343 (a 65°: 0,732, 0,749, 0,590, 0,085, 0,386). La classifica non cambia e la sequenza fissa rigetta tre volte.
- **Conseguenza nota:** Min-Z con 126 px di ricerca passa a 392 mm contro i 450 mm del datasheet. Il valore 126 viene da Carfagni e non è stato toccato.

**Luce ambiente.** Un filtro "None" o "All pass" significa che la luce visibile arriva ai sensori IR, e p. 81 aggiunge uno stream a colori dal sensore sinistro.
- Questa è una mia deduzione, ma indebolisce la motivazione "cella al chiuso, quindi niente ambiente": anche al chiuso le lampade contribuiscono all'immagine.
- Il datasheet non dice quanto. Il dato che indica un contributo reale resta il confronto con ROBI: 21 DN contro i nostri 5 DN sul metallo a 71° (1,9 DN a 65°).
- **Prova del 7 nov 2026, descrittiva, scene 0–9 (A-70):** un solo livello di luce uniforme, fissato sui dev per arrivare a 21 DN; livello e spettro senza fonte. Sui pezzi di metallo si arriva a 22 DN, ma il contrasto locale resta 17 DN contro i 4,6 DN reali. C3 scende da 0,102 a 0,031, C4 da 0,265 a 0,224. Il titolo non cambia.

**Specifica contro endpoint (calcolo mio).** A 0,9 m, il ±2% vale ±18 mm. La nostra soglia di 5 mm è quindi molto più stretta di ciò che il costruttore dichiara, e la specifica vale per un bersaglio bianco, non per il metallo.

## Corrispondenza con la revisione citata finora

`docs/SOURCES.md` (voce S-01) citava la revisione 013, aprile 2022, in una copia di terze parti. I valori che usiamo sono gli stessi, ma cambiano pagine e alcuni numeri di tabella.

| Dato | Rev 013 | Rev 017 |
|---|---|---|
| Table 3-11 | p. 37 | p. 41 |
| Proprietà camera | Table 3-48, p. 64 | **Table 3-49**, p. 71 |
| Confronto D435 / D435f | Table 3-49 | **Table 3-50**, p. 72 |
| Table 3-16 | p. 40 | p. 45 |
| Controlli del laser | p. 88 | p. 100 |
| Condizioni delle KPI | p. 81, nota 5 | p. 93, nota 4 |
| Dimezzamento potenza sopra 60 °C | p. 44 | p. 50 |

Nella revisione 017, p. 88 rimanda ancora a "Table 3-48. Depth SKU Properties", mentre quella tabella ora è la 3-49. Nel report conviene citare la revisione 017.
