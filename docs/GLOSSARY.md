# Dizionario delle sigle

Per tenere sul secondo schermo mentre leggi le risposte degli agent. Cerca con `Cmd+F`.

- **Se una sigla non c'è:** chiedi all'agent che l'ha usata di aggiungerla qui (è una regola in `CLAUDE.md`).
- **In caso di contrasto** valgono i file di origine indicati in ogni sezione (`docs/PLAN.md`, `docs/ASSUMPTIONS.md`, `docs/SOURCES.md`). Questo file riassume e va corretto.
- **Aggiornato a:** 7 nov 2026, prova sulla densità dei punti. Lo stato del lavoro non è qui, è in `docs/STATUS.md`.

## 1. Sigle che si confondono

Controlla prima qui. Sono le coppie che somigliano di più.

| Se leggi | È | Da non confondere con |
|---|---|---|
| `A1` | Il test principale del Task A: ICP con partenza spostata di 10 mm / 10° | `A-01` = assunzione n. 1. `A#1` = riga 1 della sezione A di `AI_USE_LOG.md` |
| `A2` | Test opzionale del Task A: registrazione globale, poi ICP. Non è stato fatto | `A-02` = assunzione sulla scadenza |
| "metriche A" | I numeri del Task A | Le assunzioni `A-xx` |
| `H0`, `H1`, `H2`, `H3` | Varianti dell'algoritmo ICP (senza trattino). `H3` è quella in uso | `H-1`, `H-2` = ipotesi scientifiche (con trattino) |
| `D1`…`D15` | Decisioni approvate, in PLAN §2 | `D415` = la camera. `D4` = il chip di Intel. `D = 0.015` = lobo diffuso del metallo. `D` (lettera) = opzione bright matte |
| `C1`…`C4` | Le condizioni di profondità confrontate | `(C)` = opzione rifiutata (A-53). `C2a`/`C2b` sono due livelli di `C2` |
| `R1`…`R7` | Rischi, in PLAN §8 | `r02`, `r04` = passate con roughness 0.2 e 0.4 |
| `§5.8` senza altro | Sezione del **piano** (`docs/PLAN.md`) | "report §5" o la colonna Report di ASSUMPTIONS = sezione del **report PDF** |
| Àncora `(a)`, `(b)`, `(c)` | Confronti esterni (piano, ROBI, metriche BOP) | Opzione `(a)` in A-11, A-33, A-50: scelte diverse, solo stessa lettera |
| `(i)`…`(iv)` | Criteri del gate M3, in A-38 | Meccanismi `(i)`, `(ii)` del metallo, in A-54 e A-58 |
| "opzione 1, 2, 3" | Dipende dal messaggio. Le ultime sono quelle per il gate fallito (sezione 7) | `3a`/`3b` = gate M3. `1(b)`, `2(b)`, `3(c)`, `4(a)` = revisione pre-M4 |
| "step 1…7" | Passi di M5 nello `STATUS.md` | "M4 step 1, 2, 3" = passi di M4 |
| `M1`…`M6` | Milestone | "Phase 0, 1" = fasi: 0 pianificazione, 1 esecuzione |

## 2. Come leggere i riferimenti con §

Da solo, il simbolo § indica una sezione di `docs/PLAN.md`.

| Riferimento | Contenuto |
|---|---|
| §1 | Criteri di successo per ogni requisito |
| §2 | Decisioni approvate `D1`…`D15` |
| §3 | Effetti inclusi ed esclusi, cosa non si fa, portata delle affermazioni |
| §4 | Pipeline |
| **§5** | **Protocollo dell'esperimento, congelato al tag `protocol-v1`** |
| §5.1 | Condizioni `C1`…`C4` |
| §5.2 | Task A: stima della posa |
| §5.3 | Task B: presa a ventosa |
| §5.4 | Metriche |
| §5.5 | Statistica |
| §5.6 | Primary endpoint (il risultato principale) |
| §5.7 | Ipotesi `H-1`, `H-2` |
| §5.8 | Controlli di robustezza: filtri SGBM "strict" contro "loose" su 10 scene; àncora (a) |
| §5.9 | Guasti attesi, tra cui "ICP scivola lungo i prismi" |
| §5.10 | Scene dev e test, seed, accoppiamento |
| **§5.11** | **Sanity check su C1 a offset zero: è il gate fallito ora** |
| §5.12 | Registro delle deviazioni dal protocollo (6 righe) |
| §6 | Consegna minima e lavoro opzionale |
| §7 | Milestone e gate |
| §8 | Rischi `R1`…`R7` |

Sezioni del report PDF, da `docs/REPORT_PLAN.md`: 1 problema, 2 camera, 3 pipeline, 4 modello di camera, 5 disegno dell'esperimento, 6 risultati e cosa non ha funzionato, 7 limiti, 8 riflessione, 9 nota sull'AI.

## 3. Condizioni di profondità

Fonti: PLAN §5.1, `src/synthrgbd/conditions.py`. Le cartelle sono dentro ogni scena (`data/m5/synthrgbd/train_pbr/<scena>/`).

