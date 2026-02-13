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

import numpy as np
import pandas as pd

from karol_cdg.config import CASH_FLOW_CONFIG

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


# ============================================================================
# STIMA PAYROLL MENSILE
# ============================================================================


def stima_payroll_mensile(
    anagrafiche_personale: pd.DataFrame,
    mese: int,
    anno: int,
) -> dict:
    """
    Stima le uscite mensili per stipendi e oneri contributivi
    a partire dal foglio Anagrafiche_Personale del Master.

    Colonne attese nel DataFrame:
        - Costo Lordo: retribuzione lorda mensile
        - Contributi: contributi previdenziali (se presente)
        - FTE: full-time equivalent (per proporzionare)
        - Mese, Anno: periodo di riferimento

    Se il DataFrame è vuoto o non ha le colonne attese, ritorna stime
    basate su parametri di default (ricavi consolidati ~€10.4M).

    Parametri:
        anagrafiche_personale: DataFrame dal foglio Anagrafiche_Personale
        mese: mese di riferimento (1-12)
        anno: anno di riferimento

    Ritorna:
        dict con chiavi: stipendi_lordi, oneri_contributivi, totale_payroll
    """
    aliquota = CASH_FLOW_CONFIG.get("aliquota_contributiva", 0.33)

    # Filtra per il periodo richiesto se le colonne esistono
    df = anagrafiche_personale.copy()
    if df.empty or "Costo Lordo" not in df.columns:
        # Stima basata su parametri di default: ~60% dei ricavi annui
        # Ricavi consolidati ~€10.4M → costo personale ~€6.2M → mensile ~€520K
        stipendi_lordi = 520_000.0
        oneri = stipendi_lordi * aliquota
        logger.warning(
            "Anagrafiche_Personale vuoto o senza colonne attese, "
            "uso stima di default payroll=%.0f €/mese",
            stipendi_lordi + oneri,
        )
        return {
            "stipendi_lordi": round(stipendi_lordi, 2),
            "oneri_contributivi": round(oneri, 2),
            "totale_payroll": round(stipendi_lordi + oneri, 2),
        }

    # Filtra per mese/anno se disponibili
    if "Mese" in df.columns and "Anno" in df.columns:
        df_periodo = df[(df["Mese"] == mese) & (df["Anno"] == anno)]
        if df_periodo.empty:
            # Se nessun dato per il periodo, usa l'ultimo disponibile
            df_periodo = df
    else:
        df_periodo = df

    # Calcola totale lordo
    stipendi_lordi = pd.to_numeric(df_periodo["Costo Lordo"], errors="coerce").sum()
    if stipendi_lordi == 0:
        stipendi_lordi = 520_000.0

    # Se la colonna Contributi è presente, usala; altrimenti stima
    if "Contributi" in df_periodo.columns:
        oneri = pd.to_numeric(df_periodo["Contributi"], errors="coerce").sum()
        if oneri == 0:
            oneri = stipendi_lordi * aliquota
    else:
        oneri = stipendi_lordi * aliquota

    totale = stipendi_lordi + oneri

    logger.info(
        "Stima payroll %02d/%d: lordi=%.2f, oneri=%.2f, totale=%.2f",
        mese, anno, stipendi_lordi, oneri, totale,
    )

    return {
        "stipendi_lordi": round(stipendi_lordi, 2),
        "oneri_contributivi": round(oneri, 2),
        "totale_payroll": round(totale, 2),
    }


# ============================================================================
# SCADENZE FISCALI RICORRENTI
# ============================================================================


