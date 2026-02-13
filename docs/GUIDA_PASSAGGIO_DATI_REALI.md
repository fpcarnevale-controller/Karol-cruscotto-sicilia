# Guida Operativa: Passaggio da Dati Demo a Dati Reali

## Karol CDG - Controllo di Gestione Gruppo Karol S.p.A.

**Versione**: 1.0
**Destinatario**: Controller / Responsabile CDG
**Prerequisiti**: Competenze Excel avanzate, accesso ai gestionali aziendali
**Ultimo aggiornamento**: Febbraio 2026

---

## Indice

1. [Panoramica del Sistema](#1-panoramica-del-sistema)
2. [Mappa delle Fonti Dati](#2-mappa-delle-fonti-dati)
3. [Il File Master: KAROL_CDG_MASTER.xlsx](#3-il-file-master)
4. [Raccolta Dati da E-Solver (SISTEMI)](#4-raccolta-dati-da-e-solver)
5. [Raccolta Dati da Zucchetti Paghe](#5-raccolta-dati-da-zucchetti)
6. [Raccolta Dati da Caremed/INNOGEA](#6-raccolta-dati-da-caremed)
7. [Raccolta Dati da HT Sang](#7-raccolta-dati-da-ht-sang)
8. [Compilazione Foglio Scadenzario](#8-compilazione-foglio-scadenzario)
9. [Procedura di Sostituzione Dati](#9-procedura-di-sostituzione-dati)
10. [Checklist di Validazione](#10-checklist-di-validazione)
11. [Test e Verifica Dashboard](#11-test-e-verifica-dashboard)
12. [Predisposizione per Automazione n8n](#12-predisposizione-per-automazione-n8n)
13. [Risoluzione Problemi Comuni](#13-risoluzione-problemi-comuni)
14. [Appendice: Codici e Riferimenti](#14-appendice)

---

## 1. Panoramica del Sistema

### Come funziona la dashboard

La dashboard Karol CDG legge **un unico file Excel** (`dati/KAROL_CDG_MASTER.xlsx`) e da questo calcola tutto:

```
Fonti Dati Aziendali          File Master              Dashboard
========================       ===========              =========
E-Solver (contabilita')  --\                          /-- CE Industriale
Zucchetti (paghe)        ----> KAROL_CDG_MASTER.xlsx ----> CE Gestionale
Caremed (produzione)     --/   (23 fogli)             \-- KPI + Cash Flow
HT Sang (produzione)     -/                            \-- Scenari + Alert
```

**Flusso dei dati**:
1. Esportate i dati dai gestionali (CSV o Excel)
2. Copiate/incollate i dati nei fogli giusti del Master
3. Salvate il file Master
4. La dashboard si aggiorna automaticamente (premete "Ricarica dati" nella sidebar)

### Fogli del file Master che dovete compilare

| # | Foglio | Cosa contiene | Fonte dati | Priorita' |
|---|--------|---------------|------------|-----------|
| 1 | **Costi_Mensili** | Tutti i costi per UO e mese | E-Solver | ALTA |
| 2 | **Produzione_Mensile** | Ricavi per UO e mese | Caremed + HT Sang | ALTA |
| 3 | **Anagrafiche_Personale** | Elenco dipendenti e costi | Zucchetti | ALTA |
| 4 | **Costi_Sede_Dettaglio** | Costi sede da allocare | E-Solver | ALTA |
| 5 | **Scadenzario** | Scadenze incassi/pagamenti | Manuale + E-Solver | MEDIA |
| 6 | **Piano_Conti** | Piano dei conti codificato | E-Solver | UNA TANTUM |
| 7 | **Driver_Allocazione** | Parametri allocazione sede | Manuale | UNA TANTUM |

I fogli rimanenti (Anagrafiche_UO, Benchmark_Settore, Soglie_Alert, ecc.) contengono configurazione gia' predisposta e normalmente non devono essere modificati.

---

## 2. Mappa delle Fonti Dati

### Quale gestionale per quale struttura

| Gestionale | Fornitore | Tipo Dato | Strutture | Formato Export |
|------------|-----------|-----------|-----------|----------------|
| **E-Solver** | SISTEMI | Contabilita', Ciclo attivo/passivo, Saldi | Tutte le UO | CSV (sep. `;`) |
| **Zucchetti** | ZUCCHETTI | Paghe, Presenze, Costi personale | Tutte le UO | CSV (sep. `;`) |
| **Caremed/INNOGEA** | INNOGEA | Produzione sanitaria, DRG, Prestazioni | COS, LAB, BET | Excel (.xlsx) |
| **HT Sang** | HT Sang | Produzione sanitaria RSA, FKT, CTA | VLB, CTA, BRG | Excel (.xlsx) |

### Codici Unita' Operative (UO)

| Codice | Nome completo | Tipo | Stato | PL |
|--------|---------------|------|-------|----|
| **VLB** | RSA Villabate | RSA Alzheimer | Operativa | 44 |
| **CTA** | CTA Ex Stagno | CTA Psichiatria | Operativa | 40 |
| **COS** | Casa di Cura Cosentino | Casa di Cura / Riabilitazione | Operativa | 50 |
| **LAB** | Karol Lab | Laboratorio Analisi | Operativa | - |
| **KCP** | Karol Casa Protetta | RSA | Operativa | - |
| **KMC** | Karol Medical Center | Day Surgery / Ambulatorio | In attesa | - |
| **BRG** | Borgo Ritrovato | RSA / FKT / Centro Diurno | In attesa | 80 |
| **ROM** | RSA Roma S. Margherita | Riabilitazione | In attesa | 77 |
| **BET** | Karol Betania | RSA / Riabilitazione (Calabria) | Cliente | - |
| **ZAR** | Zaharaziz | Ristorazione | Cliente | - |

**UO operative (quelle da compilare)**: VLB, CTA, COS, LAB, KCP

---

## 3. Il File Master

### Dove si trova

```
Karol-cruscotto-sicilia/
  dati/
    KAROL_CDG_MASTER.xlsx    <-- QUESTO FILE
```

### Regola d'oro

**NON cambiate mai** i nomi dei fogli, i nomi delle colonne, o la struttura delle righe/colonne. Il sistema legge esattamente quei nomi. Se rinominate una colonna, la dashboard si rompe.

### Backup prima di modificare

Prima di ogni modifica:
1. Copiate il file Master
2. Rinominatelo con la data: `KAROL_CDG_MASTER_backup_2026-02-10.xlsx`
3. Salvate la copia nella cartella `backup/`

---

## 4. Raccolta Dati da E-Solver (SISTEMI)

### 4.1 Cosa serve da E-Solver

Da E-Solver dovete estrarre **due tipologie di dati**:

**A) Saldi contabili per centro di costo** (alimenta il foglio `Costi_Mensili` e `Costi_Sede_Dettaglio`)

**B) Piano dei conti** (alimenta il foglio `Piano_Conti`, una tantum)

### 4.2 Export Saldi da E-Solver

1. Aprite E-Solver
2. Andate su: **Contabilita' > Stampe > Saldi per centro di costo**
3. Impostate il filtro:
   - Periodo: mese di interesse (es. Gennaio 2026)
   - Centro di costo: Tutti (oppure filtrate per UO)
4. Esportate in CSV

Il file CSV esportato deve avere queste colonne (separatore `;`):

```
codice_conto;descrizione;dare;avere;saldo;centro_costo;mese;anno
```

**Formato importi**: italiano con punto per migliaia e virgola per decimali
Esempio: `1.234,56` (NON `1234.56`)

**Esempio di riga**:
```
CD01;Personale - Medici;45.678,90;0,00;45.678,90;VLB;1;2026
```

### 4.3 Come compilare il foglio Costi_Mensili

Il foglio `Costi_Mensili` ha queste colonne:

| Colonna | Descrizione | Esempio |
|---------|-------------|---------|
| `Codice UO` | Codice unita' operativa (3 lettere) | VLB |
| `Codice Voce` | Codice costo dal piano conti | CD01 |
| `Descrizione` | Nome della voce di costo | Personale - Medici |
| `Mese` | Numero del mese (1-12) | 1 |
| `Anno` | Anno di riferimento (4 cifre) | 2026 |
| `Importo` | Importo in euro (numero positivo) | 45678.90 |

**Procedura passo-passo**:

1. Aprite l'export CSV da E-Solver in Excel
2. Aprite il file Master, foglio `Costi_Mensili`
3. Per ogni riga dell'export E-Solver:
   - Identificate il codice voce corrispondente (vedi tabella codici in Appendice)
   - Identificate il centro di costo (= codice UO)
   - Copiate: `Codice UO`, `Codice Voce`, `Descrizione`, `Mese`, `Anno`, `Importo`
4. Salvate

**Codici voce da usare** (i piu' comuni):

| Codice | Voce | Dove trovarla in E-Solver |
|--------|------|---------------------------|
| CD01 | Personale - Medici | Conti 60.10.xxx con CDC = UO |
| CD02 | Personale - Infermieri | Conti 60.20.xxx con CDC = UO |
| CD03 | Personale - OSS/Ausiliari | Conti 60.30.xxx con CDC = UO |
| CD04 | Personale - Tecnici | Conti 60.40.xxx con CDC = UO |
| CD05 | Personale - Amministrativi | Conti 60.50.xxx con CDC = UO |
| CD10 | Farmaci e presidi | Conti 61.xxx con CDC = UO |
| CD11 | Materiale diagnostico | Conti 62.xxx con CDC = UO |
| CD12 | Vitto | Conti 63.xxx con CDC = UO |
| CD20 | Lavanderia | Conti 64.10.xxx con CDC = UO |
| CD21 | Pulizie | Conti 64.20.xxx con CDC = UO |
| CD22 | Manutenzioni | Conti 64.30.xxx con CDC = UO |
| CD23 | Utenze | Conti 64.40.xxx con CDC = UO |
| CD24 | Consulenze sanitarie | Conti 65.xxx con CDC = UO |
| CD30 | Ammortamenti | Conti 66.xxx con CDC = UO |

> **Nota**: La corrispondenza esatta tra i conti E-Solver e i codici Karol CDG dipende dal vostro piano dei conti. Nella fase iniziale, create una tabella di mappatura con il vostro commercialista/contabile.

### 4.4 Come compilare il foglio Costi_Sede_Dettaglio

Stesso procedimento, ma per i costi con centro di costo "Sede" o "HQ":

| Colonna | Descrizione | Esempio |
|---------|-------------|---------|
| `Codice Voce` | Codice costo sede | CS01 |
| `Descrizione` | Nome della voce | Contabilita'/Amministrazione |
| `Mese` | Numero del mese | 1 |
| `Anno` | Anno | 2026 |
| `Importo` | Importo in euro | 18500.00 |

**Codici voce sede**:

| Codice | Voce |
|--------|------|
| CS01 | Contabilita'/Amministrazione |
| CS02 | Paghe/HR |
| CS03 | Acquisti centralizzati |
| CS04 | IT/Sistemi informativi |
| CS05 | Qualita'/Compliance |
| CS10 | Direzione Generale |
| CS11 | Affari Legali |
| CS12 | Strategia/Sviluppo |
| CS20 | Costi comuni non allocabili |

### 4.5 Piano dei Conti (una tantum)

Il foglio `Piano_Conti` va compilato solo la prima volta. Contiene la mappatura tra i conti E-Solver e i codici Karol CDG:

| Colonna | Descrizione | Esempio |
|---------|-------------|---------|
| `codice_conto` | Codice conto E-Solver | 60.10.001 |
| `descrizione` | Descrizione del conto | Stipendi medici |
| `tipo` | "ricavo" oppure "costo" | costo |
| `centro_costo` | Centro di costo E-Solver | VLB |

---

## 5. Raccolta Dati da Zucchetti Paghe

### 5.1 Cosa serve da Zucchetti

Da Zucchetti serve l'**export costi del personale** mensile.

### 5.2 Export da Zucchetti

1. Aprite il portale Zucchetti
2. Andate su: **Report > Costi del personale > Export mensile**
3. Impostate: mese e anno di riferimento
4. Esportate in CSV

Il file CSV esportato deve avere queste colonne (separatore `;`):

```
matricola;cognome;nome;qualifica;unita_operativa;costo_lordo;contributi;tfr;costo_totale;ore_ordinarie;ore_straordinarie;mese;anno
```

**Esempio di riga**:
```
001234;ROSSI;Mario;Medico;VLB;4.500,00;1.485,00;375,00;6.360,00;156;12;1;2026
```

### 5.3 Come compilare il foglio Anagrafiche_Personale

Il foglio `Anagrafiche_Personale` ha queste colonne:

| Colonna | Descrizione | Esempio |
|---------|-------------|---------|
| `Matricola` | Numero matricola Zucchetti | 001234 |
| `Cognome` | Cognome dipendente | ROSSI |
| `Nome` | Nome dipendente | Mario |
| `Qualifica` | Qualifica professionale | Medico |
| `Unita Operativa` | Codice UO (3 lettere) | VLB |
| `Data Assunzione` | Data di assunzione (GG/MM/AAAA) | 15/03/2020 |
| `Tipo Contratto` | Tipo (Tempo Indeterminato, ecc.) | Tempo Indeterminato |
| `Ore Settimanali` | Ore contrattuali settimanali | 36 |
| `RAL` | Retribuzione Annua Lorda | 55000 |
| `Costo Mensile Azienda` | Costo lordo mensile per l'azienda | 6360 |
| `CCNL` | Contratto applicato | AIOP |
| `Livello` | Livello contrattuale | D |

**Procedura passo-passo**:

1. Esportate da Zucchetti l'elenco dipendenti in forza
2. Per ogni dipendente, copiate i dati nelle colonne corrispondenti
3. Usate il codice UO corretto (VLB, CTA, COS, LAB, KCP)
4. Per il campo `Costo Mensile Azienda` usate il valore `costo_totale` di Zucchetti

**Qualifiche accettate dal sistema** (usate esattamente questi nomi):
- `Medico`
- `Infermiere`
- `OSS/Ausiliario`
- `Tecnico Laboratorio`
- `Tecnico Radiologia`
- `Fisioterapista`
- `Amministrativo`
- `Dirigente`
- `Altro`

### 5.4 Collegamento con i costi personale

I costi da Zucchetti confluiscono anche nel foglio `Costi_Mensili` come codici CD01-CD05. Potete:
- **Opzione A**: Inserire i totali per qualifica/UO da Zucchetti nei codici CD01-CD05 di Costi_Mensili
- **Opzione B**: Lasciare che siano i saldi E-Solver a popolare CD01-CD05 (se in E-Solver i costi personale sono registrati per centro di costo)

**Consiglio**: Usate E-Solver come fonte per Costi_Mensili e Zucchetti per Anagrafiche_Personale. In questo modo ogni fonte fa una cosa sola e i dati non si sovrappongono.

---

## 6. Raccolta Dati da Caremed/INNOGEA

### 6.1 Strutture interessate

Caremed e' il gestionale di produzione per:
- **COS** - Casa di Cura Cosentino
- **LAB** - Karol Lab (Laboratorio)
- **BET** - Karol Betania (se gestito centralmente)

### 6.2 Export da Caremed

1. Aprite Caremed/INNOGEA
2. Andate su: **Report > Produzione > Export mensile**
3. Filtrate per: struttura + mese di interesse
4. Esportate in Excel (.xlsx)

Le colonne attese nel file sono:

```
tipo_prestazione | codice | descrizione | quantita | tariffa | importo | data | paziente_id
```

**Esempio**:
| tipo_prestazione | codice | descrizione | quantita | tariffa | importo | data | paziente_id |
|---|---|---|---|---|---|---|---|
| Degenza | DRG_123 | Intervento ortopedico | 1 | 3500.00 | 3500.00 | 15/01/2026 | PAZ001 |
| Ambulatorio | AMB_045 | Visita ortopedica | 1 | 80.00 | 80.00 | 15/01/2026 | PAZ002 |

### 6.3 Come compilare il foglio Produzione_Mensile

Il foglio `Produzione_Mensile` ha queste colonne:

| Colonna | Descrizione | Esempio |
|---------|-------------|---------|
| `Codice UO` | Codice unita' operativa | COS |
| `Codice Voce` | Codice ricavo (R01-R07) | R01 |
| `Descrizione` | Descrizione voce ricavo | Ricavi da convenzione SSN - Degenza |
| `Mese` | Numero del mese | 1 |
| `Anno` | Anno | 2026 |
| `Importo` | Totale ricavi del mese | 285000.00 |
| `Quantita` | Numero prestazioni/giornate | 450 |

**Come trasformare i dati Caremed per il Master**:

1. Raggruppate le prestazioni di Caremed per **tipo** e **mese**
2. Sommate gli importi per ottenere il totale mensile
3. Assegnate il codice ricavo corretto:

| Tipo prestazione Caremed | Codice Karol CDG | Descrizione |
|---|---|---|
| Degenza SSN/Convenzione | **R01** | Ricavi da convenzione SSN/ASP - Degenza |
| Ambulatoriale SSN | **R02** | Ricavi da convenzione SSN/ASP - Ambulatoriale |
| Laboratorio SSN | **R03** | Ricavi da convenzione SSN/ASP - Laboratorio |
| Degenza privata/solvenza | **R04** | Ricavi privati/solvenza - Degenza |
| Pacchetti comfort | **R05** | Ricavi privati/solvenza - Pacchetti comfort |
| Ambulat./Lab. privato | **R06** | Ricavi privati/solvenza - Ambulatoriale/Lab. |
| Altro (affitti, rimborsi) | **R07** | Altri ricavi |

**Esempio pratico**: se a Gennaio 2026 la COS ha prodotto:
- 450 giornate di degenza SSN per EUR 285.000
- 120 visite ambulatoriali SSN per EUR 15.000
- 30 prestazioni private per EUR 8.000

Scriverete 3 righe nel foglio Produzione_Mensile:
```
COS | R01 | Ricavi da convenzione SSN - Degenza   | 1 | 2026 | 285000 | 450
COS | R02 | Ricavi da convenzione SSN - Ambulat.   | 1 | 2026 |  15000 | 120
COS | R06 | Ricavi privati - Ambulat./Lab.         | 1 | 2026 |   8000 |  30
```

---

## 7. Raccolta Dati da HT Sang

### 7.1 Strutture interessate

HT Sang e' il gestionale di produzione per:
- **VLB** - RSA Villabate
- **CTA** - CTA Ex Stagno
- **BRG** - Borgo Ritrovato (quando sara' operativa)

### 7.2 Export da HT Sang

1. Aprite HT Sang
2. Andate su: **Report > Produzione mensile**
3. Filtrate per: struttura + mese
4. Esportate in Excel (.xlsx)

Le colonne sono le stesse di Caremed:
```
tipo_prestazione | codice | descrizione | quantita | tariffa | importo | data | paziente_id
```

### 7.3 Come compilare Produzione_Mensile per RSA/CTA

Per le RSA e CTA, il ricavo principale e' la **retta giornaliera** (convenzione ASP):

| Tipo HT Sang | Codice Karol CDG |
|---|---|
| Retta giornaliera SSN/ASP | **R01** |
| Prestazioni ambulatoriali SSN | **R02** |
| Quota privata/compartecipazione | **R04** |

**Esempio**: VLB a Gennaio 2026, 44 posti letto, occupancy 95%:
- 44 x 31 x 0.95 = 1.296 giornate
- Tariffa ASP: EUR 105/giornata
- Totale: EUR 136.080

```
VLB | R01 | Ricavi da convenzione SSN - Degenza | 1 | 2026 | 136080 | 1296
```

---

## 8. Compilazione Foglio Scadenzario

### 8.1 A cosa serve

Il foglio `Scadenzario` alimenta la sezione **Cash Flow** della dashboard. Serve per prevedere quando entreranno e usciranno i soldi.

### 8.2 Colonne del foglio Scadenzario

| Colonna | Descrizione | Esempio |
|---------|-------------|---------|
| `Data Scadenza` | Quando scade il pagamento/incasso (GG/MM/AAAA) | 15/02/2026 |
| `Tipo (Incasso/Pagamento)` | Scrivere `Incasso` oppure `Pagamento` | Incasso |
| `Categoria` | Tipo di flusso (vedi tabella sotto) | SSN Convenzione |
| `Importo` | Importo in euro (numero positivo) | 136080.00 |
| `Controparte` | Nome del debitore/creditore | ASP Palermo |
| `Unita Operativa` | Codice UO (3 lettere) | VLB |
| `Stato (Previsto/Confermato/Pagato)` | Stato corrente | Previsto |
| `Note` | Note libere (facoltativo) | Retta Gennaio 2026 |

### 8.3 Categorie accettate

**Per gli Incassi** (Tipo = `Incasso`):
| Categoria | Descrizione |
|-----------|-------------|
| `SSN Convenzione` | Incassi da ASP/SSN per prestazioni convenzionate |
| `Privato/Solvenza` | Incassi da pazienti privati |
| `Altro` | Altri incassi (affitti, rimborsi, contributi) |

**Per i Pagamenti** (Tipo = `Pagamento`):
| Categoria | Descrizione |
|-----------|-------------|
| `Fornitori` | Pagamenti a fornitori (farmaci, materiali, servizi) |
| `Personale` | Stipendi e contributi |
| `Fiscale` | F24, IVA, IRES, IRAP |
| `Finanziario` | Rate mutui, leasing, debiti finanziari |
| `CAPEX` | Investimenti in attrezzature/immobili |

### 8.4 Come compilare lo Scadenzario

**Fonti per lo Scadenzario**:

1. **Incassi SSN/ASP**: Prendete le fatture emesse verso ASP dal ciclo attivo E-Solver. Stimate i tempi di incasso (tipicamente 90-150 giorni dalla fattura)

2. **Pagamenti Fornitori**: Prendete lo scadenzario fornitori da E-Solver (ciclo passivo). Per ogni fattura fornitore, inserite la data scadenza e l'importo

3. **Stipendi**: Inserite una riga per ogni mese con il totale costo personale da Zucchetti. Data: 27 del mese (o la data di pagamento stipendi)

4. **Scadenze Fiscali**: Il sistema genera automaticamente le scadenze fiscali standard (F24 il 16 di ogni mese, IVA trimestrale, IRES/IRAP). Se volete valori piu' precisi, inseriteli manualmente

5. **Rate Finanziarie**: Inserite le rate dei mutui/leasing con le date di scadenza

**Esempio completo Scadenzario per un mese**:

| Data Scadenza | Tipo | Categoria | Importo | Controparte | UO | Stato | Note |
|---|---|---|---|---|---|---|---|
| 15/02/2026 | Incasso | SSN Convenzione | 136080.00 | ASP Palermo | VLB | Previsto | Retta Gen 2026 |
| 15/02/2026 | Incasso | SSN Convenzione | 210000.00 | ASP Palermo | CTA | Previsto | Retta Gen 2026 |
| 20/02/2026 | Incasso | SSN Convenzione | 285000.00 | ASP Palermo | COS | Previsto | Degenza Gen 2026 |
| 27/02/2026 | Pagamento | Personale | 380000.00 | Dipendenti | VLB | Confermato | Stipendi Feb 2026 |
| 16/02/2026 | Pagamento | Fiscale | 45000.00 | Erario | SEDE | Confermato | F24 Febbraio |
| 28/02/2026 | Pagamento | Fornitori | 35000.00 | Fornitore Farmaci SpA | COS | Previsto | Ft. 123/2026 |
| 01/03/2026 | Pagamento | Finanziario | 15000.00 | Banca XYZ | SEDE | Confermato | Rata mutuo |

### 8.5 Consigli operativi per lo Scadenzario

- Inserite almeno **6 mesi in avanti** di scadenze per avere previsioni significative
- Aggiornate lo stato: quando un pagamento viene effettuato, cambiate lo stato da `Previsto` a `Pagato`
- Per gli incassi ASP, considerate un ritardo medio di **120 giorni** dalla fattura
- Inserite le scadenze fiscali ricorrenti per tutto l'anno in blocco

---

## 9. Procedura di Sostituzione Dati

### 9.1 Preparazione

**Prima di iniziare, assicuratevi di avere**:

- [ ] Export CSV da E-Solver (saldi per CDC, ultimo mese chiuso)
- [ ] Export CSV da Zucchetti (costi personale, ultimo mese)
- [ ] Export Excel da Caremed (produzione COS + LAB, ultimo mese)
- [ ] Export Excel da HT Sang (produzione VLB + CTA, ultimo mese)
- [ ] Scadenzario fornitori da E-Solver
- [ ] Piano pagamento stipendi
- [ ] Scadenze fiscali prossimi 6 mesi

### 9.2 Procedura passo-passo

**Passo 1: Backup**
1. Aprite la cartella del progetto
2. Copiate `dati/KAROL_CDG_MASTER.xlsx`
3. Incollatelo in `backup/` con nome `KAROL_CDG_MASTER_backup_AAAA-MM-GG.xlsx`

**Passo 2: Pulire i dati demo**
1. Aprite `dati/KAROL_CDG_MASTER.xlsx`
2. Per ogni foglio dati (Costi_Mensili, Produzione_Mensile, Anagrafiche_Personale, Costi_Sede_Dettaglio, Scadenzario):
   - Selezionate tutte le righe di dati (NON l'intestazione, riga 1)
   - Cancellatele (Canc o Elimina righe)
3. NON cancellate la riga di intestazione (riga 1)

**Passo 3: Compilare Piano_Conti (solo la prima volta)**
1. Andate al foglio `Piano_Conti`
2. Copiate la mappatura tra conti E-Solver e codici Karol CDG
3. Questo foglio serve come riferimento, non cambia ogni mese

**Passo 4: Compilare Costi_Mensili**
1. Preparate i dati dall'export E-Solver come spiegato nella Sezione 4.3
2. Incollate nel foglio `Costi_Mensili`
3. Verificate: ogni riga ha un Codice UO valido (VLB, CTA, COS, LAB, KCP)?
4. Verificate: ogni riga ha un Codice Voce valido (CD01-CD30)?

**Passo 5: Compilare Produzione_Mensile**
1. Preparate i dati da Caremed (COS, LAB) e HT Sang (VLB, CTA)
2. Aggregate come spiegato nelle Sezioni 6.3 e 7.3
3. Incollate nel foglio `Produzione_Mensile`
4. Verificate: i codici ricavo sono R01-R07?

**Passo 6: Compilare Anagrafiche_Personale**
1. Preparate l'export da Zucchetti come spiegato nella Sezione 5.3
2. Incollate nel foglio `Anagrafiche_Personale`
3. Verificate: le qualifiche sono quelle accettate dal sistema?

**Passo 7: Compilare Costi_Sede_Dettaglio**
1. Estraete i costi sede da E-Solver (centri di costo "Sede" o "HQ")
2. Incollate nel foglio usando i codici CS01-CS20
3. Verificate: ogni riga ha mese e anno?

**Passo 8: Compilare Scadenzario**
1. Compilate come spiegato nella Sezione 8
2. Inserite almeno 6 mesi di scadenze

**Passo 9: Salvare e verificare**
1. Salvate il file Master (Ctrl+S)
2. Aprite la dashboard (o premete "Ricarica dati" se gia' aperta)
3. Verificate che i dati appaiano correttamente in ogni sezione

---

## 10. Checklist di Validazione

### Dopo aver inserito i dati, verificate:

**Controlli su Costi_Mensili**:
- [ ] Tutte le UO operative hanno almeno una riga (VLB, CTA, COS, LAB, KCP)
- [ ] I codici voce sono tutti validi (CD01-CD30, CS01-CS20)
- [ ] Gli importi sono numeri positivi (no testo, no simboli EUR)
- [ ] Ogni mese ha costi coerenti (il totale non varia troppo da un mese all'altro)
- [ ] Il personale (CD01-CD05) e' coerente con Zucchetti

**Controlli su Produzione_Mensile**:
- [ ] Tutte le UO operative hanno ricavi
- [ ] I codici voce sono R01-R07
- [ ] I ricavi sono coerenti con la produzione effettiva
- [ ] Per le RSA: giornate = posti_letto x giorni_mese x occupancy

**Controlli su Anagrafiche_Personale**:
- [ ] Il numero dipendenti per UO e' corretto
- [ ] Le qualifiche sono tra quelle accettate
- [ ] Il costo mensile azienda e' ragionevole (non troppo basso, non troppo alto)

**Controlli su Scadenzario**:
- [ ] I tipi sono esattamente `Incasso` o `Pagamento` (no varianti)
- [ ] Gli stati sono esattamente `Previsto`, `Confermato` o `Pagato`
- [ ] Le date sono nel formato GG/MM/AAAA
- [ ] Ci sono scadenze per almeno 6 mesi futuri

**Controlli incrociati (coerenza)**:
- [ ] Totale costi personale (CD01-CD05) di Costi_Mensili e' circa uguale a: somma Costo Mensile Azienda di Anagrafiche_Personale x mesi
- [ ] Totale ricavi di Produzione_Mensile e' circa uguale a: somma Incassi SSN dello Scadenzario (con lag temporale)
- [ ] Il rapporto costi/ricavi per UO e' tra 30% e 150% (altrimenti c'e' un errore)

---

## 11. Test e Verifica Dashboard

### 11.1 Avvio dashboard locale

Se state testando in locale:

```
# Aprite un terminale nella cartella del progetto
cd C:\Users\fraca\Karol-cruscotto-sicilia
streamlit run karol_cdg/webapp/app.py
```

### 11.2 Cosa verificare pagina per pagina

**Home**:
- I ricavi consolidati appaiono?
- Il MOL consolidato e' ragionevole (8-20%)?
- I semafori delle UO funzionano?

**CE Industriale**:
- Ogni UO ha ricavi e costi?
- Il MOL industriale e' positivo per le UO operative?
- Le percentuali sono coerenti (costo personale 45-60% dei ricavi)?

**CE Gestionale**:
- I costi sede sono allocati a tutte le UO?
- Il MOL gestionale e' inferiore al MOL industriale (corretto: sede riduce il margine)?

**KPI**:
- Gli indicatori sono tutti popolati (no "N/A" o valori vuoti)?
- L'occupancy delle RSA e' tra 80-100%?

**Cash Flow** (la nuova sezione):
- Il grafico waterfall mostra incassi e pagamenti?
- Il burn rate ha andamento realistico?
- La heatmap scadenze mostra la distribuzione nel tempo?
- Il DSCR e' calcolato (valore tipico > 1.0)?
- Gli alert si attivano se la cassa scende sotto EUR 200.000?

### 11.3 Problemi comuni da cercare

| Sintomo | Causa probabile | Soluzione |
|---------|----------------|-----------|
| "Nessun dato" in una pagina | Foglio Master vuoto o colonna rinominata | Verificare il foglio corrispondente |
| Valori tutti a zero | Importi in formato testo invece che numero | Convertire la colonna in formato numero |
| "KeyError" nel log | Nome colonna errato nel foglio | Controllare che i nomi siano esatti |
| Cash Flow piatto | Scadenzario vuoto | Compilare lo Scadenzario |
| MOL negativo per tutte le UO | Costi inseriti ma ricavi mancanti | Compilare Produzione_Mensile |

---

## 12. Predisposizione per Automazione n8n

### 12.1 Architettura obiettivo

L'obiettivo futuro e' automatizzare il caricamento dati con n8n:

```
                    n8n Workflow
E-Solver ----CSV----> [Nodo 1: Leggi CSV]
                          |
Zucchetti --CSV----> [Nodo 2: Leggi CSV]    ---> [Nodo 5: Scrivi Excel Master]
                          |
Caremed ---Excel---> [Nodo 3: Leggi Excel]
                          |
HT Sang ---Excel---> [Nodo 4: Leggi Excel]
```

### 12.2 Preparazione per n8n

Per quando implementerete n8n, serve che:

1. **Gli export siano standardizzati**: Ogni gestionale deve esportare sempre con le stesse colonne, nello stesso formato, nella stessa cartella

2. **Cartelle di appoggio**: Create queste cartelle per gli export automatici:
   ```
   dati/
     import/
       esolver/        <-- export CSV da E-Solver
       zucchetti/      <-- export CSV da Zucchetti
       caremed/        <-- export Excel da Caremed
       htsang/         <-- export Excel da HT Sang
       archivio/       <-- file processati (n8n li sposta qui)
   ```

3. **Naming convention per i file**: Usate nomi standardizzati per gli export:
   ```
   esolver_saldi_AAAA-MM.csv
   zucchetti_costi_AAAA-MM.csv
   caremed_produzione_UO_AAAA-MM.xlsx
   htsang_produzione_UO_AAAA-MM.xlsx
   ```
   Esempio: `esolver_saldi_2026-02.csv`, `caremed_produzione_COS_2026-02.xlsx`

4. **Tabella di mappatura**: Create un file Excel separato con la mappatura tra conti E-Solver e codici Karol CDG. n8n usera' questa tabella per tradurre automaticamente i codici

### 12.3 Workflow n8n suggerito

Il workflow n8n futuro avra' questi passi:

1. **Trigger**: Schedulato (es. primo del mese) oppure manuale
2. **Leggi export**: Lettura dei file dalle cartelle import
3. **Trasforma**: Mappatura codici, aggregazione, validazione
4. **Scrivi Master**: Aggiornamento dei fogli del file Master
5. **Archivia**: Spostamento file processati in archivio
6. **Notifica**: Email o Slack con riepilogo caricamento

### 12.4 Script Python gia' disponibili

Il sistema ha gia' moduli Python pronti per l'import automatizzato:

| Modulo | Cosa fa | File |
|--------|---------|------|
| `import_esolver.py` | Legge CSV E-Solver, converte importi italiani, valida | `karol_cdg/data/import_esolver.py` |
| `import_zucchetti.py` | Legge CSV Zucchetti, converte ore (HH:MM), calcola FTE | `karol_cdg/data/import_zucchetti.py` |
| `import_produzione.py` | Legge Excel Caremed/HT Sang, normalizza | `karol_cdg/data/import_produzione.py` |
| `validators.py` | Valida codici UO, periodi, coerenza importi | `karol_cdg/data/validators.py` |

Questi moduli possono essere richiamati da n8n tramite un nodo "Execute Command" o attraverso un piccolo script wrapper.

---

## 13. Risoluzione Problemi Comuni

### Problema: La dashboard mostra "File Master non trovato"

**Causa**: Il file non si trova nel percorso atteso.

**Soluzione**:
1. Verificate che il file sia in `dati/KAROL_CDG_MASTER.xlsx`
2. Verificate che il nome sia esattamente `KAROL_CDG_MASTER.xlsx` (maiuscole/minuscole contano)
3. Se siete su Streamlit Cloud, verificate che il file sia nel repository Git

### Problema: I numeri sono tutti zero o NaN

**Causa**: Gli importi sono in formato testo invece che numero.

**Soluzione**:
1. Aprite il foglio in Excel
2. Selezionate la colonna degli importi
3. Verificate che il formato cella sia "Numero", non "Testo"
4. Se necessario: Dati > Testo in colonne > Fine (forzare la conversione)
5. Rimuovete eventuali simboli EUR o spazi

### Problema: "KeyError: 'Codice UO'" nel log

**Causa**: La colonna ha un nome diverso da quello atteso (es. spazio in piu', accento mancante).

**Soluzione**:
1. Aprite il foglio in Excel
2. Verificate che l'intestazione (riga 1) corrisponda esattamente ai nomi nella tabella
3. Attenzione a: spazi prima/dopo il nome, lettere maiuscole/minuscole

### Problema: Il Cash Flow e' piatto (linea dritta)

**Causa**: Lo Scadenzario e' vuoto o ha poche righe.

**Soluzione**:
1. Compilate lo Scadenzario con almeno 6 mesi di scadenze
2. Assicuratevi di avere sia Incassi che Pagamenti
3. Dopo aver compilato, premete "Ricarica dati" nella dashboard

### Problema: Il MOL e' negativo per tutte le UO

**Causa**: Mancano i ricavi oppure i costi sono gonfiati.

**Soluzione**:
1. Verificate che Produzione_Mensile abbia righe per tutte le UO
2. Confrontate il totale ricavi con i dati reali
3. Verificate che i costi non siano inseriti 2 volte (es. personale sia in E-Solver che in Zucchetti)

### Problema: Streamlit Cloud non si aggiorna

**Causa**: Le modifiche al file Master non sono nel repository Git.

**Soluzione**:
1. Committate le modifiche:
   ```
   git add dati/KAROL_CDG_MASTER.xlsx
   git commit -m "Aggiornamento dati mese AAAA-MM"
   git push
   ```
2. Attendete 2-3 minuti che Streamlit Cloud rilevi il cambiamento
3. Premete "Ricarica dati" nella dashboard

---

## 14. Appendice

### A. Tabella completa Codici Voce

#### Ricavi (R01-R07)
| Codice | Descrizione |
|--------|-------------|
| R01 | Ricavi da convenzione SSN/ASP - Degenza |
| R02 | Ricavi da convenzione SSN/ASP - Ambulatoriale |
| R03 | Ricavi da convenzione SSN/ASP - Laboratorio |
| R04 | Ricavi privati/solvenza - Degenza |
| R05 | Ricavi privati/solvenza - Pacchetti comfort |
| R06 | Ricavi privati/solvenza - Ambulatoriale/Laboratorio |
| R07 | Altri ricavi (affitti, rimborsi, contributi) |

#### Costi Diretti (CD01-CD30)
| Codice | Descrizione |
|--------|-------------|
| **Personale** | |
| CD01 | Personale - Medici |
| CD02 | Personale - Infermieri |
| CD03 | Personale - OSS/Ausiliari |
| CD04 | Personale - Tecnici (lab, rad, FKT) |
| CD05 | Personale - Amministrativi di struttura |
| **Acquisti** | |
| CD10 | Farmaci e presidi sanitari |
| CD11 | Materiale diagnostico |
| CD12 | Vitto (gestione interna) |
| CD13 | Altri materiali di consumo |
| **Servizi** | |
| CD20 | Lavanderia |
| CD21 | Pulizie |
| CD22 | Manutenzioni ordinarie |
| CD23 | Utenze (quota struttura) |
| CD24 | Consulenze sanitarie esterne |
| **Ammortamenti** | |
| CD30 | Ammortamenti attrezzature e arredi |

#### Costi Sede (CS01-CS20)
| Codice | Descrizione | Driver allocazione |
|--------|-------------|-------------------|
| CS01 | Contabilita'/Amministrazione | Numero fatture |
| CS02 | Paghe/HR | Numero cedolini |
| CS03 | Acquisti centralizzati | Euro acquistato |
| CS04 | IT/Sistemi informativi | Numero postazioni IT |
| CS05 | Qualita'/Compliance | Posti letto |
| CS10 | Direzione Generale | Ricavi |
| CS11 | Affari Legali | Quota fissa |
| CS12 | Strategia/Sviluppo | Non allocabile |
| CS20 | Costi comuni non allocabili | Non allocabile |

#### Altri Costi (AC01-AC03)
| Codice | Descrizione |
|--------|-------------|
| AC01 | Ammortamenti immobili/investimenti centralizzati |
| AC02 | Oneri finanziari (quota debito) |
| AC03 | Imposte |

### B. Parametri Cash Flow configurati

| Parametro | Valore | Significato |
|-----------|--------|-------------|
| Cassa iniziale default | EUR 500.000 | Saldo cassa di partenza |
| Soglia minima cassa | EUR 200.000 | Sotto questo valore scatta l'alert rosso |
| DSCR warning | 1.1 | Sotto questo valore: attenzione |
| DSCR critico | 1.0 | Sotto 1.0: non si coprono i debiti |
| Servizio debito annuale | EUR 180.000 | Rate mutui/leasing annuali |
| Aliquota contributiva | 33% | Per stima oneri su payroll |

### C. Calendario aggiornamento consigliato

| Quando | Cosa fare | Fonte |
|--------|-----------|-------|
| **1-5 del mese** | Chiudere mese precedente in E-Solver | Amministrazione |
| **5-10 del mese** | Esportare saldi CDC da E-Solver | Controller |
| **5-10 del mese** | Esportare costi personale da Zucchetti | HR/Paghe |
| **5-10 del mese** | Esportare produzione da Caremed e HT Sang | Resp. sanitari |
| **10-15 del mese** | Compilare/aggiornare Master Excel | Controller |
| **10-15 del mese** | Aggiornare Scadenzario (nuove scadenze) | Controller |
| **15 del mese** | Verificare dashboard e segnalare anomalie | Controller |
| **Trimestrale** | Revisione completa dati e benchmark | Controller + DG |

---

**Fine della guida**

Per domande o supporto tecnico, contattare il team di sviluppo.