| Sigla | Cos'è | Ruolo | Cartella |
|---|---|---|---|
| `C1` | Profondità ideale del simulatore | Limite superiore; usata per il sanity check | `depth` |
| `C2a` | Ideale + rumore gaussiano, ε_d = 0.08 px | Baseline ingenua, solo descrittiva | `depth_c2a` |
| `C2b` | Ideale + rumore gaussiano, ε_d = 0.234 px (tarato su Carfagni a 1 m; 0.262 px a 65°) | Baseline ingenua usata nei test | `depth_c2b` |
| `C3` | Stereo simulato, parti di metallo, roughness 0.15 | **Il modello di camera** | `depth_stereo_metal` |
| `C4` | Stereo simulato, parti opache, albedo 0.25 (0.247 a 65°) | Isola l'effetto del materiale | `depth_stereo_matte` |
| `C3r02`, `C3r04` | Come C3 con roughness 0.2 e 0.4 | Descrittive, 50 scene (A-51) | `depth_stereo_r02`, `_r04` |
| `C3nogloss` | Come C3 senza riflessi | Descrittiva: com'era prima del bug fix (A-57) | `depth_stereo_nogloss` |
| `C4bright` | Come C4 con albedo 0.5 | Descrittiva: separa "scuro" da "opaco" (A-52) | `depth_stereo_bright` |
| `C3loose`, `C4loose` | C3 e C4 con uniqueness e speckle spenti. Il controllo sinistra-destra è **rimasto acceso**, anche se §5.8 chiedeva di spegnerlo (voce 18 di `docs/M5_OPEN_ITEMS.md`) | §5.8, scene 0–9 | `depth_stereo_metal_loose`, `_matte_loose` |
| `C3nouniq`, `C3nolr`, `C3nospeckle` | C3 con un filtro spento alla volta. **`C3nolr` è identica a C3:** il valore −1 non spegne il controllo sinistra-destra in OpenCV 5.0.0 | §5.8, solo classi del sensore | `depth_stereo_metal_nouniq`, ecc. |
| `C3redraw1`, `C3redraw2` | Stesse immagini IR e stesso matcher, nuovo rumore casuale | Misura la variabilità di C3 (A-59) | `depth_stereo_metal_redraw1`, `2` |
| `C3looselr`, `C4looselr` | C3 e C4 con tutti e tre i filtri spenti: uniqueness, speckle e controllo sinistra-destra (valore 1000) | Rifacimento del §5.8, scene 0–9 (A-63) | `depth_stereo_metal_looselr`, `depth_stereo_matte_looselr` |
| `C3nolr1000` | C3 con il solo controllo sinistra-destra spento davvero | §5.8, solo classi del sensore (A-63) | `depth_stereo_metal_nolr1000` |
| `C3e1`, `C4e1` | C3 e C4 con rumore IR più basso: `e_per_dn` 1 invece del valore in configurazione | Descrittive, scene 0–9 (A-64) | `depth_stereo_metal_e1`, `depth_stereo_matte_e1` |
| `C3shuf`, `C3sym`, `C3both` | C3 con gli errori rimescolati nello spazio dentro ogni parte, con il segno casuale, o entrambe le cose. `C3both` è il miglior rumore additivo possibile per parte: stesse ampiezze, media nulla, indipendente | Controllo della struttura dell'errore, scene 0–9 (A-73) | `depth_stereo_metal_shuf`, `_sym`, `_both` |
| `C3amb`, `C4amb` | C3 e C4 con luce ambiente aggiunta alla radianza del proiettore, un solo livello fissato sui dev | Descrittive, scene 0–9 (A-70) | `depth_stereo_metal_amb`, `depth_stereo_matte_amb` |
| `C3dots10k`, `C4dots10k` | C3 e C4 con un nuovo render a 10 000 punti invece di 30 000 | Descrittive, scene 0–9 (A-74) | `depth_stereo_metal_dots10000`, `depth_stereo_matte_dots10000` |

**Dal 6 nov 2026 la corsa primaria è a 71° (A-66):** fx 897,25 px, C2b 0,234 px, dati in `data/hfov71/`. I valori attuali sono in `configs/`; quelli della corsa archiviata a 65° sono tra parentesi.

Solo C1, C2a, C2b, C3 e C4 sono condizioni del protocollo. Le altre non entrano mai nei test confermativi.

## 4. Varianti di ICP (harness)

Fonti: ledger sotto A-45, `scripts/select_harness.py`, `configs/harness.yaml`.

| Sigla | Cosa fa | Stato |
|---|---|---|
| `H0` | Uno stadio: corrispondenze fino a 15 mm, Tukey 5 mm, filtro back-face | §5.11 (A-62): primo giro 452/459, secondo giro 459/459 |
| `H1` | Tre stadi da grossolano a fine (20, 10, 5 mm), filtro back-face | §5.11 (A-62): primo giro 452/459, secondo giro 459/459 |
| `H2` | H1 + visibilità ray-cast | Ha fallito il sanity check con il bug della cache (416/459). Bug corretto il 5 nov (ade985f, A-62): secondo giro 459/459. Superata da H3 su dev |
| `H3` | H2 + limite a ogni passo (5 mm, 5°) | Scelta a M4; superata da H2 dopo il fix dei riflessi. **In uso** (scelta su dev il 5 nov, A-62). §5.11: primo giro 421/459 con il bug della cache, secondo giro 459/459 |
| `solver: lm` | ICP scritto da noi, smorzato (Levenberg-Marquardt) | Candidato al primo giro del §5.11 (A-62), con stadi 20/10/5: non passa. Escluso dal secondo giro: non ha test e guadagna una sola vista rispetto a H1 |