def genera_scadenze_fiscali(anno: int) -> List[VoceScadenzario]:
    """
    Genera le scadenze fiscali ricorrenti italiane come VoceScadenzario.

    Scadenze generate:
    - F24 (giorno 16 di ogni mese): versamento ritenute e contributi
    - IVA trimestrale (mesi 3, 6, 9, 12): liquidazione IVA
    - IRES/IRAP acconto (30 giugno): acconto imposte
    - IRES/IRAP saldo (30 novembre): saldo imposte

    Importi stimati in proporzione ai ricavi consolidati (~€10.4M).

    Parametri:
        anno: anno di riferimento

    Ritorna:
        Lista di VoceScadenzario con le scadenze fiscali
    """
    scadenze = []
    config_fiscale = CASH_FLOW_CONFIG.get("scadenze_fiscali_tipo", {})

    # F24 mensile: ritenute + contributi (~4% dei ricavi mensili)
    # Ricavi ~€10.4M → mensile ~€867K → F24 ~€35K/mese
    importo_f24_mensile = 35_000.0
    f24_config = config_fiscale.get("F24", {"giorno": 16})
    giorno_f24 = f24_config.get("giorno", 16)

    for mese in range(1, 13):
        try:
            data_scad = date(anno, mese, giorno_f24)
        except ValueError:
            # Se il giorno non esiste nel mese (es. 30 febbraio)
            data_scad = date(anno, mese, 28) if mese == 2 else date(anno, mese, giorno_f24)

        scadenze.append(VoceScadenzario(
            data_scadenza=data_scad,
            tipo="pagamento",
            categoria="Fiscale - F24",
            importo=importo_f24_mensile,
            controparte="Erario",
            nota=f"F24 ritenute e contributi {mese:02d}/{anno}",
            stato="previsto",
        ))

    # IVA trimestrale: ~2.5% dei ricavi trimestrali
    # Ricavi ~€10.4M → trimestrale ~€2.6M → IVA netta ~€65K/trim
    importo_iva_trim = 65_000.0
    iva_config = config_fiscale.get("IVA", {"mesi": [3, 6, 9, 12]})
    mesi_iva = iva_config.get("mesi", [3, 6, 9, 12])

    for mese in mesi_iva:
        giorno_iva = 16
        try:
            data_scad = date(anno, mese, giorno_iva)
        except ValueError:
            data_scad = date(anno, mese, 28)

        scadenze.append(VoceScadenzario(
            data_scadenza=data_scad,
            tipo="pagamento",
            categoria="Fiscale - IVA",
            importo=importo_iva_trim,
            controparte="Erario",
            nota=f"Liquidazione IVA trimestrale Q{mese // 3}/{anno}",
            stato="previsto",
        ))

    # IRES/IRAP acconto (30 giugno)
    # Stima: ~3% dei ricavi → ~€312K annuo → acconto 40% = ~€125K
    ires_acconto_config = config_fiscale.get("IRES_IRAP_acconto", {"mese": 6, "giorno": 30})
    importo_acconto = 125_000.0
    scadenze.append(VoceScadenzario(
        data_scadenza=date(anno, ires_acconto_config.get("mese", 6),
                          ires_acconto_config.get("giorno", 30)),
        tipo="pagamento",
        categoria="Fiscale - IRES/IRAP",
        importo=importo_acconto,
        controparte="Erario",
        nota=f"Acconto IRES/IRAP {anno}",
        stato="previsto",
    ))

    # IRES/IRAP saldo (30 novembre)
    # Saldo 60% = ~€187K
    ires_saldo_config = config_fiscale.get("IRES_IRAP_saldo", {"mese": 11, "giorno": 30})
    importo_saldo = 187_000.0
    scadenze.append(VoceScadenzario(
        data_scadenza=date(anno, ires_saldo_config.get("mese", 11),
                          ires_saldo_config.get("giorno", 30)),
        tipo="pagamento",
        categoria="Fiscale - IRES/IRAP",
        importo=importo_saldo,
        controparte="Erario",
        nota=f"Saldo IRES/IRAP {anno}",
        stato="previsto",
    ))

    logger.info(
        "Generate %d scadenze fiscali per anno %d",
        len(scadenze), anno,
    )
    return scadenze


# ============================================================================
# CASH FLOW DIRETTO SETTIMANALE
# ============================================================================


