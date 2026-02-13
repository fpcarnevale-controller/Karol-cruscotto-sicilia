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

## FASE 2 DA FARE — Automazione caricamento dati

### Domande da chiarire
- Accesso ai software aziendali: API disponibili o solo export manuale?
- Frequenza aggiornamento desiderata per ogni fonte dati (settimanale/mensile?)
- I report CSV/Excel che i software producono: puoi condividerne un campione?
- Preferenza tra n8n workflow o script Python schedulati?
