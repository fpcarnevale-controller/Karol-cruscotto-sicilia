"""
Modulo di validazione dati.

Fornisce funzioni per la validazione e il controllo di qualita' dei dati
importati nel sistema di Controllo di Gestione Karol:
  - Validazione codici unita' operative
  - Validazione formati periodo (MM/YYYY)
  - Controllo completezza dati (colonne obbligatorie e valori nulli)
  - Verifica coerenza importi (ricavi vs costi)
  - Generazione report di validazione testuale
  - Individuazione duplicati

Tutte le funzioni gestiscono errori in modo controllato e registrano
le anomalie tramite il modulo logging.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd

from karol_cdg.config import (
    ALERT_CONFIG,
    FORMATO_MESE,
    MESI_IT,
    RICAVI_RIFERIMENTO,
    UNITA_OPERATIVE,
)

logger = logging.getLogger(__name__)

# ============================================================================
# COSTANTI INTERNE
# ============================================================================

# Pattern per il formato periodo MM/YYYY
_PATTERN_PERIODO = re.compile(r"^(0[1-9]|1[0-2])/(\d{4})$")

# Soglie per la validazione coerenza importi
_RAPPORTO_COSTI_RICAVI_MAX = 1.5  # Costi non devono superare il 150% dei ricavi
_RAPPORTO_COSTI_RICAVI_MIN = 0.3  # Costi non dovrebbero essere sotto il 30% dei ricavi


# ============================================================================
# FUNZIONI PUBBLICHE
# ============================================================================


def valida_codice_uo(codice: str) -> bool:
    """
    Valida che un codice unita' operativa esista nell'anagrafica
    configurata in config.py (dizionario UNITA_OPERATIVE).

    Parametri
    ---------
    codice : str
        Codice dell'unita' operativa da validare (es. "VLB", "COS").

    Ritorna
    -------
    bool
        True se il codice esiste nell'anagrafica, False altrimenti.
    """
    if not codice or not isinstance(codice, str):
        logger.warning("Codice UO nullo o non stringa: %s", codice)
        return False

    codice_normalizzato = codice.strip().upper()

    if codice_normalizzato in UNITA_OPERATIVE:
        logger.debug(
            "Codice UO '%s' valido: %s",
            codice_normalizzato,
            UNITA_OPERATIVE[codice_normalizzato].nome,
        )
        return True

    logger.warning(
        "Codice UO '%s' non trovato nell'anagrafica. "
        "Codici validi: %s",
        codice_normalizzato,
        list(UNITA_OPERATIVE.keys()),
    )
    return False


def valida_periodo(periodo: str) -> bool:
    """
    Valida che una stringa periodo sia nel formato MM/YYYY e rappresenti
    una data plausibile.

    Parametri
    ---------
    periodo : str
        Stringa del periodo da validare (es. "03/2025", "12/2024").

    Ritorna
    -------
    bool
        True se il formato e' valido e la data e' plausibile, False altrimenti.
    """
    if not periodo or not isinstance(periodo, str):
        logger.warning("Periodo nullo o non stringa: %s", periodo)
        return False

    periodo_pulito = periodo.strip()

    # Verifica formato con espressione regolare
    match = _PATTERN_PERIODO.match(periodo_pulito)
    if not match:
        logger.warning(
            "Formato periodo non valido: '%s'. Atteso MM/YYYY (es. '03/2025').",
            periodo_pulito,
        )
        return False

    mese = int(match.group(1))
    anno = int(match.group(2))

    # Verifica plausibilita' dell'anno (non troppo nel passato o futuro)
    anno_corrente = datetime.now().year
    if anno < 2000 or anno > anno_corrente + 2:
        logger.warning(
            "Anno non plausibile nel periodo '%s': %d. "
            "Atteso tra 2000 e %d.",
            periodo_pulito,
            anno,
            anno_corrente + 2,
        )
        return False

    logger.debug(
        "Periodo '%s' valido: %s %d",
        periodo_pulito,
        MESI_IT.get(mese, str(mese)),
        anno,
    )
    return True


def valida_completezza_dati(
    dati: pd.DataFrame, colonne_richieste: list
) -> dict:
    """
    Verifica la completezza dei dati in un DataFrame:
    - Presenza di tutte le colonne richieste
    - Conteggio valori nulli per colonna
    - Percentuale di completezza complessiva

    Parametri
    ---------
    dati : pd.DataFrame
        DataFrame da validare.
    colonne_richieste : list
        Lista dei nomi delle colonne obbligatorie.

    Ritorna
    -------
    dict
        Dizionario con i risultati della validazione:
        - valido (bool): True se tutte le colonne sono presenti
        - colonne_mancanti (list): colonne richieste non trovate
        - colonne_presenti (list): colonne richieste trovate
        - righe_totali (int): numero totale di righe
        - valori_nulli (dict): conteggio nulli per ogni colonna richiesta
        - percentuale_completezza (float): % di celle non nulle
        - messaggio (str): riepilogo della validazione
    """
    risultato = {
        "valido": False,
        "colonne_mancanti": [],
        "colonne_presenti": [],
        "righe_totali": 0,
        "valori_nulli": {},
        "percentuale_completezza": 0.0,
        "messaggio": "",
    }

    # Gestione DataFrame nullo o vuoto
    if dati is None:
        risultato["messaggio"] = "DataFrame nullo."
        logger.error(risultato["messaggio"])
        return risultato

    if dati.empty:
        risultato["messaggio"] = "DataFrame vuoto (nessuna riga)."
        logger.warning(risultato["messaggio"])
        return risultato

    risultato["righe_totali"] = len(dati)

    # Verifica presenza colonne
    colonne_mancanti = [c for c in colonne_richieste if c not in dati.columns]
    colonne_presenti = [c for c in colonne_richieste if c in dati.columns]

    risultato["colonne_mancanti"] = colonne_mancanti
    risultato["colonne_presenti"] = colonne_presenti

    if colonne_mancanti:
        risultato["messaggio"] = (
            f"Colonne mancanti: {colonne_mancanti}. "
            f"Trovate {len(colonne_presenti)}/{len(colonne_richieste)} "
            f"colonne richieste."
        )
        logger.error(risultato["messaggio"])
        # Calcola completezza solo sulle colonne presenti
        if not colonne_presenti:
            return risultato
    else:
        risultato["valido"] = True

    # Analisi valori nulli per ogni colonna presente
    celle_totali = 0
    celle_nulle_totali = 0

    for col in colonne_presenti:
        # Conta come nullo: NaN, None, stringhe vuote
        nulli = dati[col].isna().sum()
        if dati[col].dtype == object:
            nulli += (dati[col].str.strip() == "").sum()

        risultato["valori_nulli"][col] = int(nulli)
        celle_totali += len(dati)
        celle_nulle_totali += nulli

    # Calcola percentuale di completezza
    if celle_totali > 0:
        risultato["percentuale_completezza"] = round(
            (1.0 - celle_nulle_totali / celle_totali) * 100, 2
        )

    # Segnala colonne con molti valori nulli (>10%)
    colonne_con_nulli = {
        col: n_nulli
        for col, n_nulli in risultato["valori_nulli"].items()
        if n_nulli > 0
    }

    if colonne_con_nulli:
        dettaglio = ", ".join(
            f"{col}: {n}" for col, n in colonne_con_nulli.items()
        )
        msg_nulli = f"Valori nulli rilevati: {dettaglio}."
        if risultato["valido"]:
            risultato["messaggio"] = (
                f"Tutte le colonne presenti. "
                f"Completezza: {risultato['percentuale_completezza']:.1f}%. "
                f"{msg_nulli}"
            )
        else:
            risultato["messaggio"] += f" {msg_nulli}"
        logger.info(risultato["messaggio"])
    elif risultato["valido"]:
        risultato["messaggio"] = (
            f"Dati completi: {len(colonne_presenti)} colonne, "
            f"{risultato['righe_totali']} righe, "
            f"completezza {risultato['percentuale_completezza']:.1f}%."
        )
        logger.info(risultato["messaggio"])

    return risultato


def valida_coerenza_importi(ricavi: float, costi: float) -> dict:
    """
    Verifica la coerenza tra ricavi e costi.

    Controlli effettuati:
    - I ricavi non devono essere negativi
    - I costi non devono essere negativi
    - Il rapporto costi/ricavi deve essere ragionevole
    - Il margine non deve essere eccessivamente negativo

    Parametri
    ---------
    ricavi : float
        Totale ricavi del periodo.
    costi : float
        Totale costi del periodo.

    Ritorna
    -------
    dict
        Dizionario con i risultati della validazione:
        - coerente (bool): True se gli importi sono coerenti
        - ricavi (float): importo ricavi
        - costi (float): importo costi
        - margine (float): ricavi - costi
        - margine_percentuale (float): margine / ricavi * 100
        - rapporto_costi_ricavi (float): costi / ricavi
        - anomalie (list): lista di anomalie rilevate
        - messaggio (str): riepilogo
    """
    risultato = {
        "coerente": True,
        "ricavi": ricavi,
        "costi": costi,
        "margine": 0.0,
        "margine_percentuale": 0.0,
        "rapporto_costi_ricavi": 0.0,
        "anomalie": [],
        "messaggio": "",
    }

    # Controllo valori negativi
    if ricavi < 0:
        risultato["anomalie"].append(
            f"Ricavi negativi: {ricavi:,.2f} euro."
        )
        risultato["coerente"] = False

    if costi < 0:
        risultato["anomalie"].append(
            f"Costi negativi: {costi:,.2f} euro."
        )
        risultato["coerente"] = False

    # Calcolo margine
    margine = ricavi - costi
    risultato["margine"] = round(margine, 2)

    # Calcolo percentuali (evita divisione per zero)
    if ricavi > 0:
        risultato["margine_percentuale"] = round((margine / ricavi) * 100, 2)
        risultato["rapporto_costi_ricavi"] = round(costi / ricavi, 4)
    elif costi > 0:
        # Ricavi zero ma costi presenti: anomalia
        risultato["anomalie"].append(
            f"Ricavi nulli con costi presenti ({costi:,.2f} euro)."
        )
        risultato["coerente"] = False

    # Controllo rapporto costi/ricavi
    if ricavi > 0:
        rapporto = costi / ricavi

        if rapporto > _RAPPORTO_COSTI_RICAVI_MAX:
            risultato["anomalie"].append(
                f"Rapporto costi/ricavi anomalo: {rapporto:.2f} "
                f"(soglia massima: {_RAPPORTO_COSTI_RICAVI_MAX:.2f}). "
                f"I costi superano significativamente i ricavi."
            )
            risultato["coerente"] = False

        if rapporto < _RAPPORTO_COSTI_RICAVI_MIN and costi > 0:
            risultato["anomalie"].append(
                f"Rapporto costi/ricavi molto basso: {rapporto:.2f} "
                f"(soglia minima: {_RAPPORTO_COSTI_RICAVI_MIN:.2f}). "
                f"Possibile incompletezza dei dati di costo."
            )

    # Controllo MOL minimo da config
    mol_minimo = ALERT_CONFIG.get("mol_minimo_uo", 0.05)
    if ricavi > 0 and risultato["margine_percentuale"] / 100 < -mol_minimo:
        risultato["anomalie"].append(
            f"Margine fortemente negativo: {risultato['margine_percentuale']:.1f}%."
        )

    # Costruzione messaggio riepilogativo
    if risultato["anomalie"]:
        risultato["messaggio"] = (
            f"Validazione importi: {len(risultato['anomalie'])} anomalia/e. "
            + " ".join(risultato["anomalie"])
        )
        logger.warning(risultato["messaggio"])
    else:
        risultato["messaggio"] = (
            f"Importi coerenti. "
            f"Ricavi: {ricavi:,.2f}, Costi: {costi:,.2f}, "
            f"Margine: {margine:,.2f} ({risultato['margine_percentuale']:.1f}%)."
        )
        logger.info(risultato["messaggio"])

    return risultato


def report_validazione(risultati: list) -> str:
    """
    Genera un report di validazione testuale a partire da una lista
    di risultati di validazione.

    Ogni elemento della lista puo' essere un dizionario restituito da una
    delle funzioni di validazione di questo modulo (valida_completezza_dati,
    valida_coerenza_importi, ecc.) oppure un dizionario generico con
    almeno le chiavi 'tipo' e 'messaggio'.

    Parametri
    ---------
    risultati : list
        Lista di dizionari con i risultati delle validazioni.

    Ritorna
    -------
    str
        Report testuale formattato.
    """
    if not risultati:
        return "Nessun risultato di validazione da riportare."

    linee = []
    linee.append("=" * 70)
    linee.append("REPORT DI VALIDAZIONE DATI")
    linee.append(f"Data generazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linee.append("=" * 70)
    linee.append("")

    n_ok = 0
    n_warning = 0
    n_errore = 0

    for i, risultato in enumerate(risultati, start=1):
        if not isinstance(risultato, dict):
            linee.append(f"[{i}] Risultato non valido (tipo: {type(risultato)})")
            n_errore += 1
            continue

        # Determina lo stato della validazione
        # Controlla diverse chiavi possibili per lo stato
        valido = risultato.get("valido", risultato.get("coerente", risultato.get("quadra")))
        tipo = risultato.get("tipo", f"Validazione #{i}")
        messaggio = risultato.get("messaggio", "Nessun dettaglio disponibile.")

        if valido is True:
            stato = "[OK]"
            n_ok += 1
        elif valido is False:
            anomalie = risultato.get("anomalie", [])
            if anomalie:
                stato = "[ERRORE]"
                n_errore += 1
            else:
                stato = "[ERRORE]"
                n_errore += 1
        else:
            stato = "[ATTENZIONE]"
            n_warning += 1

        linee.append(f"  {stato} {tipo}")
        linee.append(f"         {messaggio}")

        # Dettaglio anomalie se presenti
        anomalie = risultato.get("anomalie", [])
        if anomalie:
            for anomalia in anomalie:
                linee.append(f"         - {anomalia}")

        # Dettaglio valori nulli se presenti
        valori_nulli = risultato.get("valori_nulli", {})
        nulli_significativi = {
            col: n for col, n in valori_nulli.items() if n > 0
        }
        if nulli_significativi:
            linee.append("         Valori nulli per colonna:")
            for col, n_nulli in nulli_significativi.items():
                righe_tot = risultato.get("righe_totali", 0)
                pct = (n_nulli / righe_tot * 100) if righe_tot > 0 else 0
                linee.append(
                    f"           - {col}: {n_nulli} ({pct:.1f}%)"
                )

        linee.append("")

    # Riepilogo finale
    linee.append("-" * 70)
    linee.append("RIEPILOGO")
    linee.append(f"  Validazioni totali:   {len(risultati)}")
    linee.append(f"  Superati (OK):        {n_ok}")
    linee.append(f"  Attenzione:           {n_warning}")
    linee.append(f"  Errori:               {n_errore}")

    if n_errore > 0:
        linee.append("")
        linee.append(
            "  ATTENZIONE: sono presenti errori di validazione che "
            "richiedono intervento prima di procedere con l'elaborazione."
        )

    linee.append("=" * 70)

    report_testo = "\n".join(linee)
    logger.info(
        "Report validazione generato: %d validazioni "
        "(%d OK, %d attenzione, %d errori)",
        len(risultati),
        n_ok,
        n_warning,
        n_errore,
    )

    return report_testo


def controlla_duplicati(df: pd.DataFrame, chiave: list) -> pd.DataFrame:
    """
    Individua le righe duplicate in un DataFrame sulla base di una
    chiave composta (lista di colonne).

    Parametri
    ---------
    df : pd.DataFrame
        DataFrame da analizzare.
    chiave : list
        Lista dei nomi delle colonne che costituiscono la chiave univoca
        (es. ["matricola", "mese", "anno"]).

    Ritorna
    -------
    pd.DataFrame
        DataFrame contenente solo le righe duplicate (tutte le occorrenze,
        non solo la prima). DataFrame vuoto se non ci sono duplicati.
    """
    if df is None or df.empty:
        logger.info("DataFrame vuoto, nessun duplicato possibile.")
        return pd.DataFrame()

    if not chiave:
        logger.error("Lista chiave vuota: impossibile verificare duplicati.")
        return pd.DataFrame()

    # Verifica che tutte le colonne chiave esistano nel DataFrame
    colonne_mancanti = [c for c in chiave if c not in df.columns]
    if colonne_mancanti:
        logger.error(
            "Colonne chiave non presenti nel DataFrame: %s. "
            "Colonne disponibili: %s",
            colonne_mancanti,
            list(df.columns),
        )
        return pd.DataFrame()

    try:
        # Identifica duplicati (keep=False per mostrare tutte le occorrenze)
        maschera_duplicati = df.duplicated(subset=chiave, keep=False)
        duplicati = df[maschera_duplicati].copy()

        if duplicati.empty:
            logger.info(
                "Nessun duplicato trovato sulla chiave %s (%d righe analizzate).",
                chiave,
                len(df),
            )
        else:
            # Calcola il numero di gruppi duplicati
            n_gruppi = duplicati.groupby(chiave).ngroups
            logger.warning(
                "Trovati %d duplicati in %d gruppi sulla chiave %s "
                "(%d righe analizzate).",
                len(duplicati),
                n_gruppi,
                chiave,
                len(df),
            )

        return duplicati

    except Exception as exc:
        logger.error(
            "Errore durante il controllo duplicati sulla chiave %s: %s",
            chiave,
            exc,
        )
        return pd.DataFrame()