def _converti_scadenzario_df(scadenzario_df: pd.DataFrame) -> List[VoceScadenzario]:
    """
    Converte il foglio Scadenzario del Master Excel in una lista di VoceScadenzario.

    Colonne attese:
        - Data Scadenza
        - Tipo (Incasso/Pagamento)
        - Categoria
        - Importo
        - Controparte
        - Stato (Previsto/Confermato/Pagato)
        - Note
    """
    voci = []
    if scadenzario_df.empty:
        return voci

    for _, row in scadenzario_df.iterrows():
        try:
            data_raw = row.get("Data Scadenza")
            if pd.isna(data_raw):
                continue

            if isinstance(data_raw, datetime):
                data_scad = data_raw.date()
            elif isinstance(data_raw, date):
                data_scad = data_raw
            elif isinstance(data_raw, str):
                # Prova formato dd/mm/yyyy
                data_scad = datetime.strptime(data_raw, "%d/%m/%Y").date()
            else:
                continue

            tipo_raw = str(row.get("Tipo (Incasso/Pagamento)", "")).strip().lower()
            if "incasso" in tipo_raw:
                tipo = "incasso"
            elif "pagamento" in tipo_raw:
                tipo = "pagamento"
            else:
                tipo = tipo_raw

            importo = float(row.get("Importo", 0) or 0)
            if importo == 0:
                continue

            stato_raw = str(row.get("Stato (Previsto/Confermato/Pagato)", "previsto")).strip().lower()
            if "confermato" in stato_raw:
                stato = "confermato"
            elif "pagato" in stato_raw:
                stato = "pagato"
            else:
                stato = "previsto"

            voci.append(VoceScadenzario(
                data_scadenza=data_scad,
                tipo=tipo,
                categoria=str(row.get("Categoria", "") or ""),
                importo=abs(importo),
                controparte=str(row.get("Controparte", "") or ""),
                nota=str(row.get("Note", "") or ""),
                stato=stato,
            ))
        except (ValueError, TypeError) as e:
            logger.warning("Riga scadenzario non valida, saltata: %s", e)
            continue

    logger.info("Convertite %d voci dallo scadenzario Excel", len(voci))
    return voci


