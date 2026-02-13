# SCHEDA MIGLIORAMENTI DASHBOARD — Karol Cruscotto Sicilia

## Contesto

Il file `index.html` è un componente React standalone (SPA) che usa Recharts per i grafici. I dati sono hardcoded nell'array `struttureDati` (righe 11-136). Il deploy avviene tramite GitHub Pages. Il backend Python in `karol_cdg/` NON è collegato alla dashboard React: sono due sistemi separati. Questa scheda riguarda esclusivamente il miglioramento del file `index.html`.

---

## AUDIT STATO ATTUALE

### Problemi critici

1. **DATI FALSI / PLACEHOLDER** — RSA mostra 7 valori identici (€204.716/mese), Cosentino 7 valori identici (€340.567/mese). Solo CTA e parzialmente Radiologia/FKT hanno variabilità mensile reale. Questo invalida qualsiasi analisi di trend. I dati fake devono essere segnalati visivamente o sostituiti con dati reali.

2. **NESSUNA SEZIONE CASH FLOW** — Il titolo dice "Cruscotto Flusso di Cassa" ma non c'è nessun grafico o analisi di cash flow. C'è solo il confronto fatturato vs budget. Il modulo Python `karol_cdg/core/cash_flow.py` prevede: cash flow operativo settimanale, cash flow strategico pluriennale con scenari, DSO/DPO, copertura cassa. Niente di tutto ciò è rappresentato nel frontend.

3. **PIE CHART INUTILE** — Il grafico "Livello di Criticità" usa una PieChart con 3 categorie (alta=0, media=1, bassa=4). Un pie chart con un solo spicchio significativo non comunica nulla. Spreco di spazio prezioso.

4. **MANCANO TREND TEMPORALI** — Non c'è nessun grafico che mostri l'andamento nel tempo. L'unico grafico è il bar chart aggregato per struttura.

5. **NESSUN KPI OPERATIVO** — Il sistema Python prevede 15+ KPI con semafori (occupancy, MOL%, DSO, DPO, copertura cassa, costo personale/giornata, ecc.). La dashboard mostra solo 4 metriche aggregate nel header.

---

## MIGLIORAMENTI DA IMPLEMENTARE

### A. STRUTTURA GENERALE E NAVIGAZIONE

**A1. Aggiungi Tab di navigazione in alto**

Sostituisci la singola pagina monolitica con un sistema a tab (o sezioni con scroll e indice laterale). Le sezioni devono essere:

- **Overview** — KPI cards + performance riepilogativa
- **Strutture** — Dettaglio per singola struttura con drill-down
- **Trend Mensili** — Andamenti temporali
- **Cash Flow** — Sezione completamente nuova (vedi sotto)
- **Alert & Azioni** — Sistema semafori e raccomandazioni

Implementazione suggerita: usa uno state `activeTab` e renderizza condizionalmente le sezioni. Usa dei bottoni orizzontali styled come tab, con la tab attiva evidenziata con `border-bottom` colorato.

**A2. Header rivisitato**

L'header attuale è generico. Miglioralo:

```
Header fisso in alto:
- Logo "KAROL" a sinistra (già presente nel progetto come SVG in assets/)
- Titolo centrato: "Controllo di Gestione — Sicilia"
- A destra: periodo di riferimento "Gen-Lug 2025" + indicatore stato dati (pallino verde/rosso)
- Sotto l'header: barra KPI con le 4 metriche principali (fatturato, budget, %, scostamento)
  ma AGGIUNGI anche: DSO medio (giorni), Copertura cassa (mesi), Occupancy media (%)
```

Le card KPI attuali vanno da 4 a 7, con layout responsivo `grid-cols-2 md:grid-cols-4 lg:grid-cols-7`. Per le 3 nuove card usa valori simulati ma realistici:
- DSO medio: 135 giorni (semaforo giallo, soglia verde <120, soglia rossa >150)
- Copertura cassa: 1.8 mesi (semaforo giallo, soglia verde >2.0, soglia rossa <1.0)
- Occupancy media: 91.2% (semaforo verde, soglia verde >90%, soglia gialla >80%)

