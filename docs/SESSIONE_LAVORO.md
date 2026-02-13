# Sessione di lavoro - Cruscotto CdG Karol
**Data**: 13/02/2026

## Analisi completata

Esplorazione completa del progetto (45 moduli Python, 23 fogli Master Excel, dashboard Streamlit 8 pagine).

### Struttura chiave
- **Master**: `dati/KAROL_CDG_MASTER.xlsx` — centro di tutto il sistema
- **Pipeline**: `karol_cdg/elabora.py` — legge Master → calcola CE-I → alloca costi sede → CE-G → KPI → output
- **Dashboard**: Streamlit (`karol_cdg/webapp/`) + HTML legacy (`index.html`)
- **Import**: Moduli per E-Solver (CSV), Zucchetti (CSV), Caremed/HT Sang (Excel)
- **Template**: 6 template pronti in `dati/template/`
- **Config**: `karol_cdg/config.py` — 5 UO operative (VLB, CTA, COS, LAB, KCP)

### Software aziendali coinvolti
1. **E-Solver** (SISTEMI) — contabilità generale, saldi, piano dei conti
2. **Zucchetti** — paghe, anagrafiche personale, costi del lavoro
3. **Caremed** — produzione ambulatoriale/laboratorio (COS, LAB)
4. **HT Sang** — produzione RSA/degenza (VLB, CTA, KCP)

### Stato attuale
- Dati: **DEMO/SIMULATI** — da sostituire con dati reali
- Automazione n8n: **PREDISPOSTA** ma non implementata
- Cartella import (`dati/import/`): presente ma vuota

## Prossimi passi concordati

### Fase 1 — Test con dati simulati nuovi
- Generare dataset simulato realistico (12 mesi, 5 UO)
- Caricare nel Master
- Eseguire pipeline completa (elabora.py)
- Verificare output: CE-I, CE-G, KPI, Cash Flow, Alert
- Controllare dashboard Streamlit

### Fase 2 — Automazione caricamento dati
- **Opzione A**: Collegamento diretto ai software (API/export automatico)
- **Opzione B**: Caricamento settimanale manuale/semi-automatico da report CSV/Excel
- Valutare n8n workflow o script Python schedulati
- Definire formato standard per ogni sorgente dati

## FASE 1 COMPLETATA — 13/02/2026

### Risultati test end-to-end
- Dataset: 12 mesi (gen-dic 2025), 5 UO operative, parametri benchmark settore
- Pipeline: lettura → CE-I → allocazione sede → CE-G → KPI → output Excel ✓
- 228 righe produzione, 816 costi, 21 sede, 1272 personale, 74 scadenzario
- 27 KPI calcolati: 15 VERDE, 8 GIALLO, 4 ROSSO

### Numeri chiave
| UO | Ricavi | MOL-I % | MOL-G % | Alert |
|----|--------|---------|---------|-------|
| VLB | 2.004K | 16.4% | -1.2% | Sede pesa troppo |
| CTA | 1.896K | 11.9% | -5.3% | Idem |
| COS | 3.799K | 23.0% | 8.8% | OK |
| LAB | 1.450K | 38.5% | 23.9% | Top performer |
| KCP | 700K | 13.8% | -8.7% | Struttura piccola |
| **TOTALE** | **9.849K** | **21.2%** | **5.0%** | **Sotto soglia 8%** |

### Costi Sede
- Allocabili: 1.592K (16.2% ricavi) — in linea
- Non allocabili: 403K (Sviluppo River Rock + Storici)

### File generati
- `genera_dati_test.py` — generatore dati simulati riutilizzabile
- `REPORT_TEST_CDG.xlsx` — report con riepilogo, CE, KPI, prossimi passi
- `dati/KAROL_CDG_MASTER_BACKUP.xlsx` — backup dati originali

## Dashboard HTML aggiornata — 13/02/2026

