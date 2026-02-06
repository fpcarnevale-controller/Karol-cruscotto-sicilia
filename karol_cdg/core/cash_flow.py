"""
Calcolo dei flussi di cassa (Cash Flow).

Il modulo gestisce due orizzonti di analisi:

1. CASH FLOW OPERATIVO (1-3 mesi, granularità settimanale/mensile)
   - Basato sullo scadenzario reale (fatture da incassare / da pagare)
   - Utile per la gestione quotidiana della tesoreria
   - Alert su criticità di cassa a breve termine

2. CASH FLOW STRATEGICO (12-60 mesi, granularità annuale)
   - Basato su proiezioni EBITDA, investimenti, debito
   - Utile per pianificazione finanziaria e valutazione sostenibilità
   - Scenari ottimistico / base / pessimistico

KPI finanziari collegati:
    - DSO (Days Sales Outstanding) - tempi medi di incasso
    - DPO (Days Payable Outstanding) - tempi medi di pagamento
    - Copertura cassa - mesi di autonomia finanziaria

Autore: Karol CDG
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    ALERT_CONFIG,
    SCENARI_CASH_FLOW,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class VoceScadenzario:
    """
    Rappresenta una singola voce dello scadenzario (incasso o pagamento).

    Attributi:
        data_scadenza: data prevista per l'incasso o il pagamento
        tipo: 'incasso' o 'pagamento'
        categoria: categoria della voce (es. "ASP Palermo", "Fornitore farmaci")
        importo: importo in euro (sempre positivo)
        controparte: nome della controparte (ASP, fornitore, ecc.)
        nota: nota esplicativa
        stato: stato della voce ('previsto', 'confermato', 'pagato')
    """
    data_scadenza: date
    tipo: str  # 'incasso' o 'pagamento'
    categoria: str
    importo: float
    controparte: str = ""
    nota: str = ""
    stato: str = "previsto"  # 'previsto', 'confermato', 'pagato'


# ============================================================================
# CASH FLOW OPERATIVO
# ============================================================================


def calcola_cash_flow_operativo(
    scadenzario: List[VoceScadenzario],
    cassa_iniziale: float,
    settimane: int = 12,
) -> pd.DataFrame:
    """
    Calcola il cash flow operativo settimanale/mensile basato sullo
    scadenzario reale di incassi e pagamenti.

    Per ogni settimana calcola:
    - Incassi previsti/confermati
    - Pagamenti previsti/confermati
    - Flusso netto settimanale
    - Saldo cassa progressivo

    Parametri:
        scadenzario: lista di VoceScadenzario con tutti gli incassi/pagamenti
        cassa_iniziale: saldo di cassa all'inizio del periodo (euro)
        settimane: numero di settimane da proiettare (default: 12 = ~3 mesi)

    Ritorna:
        DataFrame con colonne:
            - settimana: numero progressivo
            - data_inizio: data inizio settimana
            - data_fine: data fine settimana
            - incassi_previsti: totale incassi previsti nella settimana
            - incassi_confermati: totale incassi confermati nella settimana
            - pagamenti_previsti: totale pagamenti previsti nella settimana
            - pagamenti_confermati: totale pagamenti confermati nella settimana
            - flusso_netto: incassi - pagamenti
            - saldo_cassa: saldo progressivo
    """
    logger.info(
        "Calcolo cash flow operativo: %d voci scadenzario, cassa iniziale=%.2f, "
        "%d settimane",
        len(scadenzario),
        cassa_iniziale,
        settimane,
    )

    oggi = date.today()
    # Inizio settimana corrente (lunedì)
    inizio = oggi - timedelta(days=oggi.weekday())

    righe = []
    saldo = cassa_iniziale

    for i in range(settimane):
        data_inizio_sett = inizio + timedelta(weeks=i)
        data_fine_sett = data_inizio_sett + timedelta(days=6)

        # Filtra le voci dello scadenzario per questa settimana
        incassi_previsti = 0.0
        incassi_confermati = 0.0
        pagamenti_previsti = 0.0
        pagamenti_confermati = 0.0

        for voce in scadenzario:
            if data_inizio_sett <= voce.data_scadenza <= data_fine_sett:
                if voce.tipo == "incasso":
                    if voce.stato == "confermato":
                        incassi_confermati += voce.importo
                    elif voce.stato == "previsto":
                        incassi_previsti += voce.importo
                    # Se 'pagato', è già stato incassato: non lo consideriamo
                    # nel futuro ma potrebbe servire per riconciliazione
                elif voce.tipo == "pagamento":
                    if voce.stato == "confermato":
                        pagamenti_confermati += voce.importo
                    elif voce.stato == "previsto":
                        pagamenti_previsti += voce.importo

        totale_incassi = incassi_previsti + incassi_confermati
        totale_pagamenti = pagamenti_previsti + pagamenti_confermati
        flusso_netto = totale_incassi - totale_pagamenti
        saldo += flusso_netto

        righe.append({
            "settimana": i + 1,
            "data_inizio": data_inizio_sett,
            "data_fine": data_fine_sett,
            "incassi_previsti": round(incassi_previsti, 2),
            "incassi_confermati": round(incassi_confermati, 2),
            "totale_incassi": round(totale_incassi, 2),
            "pagamenti_previsti": round(pagamenti_previsti, 2),
            "pagamenti_confermati": round(pagamenti_confermati, 2),
            "totale_pagamenti": round(totale_pagamenti, 2),
            "flusso_netto": round(flusso_netto, 2),
            "saldo_cassa": round(saldo, 2),
        })

    df = pd.DataFrame(righe)
    logger.info(
        "Cash flow operativo calcolato: saldo finale=%.2f",
        saldo if righe else cassa_iniziale,
    )
    return df


# ============================================================================
# CASH FLOW STRATEGICO
# ============================================================================


def calcola_cash_flow_strategico(
    ebitda_annuale: float,
    variazione_ccn: float,
    capex: float,
    servizio_debito: float,
    imposte: float,
    anni: int = 5,
    crescita_params: dict = None,
) -> pd.DataFrame:
    """
    Calcola il cash flow strategico pluriennale (metodo indiretto).

    Struttura del calcolo:
        EBITDA
        - Variazione CCN (Capitale Circolante Netto)
        = Cash flow operativo
        - CAPEX (investimenti)
        = Free Cash Flow
        - Servizio debito (quota capitale + interessi)
        - Imposte
        = Cash flow netto

    Parametri:
        ebitda_annuale: EBITDA di partenza (anno 1)
        variazione_ccn: assorbimento/rilascio CCN annuale (positivo = assorbimento)
        capex: investimenti annuali previsti
        servizio_debito: quota annuale di rimborso debito + interessi
        imposte: imposte annuali stimate
        anni: numero di anni da proiettare (default: 5)
        crescita_params: parametri di crescita annuale (opzionale):
            {
                'crescita_ebitda_pct': float,  # crescita % annuale EBITDA
                'riduzione_ccn_pct': float,    # miglioramento % CCN annuale
                'capex_anno': dict,            # {anno: capex} per investimenti specifici
            }

    Ritorna:
        DataFrame con colonne:
            - anno: numero progressivo (1, 2, 3, ...)
            - ebitda: EBITDA dell'anno
            - variazione_ccn: variazione CCN dell'anno
            - cash_flow_operativo: EBITDA - variazione CCN
            - capex: investimenti dell'anno
            - free_cash_flow: CF operativo - CAPEX
            - servizio_debito: rimborso debito dell'anno
            - imposte: imposte dell'anno
            - cash_flow_netto: CF finale dell'anno
            - cash_flow_cumulato: CF netto cumulato
    """
    logger.info(
        "Calcolo cash flow strategico: EBITDA=%.2f, anni=%d", ebitda_annuale, anni
    )

    if crescita_params is None:
        crescita_params = {}

    crescita_ebitda = crescita_params.get("crescita_ebitda_pct", 0.0)
    riduzione_ccn = crescita_params.get("riduzione_ccn_pct", 0.0)
    capex_per_anno = crescita_params.get("capex_anno", {})

    righe = []
    cumulato = 0.0

    for anno in range(1, anni + 1):
        # Calcola EBITDA con crescita progressiva
        ebitda = ebitda_annuale * ((1 + crescita_ebitda) ** (anno - 1))

        # Calcola variazione CCN con miglioramento progressivo
        var_ccn = variazione_ccn * ((1 - riduzione_ccn) ** (anno - 1))

        # CAPEX: usa valore specifico per anno se disponibile
        capex_anno = capex_per_anno.get(anno, capex)

        # Calcoli
        cf_operativo = ebitda - var_ccn
        free_cf = cf_operativo - capex_anno
        cf_netto = free_cf - servizio_debito - imposte
        cumulato += cf_netto

        righe.append({
            "anno": anno,
            "ebitda": round(ebitda, 2),
            "variazione_ccn": round(var_ccn, 2),
            "cash_flow_operativo": round(cf_operativo, 2),
            "capex": round(capex_anno, 2),
            "free_cash_flow": round(free_cf, 2),
            "servizio_debito": round(servizio_debito, 2),
            "imposte": round(imposte, 2),
            "cash_flow_netto": round(cf_netto, 2),
            "cash_flow_cumulato": round(cumulato, 2),
        })

    df = pd.DataFrame(righe)
    logger.info(
        "Cash flow strategico calcolato: CF netto anno 1=%.2f, cumulato %d anni=%.2f",
        righe[0]["cash_flow_netto"] if righe else 0.0,
        anni,
        cumulato,
    )
    return df


# ============================================================================
# SCENARI
# ============================================================================


def applica_scenario(
    cash_flow_base: pd.DataFrame,
    parametri_scenario: dict,
) -> pd.DataFrame:
    """
    Applica un set di parametri scenario al cash flow base,
    generando una proiezione ottimistica, base o pessimistica.

    I parametri dello scenario possono modificare:
    - Ricavi (crescita o contrazione)
    - DSO (tempi di incasso)
    - Costi imprevisti
    - Occupancy (tasso di occupazione)

    Parametri:
        cash_flow_base: DataFrame del cash flow base (output di calcola_cash_flow_strategico)
        parametri_scenario: dizionario parametri dallo scenario
            (vedi SCENARI_CASH_FLOW in config.py)

    Ritorna:
        DataFrame modificato con lo scenario applicato
    """
    nome_scenario = parametri_scenario.get("label", "Scenario")
    logger.info("Applicazione scenario '%s' al cash flow", nome_scenario)

    df = cash_flow_base.copy()

    crescita_ricavi = parametri_scenario.get("crescita_ricavi_pct", 0.0)
    costi_imprevisti = parametri_scenario.get("costi_imprevisti_pct", 0.0)
    occupancy_delta = parametri_scenario.get("occupancy_delta", 0.0)

    for idx in df.index:
        anno = df.loc[idx, "anno"]

        # Modifica EBITDA per crescita ricavi e variazione occupancy
        fattore_ricavi = (1 + crescita_ricavi) ** anno
        fattore_occupancy = 1 + occupancy_delta
        fattore_combinato = fattore_ricavi * fattore_occupancy

        df.loc[idx, "ebitda"] = round(
            df.loc[idx, "ebitda"] * fattore_combinato, 2
        )

        # Aggiungi costi imprevisti come riduzione del CF operativo
        imprevisti = df.loc[idx, "ebitda"] * costi_imprevisti
        df.loc[idx, "cash_flow_operativo"] = round(
            df.loc[idx, "ebitda"] - df.loc[idx, "variazione_ccn"] - imprevisti, 2
        )

        # Ricalcola le voci a cascata
        df.loc[idx, "free_cash_flow"] = round(
            df.loc[idx, "cash_flow_operativo"] - df.loc[idx, "capex"], 2
        )
        df.loc[idx, "cash_flow_netto"] = round(
            df.loc[idx, "free_cash_flow"]
            - df.loc[idx, "servizio_debito"]
            - df.loc[idx, "imposte"],
            2,
        )

    # Ricalcola il cumulato
    cumulato = 0.0
    for idx in df.index:
        cumulato += df.loc[idx, "cash_flow_netto"]
        df.loc[idx, "cash_flow_cumulato"] = round(cumulato, 2)

    # Aggiungi colonna scenario
    df["scenario"] = nome_scenario

    return df


# ============================================================================
# KPI FINANZIARI
# ============================================================================


def calcola_dso(
    crediti: float, ricavi_periodo: float, giorni_periodo: int
) -> float:
    """
    Calcola il DSO (Days Sales Outstanding) - giorni medi di incasso.

    Formula: DSO = (Crediti / Ricavi periodo) * Giorni periodo

    Nel contesto sanitario siciliano, il DSO verso le ASP può essere
    molto elevato (120-180 giorni). Il benchmark è:
    - ASP: < 150 giorni (alert se > 150)
    - Privati: < 60 giorni

    Parametri:
        crediti: saldo crediti verso clienti (euro)
        ricavi_periodo: ricavi del periodo di riferimento (euro)
        giorni_periodo: numero di giorni del periodo (es. 365, 90, 30)

    Ritorna:
        DSO in giorni
    """
    if ricavi_periodo == 0.0:
        logger.warning("Ricavi pari a zero, impossibile calcolare DSO")
        return 0.0

    dso = (crediti / ricavi_periodo) * giorni_periodo
    logger.debug("DSO calcolato: %.1f giorni", dso)
    return round(dso, 1)


def calcola_dpo(
    debiti: float, acquisti_periodo: float, giorni_periodo: int
) -> float:
    """
    Calcola il DPO (Days Payable Outstanding) - giorni medi di pagamento.

    Formula: DPO = (Debiti / Acquisti periodo) * Giorni periodo

    Parametri:
        debiti: saldo debiti verso fornitori (euro)
        acquisti_periodo: acquisti del periodo di riferimento (euro)
        giorni_periodo: numero di giorni del periodo (es. 365, 90, 30)

    Ritorna:
        DPO in giorni
    """
    if acquisti_periodo == 0.0:
        logger.warning("Acquisti pari a zero, impossibile calcolare DPO")
        return 0.0

    dpo = (debiti / acquisti_periodo) * giorni_periodo
    logger.debug("DPO calcolato: %.1f giorni", dpo)
    return round(dpo, 1)


def calcola_copertura_cassa(
    cassa: float, uscite_medie_mensili: float
) -> float:
    """
    Calcola la copertura di cassa in mesi.

    Indica quanti mesi l'azienda può sostenere le uscite correnti
    con la cassa disponibile, senza nuovi incassi.

    Formula: Copertura = Cassa / Uscite medie mensili

    Parametri:
        cassa: saldo di cassa disponibile (euro)
        uscite_medie_mensili: media mensile delle uscite (euro)

    Ritorna:
        Copertura in mesi (es. 2.5 = due mesi e mezzo)
    """
    if uscite_medie_mensili == 0.0:
        logger.warning("Uscite mensili pari a zero, copertura illimitata")
        return float("inf")

    copertura = cassa / uscite_medie_mensili
    logger.debug("Copertura cassa: %.1f mesi", copertura)
    return round(copertura, 1)


# ============================================================================
# ALERT DI CASSA
# ============================================================================


def genera_alert_cassa(
    cash_flow: pd.DataFrame, soglie: dict = None
) -> list:
    """
    Genera alert automatici sulla base del cash flow calcolato.

    Alert possibili:
    - ROSSO: saldo cassa negativo in qualsiasi settimana/anno
    - ROSSO: saldo cassa sotto la soglia minima
    - GIALLO: copertura cassa inferiore alla soglia
    - GIALLO: flusso netto negativo per più settimane consecutive

    Parametri:
        cash_flow: DataFrame del cash flow (operativo o strategico)
        soglie: dizionario con le soglie personalizzate (opzionale,
                default da ALERT_CONFIG)

    Ritorna:
        Lista di dizionari alert:
        [
            {
                'livello': 'rosso' | 'giallo' | 'verde',
                'messaggio': str,
                'periodo': str,         # settimana o anno
                'valore': float,
                'soglia': float,
            }
        ]
    """
    if soglie is None:
        soglie = ALERT_CONFIG

    cassa_minima = soglie.get("cassa_minima", 200_000)

    alert_list = []

    # Verifica se il DataFrame ha la colonna 'saldo_cassa' (operativo)
    # o 'cash_flow_cumulato' (strategico)
    colonna_saldo = None
    colonna_periodo = None

    if "saldo_cassa" in cash_flow.columns:
        colonna_saldo = "saldo_cassa"
        colonna_periodo = "settimana"
    elif "cash_flow_cumulato" in cash_flow.columns:
        colonna_saldo = "cash_flow_cumulato"
        colonna_periodo = "anno"
    else:
        logger.warning("DataFrame non riconosciuto per generazione alert")
        return alert_list

    settimane_negative_consecutive = 0

    for _, riga in cash_flow.iterrows():
        saldo = riga.get(colonna_saldo, 0.0)
        periodo = riga.get(colonna_periodo, "N/D")
        flusso = riga.get("flusso_netto", riga.get("cash_flow_netto", 0.0))

        # Alert ROSSO: saldo cassa negativo
        if saldo < 0:
            alert_list.append({
                "livello": "rosso",
                "messaggio": (
                    f"CRITICO: Saldo cassa negativo al periodo {periodo} "
                    f"({saldo:,.2f} euro)"
                ),
                "periodo": str(periodo),
                "valore": saldo,
                "soglia": 0.0,
            })

        # Alert ROSSO: saldo sotto la soglia minima
        elif saldo < cassa_minima:
            alert_list.append({
                "livello": "rosso",
                "messaggio": (
                    f"ATTENZIONE: Saldo cassa ({saldo:,.2f} euro) "
                    f"sotto la soglia minima ({cassa_minima:,.2f} euro) "
                    f"al periodo {periodo}"
                ),
                "periodo": str(periodo),
                "valore": saldo,
                "soglia": cassa_minima,
            })

        # Conteggio settimane con flusso negativo consecutivo
        if flusso < 0:
            settimane_negative_consecutive += 1
        else:
            # Alert GIALLO se ci sono state 3+ settimane negative consecutive
            if settimane_negative_consecutive >= 3:
                alert_list.append({
                    "livello": "giallo",
                    "messaggio": (
                        f"ATTENZIONE: {settimane_negative_consecutive} periodi "
                        f"consecutivi con flusso netto negativo "
                        f"(fino al periodo {periodo})"
                    ),
                    "periodo": str(periodo),
                    "valore": float(settimane_negative_consecutive),
                    "soglia": 3.0,
                })
            settimane_negative_consecutive = 0

    # Controlla se l'ultimo periodo ha ancora una sequenza negativa aperta
    if settimane_negative_consecutive >= 3:
        ultimo_periodo = cash_flow.iloc[-1].get(colonna_periodo, "N/D")
        alert_list.append({
            "livello": "giallo",
            "messaggio": (
                f"ATTENZIONE: {settimane_negative_consecutive} periodi "
                f"consecutivi con flusso netto negativo (in corso, "
                f"ultimo periodo {ultimo_periodo})"
            ),
            "periodo": str(ultimo_periodo),
            "valore": float(settimane_negative_consecutive),
            "soglia": 3.0,
        })

    if not alert_list:
        logger.info("Nessun alert di cassa generato")
    else:
        n_rossi = sum(1 for a in alert_list if a["livello"] == "rosso")
        n_gialli = sum(1 for a in alert_list if a["livello"] == "giallo")
        logger.info(
            "Generati %d alert di cassa: %d rossi, %d gialli",
            len(alert_list),
            n_rossi,
            n_gialli,
        )

    return alert_list