---

### B. GRAFICI — SOSTITUZIONI E AGGIUNTE

**B1. Sostituisci il bar chart "Performance vs Budget"**

Il grafico attuale ha problemi:
- Label troncate a 12 caratteri (illeggibili)
- Budget in grigio troppo spento (#e5e7eb)
- Non mostra lo scostamento in modo immediato

Sostituiscilo con un **bar chart orizzontale con divergenza dallo zero**:

```
Asse Y: nomi struttura completi (in orizzontale, quindi leggibili)
Asse X: scostamento in euro (negativo a sinistra in rosso, positivo a destra in verde)
Ogni barra mostra lo scostamento assoluto con il valore €
Ordina le strutture dal peggiore al migliore scostamento
```

Colori:
- Scostamento negativo: `#ef4444` (rosso)
- Scostamento positivo: `#10b981` (verde)
- Linea di riferimento zero: `#94a3b8` (grigio)

Sotto questo grafico aggiungi una riga di testo: "Scostamento totale: €XX.XXX" con colore condizionale.

**B2. Sostituisci il pie chart con una Heatmap / Tabella semaforo**

Elimina completamente il PieChart "Livello di Criticità". Al suo posto metti una **tabella semaforo compatta** che mostri i KPI per ogni struttura:

```
Righe: CTA, RSA, Cosentino, Radiologia, FKT
Colonne: % Realizzazione | Scostamento € | Occupancy | MOL % | Status

Ogni cella ha sfondo colorato:
- Verde (#dcfce7): KPI in target
- Giallo (#fef9c3): KPI in area attenzione  
- Rosso (#fee2e2): KPI critico
```

Per i KPI che non abbiamo ancora (Occupancy, MOL%), usa placeholder con sfondo grigio chiaro e testo "n/d" — questo comunica che il dato manca ed è necessario. Non inventare dati.

**B3. Aggiungi grafico TREND MENSILE**

Aggiungi un LineChart con:
- Asse X: Gen, Feb, Mar, Apr, Mag, Giu, Lug
- Una linea per ogni struttura (colori distinti e consistenti)
- Tooltip che mostra il valore esatto e la % vs budget del mese
- Possibilità di mostrare/nascondere le singole linee cliccando sulla legenda

Colori per struttura (consistenti in tutta la dashboard):
- CTA: `#3b82f6` (blu)
- RSA: `#10b981` (verde)
- Cosentino: `#8b5cf6` (viola)
- Radiologia: `#f59e0b` (ambra)
- FKT: `#ec4899` (rosa)

Nota: per RSA e Cosentino i dati mensili sono identici — il grafico mostrerà linee piatte. Va bene, è un segnale visivo che i dati non sono reali.

**B4. Aggiungi grafico a barre BUDGET vs REALIZZATO per mese (stacked/grouped)**

Sotto il trend, aggiungi un selettore struttura (dropdown o bottoni). Al click, mostra un bar chart verticale con:
- Per ogni mese: barra budget (grigio chiaro `#e2e8f0`) e barra fatturato (colore della struttura)
- Linea sovrapposta con la % cumulata di realizzazione
- Questo è il grafico più utile per il confronto mensile dettagliato

---

### C. SEZIONE CASH FLOW — COMPLETAMENTE NUOVA

Questa è la sezione più importante da creare. Deve essere una tab dedicata con almeno 3 visualizzazioni.

**C1. Waterfall Chart — Composizione Cash Flow**

Crea un waterfall chart (a cascata) con le seguenti voci:

```
Ricavi totali (barra verde, dal basso)
- Costi personale (barra rossa, decresce)
- Costi diretti (barra rossa, decresce)
= EBITDA (subtotale, barra blu)
- Variazione CCN (barra rossa o verde)
= Cash Flow Operativo (subtotale, barra blu scuro)
- CAPEX (barra rossa, decresce)
= Free Cash Flow (subtotale, barra viola)
- Servizio debito (barra rossa, decresce)
- Imposte (barra rossa, decresce)
= Cash Flow Netto (barra finale, verde se positivo, rosso se negativo)
```

Recharts non ha un waterfall nativo. Implementalo con BarChart stacked:
- Usa una barra "invisibile" (fill trasparente) come base
- Usa una barra colorata per il valore effettivo
- I subtotali hanno lo sfondo pieno che parte da zero

Usa questi dati simulati ma realistici per il Gruppo Karol Sicilia (annualizzati):

```javascript
const datiWaterfall = [
  { voce: "Ricavi", valore: 9160785, tipo: "entrata", base: 0 },
  { voce: "Personale", valore: -5130000, tipo: "uscita", base: 9160785 },
  { voce: "Costi diretti", valore: -2290000, tipo: "uscita", base: 4030785 },
  { voce: "EBITDA", valore: 1740785, tipo: "subtotale", base: 0 },
  { voce: "Var. CCN", valore: -180000, tipo: "uscita", base: 1740785 },
  { voce: "CF Operativo", valore: 1560785, tipo: "subtotale", base: 0 },
  { voce: "CAPEX", valore: -320000, tipo: "uscita", base: 1560785 },
  { voce: "Free CF", valore: 1240785, tipo: "subtotale", base: 0 },
  { voce: "Debito", valore: -680000, tipo: "uscita", base: 1240785 },
  { voce: "Imposte", valore: -210000, tipo: "uscita", base: 560785 },
  { voce: "CF Netto", valore: 350785, tipo: "finale", base: 0 },
];
```

I subtotali e il valore finale partono sempre da base 0 (barra piena).
Le voci intermedie partono dalla base del subtotale precedente e decrementano.

Colori:
- Entrate: `#10b981`
- Uscite: `#ef4444`
- Subtotali: `#3b82f6`
- Finale positivo: `#059669` (verde scuro)
- Finale negativo: `#dc2626` (rosso scuro)

**C2. Line Chart — Andamento Saldo Cassa Settimanale (12 settimane)**

Crea un AreaChart con:
- Asse X: Settimana 1-12 (prossime 12 settimane)
- Area fill: verde sopra la soglia minima cassa, rosso sotto
- Linea principale: saldo cassa progressivo
- Linea orizzontale tratteggiata: soglia minima cassa (€200.000 da config)
- Annotation: se il saldo scende sotto soglia, mostra un punto rosso con tooltip "ALERT"

Dati simulati:

```javascript
const datiCassaSettimanale = [
  { settimana: "S1", saldo: 420000, incassi: 180000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S2", saldo: 390000, incassi: 120000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S3", saldo: 340000, incassi: 100000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S4", saldo: 510000, incassi: 320000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S5", saldo: 460000, incassi: 100000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S6", saldo: 380000, incassi: 70000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S7", saldo: 290000, incassi: 60000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S8", saldo: 240000, incassi: 100000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S9", saldo: 210000, incassi: 120000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S10", saldo: 180000, incassi: 120000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S11", saldo: 350000, incassi: 320000, pagamenti: 150000, soglia: 200000 },
  { settimana: "S12", saldo: 400000, incassi: 200000, pagamenti: 150000, soglia: 200000 },
];
```

Nota: la settimana 10 scende sotto soglia — l'alert deve essere visibile. Il pattern è realistico per il settore sanitario convenzionato dove gli incassi ASP arrivano a blocchi.

**C3. Scenario Analysis — 3 linee a confronto**

Crea un LineChart con 3 linee (scenario ottimistico, base, pessimistico) su 5 anni:

```javascript
const datiScenari = [
  { anno: "2025", ottimistico: 350000, base: 250000, pessimistico: 80000 },
  { anno: "2026", ottimistico: 720000, base: 480000, pessimistico: 120000 },
  { anno: "2027", ottimistico: 1150000, base: 750000, pessimistico: -50000 },
  { anno: "2028", ottimistico: 1650000, base: 1050000, pessimistico: -180000 },
  { anno: "2029", ottimistico: 2250000, base: 1400000, pessimistico: -350000 },
];
```

Colori:
- Ottimistico: `#10b981` (verde) con area fill leggera
- Base: `#3b82f6` (blu) linea più spessa (strokeWidth 3)
- Pessimistico: `#ef4444` (rosso) con area fill leggera

Aggiungi zona grigia sotto lo zero come "zona di pericolo". Se lo scenario pessimistico entra in negativo, colora quell'area in rosso semitrasparente.

**C4. KPI Finanziari — Cards dedicate al Cash Flow**

Sotto i grafici, aggiungi una riga di 4 card:

```
| DSO ASP: 135 gg        | DPO Fornitori: 95 gg    | DSCR: 1.15x            | Copertura: 1.8 mesi    |
| 🟡 Target: <120 gg     | 🟢 Target: <120 gg      | 🟡 Target: >1.2x       | 🟡 Target: >2.0 mesi   |
```

Usa le soglie da `config.py`:
- DSO ASP: verde <120, giallo <150, rosso >150
- DPO: verde <90, giallo <120, rosso >120
- DSCR: verde >1.2, giallo >1.0, rosso <1.0
- Copertura cassa: verde >2.0 mesi, giallo >1.0, rosso <1.0

---

### D. DESIGN E PALETTE

**D1. Palette colori unificata**

Definisci una palette costante all'inizio del componente e usala ovunque:

```javascript
const COLORI = {
  primario: '#1F4E79',       // Blu Karol (header, titoli)
  primarioChiaro: '#2E75B6', // Blu chiaro (accent)
  sfondo: '#F8FAFC',         // Grigio chiarissimo (sfondo pagina)
  cardSfondo: '#FFFFFF',     // Bianco (sfondo card)
  
  // Semaforo
  verde: '#059669',
  verdeSfondo: '#dcfce7',
  giallo: '#d97706',
  gialloSfondo: '#fef9c3',
  rosso: '#dc2626',
  rossoSfondo: '#fee2e2',
  
  // Strutture (consistenti ovunque)
  cta: '#3b82f6',
  rsa: '#10b981',
  cosentino: '#8b5cf6',
  radiologia: '#f59e0b',
  fkt: '#ec4899',
  
  // Grafici
  budget: '#cbd5e1',
  fatturato: '#3b82f6',
  linea_soglia: '#94a3b8',
  
  // Testo
  testoScuro: '#1e293b',
  testoMedio: '#475569',
  testoChiaro: '#94a3b8',
};
```

**D2. Tipografia**

- Titoli sezione: `text-xl font-semibold` colore `COLORI.primario`
- Sottotitoli: `text-sm font-medium` colore `COLORI.testoMedio`
- Valori metriche: `text-2xl font-bold` (non text-3xl, troppo grande sulle card attuali)
- Numeri tabella: `font-mono text-sm` per allineamento
- Note e caption: `text-xs` colore `COLORI.testoChiaro`

**D3. Ombre e bordi**

Standardizza le card:
```
className="bg-white rounded-xl shadow-sm border border-gray-100 p-5"
```
Elimina `shadow-lg` e `rounded-2xl` — troppo pesanti. Usa ombre leggere e arrotondamento moderato per un look più professionale e meno "giocattolo".

**D4. Spaziatura**

- Gap tra card KPI: `gap-4` (non gap-6)
- Padding sezioni: `p-5` (non p-6)
- Margine tra sezioni: `mb-6` (non mb-8)
- Tutto più compatto = più informazione visibile senza scroll

---

### E. QUALITÀ DATI — SEGNALAZIONE VISIVA

**E1. Badge "Dati Placeholder"**

Per le strutture dove i dati mensili sono identici (RSA, Cosentino), aggiungi un badge visivo:

```html
<span className="bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded-full">
  ⚠ Dati budget (non consuntivo)
</span>
```

Questo va accanto al nome della struttura nei grafici e nelle tabelle.

**E2. Indicatore completezza dati in header**

Nell'header, accanto al periodo, mostra:

```
Completezza dati: 40% ████░░░░░░ (2/5 strutture con consuntivo reale)
```

Usa una progress bar semplice. 40% = solo CTA e parzialmente Radiologia/FKT hanno dati reali.

---

### F. RESPONSIVITÀ E PRINT

**F1. Responsive migliorato**

Le card KPI attualmente usano `md:grid-cols-4`. Per 7 card serve:
```
grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7
```

I grafici devono avere altezze responsive:
- Mobile: `height={250}`
- Desktop: `height={350}`

Usa un hook o una variabile per gestirlo.

**F2. Print-friendly**

Aggiungi un bottone "Stampa Dashboard" che:
- Applica `@media print` CSS per nascondere sidebar, bottoni interattivi
- Forza sfondo bianco
- Riduce padding
- Mostra tutti i grafici senza scroll

```css
@media print {
  .no-print { display: none !important; }
  .print-break { page-break-before: always; }
  body { background: white !important; }
}
```

---

### G. MODAL ESISTENTI — MIGLIORAMENTI

**G1. Modal Report**

Il modal report attuale è funzionale ma migliorabile:
- Aggiungi data/ora di generazione
- Aggiungi un vero bottone "Esporta PDF" (usa `window.print()` con CSS dedicato)
- La tabella è troppo compressa (`text-xs`): usa `text-sm`

**G2. Modal Proiezioni**

La proiezione annuale attuale fa una semplice media aritmetica (fatturato/7*12). È naive perché:
- Non tiene conto della stagionalità (agosto è chiuso per CTA)
- Non distingue tra dati reali e placeholder

Migliora: mostra una nota che spiega il metodo di proiezione e i suoi limiti. Aggiungi un disclaimer: "Proiezione basata su media lineare 7 mesi. Non tiene conto di stagionalità e chiusure agosto."

---

## PRIORITÀ DI IMPLEMENTAZIONE

| Priorità | Intervento | Impatto | Complessità |
|----------|-----------|---------|-------------|
| 1 | C1-C4: Sezione Cash Flow completa | Altissimo | Alta |
| 2 | B1: Bar chart orizzontale scostamenti | Alto | Bassa |
| 3 | B2: Tabella semaforo KPI | Alto | Media |
| 4 | D1-D4: Palette e design unificato | Alto | Bassa |
| 5 | B3: Trend mensile LineChart | Medio | Bassa |
| 6 | A1: Sistema tab navigazione | Medio | Media |
| 7 | E1-E2: Indicatori qualità dati | Medio | Bassa |
| 8 | B4: Dettaglio struttura con drill-down | Medio | Media |
| 9 | F1-F2: Responsività e stampa | Basso | Bassa |
| 10 | G1-G2: Miglioramento modal | Basso | Bassa |

---

## NOTE TECNICHE

- Il file è un singolo `index.html` con React + Recharts, deployato su GitHub Pages
- NON importare librerie aggiuntive oltre a quelle già usate (React, Recharts)
- Per il waterfall chart: implementalo con BarChart stacked usando barre invisibili come base
- Tutti i dati sono hardcoded nel componente: mantieni questa struttura ma organizza i dati in oggetti separati all'inizio del file (uno per sezione)
- Formattazione valuta: usa sempre la funzione `formattaValuta` già presente
- I dati cash flow simulati sono realistici per il Gruppo Karol Sicilia basandosi sui ricavi di riferimento (~€9.2M per Karol S.p.A. Sicilia) e i parametri di `config.py`
- Mantieni UTF-8 corretto per le emoji nella navigazione