- `index.html` riscritto completamente (753 righe)
- 4 viste navigabili: Overview, CE Industriale, KPI Semafori, Trend Mensile
- Dati: 5 UO con CE-I completo (R01-R07, CD01-CD30), CE-G, costi sede, KPI semafori
- Grafici: BarChart CE per UO, PieChart alert/costi sede, LineChart trend 12 mesi, margini MOL-I/MOL-G
- Tabella riepilogo con semafori colorati (click per dettaglio UO con modale)
- KPI con sistema semafori (ROSSO/GIALLO/VERDE) per ogni UO + consolidato gruppo
- Trend mensili aggregati + singole UO con mini-grafici

## Dashboard v3.0 — 13/02/2026

### Architettura confermata
- React 18.2.0 + Recharts 2.12.7 via esm.sh + importmap (no bundler)
- Babel standalone per JSX transformation
- Deploy: GitHub Pages su branch `claude/add-financial-forecasting-sXecY`
- URL: https://fpcarnevale-controller.github.io/Karol-cruscotto-sicilia/
- Commit: `a483e2a`

### Modifiche implementate

**Fase 1 — Ristrutturazione dati e formattazione**
- `KAROL_DATA`: oggetto centralizzato con breakdown costi per UO (personale, materiali, servizi, utenze, manutenzione, altri), dati budget, ammortamenti, oneri finanziari
- `BENCHMARK`: costanti settore (pers 55%, MOL-I 15%, MOL-G 8%, occ 90%, costo PL/gg €130, DSO 120gg)
- Margini (MOL-I, MOL-G, EBIT) calcolati automaticamente da KAROL_DATA
- KPI semafori auto-generati da benchmark (non più hardcoded)
- `formatEuro`: tutti gli importi in formato preciso € X.XXX.XXX — eliminati fmtK/fmtM

**Fase 1c — Overview ridisegnata**
- 6 card costi gestionali (Personale, Materiali, Servizi, Utenze, Manutenzione, Sede) con semaforo vs benchmark
- Matrice KPI: aggiunta colonna "Costo PL/gg"
- Click su riga UO naviga direttamente a tab Strutture

**Fase 2 — Conto Economico (nuovo tab)**
- Sub-tab "CE Consolidato": tabella P&L completa Consuntivo vs Budget con delta e % ricavi
- Sub-tab "CE per BU": selezione UO + P&L individuale + riga riconciliazione automatica
- Sub-tab "Forecast": linearizzazione a 12 mesi, confronto vs budget per UO + totale

**Fase 3a — Analisi Costi (tab ridisegnato)**
- Stacked bar composizione costi per UO (6 categorie)
- Benchmark incidenza % su ricavi (personale %, costi dir %) con confronto settore
- Narrative per UO invariate

**Fase 3b — Simulazioni (nuovo tab)**
- 4 slider: Ricavi (±20%), Personale (±15%), Sede (−30/+10%), Occupancy (±10pp)
- Impatto real-time su Ricavi/MOL-G/EBIT con delta evidenziato
- Waterfall delta (MOL-G attuale → variazioni → MOL-G simulato)
- KPI simulati (MOL-G %, Pers %, Sede %)
- Pulsante Reset

**Miglioramenti generali**
- 7 tab totali: Overview | Conto Economico | Strutture | Trend | Cash Flow | Analisi | Simulazioni
- Footer aggiornato v3.0 con data ultimo aggiornamento da KAROL_DATA.meta
- Cash Flow: importi waterfall/cassa in formato preciso
- Strutture: aggiunto Costo PL/gg nel dettaglio UO

### Numeri chiave (invariati rispetto a test)
| Metrica | Valore |
|---------|--------|
| Ricavi Totali | € 9.849.287 |
| MOL Industriale | € 2.084.759 (21,2%) |
| Costi Sede | € 1.592.000 (16,2%) |
| MOL Gestionale | € 492.759 (5,0%) |
| EBIT | -€ 9.241 |
| CF Netto | -€ 600.241 |

### File (1.082 righe)
- `index.html` — SPA completa, deploy-ready

---

## Dashboard v3.1 — 13/02/2026

### Modifiche implementate