## 5. Task, metriche, ipotesi

Fonti: PLAN §5.2–5.7, A-60.

| Sigla | Significato |
|---|---|
| Task A | Stima della posa 6D con ICP sul modello CAD. È il task principale |
| Task B | Scelta di un punto di presa con ventosa da 10 mm di raggio. Riesce solo sulle staffe (A-33) |
| `A1` | Task A con partenza dalla posa vera spostata di 10 mm e 10° |
| sweep | Lo stesso test con spostamenti 2/2, 5/5, 10/10, 20/20 (mm/gradi) |
| `A2` | Opzionale, non fatto: registrazione globale FPFH + RANSAC, poi ICP |
| MSSD | Errore di posa in mm: il vertice peggiore, tenendo conto delle simmetrie del pezzo |
| recall@5 mm | Frazione di casi con MSSD < 5 mm |
| **Primary endpoint** | Recall@5 mm in A1. È il numero principale dell'esperimento |
| `H-1` | Ipotesi: recall C1 ≥ C2 > C3. Solo "C2b > C3" è testata; "C1 ≥ C2" è descrittiva |
| `H-2` | Ipotesi: recall C3 ≠ C4 |
| fixed sequence | Test in ordine fisso, α = 0.05: C1 vs C3 → C2b vs C3 → C3 vs C4. Se uno non è significativo, i successivi sono solo esplorativi |
| regola A-60 | Un confronto è significativo solo se McNemar dà p < 0.05 **e** l'intervallo bootstrap al 95% esclude lo 0 |
| instance-view | Un pezzo visto in una vista. È l'unità di conteggio (test: 459) |

## 6. Milestone e gate

Fonte: PLAN §7, `docs/STATUS.md`.

| Sigla | Contenuto | Stato al 4 nov sera |
|---|---|---|
| Phase 0 | Pianificazione, ricerca, verifica delle fonti | Fatta il 3 nov |
| `M1` | BlenderProc funzionante su questo Mac | Fatta |
| `M2` | Pezzi, scene con fisica, output BOP | Fatta |
| `M3` | Immagini IR, proiettore, SGBM, test sul piano | Fatta, con un criterio fallito di poco e accettato (3a) |
| `M4` | Modello di camera, scelta dei parametri su dev, pilota | Fatta |
| `M5` | Render di test, metriche, statistica | **Chiusa il 2026-11-05** (risultati in `data/m5/results_v2/`). Dubbi e cose non fatte in `docs/M5_OPEN_ITEMS.md` |
| `M6` | Report e README | Da fare |

Scadenze: metriche A entro ven 6 nov; bozza del report gio sera; code freeze sab 7 nov 20:00; invio previsto dom 8 nov 18:00; scadenza dom 8 nov 23:59 CET.

Passi di M5 nello `STATUS.md`: step 1 controllo del meccanismo (fatto); 2 passate extra (fatto); 3 render di test (fatto); 4 sanity (fallito al primo giro, passa al secondo; scelta H3); 5 metriche (fatte); 6 push (fatto); 7 ROBI (da fare).

## 7. Opzioni con etichetta

Le lettere e i numeri valgono solo nel loro contesto.