def calcola_cash_flow_diretto_settimanale(
    scadenzario_df: pd.DataFrame,
    payroll: dict,
    scadenze_fiscali: list,
    cassa_iniziale: float,
    costi_mensili_df: pd.DataFrame,
    settimane: int = 12,
    ritardo_incassi_giorni: int = 0,
) -> pd.DataFrame:
    """
    Implementa il Direct Cash Flow Method con granularità settimanale.

    Converte il foglio Scadenzario del Master in VoceScadenzario, integra
    le stime di payroll e scadenze fiscali, e produce un cash flow
    settimanale dettagliato.

    Il parametro ritardo_incassi_giorni sposta in avanti le date degli
    incassi per la sensitivity analysis.

    Parametri:
        scadenzario_df: DataFrame dal foglio Scadenzario del Master
        payroll: dict con stima payroll mensile (da stima_payroll_mensile)
        scadenze_fiscali: lista di VoceScadenzario fiscali
        cassa_iniziale: saldo di cassa iniziale (euro)
        costi_mensili_df: DataFrame dal foglio Costi_Mensili
        settimane: numero di settimane da proiettare (default: 12)
        ritardo_incassi_giorni: giorni di ritardo incassi (sensitivity)

    Ritorna:
        DataFrame settimanale con colonne:
            cassa_iniziale, incassi_operativi, uscite_personale,
            uscite_fornitori, uscite_fiscali, uscite_investimenti,
            flusso_netto, cassa_finale
    """
    logger.info(
        "Calcolo cash flow diretto settimanale: cassa_iniziale=%.2f, "
        "settimane=%d, ritardo_incassi=%d gg",
        cassa_iniziale, settimane, ritardo_incassi_giorni,
    )

    # Converti scadenzario Excel in voci
    voci_scadenzario = _converti_scadenzario_df(scadenzario_df)

    # Applica ritardo incassi
    if ritardo_incassi_giorni > 0:
        for voce in voci_scadenzario:
            if voce.tipo == "incasso":
                voce.data_scadenza = voce.data_scadenza + timedelta(
                    days=ritardo_incassi_giorni
                )

    # Aggiungi scadenze fiscali
    tutte_le_voci = voci_scadenzario + list(scadenze_fiscali)

    # Stima uscite fornitori non-personale dai costi mensili
    # Filtra solo costi non-personale (CD10+) per evitare doppio conteggio
    uscite_fornitori_mensili = 0.0
    if not costi_mensili_df.empty and "Importo" in costi_mensili_df.columns:
        df_costi = costi_mensili_df.copy()
        df_costi["Importo"] = pd.to_numeric(df_costi["Importo"], errors="coerce")

        # Escludi voci personale (CD01-CD05) se colonna Codice Voce esiste
        if "Codice Voce" in df_costi.columns:
            mask_non_pers = ~df_costi["Codice Voce"].astype(str).str.match(
                r"^CD0[1-5]$", na=False
            )
            df_non_pers = df_costi[mask_non_pers]
        else:
            df_non_pers = df_costi

        # Calcola media mensile (il df ha più mesi di dati)
        if "Anno" in df_non_pers.columns and "Mese" in df_non_pers.columns:
            n_mesi = df_non_pers.groupby(["Anno", "Mese"]).ngroups
            totale = df_non_pers["Importo"].sum()
            uscite_fornitori_mensili = totale / max(n_mesi, 1)
        else:
            uscite_fornitori_mensili = df_non_pers["Importo"].sum()

    if uscite_fornitori_mensili == 0:
        uscite_fornitori_mensili = 200_000.0

    # Payroll settimanale
    payroll_settimanale = payroll.get("totale_payroll", 0.0) / 4.33

    # Fornitori settimanale (già escluso personale)
    fornitori_settimanale = uscite_fornitori_mensili / 4.33

    # CAPEX mensile dal piano industriale
    anno_corrente = date.today().year
    capex_annuale = CASH_FLOW_CONFIG.get("capex_piano_industriale", {}).get(
        anno_corrente, 0
    )
    capex_settimanale = capex_annuale / 52

    # Stima ricavi settimanali di base (per settimane senza incassi da scadenzario)
    # = payroll + fornitori + margine 10% (l'azienda deve essere in equilibrio)
    ricavi_settimanali_stima = (payroll_settimanale + fornitori_settimanale) * 1.10

    oggi = date.today()
    inizio = oggi - timedelta(days=oggi.weekday())

    righe = []
    saldo = cassa_iniziale

    for i in range(settimane):
        data_inizio_sett = inizio + timedelta(weeks=i)
        data_fine_sett = data_inizio_sett + timedelta(days=6)

        # Incassi operativi dalla scadenzario
        incassi = 0.0
        uscite_fiscali = 0.0

        for voce in tutte_le_voci:
            if data_inizio_sett <= voce.data_scadenza <= data_fine_sett:
                if voce.tipo == "incasso" and voce.stato != "pagato":
                    incassi += voce.importo
                elif voce.tipo == "pagamento" and voce.stato != "pagato":
                    if "Fiscal" in voce.categoria or "F24" in voce.categoria or \
                       "IVA" in voce.categoria or "IRES" in voce.categoria:
                        uscite_fiscali += voce.importo

        # Se incassi da scadenzario inferiori alla stima settimanale,
        # usa la stima come baseline (lo scadenzario e' incompleto)
        incassi = max(incassi, ricavi_settimanali_stima)

        flusso_netto = (
            incassi
            - payroll_settimanale
            - fornitori_settimanale
            - uscite_fiscali
            - capex_settimanale
        )

        cassa_inizio = saldo
        saldo += flusso_netto

        righe.append({
            "settimana": i + 1,
            "data_inizio": data_inizio_sett,
            "data_fine": data_fine_sett,
            "cassa_iniziale": round(cassa_inizio, 2),
            "incassi_operativi": round(incassi, 2),
            "uscite_personale": round(payroll_settimanale, 2),
            "uscite_fornitori": round(fornitori_settimanale, 2),
            "uscite_fiscali": round(uscite_fiscali, 2),
            "uscite_investimenti": round(capex_settimanale, 2),
            "flusso_netto": round(flusso_netto, 2),
            "cassa_finale": round(saldo, 2),
        })

    df = pd.DataFrame(righe)
    logger.info(
        "Cash flow diretto settimanale calcolato: %d settimane, "
        "cassa finale=%.2f",
        settimane, saldo,
    )
    return df


# ============================================================================
# CASH FLOW DIRETTO MENSILE
# ============================================================================