**Export PDF/Excel**
- CDN: jsPDF 2.5.1, html2canvas 1.4.1, SheetJS 0.18.5
- Pulsante 📥 nell'header con modale configurazione
- PDF: cattura screenshot tab attivo → multi-pagina A4
- Excel: workbook 5 fogli (Riepilogo, CE Consolidato, Trend Mensile, KPI, Cash Flow)

**Strutture — Donut chart**
- PieChart (donut) per composizione costi per UO nel tab Strutture
- 6 categorie: Personale, Materiali, Servizi, Utenze, Manutenzione, Altri
- Affiancato al trend chart esistente in layout grid

**DSO/DPO aggiornati**
- DSO ASP: 135 → 45 gg
- DPO Fornitori: 95 → 75 gg
- BENCHMARK DSO: 120 → 60 gg
- KPI cash flow ora dinamici da KAROL_DATA (non più hardcoded)

**Specifiche import dati**
- Documento `docs/SPECIFICHE_IMPORT_DATI_CDG.docx` con formato file per E-Solver, Zucchetti, Caremed, HT Sang
- Workflow di caricamento e push automation (`push.bat`)

---

## Dashboard v3.2 — 13/02/2026

### Modifiche implementate

**Forecast — 3 metodi di proiezione**
- Linearizzazione: media mensile × 12 (invariato, ora con selettore)
- Budget Residuo: consuntivo YTD + budget pro-rata mesi residui
- Trend Ponderato: YTD + media mobile 3M ponderata (pesi 3-2-1) × mesi residui
- Selettore metodo con bottoni + descrizione
- Grafico confronto metodi (4 barre per UO: Budget, Lin, BudRes, TrndPond)
- Note esplicative metodo attivo

**Cash Flow — CCC e Scadenziario**
- Cash Conversion Cycle: DSO + DIO - DPO con visualizzazione formula step-by-step
- Scadenziario crediti/debiti per fascia (0-30, 31-60, 61-90, >90 gg)
- Tabella con crediti, debiti, saldo netto per fascia
- Indicatori: % crediti entro 60gg, % debiti oltre 60gg
- Dati simulati coerenti con DSO 45gg / DPO 75gg

### File (1.447 righe)
- `index.html` — SPA completa, deploy-ready

---

## FASE 2 DA FARE — Automazione caricamento dati

### Domande da chiarire
- Accesso ai software aziendali: API disponibili o solo export manuale?
- Frequenza aggiornamento desiderata per ogni fonte dati (settimanale/mensile?)
- I report CSV/Excel che i software producono: puoi condividerne un campione?
- Preferenza tra n8n workflow o script Python schedulati?

## v3.4 — Dati Reali Q1 2025

### Fonti analizzate
1. **DATI_CE_KSPA_31032025.xlsx** — CE Q1 2025 (375 righe, 18 CDC)
2. **HR_KSPA_Anno2025.xlsx** — Costi personale HR (8.726 righe)
3. **Produzione_Gruppo_gen-agosto.2025.xlsx** — Produzione/fatturato Q1
4. **CentriCosto_PianoConti_Karol2024.xlsx** — Struttura CDC
5. **strutture centri di costo e o ricavo.pdf** — Mappatura strutture

### Operazioni eseguite
- Mappatura 18 CDC → 4 UO + HQ + LAB (controllata fuori perimetro)
- Riconciliazione CE vs HR vs Produzione (delta personale +14% HR vs CE per TFR/INAIL/mens.agg)
- Annualizzazione Q1 × 4 lineare
- KAROL_DATA aggiornato con dati reali:
  - 4 UO operative (VLB, CTA, COS, KCP) — LAB estratta in oggetto separato
  - SEDE/HQ con breakdown costi reali
  - Waterfall corretto con flusso Ricavi BU → costi → MOL-I → Proventi HQ → Sede → MOL-G → Risultato
  - Narrative con analisi reale per struttura
  - mesiDisp = 3 (Gen-Mar) per trend charts
- Report analisi: `docs/ANALISI_Q1_2025.md`

### Risultati chiave
- MOL-I BU: €1.986k (18,1%) — sopra benchmark 15%
- Sede HQ: €2.335k (21,3% ricavi BU) — anomalia critica
- MOL-G: -€140k — gruppo in perdita per eccesso costi sede
- VLB personale 75%, KCP 79% — insostenibili
- CTA e COS performanti (MOL-I 33% e 16,6%)