| Etichetta | Contesto | Significato | Esito |
|---|---|---|---|
| Opzione 1 | Gate §5.11, 4 nov sera | Diagnosticare prima su C1 a offset zero | Scelta il 5 nov (A-62) |
| Opzione 2 | Gate §5.11 | Passare subito a H3 e rifare il check | Non scelta |
| Opzione 3 | Gate §5.11 | Rilassare la soglia o restringere il check | Non scelta: la soglia non si tocca (A-62) |
| `3a` | Gate M3 criterio (iii) | Tenere stereo e impostazioni, documentare il fallimento marginale | Scelta |
| `3b` | Gate M3 criterio (iii) | Speckle window a 200 px | Rifiutata |
| `1(b)` | Revisione pre-M4 | Tenere §5.6, fixed sequence, C2b a 0.26 px | Scelta |
| `2(b)` | Revisione pre-M4 | ROBI dopo venerdì | Scelta; poi ROBI è diventato obbligatorio (A-55) |
| `3(c)` | Revisione pre-M4 | Tenere il pixel-locking, niente correzione subpixel | Scelta |
| `4(a)` o `4a` | Revisione pre-M4 | Auto exposure per frame sull'immagine sinistra di C3 | Scelta |
| `(a)` | A-33, §5.12 riga 1 | Tenere geometria e ventosa; Task B riportato per tipo di pezzo | Scelta |
| `(a)` | A-11 | Metallo C3 con roughness 0.15 da fonte MERL | Scelta |
| `(a)` | A-50 | Check di planarità a due lati sulla prima superficie colpita | Scelta |
| `(B)` | Avvio M5 (A-51) | Roughness 0.2 e 0.4 su tutte le 50 scene | Scelta |
| `(C)` | Avvio M5 (A-53) | Cambiare la roughness principale | Rifiutata |
| `(D)` | Avvio M5 (A-52) | Passata opaca chiara, albedo 0.5 | Scelta |
| Route 3 | D6 | Stereo fisico simulato: è il modello di camera | Scelta |
| Route 2 | D7 | Modello a regole sull'immagine, solo come ripiego | Non usata |
| Mecc. `(i)` | A-54, A-58 | Riflessi dei punti sul metallo | Attivo con i riflessi accesi |
| Mecc. `(ii)` | A-54, A-58 | SGBM riempie zone senza texture | Attivo |
| Àncora `(a)` | D5 | Test su piano opaco contro formula e Carfagni | Obbligatoria, fatta |
| Àncora `(b)` | D5, A-55 | Confronto con il dataset ROBI | Da fare dopo M5 |
| Àncora `(c)` | D5 | Metriche BOP con simmetrie | Obbligatoria, in uso |
| Criterio `(i)` | A-38, gate M3 | Bias medio < 1% della distanza | Passato |
| Criterio `(ii)` | A-38 | Pixel validi ≥ 95% | Passato |
| Criterio `(iii)` | A-38 | Distanza minima: ≤ 5% validi a ≤ 0.43 m | Fallito di poco (5.03%, 5.07%), accettato |
| Criterio `(iv)` | A-38 | Banda sinistra invalida entro ±10% | Passato |

## 8. Decisioni `D1`…`D15`

Fonte: PLAN §2.

| Sigla | Decisione |
|---|---|
| `D1` | Task A pose principale, Task B suction in parallelo |
| `D2` | Pezzi: profili a T e staffe a L generati da codice |
| `D3` | Strumenti: BlenderProc 2.8; analisi in Python con Open3D e OpenCV |
| `D4` | Camera di riferimento: Intel RealSense D415 |
| `D5` | Àncore esterne (a), (b), (c) |
| `D6` | Modello di camera: Route 3 (stereo fisico); il rumore da datasheet è solo la baseline |
| `D7` | Ripiego: Route 2, mai attivato |
| `D8` | 1280×720, camera a 0.65–0.95 m, inclinazione ≤ 30° |
| `D9` | Disegno dell'esperimento dopo revisione avversariale |
| `D10` | Scene dev 1000–1004, scene test 0–49, mai mischiate |
| `D11` | Tolleranza di planarità della ventosa: 1.0 mm |
| `D12` | Il sanity check è ICP a offset zero su C1 (§5.11) |
| `D13` | SGBM gira nel nostro ambiente Python, non dentro Blender |
| `D14` | Ambiente separato per BlenderProc con patch per macOS |
| `D15` | Impostazione di M3: proiettore, punti, criteri del gate, regola sulla risoluzione |

## 9. Assunzioni `A-01`…`A-73`

Fonte: `docs/ASSUMPTIONS.md`, che contiene dettagli, stato e misure.