def calcola_cash_flow_diretto_mensile(
    scadenzario_df: pd.DataFrame,
    payroll: dict,
    scadenze_fiscali: list,
    cassa_iniziale: float,
    costi_mensili_df: pd.DataFrame,
    mesi: int = 24,
    ritardo_incassi_giorni: int = 0,
) -> pd.DataFrame:
    """
    Implementa il Direct Cash Flow Method con granularità mensile
    per un orizzonte di 12-24 mesi.

    Stessa logica del settimanale, aggregata per mese.

    Parametri:
        scadenzario_df: DataFrame dal foglio Scadenzario
        payroll: dict con stima payroll mensile
        scadenze_fiscali: lista di VoceScadenzario fiscali
        cassa_iniziale: saldo di cassa iniziale (euro)
        costi_mensili_df: DataFrame dal foglio Costi_Mensili
        mesi: numero di mesi da proiettare (default: 24)
        ritardo_incassi_giorni: giorni di ritardo incassi (sensitivity)

    Ritorna:
        DataFrame mensile con stesse colonne del settimanale +
        colonna mese_anno (str)
    """
    logger.info(
        "Calcolo cash flow diretto mensile: cassa_iniziale=%.2f, "
        "mesi=%d, ritardo_incassi=%d gg",
        cassa_iniziale, mesi, ritardo_incassi_giorni,
    )

    voci_scadenzario = _converti_scadenzario_df(scadenzario_df)

    if ritardo_incassi_giorni > 0:
        for voce in voci_scadenzario:
            if voce.tipo == "incasso":
                voce.data_scadenza = voce.data_scadenza + timedelta(
                    days=ritardo_incassi_giorni
                )

    tutte_le_voci = voci_scadenzario + list(scadenze_fiscali)

    # Stima uscite fornitori non-personale dai costi mensili
    uscite_fornitori_mensili = 0.0
    if not costi_mensili_df.empty and "Importo" in costi_mensili_df.columns:
        df_costi = costi_mensili_df.copy()
        df_costi["Importo"] = pd.to_numeric(df_costi["Importo"], errors="coerce")

        # Escludi voci personale (CD01-CD05) se colonna Codice Voce esiste
        if "Codice Voce" in df_costi.columns:
            mask_non_pers = ~df_costi["Codice Voce"].astype(str).str.match(
                r"^CD0[1-5]$", na=False
            )
            df_non_pers = df_costi[mask_non_pers]
        else:
            df_non_pers = df_costi

        # Calcola media mensile
        if "Anno" in df_non_pers.columns and "Mese" in df_non_pers.columns:
            n_mesi = df_non_pers.groupby(["Anno", "Mese"]).ngroups
            totale = df_non_pers["Importo"].sum()
            uscite_fornitori_mensili = totale / max(n_mesi, 1)
        else:
            uscite_fornitori_mensili = df_non_pers["Importo"].sum()

    if uscite_fornitori_mensili == 0:
        uscite_fornitori_mensili = 200_000.0

    payroll_mensile = payroll.get("totale_payroll", 0.0)

    fornitori_mensile = uscite_fornitori_mensili

    # Stima ricavi mensili di base = costi totali + margine 10%
    ricavi_mensili_stima = (payroll_mensile + fornitori_mensile) * 1.10

    capex_piano = CASH_FLOW_CONFIG.get("capex_piano_industriale", {})

    oggi = date.today()
    righe = []
    saldo = cassa_iniziale

    for i in range(mesi):
        # Calcola mese/anno del periodo
        mese_num = ((oggi.month - 1 + i) % 12) + 1
        anno_num = oggi.year + ((oggi.month - 1 + i) // 12)

        # Primo e ultimo giorno del mese
        primo_giorno = date(anno_num, mese_num, 1)
        if mese_num == 12:
            ultimo_giorno = date(anno_num, 12, 31)
        else:
            ultimo_giorno = date(anno_num, mese_num + 1, 1) - timedelta(days=1)

        # Incassi dal scadenzario
        incassi = 0.0
        uscite_fiscali = 0.0

        for voce in tutte_le_voci:
            if primo_giorno <= voce.data_scadenza <= ultimo_giorno:
                if voce.tipo == "incasso" and voce.stato != "pagato":
                    incassi += voce.importo
                elif voce.tipo == "pagamento" and voce.stato != "pagato":
                    if "Fiscal" in voce.categoria or "F24" in voce.categoria or \
                       "IVA" in voce.categoria or "IRES" in voce.categoria:
                        uscite_fiscali += voce.importo

        # Se incassi da scadenzario inferiori alla stima mensile,
        # usa la stima come baseline (lo scadenzario e' incompleto)
        incassi = max(incassi, ricavi_mensili_stima)

        # CAPEX mensile per l'anno
        capex_mensile = capex_piano.get(anno_num, 0) / 12

        flusso_netto = (
            incassi
            - payroll_mensile
            - fornitori_mensile
            - uscite_fiscali
            - capex_mensile
        )

        cassa_inizio = saldo
        saldo += flusso_netto

        from karol_cdg.config import MESI_BREVI_IT
        label_mese = f"{MESI_BREVI_IT.get(mese_num, str(mese_num))} {anno_num}"

        righe.append({
            "periodo": i + 1,
            "mese_anno": label_mese,
            "mese": mese_num,
            "anno": anno_num,
            "data_inizio": primo_giorno,
            "data_fine": ultimo_giorno,
            "cassa_iniziale": round(cassa_inizio, 2),
            "incassi_operativi": round(incassi, 2),
            "uscite_personale": round(payroll_mensile, 2),
            "uscite_fornitori": round(fornitori_mensile, 2),
            "uscite_fiscali": round(uscite_fiscali, 2),
            "uscite_investimenti": round(capex_mensile, 2),
            "flusso_netto": round(flusso_netto, 2),
            "cassa_finale": round(saldo, 2),
        })

    df = pd.DataFrame(righe)
    logger.info(
        "Cash flow diretto mensile calcolato: %d mesi, cassa finale=%.2f",
        mesi, saldo,
    )
    return df


# ============================================================================
# DSCR PROSPETTICO
# ============================================================================


def calcola_dscr_prospettico(
    cash_flow_df: pd.DataFrame,
    servizio_debito_annuale: float,
) -> pd.DataFrame:
    """
    Calcola il Debt Service Coverage Ratio prospettico periodo per periodo.

    Formula: DSCR = Cash Flow Operativo / Servizio Debito per periodo

    Per cash flow settimanale, il servizio debito viene rapportato alla settimana.
    Per cash flow mensile, viene rapportato al mese.

    Parametri:
        cash_flow_df: DataFrame del cash flow (settimanale o mensile)
        servizio_debito_annuale: servizio debito annuo (euro)

    Ritorna:
        DataFrame con colonne aggiuntive: dscr, alert_dscr
    """
    df = cash_flow_df.copy()

    # Determina la granularità e rapporta il servizio debito
    if "settimana" in df.columns:
        servizio_debito_periodo = servizio_debito_annuale / 52
    else:
        servizio_debito_periodo = servizio_debito_annuale / 12

    if servizio_debito_periodo == 0:
        df["dscr"] = float("inf")
        df["alert_dscr"] = False
        return df

    # Cash flow operativo = incassi - uscite personale - uscite fornitori
    if "incassi_operativi" in df.columns:
        cf_operativo = (
            df["incassi_operativi"]
            - df["uscite_personale"]
            - df["uscite_fornitori"]
        )
    elif "flusso_netto" in df.columns:
        cf_operativo = df["flusso_netto"] + df.get("uscite_fiscali", 0) + \
                       df.get("uscite_investimenti", 0)
    else:
        cf_operativo = pd.Series([0.0] * len(df))

    df["dscr"] = (cf_operativo / servizio_debito_periodo).round(2)
    df["alert_dscr"] = df["dscr"] < CASH_FLOW_CONFIG.get("dscr_warning", 1.1)

    logger.info(
        "DSCR prospettico calcolato: min=%.2f, max=%.2f, periodi con alert=%d",
        df["dscr"].min(),
        df["dscr"].max(),
        df["alert_dscr"].sum(),
    )
    return df


# ============================================================================
# CLASSIFICAZIONE SCADENZE PER PRIORITA'
# ============================================================================


# Categorie e parole chiave per classificazione
_CATEGORIE_INDIFFERIBILI = [
    "stipend", "personale", "paga", "payroll",
    "f24", "fiscal", "tribut", "iva", "ires", "irap",
    "contribut", "inps", "inail",
    "mutuo", "rata", "finanziament", "leasing",
    "affitto", "canone",
]

_SUGGERIMENTI_DIFFERIBILI = {
    "fornitor": "Negoziare dilazione pagamento a 60-90 gg",
    "material": "Valutare acquisto just-in-time per ridurre esposizione",
    "manutenz": "Differire manutenzioni non urgenti al mese successivo",
    "consult": "Rinegoziare termini contrattuali di pagamento",
    "invest": "Valutare riscadenziamento dell'investimento",
    "attrezzat": "Valutare leasing operativo in alternativa all'acquisto",
}


def classifica_scadenze_priorita(
    scadenzario: List[VoceScadenzario],
) -> pd.DataFrame:
    """
    Classifica ogni scadenza come 'Indifferibile' o 'Differibile'.

    Scadenze Indifferibili: stipendi, F24, contributi, rate mutuo, affitti.
    Scadenze Differibili: fornitori non critici, investimenti differibili.

    Parametri:
        scadenzario: lista di VoceScadenzario

    Ritorna:
        DataFrame con colonne: data, tipo, importo, controparte,
        priorita, suggerimento_azione
    """
    righe = []

    for voce in scadenzario:
        testo_ricerca = (
            f"{voce.categoria} {voce.controparte} {voce.nota}"
        ).lower()

        # Classifica come indifferibile se contiene parole chiave
        indifferibile = any(
            keyword in testo_ricerca for keyword in _CATEGORIE_INDIFFERIBILI
        )
        priorita = "Indifferibile" if indifferibile else "Differibile"

        # Genera suggerimento per scadenze differibili
        suggerimento = ""
        if not indifferibile:
            for keyword, sugg in _SUGGERIMENTI_DIFFERIBILI.items():
                if keyword in testo_ricerca:
                    suggerimento = sugg
                    break
            if not suggerimento:
                suggerimento = "Valutare possibilità di dilazione"

        righe.append({
            "data": voce.data_scadenza,
            "tipo": voce.tipo,
            "categoria": voce.categoria,
            "importo": voce.importo,
            "controparte": voce.controparte,
            "priorita": priorita,
            "suggerimento_azione": suggerimento,
        })

    df = pd.DataFrame(righe)

    if not df.empty:
        n_indiff = (df["priorita"] == "Indifferibile").sum()
        n_diff = (df["priorita"] == "Differibile").sum()
        logger.info(
            "Classificazione scadenze: %d indifferibili, %d differibili",
            n_indiff, n_diff,
        )

    return df


# ============================================================================
# BURN RATE E RUNWAY
# ============================================================================


def calcola_burn_rate(
    cassa_iniziale: float,
    cash_flow_df: pd.DataFrame,
) -> dict:
    """
    Calcola il burn rate medio mensile e il runway (mesi di sopravvivenza).

    Il burn rate rappresenta il consumo medio mensile di cassa.
    Il runway indica quanti mesi la cassa attuale può sostenere le operazioni.

    Se il flusso netto medio è positivo (l'azienda genera cassa),
    data_esaurimento è None e runway è infinito.

    Parametri:
        cassa_iniziale: saldo di cassa attuale (euro)
        cash_flow_df: DataFrame del cash flow (mensile o settimanale)

    Ritorna:
        dict con chiavi:
            - burn_rate_mensile: consumo medio mensile (positivo = uscita netta)
            - runway_mesi: mesi di sopravvivenza
            - data_esaurimento: data stimata esaurimento cassa (o None)
    """
    if cash_flow_df.empty:
        return {
            "burn_rate_mensile": 0.0,
            "runway_mesi": float("inf"),
            "data_esaurimento": None,
        }

    # Calcola burn rate medio
    if "settimana" in cash_flow_df.columns:
        # Cash flow settimanale → converti in mensile
        flusso_medio_settimanale = cash_flow_df["flusso_netto"].mean()
        burn_rate = -flusso_medio_settimanale * 4.33
    else:
        burn_rate = -cash_flow_df["flusso_netto"].mean()

    if burn_rate <= 0:
        # L'azienda genera cassa: nessun esaurimento
        return {
            "burn_rate_mensile": round(burn_rate, 2),
            "runway_mesi": float("inf"),
            "data_esaurimento": None,
        }

    runway = cassa_iniziale / burn_rate
    data_esaurimento = date.today() + timedelta(days=int(runway * 30.44))

    logger.info(
        "Burn rate: %.2f €/mese, runway: %.1f mesi, esaurimento: %s",
        burn_rate, runway, data_esaurimento,
    )

    return {
        "burn_rate_mensile": round(burn_rate, 2),
        "runway_mesi": round(runway, 1),
        "data_esaurimento": data_esaurimento,
    }