## Materiale strategico acquisito — 13/02/2026 sera

### File analizzati
1. **BP_KarolBase - PlanB - BBS.xlsx** — Business Plan 2025-2035 con Bond €5M + MCC €5M
2. **Karol_Information_Memorandum_2026_Bond.docx** — IM per Basket Bond Sicilia (IRFIS/ExtraMOT PRO3)
3. **Karol_strutture-sanitarie.svg** — Logo ufficiale
4. **Sito web**: karolstrutturesanitarie.it — 30 strutture, 4 regioni, +1000 dipendenti

### Quadro strategico compreso
- **PFN 2025:** €24,3M (leverage 16,8x) — crisi di liquidità, non operativa
- **Composizione debito:** banche €6,4M + erario €12,4M (rateizzato) + fornitori €4,5M + personale €996k
- **3 nuove BU bloccate** per €2,3M CAPEX residuo:
  - Borgo Ritrovato (40+20 PL RSA Alzheimer Palermo)
  - KMC Day Surgery (privato, via Sciuti Palermo)
  - Roma Santa Margherita (77 PL, prima presenza Lazio)
- **Bond Basket Sicilia:** €5M, 7 anni, 5%, amortizing, non segnalato in Centrale Rischi
- **Proiezioni ricavi:** €12,9M(2025) → €18,6M(2027) → €22M(2035)
- **EBITDA:** 8,9%(2025) → 14,3%(2027) → 18,3%(2035)
- **Ammortamenti:** €918k/anno dal 2027 (erano zero nella dashboard Q1)
- **DSCR critico 2027-28** (<1,0x) mitigato da €3M crediti ASP certi + buffer cassa
- **Rottamazione quinquies** attiva + rateizzazioni AdE/INPS front-loaded 2026-28
- **ZES Unica:** potenziale credito €550k (non nel BP), finestra marzo-maggio 2026

### Insight chiave dalla combinazione Q1 reale + BP
- MOL-I BU 18,1% (Q1 reale) conferma BP assumption (EBITDA 8,9% → sale con nuove BU)
- Sede HQ 21,3% dei ricavi vs benchmark 8-12% → consulenze €812k da scomporre
- Modello di business validato: domanda >> offerta, tariffe SSR certe, liste d'attesa
- Il problema non sono i ricavi ma i costi nascosti che distruggono valore
- Crisi = espansione aggressiva autofinanziata senza equity → debito fiscale accumulato

### Costo HR Q1 — verifica dettaglio righi Zucchetti
Costo pieno confermato: righi 180 (retribuzioni 67,8%) + 190 (rettifiche) + 280 (contributi 16%) + 330 (13ma/14ma 10,1%) + 390 (INAIL 0,9%) + 430 (TFR 5,6%). Totale Q1: €1.897.150. Delta +14% vs CE per ratei non ancora contabilizzati.

### GitHub Pages
Branch corretto: **main** (era su feature branch, corretto via Settings → Pages → Source)

## Bilancio 2024 approvato — Analisi 14/02/2026

### SPA 2024
- Ricavi: €11.818k (+8,5% YoY), Valore Produzione: €14.066k
- Personale: €7.250k (51,5% VP)
- Ammortamenti: €893k (erano €82k nel 2023 → +1.157% per capitalizzazione lavori nuove BU)
- EBIT: -€121k (negativo!)
- Proventi finanziari: €1.260k (interessi di mora su crediti ASP scaduti)
- Utile netto: +€461k — **ma normalizzato (senza proventi straordinari): -€800k**
- PFN SPA: -€9.040k
- Debiti vs controllate: €8.180k (+€3.200k vs 2023)
- Debiti tributari: €5.660k