| Sigla | In breve |
|---|---|
| `A-01` | Riflessione e nota AI contano nelle 8 pagine |
| `A-02` | Scadenza dom 8 nov 23:59 CET |
| `A-03` | Cella al chiuso: niente sole né IR ambientale |
| `A-04` | Scena ferma: niente motion blur |
| `A-05` | I pezzi generati rappresentano quelli reali |
| `A-06` | Il robot conosce il CAD dei pezzi |
| `A-07` | Segmentazione data per risolta: maschere vere fornite |
| `A-08` | Profondità grezza, senza filtri Intel |
| `A-09` | Errori di calibrazione esclusi |
| `A-10` | SGBM approssima il matcher D415 abbastanza per confronti relativi |
| `A-11` | Materiale metallo: riflettanza 0.868, roughness 0.15 |
| `A-12` | Modello di rumore IR: shot + read, stessa estrazione per C3 e C4 |
| `A-13` | ε_d = 0.08 px, livello di C2a |
| `A-14` | Livello di C2b da Carfagni: ε_d = 0.234 px a 71° (0.26 px a 65°) |
| `A-15` | Atteso C1 ≈ C2 perché ICP media il rumore |
| `A-16` | Min-Z 450 mm: i pezzi sono sempre oltre |
| `A-17` | L'unità indipendente è la scena |
| `A-18` | Effetto rilevabile (MDE) con 50 scene |
| `A-19` | Parametri della ventosa |
| `A-20` | Simmetrie: profilo 8, staffa 2 |
| `A-21` | 5 mm come soglia sensata (senza fonte) |
| `A-22` | Multipath non modellato di proposito |
| `A-23` | BlenderProc gira su macOS 27.2 con patch |
| `A-24` | Regola di luminosità di C4: albedo 0.25 a 71° (0.247 a 65°) |
| `A-25` | Ricerca di 126 px emulata con 128 + maschera |
| `A-26` | 5 scene dev bastano per i parametri |
| `A-27` | Il sanity a offset zero rivela i bug |
| `A-28` | Intrinseci della camera e z-depth |
| `A-29` | Accoppiamento: stesse estrazioni casuali tra condizioni |
| `A-30` | Lo sweep muove mm e gradi insieme |
| `A-31` | 10 000 ricampionamenti bootstrap bastano |
| `A-32` | Export IR lineare da Blender |
| `A-33` | Geometria dei pezzi; la ventosa entra solo sulle staffe |
| `A-34` | Modello della scena: vassoio, caduta fisica, camera |
| `A-35` | Come si generano verità e maschere |
| `A-36` | Campo del proiettore 67° × 41° |
| `A-37` | Pattern di 30 000 punti, seed 415 |
| `A-38` | Criteri del gate M3 |
| `A-39` | Regola sulla risoluzione: 43.7 s per frame, 1280×720 |
| `A-40` | Padding di 128 px e input a 8 bit per SGBM |
| `A-41` | Proiettore come sorgente puntiforme a metà baseline |
| `A-42` | Auto exposure per frame, setpoint 20 DN |
| `A-43` | Impostazioni SGBM "strict"; pixel-locking |
| `A-44` | Punto di presa: `plane_fit` |
| `A-45` | **Tuning ledger:** ogni parametro ha una regola scritta prima |
| `A-46` | Harness ICP: normali dal CAD |
| `A-47` | Aggiunte di reporting, senza cambiare endpoint |
| `A-48` | Rotazione dell'offset attorno al centro del bounding box |
| `A-49` | Inclusi solo visib_fract ≥ 0.1; stima mancante = fallimento |
| `A-50` | Check di planarità della ventosa |
| `A-51` | Opzione (B): roughness 0.2 e 0.4 su 50 scene |
| `A-52` | Opzione (D): passata opaca chiara, albedo 0.5. L'albedo di C4 è 0.25 a 71° (0.247 a 65°) |
| `A-53` | Opzione (C) rifiutata. Niente cambia dopo i dati di test, salvo un §5.11 fallito, che ha la precedenza: usato una volta per l'harness (H3, A-62) |
| `A-54` | Controllo con figura prima del render: ha trovato il bug A-57 |
| `A-55` | ROBI obbligatorio dopo M5. Ridotto da A-65: solo Zigzag, 1 ora |
| `A-56` | Modalità operativa: l'agent si ferma solo per valori congelati, risultati che minacciano l'esperimento, gate falliti |
| `A-57` | **Bug:** `glossy_bounces = 0`, niente riflessi sul metallo fino al fix |
| `A-58` | Misure del meccanismo su C3 |
| `A-59` | Il riempimento è bistabile e i render non sono identici bit per bit |
| `A-60` | Regola di decisione: McNemar e bootstrap insieme |
| `A-61` | Regioni del sensore: bordo e interno |
| `A-62` | Diagnosi del gate §5.11: il §5.11 prevale su A-53; solo C1, offset zero, scene di test. Primo giro: nessun candidato passa, trovato il bug della cache del ray-cast. Secondo giro, con cache corretta e 200 000 campioni: H0–H3 passano tutte |
| `A-63` | Rifacimento del §5.8 con il controllo sinistra-destra spento davvero: valore 1000, perché −1 non lo spegne in OpenCV 5.0.0. Fatto il 6 nov: nessuna inversione |
| `A-64` | Prova descrittiva col rumore IR a circa un terzo (`e_per_dn` 1), scene 0–9. A 65°: C3 non si muove (0.143), C4 da 0.357 a 0.408. A 71° il passo è minore: C3 0.102 fermo, C4 da 0.265 a 0.286. Non cambia nessun numero del protocollo |
| `A-65` | Decisioni su report e consegna: metallo come valore confermativo con l'intervallo descrittivo (a 71°: 0.070 e 0.070–0.276; a 65°: 0.085 e 0.085–0.288); ROBI solo Zigzag; quick-run con una scena di esempio |
| `A-66` | **Corsa finale a 71°:** focale del sensore, si rifà tutto, risultato primario qualunque sia la direzione; 65° solo come sensibilità. Risultati precedenti già visti, da dichiarare |
| `A-67` | Gate sul piano a 71°: ROI all'80% di larghezza e altezza e criteri (ii′), (iii′), (iv′). Sostituisce per questa corsa i criteri (ii), (iii), (iv) di A-38 |
| `A-68` | Pattern a punti a 71°: stessi 30 000 punti e stesso seed, punto di 0,7 px, 3,76% dei pixel illuminati |
| `A-69` | Regola per la luce RGB: griglia di energie, al massimo 5% di pixel di parte saturi |
| `A-70` | Test con luce ambiente, solo descrittivo: un livello, 21 DN sul metallo, scene 0–9 |
| `A-71` | Strumenti di consegna: `results/`, `scripts/setup.sh`, `scripts/quick_run.py`, scena di esempio seme 0 |
| `A-72` | L'ICP non è ripetibile alla lettera: stessa profondità, risultati diversi su alcune viste instabili. Effetto sul recall di test non misurato |
| `A-73` | Controllo della struttura dell'errore: gli errori di C3 rimescolati o con segno casuale. Esito: conta dove cadono e quanto sono grandi, non la direzione |
| `A-74` | Prova sulla densità dei punti, solo descrittiva: 10 000 punti invece di 30 000, scene 0–9, lettura fissata prima della corsa |

## 10. Rischi `R1`…`R7`

Fonte: PLAN §8.

| Sigla | Rischio |
|---|---|
| `R1` | BlenderProc non funziona su questa versione di macOS |
| `R2` | Simulazione stereo poco plausibile |
| `R3` | Tempi di render e memoria su 8 GB |
| `R4` | Effetto soffitto o pavimento in A1 o B |
| `R5` | Bug silenziosi: unità, scala delle disparità, simmetrie |
| `R6` | Il report sfora i tempi |
| `R7` | I revisori non riescono a eseguire il codice |

## 11. Fonti `S-01`…`S-16`

Fonte: `docs/SOURCES.md`.

| Sigla | Fonte | Serve per |
|---|---|---|
| `S-01` | Datasheet Intel D400, rev. 013 | Geometria, proiettore, Min-Z |
| `S-02` | Keselman et al. 2017 | Formula dell'errore z² (solo la formula) |
| `S-03` | Intel, guida al tuning | ε_d = 0.08 px, risoluzione raccomandata |
| `S-04` | Carfagni et al. 2019 | Misure reali della D415 su piano |
| `S-05` | ROBI (Yang et al. 2021) | Dati reali D415 su metallo |
| `S-06` | Ahn et al. 2019 | Non usata: coefficienti non verificati |
| `S-07` | BOP 2020 (Hodaň et al.) | MSSD, regola del 10% di visibilità |
| `S-08` | Spin-out RealSense 2025 | La D415 è ancora a listino |
| `S-09` | Zhang et al. | Precedente per la simulazione stereo fisica |
| `S-10` | BlenderProc: PyPI, issue, PR | Compatibilità macOS e default |
| `S-11` | Codice stereo di BlenderProc | Perché non usiamo il suo helper |
| `S-12` | Open3D, ray casting | Tutorial |
| `S-13` | Intel, white paper sui proiettori | Densità dei punti, 0.07–0.11 px |
| `S-14` | Intel, white paper subpixel | Pixel-locking |
| `S-15` | Rakić et al. 1998 | Riflettanza dell'alluminio: 0.868 |
| `S-16` | Bieron & Peers 2020 | Roughness e lobo diffuso del metallo |

## 12. File e cartelle