### Consolidato 2024
- Ricavi: €25.800k (+5,7%), VP: €27.948k
- Personale: €15.494k (57,9% VP)
- D&A: €1.030k (impennata da €82k per capitalizzazioni)
- EBITDA: €41k (marginale)
- Utile netto: +€592k
- PFN: -€19.150k, Equity: €3.790k, Leverage: 5,1x
- Debiti tributari consolidati: €8.780k (+56%)
- Debiti previdenziali: €5.750k (+50%)
- Target gruppo: €30M ricavi 2025, €38M 2026+ con margine operativo €5M+

### Provvisorio SPA 31/08/2025
- Ricavi 8M: €7.620k (annualizzato €11.430k — convergente con 2024)
- MOL 8M: €319k (annualizzato €479k — molto peggiore del Q1×4 €1.020k)
- Oneri finanziari 8M: €197k (annualizzato €296k — il triplo del Q1)
- Cassa: €231k (critica)
- Crediti commerciali: €13.200k (DSO ~140 giorni)

### Q&A documento preparato
- File: `docs/QA_ANALISI_CRITICA_KAROL_2026.docx`
- 7 sezioni: riconciliazione fonti, criticità strutturali, stato patrimoniale, stress test Bond/DSCR, domande operative (12), tavola sinottica, raccomandazioni CdG

## Risposte Management — 14/02/2026

### Cambiamenti strategici
1. **MUTUO BANCARIO al posto del BOND** — Bond troppo lento (6-9 mesi). Mutuo 10 anni, possibile preammortamento. Ricalcolare tutto il piano finanziario.
2. **VLB scorporo necessario** — Include: Centro Gottardo (FKT, ~€40k fatture attive), cucina centralizzata, trasporto disabili, Casa Protetta 20 PL (brucia €300k+/anno). Piano: spostare 40 PL convenzionati a BRT e chiudere Casa Protetta.
3. **CTA contenzioso €7M** — Crediti in bilancio per €7M+. Transazione imminente ("fra pochi giorni"). Game-changer per liquidità se confermata.
4. **Crediti fiscali innovazione/patent box** — Studio Roma sta certificando. Spiega gap ricavi BP (€12,9M) vs consuntivo (~€11,4M): ~€1,5M di "altri ricavi" non operativi.
5. **Timeline nuove BU: giugno 2026 best case** — BRT prima (3-4 mesi ramp-up), KMC dopo, Roma 2-3 mesi post-lavori per preaccreditamento (solido).
6. **Target costi: -10%** — Condizione necessaria per superare DSCR critico 2027-28.
7. **DSO reale ASP: 45-60 giorni** — I €13,2M di crediti sono cumulo storico posizioni CTA + differenze rette regionali, non DSO corrente.
8. **Affitto VLB €219k** — Proprietario rigido, piano è chiudere e spostare a BRT.
9. **Cassa €231k gestita** — Spostando costi, ritardando pagamenti professionisti/dipendenti.
10. **Crescita a debito + COVID + gestione paternalistica** — Eccesso personale, poca attenzione ai costi, fatturato cresceva illusoriamente.

### Dati in arrivo (promessi dal management)
- Piano di rientro debiti tributari (scadenziario mensile)
- Piano di rientro debiti previdenziali
- Dettaglio consulenze HQ per fornitore/contratto
- CE mensile aprile-agosto 2025

## PROSSIMI PASSI — Sessione successiva

### Priorità alta (concordati con Francesco)
1. **Dashboard v4:** integrare PFN, ammortamenti, debt service, proiezioni 2025-2030, DSCR, 3 nuove BU
2. **Tab Piano Finanziario:** waterfall pre/post Bond, scenario base vs stress test ramp-up Roma
3. **Benchmark esterno:** bilanci KOS, Korian Italia, Sereni Orizzonti — confronto voce per voce
4. **Scenario analysis:** impatto ritardo ramp-up (3/6/12 mesi) su DSCR e cassa

### Priorità media
- Budget 2025 separato da consuntivo (quando disponibile)
- Dati Q2-Q4 per trend reale mensile
- Drill-down consulenze HQ per tipo/contratto
- Allocazione sede a UO con driver (personale, PL, ricavi)
- Export PDF: pagina dettaglio per BU + piano finanziario
- Responsive mobile / Dark mode