| Percorso | Cosa contiene |
|---|---|
| `docs/STATUS.md` | Stato attuale e prossimi passi. **Da leggere per primo** |
| `task_description.md` | La consegna di ETH. Non si modifica |
| `docs/PLAN.md` | Decisioni, protocollo, milestone, rischi |
| `docs/ASSUMPTIONS.md` | Assunzioni, ledger, ipotesi |
| `docs/SOURCES.md` | Fonti e stato di verifica |
| `docs/REPORT_PLAN.md` | Pagine per sezione del report, schema della riflessione |
| `docs/M5_OPEN_ITEMS.md` | Dubbi, cose non fatte e controlli da fare alla chiusura di M5. "Voce N" = riga N di questo file. La voce 18 aspetta una decisione |
| `docs/DIARY.md` | Cronologia, solo in aggiunta |
| `docs/AI_USE_LOG.md` | Interventi sull'AI, per la nota nel report. `A#n` = riga n della sezione A |
| `docs/personal/` | La tua guida personale, fuori da git |
| `configs/default.yaml` | Parametri congelati del protocollo |
| `configs/camera_d415_ir.yaml` | Parametri del modello di camera |
| `configs/harness.yaml` | Parametri di ICP e ventosa, oggi H3 con 200 000 campioni |
| `data/hfov71/` | **Corsa finale a 71° (A-66):** `plane/`, `intrinsics/`, `dev_iter<k>/`, `rgb_sweep/`, `dev/`, `test/` (scene 0–49 e risultati) |
| `report/` | Il report: sorgente LaTeX, PDF e `check_numbers.py`, che confronta i numeri stampati con `results/` |
| `results/` | Risultati tracciati in git: `hfov71/`, `archive_hfov65/`, `figures/`, `MANIFEST.json` (A-71) |
| `dist/` | Archivio della scena di esempio per il quick-run, fuori da git (A-71) |
| `data/m5/` | **Corsa archiviata a 65°.** Dati di test, 50 scene. `results/` contiene solo il sanity fallito; `results_v2/` i risultati con H3; `results_v2_s58/` il primo §5.8 sulle scene 0–9; `results_s58_v2/` il §5.8 rifatto e la prova sul rumore (A-63, A-64) |
| `data/m5/diag_sanity/` | Diagnosi del gate §5.11 (A-62), primo giro: candidati e ripetizioni di H2, solo C1 a offset zero |
| `data/m5/diag_sanity_fix/` | Secondo giro del §5.11: H0–H3 con la cache corretta e 200 000 campioni, solo C1 a offset zero |
| `data/m5_dev/` | Dati dev con le impostazioni finali; `selection/`, `pilot/` |
| `data/m5_diag/` | Render di convergenza: `gb1`, `gb3` = glossy bounces 1 e 3, `gb3_max12`, `gb3_s128` |
| `data/m4/` | Dati dev vecchi, riflessi spenti |
| `data/robi/` | Parte del dataset ROBI scaricata |
| `src/synthrgbd/` | Codice del progetto (`pose.py` = ICP) |
| `scripts/run_eval.py` | Lancia sanity, poi Task A e B. **Se un file di risultato esiste, non lo rifà** |
| `scripts/select_harness.py` | Sceglie la variante ICP con leximin su dev. `data/m5_dev/selection_fix/` = scelta dopo il fix |
| `scripts/run_final.sh` | Orchestratore della corsa finale a 71°: render, metriche, controlli, ridisegni, test ambiente. Riprende da dove si è fermato |
| `scripts/run_dots_test.sh` | Prova sulla densità dei punti (A-74): render, stereo, valutazione e riepilogo sulle scene 0–9 |
| `scripts/setup.sh` | Installazione da zero: controlla Python 3.11, crea `.venv`, lancia i test (A-71) |
| `scripts/quick_run.py` | Una scena di esempio senza Blender, confronto con i numeri committati, stampa `QUICK_RUN_PASS` o `QUICK_RUN_FAIL` (A-71, A-72) |
| `scripts/make_sample_archive.py` | Costruisce l'archivio della scena di esempio e i numeri attesi (A-71) |
| `scripts/make_figures.sh` | Rigenera le quattro figure dai risultati (Step 6) |
| `scripts/collect_results.py` | Copia i risultati in `results/` con il manifest di commit e semi (A-71) |
| `scripts/run_m5.sh` | Lancia le metriche principali su una cartella dati indicata esplicitamente, riprende da dove si è fermato |
| `scripts/run_m5_followup.sh` | Lancia il §5.8, la prova sul rumore e i ridisegni, sempre su una cartella indicata esplicitamente (A-63, A-64) |
| `scripts/check_stop.py` | Applica le regole di stop della corsa finale e ferma l'orchestratore (ledger "Final-run stop rules") |
| `scripts/robustness_s58.py` | Confronto strict e loose del §5.8, con la regola del ledger |
| `scripts/sanity_candidates.py` | Lancia candidati e ripetizioni di H2 per il §5.11 (A-62). Non calcola recall a offset reali |
| `scripts/sanity_diagnosis.py` | Diagnosi del §5.11: quale mesh usa davvero la cache, filtri di visibilità, conditioning, slittamenti |
| `scripts/pose_eval.py`, `suction_eval.py` | Valutazione di Task A e Task B |
| `scripts/bproc.sh` | Unico modo corretto di lanciare Blender |
| `.venv`, `.venv-bproc` | Ambienti Python: analisi e BlenderProc |
| `protocol-v1` | Tag git del congelamento (commit `4f52c67`). Non si sposta |
| obj 1, 2, 3, 4 | Profilo 60 mm, 100 mm, 150 mm, staffa a L |

## 13. Termini tecnici

| Termine | Significato |
|---|---|
| α (alfa) | Soglia di significatività dei test: 0.05 |
| active stereo | Stereo con un proiettore che aggiunge punti alla scena |
| albedo | Frazione di luce riflessa da una superficie opaca |
| ASIC, D4 | Il chip Intel che calcola la profondità nella D415 |
| auto exposure | Regola il guadagno in base alla luminosità dell'immagine |
| back-face culling | ICP ignora i punti del modello rivolti lontano dalla camera |
| baseline | Distanza tra le due camere: 55 mm |
| bistabile | Piccolissime differenze fanno saltare il risultato tra due stati (A-59) |
| BlenderProc, Blender, Cycles | Libreria per dati sintetici, programma 3D, motore di rendering |
| BOP | Benchmark e formato standard per la stima della posa |
| bootstrap | Il modo in cui si calcola il CI. Si pescano 50 scene a caso dalle 50 di test, con ripetizione (una può uscire due volte, un'altra mai), e si ricalcola il risultato. Si ripete 10 000 volte e si guarda quanto oscilla |
| bounces | Rimbalzi di luce simulati. `glossy_bounces` = rimbalzi speculari; `max_bounces` = totale |
| cache del ray-cast | Copia in memoria della scena per il ray-cast. **Bug (A-62):** in `pose.py` era indicizzata con `id()` di un array temporaneo, quindi un profilo poteva usare la mesh di un'altra lunghezza. Corretto il 5 nov (ade985f) |
| CAD | Modello 3D esatto del pezzo |
| CI, CI bootstrap | Intervallo di confidenza: i valori plausibili per il numero vero. "CI bootstrap" = calcolato col bootstrap. Si tengono i valori centrali al 95%. Se il CI di una differenza esclude 0, il segno della differenza è attendibile |
| clamp | Limite alla dimensione di un passo |
| coarse-to-fine, stadi | ICP da grossolano a preciso: 20, poi 10, poi 5 mm |
| conditioning | Quanto il sistema di equazioni è stabile. Mal condizionato = quasi singolare |
| corrispondenza | Coppia punto misurato e punto del modello più vicino |
| damping, smorzamento | Penalizza i passi grandi nelle direzioni poco vincolate |
| deviazione | Modifica successiva al congelamento, registrata in §5.12 |
| dev | Scene per scegliere i parametri (1000–1004). Mai nei risultati |
| disparità | Spostamento in pixel di un punto tra immagine sinistra e destra |
| DN | Valore di luminosità di un pixel, da 0 a 255 |
| e_per_dn | Parametro del rumore IR, tarato: 0.087 |
| erosione | Restringe la maschera di 2 px per evitare i bordi |
| fill, riempimento | SGBM assegna un valore a pixel senza texture invece di lasciarli invalidi |
| fitness | Frazione di punti misurati con un punto del modello entro la distanza massima |
| flying pixels | Punti spuri ai bordi degli oggetti |
| FOV | Campo visivo |
| gate | Controllo con criteri fissati prima. Se fallisce ci si ferma |
| faccia di testa (end face) | Una delle due facce piane alle estremità di un profilo |
| GGX | Modello matematico dei riflessi di una superficie metallica |
| GT | Ground truth: la verità nota dal simulatore |
| harness | L'insieme fisso di algoritmo e parametri usato per valutare |
| ICP | Iterative Closest Point: allinea il modello ai punti misurati a piccoli passi |
| instance-view | Un pezzo in una vista |
| IR | Infrarosso: 850 nm per il proiettore della D415 |
| Lambertiano | Riflessione opaca, uguale in tutte le direzioni |
| ledger | Tabella in A-45: per ogni parametro, cosa si può guardare e con quale regola |
| leximin | Confronta i risultati ordinati dal peggiore: vince chi ha il peggiore più alto, poi il secondo, ecc. |
| LM | Levenberg-Marquardt: ottimizzazione con smorzamento |
| matcher | L'algoritmo che accoppia immagine sinistra e destra |
| maximin | Sceglie chi ha il peggior risultato più alto. Degenere quando C3 è 0 ovunque |
| McNemar | Test per due condizioni sugli stessi casi. Guarda solo quelli in cui ne riesce una sola: senza differenza reale si dividerebbero circa a metà. Il **p** (p-value) dice quanto spesso il caso darebbe uno squilibrio almeno così forte; serve p < 0.05 |
| MDE | Effetto minimo rilevabile |
| MERL | Database di misure di materiali da cui viene la roughness |
| Min-Z | Distanza minima misurabile: 450 mm a 1280×720 |
| near-singular, quasi singolare | Sistema in cui alcune direzioni sono quasi senza vincoli |
| normal matrix | La matrice 6×6 che ICP risolve a ogni passo |
| offset | Errore introdotto di proposito nella posa di partenza |
| offset zero | ICP parte esattamente dalla posa vera |
| Open3D, OpenCV | Librerie: ICP e geometria; SGBM e immagini |
| pairing, accoppiamento | Stesse scene, pose e casualità tra condizioni |
| pilota | Prova su dev. Non è un risultato |
| pixel-locking | Le disparità tendono a valori interi |
| `plane_fit` | Punto di presa calcolato da un piano adattato ai punti sotto la ventosa |
| point-to-plane | ICP che misura la distanza lungo la normale alla superficie |
| posa 6D | Posizione (3 numeri) e orientamento (3 numeri) di un pezzo |
| protocollo congelato | Regole fissate prima dei dati, al tag `protocol-v1` |
| ray-cast, visibilità | ICP tiene solo i punti del modello che la camera vedrebbe per primi |
| recall | Frazione di casi riusciti |
| render | Generazione di un'immagine da una scena 3D |
| RGB-D | Immagine a colori + profondità per pixel |
| ROBI | Dataset reale di pezzi metallici ripresi con una D415 |
| Chrome screw, Zigzag | Due oggetti del dataset ROBI |
| ROI | Regione dell'immagine usata per una misura |
| roughness | Ruvidità del metallo. Bassa = specchio |
| sample, campioni | Raggi per pixel nel rendering: 32 per le immagini IR |
| sanity check | Controllo che il sistema funzioni prima di guardare i risultati |
| seed | Numero che fissa la casualità |
| setpoint | Luminosità media obiettivo dell'auto exposure: 20 DN |
| sample spacing | Distanza media tra i campioni CAD: √(area/N). Sul profilo da 150 mm: 0.80 mm con 50 000 campioni, 0.40 mm con 200 000 |
| SGBM | Semi-Global Block Matching: l'algoritmo stereo usato, da OpenCV |
| SNR | Rapporto segnale/rumore |
| speckle filter | Filtro SGBM che toglie piccole macchie isolate. Finestra: 100 px |
| strict, loose | SGBM con i filtri accesi, oppure con i tre filtri spenti |
| suction | Presa con ventosa |
| test (scene) | Le 50 scene dei risultati (0–49) |
| Tukey | Peso che riduce l'influenza dei punti molto lontani |
| uniqueness | Filtro SGBM che scarta gli accoppiamenti ambigui |
| visib_fract | Frazione visibile di un pezzo |
| z-depth | Distanza lungo l'asse della camera, non lungo il raggio |
