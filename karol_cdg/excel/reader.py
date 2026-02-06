"""
Lettura dati dal file Excel master (KAROL_CDG_MASTER.xlsx).

Modulo per la lettura di tutti i fogli del file Excel principale del sistema
di Controllo di Gestione Karol CDG. Ogni funzione legge un foglio specifico
e restituisce un DataFrame pandas oppure un dizionario di parametri.

In caso di foglio mancante o errore di lettura, le funzioni registrano
l'anomalia tramite logging e restituiscono un DataFrame vuoto o un
dizionario vuoto, senza sollevare eccezioni.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from karol_cdg.config import EXCEL_MASTER

logger = logging.getLogger(__name__)

# ============================================================================
# NOMI FOGLI DEL FILE MASTER
# ============================================================================

FOGLIO_ANAGRAFICHE_UO = "Anagrafiche_UO"
FOGLIO_PIANO_CONTI = "Piano_Conti"
FOGLIO_COSTI_MENSILI = "Costi_Mensili"
FOGLIO_PRODUZIONE_MENSILE = "Produzione_Mensile"
FOGLIO_COSTI_SEDE = "Costi_Sede_Dettaglio"
FOGLIO_DRIVER_ALLOCAZIONE = "Driver_Allocazione"
FOGLIO_SCADENZARIO = "Scadenzario"
FOGLIO_BENCHMARK = "Benchmark_Settore"
FOGLIO_PARAMETRI_SCENARI = "Parametri_Scenari"
FOGLIO_SOGLIE_ALERT = "Soglie_Alert"


# ============================================================================
# FUNZIONE BASE DI LETTURA
# ============================================================================


def leggi_foglio(
    file_path: Path,
    nome_foglio: str,
    skiprows: int = 0,
) -> pd.DataFrame:
    """
    Legge un foglio specifico dal file Excel master.

    Utilizza il motore openpyxl per la lettura. Se il foglio non esiste
    o il file non e' raggiungibile, restituisce un DataFrame vuoto e
    registra l'errore nel log.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel (tipicamente KAROL_CDG_MASTER.xlsx).
    nome_foglio : str
        Nome del foglio da leggere.
    skiprows : int
        Numero di righe iniziali da saltare (default 0).

    Ritorna
    -------
    pd.DataFrame
        Contenuto del foglio come DataFrame. DataFrame vuoto in caso
        di errore.
    """
    percorso = Path(file_path)

    if not percorso.exists():
        logger.error("File Excel non trovato: %s", percorso)
        return pd.DataFrame()

    try:
        df = pd.read_excel(
            percorso,
            sheet_name=nome_foglio,
            engine="openpyxl",
            skiprows=skiprows,
        )
        logger.info(
            "Foglio '%s' letto correttamente da %s (%d righe, %d colonne)",
            nome_foglio,
            percorso.name,
            len(df),
            len(df.columns),
        )
        return df

    except ValueError as exc:
        # pandas solleva ValueError se il foglio non esiste
        logger.error(
            "Foglio '%s' non trovato nel file %s: %s",
            nome_foglio,
            percorso.name,
            exc,
        )
        return pd.DataFrame()

    except Exception as exc:
        logger.error(
            "Errore nella lettura del foglio '%s' da %s: %s",
            nome_foglio,
            percorso.name,
            exc,
        )
        return pd.DataFrame()


# ============================================================================
# LETTURA ANAGRAFICHE UNITA' OPERATIVE
# ============================================================================


def leggi_anagrafiche_uo(file_path: Path) -> pd.DataFrame:
    """
    Legge le anagrafiche delle Unita' Operative dal foglio "Anagrafiche_UO".

    Colonne attese: codice, nome, tipologia, regione, posti_letto,
    attiva, societa, note.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con l'anagrafica delle UO. DataFrame vuoto se il
        foglio non esiste o contiene errori.
    """
    logger.info("Lettura anagrafiche UO da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_ANAGRAFICHE_UO)

    if df.empty:
        logger.warning("Nessuna anagrafica UO trovata.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Verifica colonne minime obbligatorie
    colonne_obbligatorie = ["codice", "nome"]
    mancanti = [c for c in colonne_obbligatorie if c not in df.columns]
    if mancanti:
        logger.error(
            "Colonne obbligatorie mancanti nel foglio %s: %s. "
            "Colonne trovate: %s",
            FOGLIO_ANAGRAFICHE_UO,
            mancanti,
            list(df.columns),
        )
        return pd.DataFrame()

    # Pulizia campi testo
    for col in ["codice", "nome"]:
        df[col] = df[col].astype(str).str.strip()

    logger.info("Anagrafiche UO caricate: %d unita' operative", len(df))
    return df


# ============================================================================
# LETTURA PIANO DEI CONTI
# ============================================================================


def leggi_piano_conti(file_path: Path) -> pd.DataFrame:
    """
    Legge il piano dei conti dal foglio "Piano_Conti".

    Colonne attese: codice_conto, descrizione, tipo, centro_costo,
    voce_ce (mappatura alla voce del Conto Economico).

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con il piano dei conti. DataFrame vuoto se il
        foglio non esiste o contiene errori.
    """
    logger.info("Lettura piano dei conti da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_PIANO_CONTI)

    if df.empty:
        logger.warning("Nessun dato trovato nel piano dei conti.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Verifica colonne minime
    colonne_obbligatorie = ["codice_conto", "descrizione"]
    mancanti = [c for c in colonne_obbligatorie if c not in df.columns]
    if mancanti:
        logger.error(
            "Colonne obbligatorie mancanti nel foglio %s: %s",
            FOGLIO_PIANO_CONTI,
            mancanti,
        )
        return pd.DataFrame()

    # Pulizia
    df["codice_conto"] = df["codice_conto"].astype(str).str.strip()
    df["descrizione"] = df["descrizione"].astype(str).str.strip()

    logger.info("Piano dei conti caricato: %d conti", len(df))
    return df


# ============================================================================
# LETTURA COSTI MENSILI
# ============================================================================


def leggi_costi_mensili(file_path: Path, periodo: str) -> pd.DataFrame:
    """
    Legge i costi mensili dal foglio "Costi_Mensili" e filtra per periodo.

    Colonne attese: codice_uo, voce_costo, importo, mese, anno,
    centro_costo.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.
    periodo : str
        Periodo di riferimento nel formato "MM/YYYY" (es. "03/2026").
        Viene utilizzato per filtrare i dati del mese corrispondente.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con i costi del periodo richiesto.
        DataFrame vuoto se non ci sono dati per il periodo.
    """
    logger.info("Lettura costi mensili da: %s (periodo: %s)", file_path, periodo)

    df = leggi_foglio(file_path, FOGLIO_COSTI_MENSILI)

    if df.empty:
        logger.warning("Nessun dato trovato nel foglio costi mensili.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Filtra per periodo richiesto
    df = _filtra_per_periodo(df, periodo, FOGLIO_COSTI_MENSILI)

    # Conversione importi a numerico
    if "importo" in df.columns:
        df["importo"] = pd.to_numeric(df["importo"], errors="coerce").fillna(0.0)

    logger.info(
        "Costi mensili caricati per %s: %d righe, totale %.2f",
        periodo,
        len(df),
        df["importo"].sum() if "importo" in df.columns and not df.empty else 0.0,
    )
    return df


# ============================================================================
# LETTURA PRODUZIONE MENSILE
# ============================================================================


def leggi_produzione_mensile(file_path: Path, periodo: str) -> pd.DataFrame:
    """
    Legge i dati di produzione mensile dal foglio "Produzione_Mensile"
    e filtra per periodo.

    Colonne attese: codice_uo, tipo_prestazione, quantita, ricavo_unitario,
    ricavo_totale, giornate_degenza, presenze, mese, anno.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.
    periodo : str
        Periodo di riferimento nel formato "MM/YYYY".

    Ritorna
    -------
    pd.DataFrame
        DataFrame con la produzione del periodo richiesto.
    """
    logger.info("Lettura produzione mensile da: %s (periodo: %s)", file_path, periodo)

    df = leggi_foglio(file_path, FOGLIO_PRODUZIONE_MENSILE)

    if df.empty:
        logger.warning("Nessun dato trovato nel foglio produzione mensile.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Filtra per periodo
    df = _filtra_per_periodo(df, periodo, FOGLIO_PRODUZIONE_MENSILE)

    # Conversione colonne numeriche
    colonne_numeriche = [
        "quantita", "ricavo_unitario", "ricavo_totale",
        "giornate_degenza", "presenze",
    ]
    for col in colonne_numeriche:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    logger.info(
        "Produzione mensile caricata per %s: %d righe",
        periodo,
        len(df),
    )
    return df


# ============================================================================
# LETTURA COSTI SEDE
# ============================================================================


def leggi_costi_sede(file_path: Path) -> pd.DataFrame:
    """
    Legge la classificazione dei costi di sede dal foglio
    "Costi_Sede_Dettaglio".

    Colonne attese: voce_costo, categoria, importo_annuo, importo_mensile,
    driver, allocabile, note.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con il dettaglio dei costi di sede.
    """
    logger.info("Lettura costi sede da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_COSTI_SEDE)

    if df.empty:
        logger.warning("Nessun dato trovato nel foglio costi sede.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Conversione importi
    for col in ["importo_annuo", "importo_mensile"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    logger.info("Costi sede caricati: %d voci", len(df))
    return df


# ============================================================================
# LETTURA DRIVER DI ALLOCAZIONE
# ============================================================================


def leggi_driver_allocazione(file_path: Path) -> pd.DataFrame:
    """
    Legge i driver di allocazione dei costi sede dal foglio
    "Driver_Allocazione".

    Colonne attese: codice_uo, driver, valore, peso_percentuale.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con i driver di allocazione per ogni UO.
    """
    logger.info("Lettura driver di allocazione da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_DRIVER_ALLOCAZIONE)

    if df.empty:
        logger.warning("Nessun dato trovato nel foglio driver allocazione.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Conversione colonne numeriche
    for col in ["valore", "peso_percentuale"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    logger.info("Driver di allocazione caricati: %d righe", len(df))
    return df


# ============================================================================
# LETTURA SCADENZARIO
# ============================================================================


def leggi_scadenzario(file_path: Path) -> pd.DataFrame:
    """
    Legge lo scadenzario pagamenti dal foglio "Scadenzario".

    Colonne attese: tipo (incasso/pagamento), controparte, importo,
    data_scadenza, data_prevista_incasso, stato, codice_uo, note.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con le scadenze di incassi e pagamenti.
    """
    logger.info("Lettura scadenzario da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_SCADENZARIO)

    if df.empty:
        logger.warning("Nessun dato trovato nel foglio scadenzario.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Conversione importo
    if "importo" in df.columns:
        df["importo"] = pd.to_numeric(df["importo"], errors="coerce").fillna(0.0)

    # Conversione date
    for col_data in ["data_scadenza", "data_prevista_incasso"]:
        if col_data in df.columns:
            df[col_data] = pd.to_datetime(df[col_data], errors="coerce")

    logger.info("Scadenzario caricato: %d scadenze", len(df))
    return df


# ============================================================================
# LETTURA BENCHMARK DI SETTORE
# ============================================================================


def leggi_benchmark(file_path: Path) -> pd.DataFrame:
    """
    Legge i benchmark di settore dal foglio "Benchmark_Settore".

    Colonne attese: tipologia, indicatore, valore_min, valore_max,
    fonte, anno_riferimento.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con i benchmark di settore per tipologia di struttura.
    """
    logger.info("Lettura benchmark di settore da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_BENCHMARK)

    if df.empty:
        logger.warning("Nessun dato trovato nel foglio benchmark settore.")
        return df

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # Conversione colonne numeriche
    for col in ["valore_min", "valore_max"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    logger.info("Benchmark caricati: %d indicatori", len(df))
    return df


# ============================================================================
# LETTURA PARAMETRI SCENARI
# ============================================================================


def leggi_parametri_scenari(file_path: Path) -> dict:
    """
    Legge i parametri per gli scenari di cash flow dal foglio
    "Parametri_Scenari".

    Il foglio ha una struttura chiave-valore organizzata per scenario
    (ottimistico, base, pessimistico). La funzione restituisce un
    dizionario annidato con i parametri di ciascuno scenario.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    dict
        Dizionario con struttura:
        {
            "ottimistico": {"dso_asp_giorni": 90, ...},
            "base": {"dso_asp_giorni": 120, ...},
            "pessimistico": {"dso_asp_giorni": 150, ...},
        }
        Dizionario vuoto in caso di errore.
    """
    logger.info("Lettura parametri scenari da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_PARAMETRI_SCENARI)

    if df.empty:
        logger.warning(
            "Nessun dato trovato nel foglio %s. "
            "Verranno utilizzati i parametri predefiniti da config.",
            FOGLIO_PARAMETRI_SCENARI,
        )
        return {}

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    parametri: dict = {}

    try:
        # Struttura attesa: colonne "scenario", "parametro", "valore"
        if not {"scenario", "parametro", "valore"}.issubset(set(df.columns)):
            logger.error(
                "Struttura del foglio %s non valida. "
                "Colonne attese: scenario, parametro, valore. "
                "Colonne trovate: %s",
                FOGLIO_PARAMETRI_SCENARI,
                list(df.columns),
            )
            return {}

        for scenario in df["scenario"].dropna().unique():
            righe_scenario = df[df["scenario"] == scenario]
            parametri[str(scenario).strip().lower()] = {}
            for _, riga in righe_scenario.iterrows():
                chiave = str(riga["parametro"]).strip()
                valore = riga["valore"]
                # Tenta conversione a numerico
                try:
                    valore = float(valore)
                except (ValueError, TypeError):
                    pass
                parametri[str(scenario).strip().lower()][chiave] = valore

        logger.info(
            "Parametri scenari caricati: %d scenari (%s)",
            len(parametri),
            ", ".join(parametri.keys()),
        )

    except Exception as exc:
        logger.error(
            "Errore nell'elaborazione dei parametri scenari: %s", exc
        )
        return {}

    return parametri


# ============================================================================
# LETTURA SOGLIE ALERT
# ============================================================================


def leggi_soglie_alert(file_path: Path) -> dict:
    """
    Legge le soglie di allarme (semaforo) dal foglio "Soglie_Alert".

    Il foglio ha una struttura con colonne: indicatore, soglia_verde,
    soglia_gialla, invertito (flag per indicatori dove il valore basso
    e' migliore, es. costo personale su ricavi).

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel master.

    Ritorna
    -------
    dict
        Dizionario con struttura:
        {
            "nome_indicatore": {
                "verde": float,
                "giallo": float,
                "invertito": bool,
            },
            ...
        }
        Dizionario vuoto in caso di errore.
    """
    logger.info("Lettura soglie alert da: %s", file_path)

    df = leggi_foglio(file_path, FOGLIO_SOGLIE_ALERT)

    if df.empty:
        logger.warning(
            "Nessun dato trovato nel foglio %s. "
            "Verranno utilizzate le soglie predefinite da config.",
            FOGLIO_SOGLIE_ALERT,
        )
        return {}

    # Normalizza nomi colonne
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    soglie: dict = {}

    try:
        # Struttura attesa: indicatore, soglia_verde, soglia_gialla, invertito
        colonne_richieste = {"indicatore", "soglia_verde", "soglia_gialla"}
        if not colonne_richieste.issubset(set(df.columns)):
            logger.error(
                "Struttura del foglio %s non valida. "
                "Colonne minime attese: %s. Colonne trovate: %s",
                FOGLIO_SOGLIE_ALERT,
                colonne_richieste,
                list(df.columns),
            )
            return {}

        for _, riga in df.iterrows():
            indicatore = str(riga["indicatore"]).strip()
            if not indicatore or indicatore == "nan":
                continue

            soglia_verde = pd.to_numeric(riga.get("soglia_verde"), errors="coerce")
            soglia_gialla = pd.to_numeric(riga.get("soglia_gialla"), errors="coerce")

            # Il campo 'invertito' puo' essere booleano, stringa o numerico
            invertito_raw = riga.get("invertito", False)
            if isinstance(invertito_raw, str):
                invertito = invertito_raw.strip().lower() in ("si", "true", "1", "vero")
            else:
                invertito = bool(invertito_raw) if pd.notna(invertito_raw) else False

            soglie[indicatore] = {
                "verde": float(soglia_verde) if pd.notna(soglia_verde) else 0.0,
                "giallo": float(soglia_gialla) if pd.notna(soglia_gialla) else 0.0,
                "invertito": invertito,
            }

        logger.info("Soglie alert caricate: %d indicatori", len(soglie))

    except Exception as exc:
        logger.error("Errore nell'elaborazione delle soglie alert: %s", exc)
        return {}

    return soglie


# ============================================================================
# FUNZIONI AUSILIARIE INTERNE
# ============================================================================


def _filtra_per_periodo(
    df: pd.DataFrame,
    periodo: str,
    nome_foglio: str,
) -> pd.DataFrame:
    """
    Filtra un DataFrame per il periodo indicato (formato "MM/YYYY").

    Cerca le colonne 'mese' e 'anno' nel DataFrame e filtra le righe
    corrispondenti. Se le colonne non esistono, restituisce il DataFrame
    originale con un avviso nel log.

    Parametri
    ---------
    df : pd.DataFrame
        DataFrame da filtrare.
    periodo : str
        Periodo nel formato "MM/YYYY".
    nome_foglio : str
        Nome del foglio (utilizzato solo per i messaggi di log).

    Ritorna
    -------
    pd.DataFrame
        DataFrame filtrato per il periodo richiesto.
    """
    if df.empty:
        return df

    # Verifica che le colonne mese/anno esistano
    if "mese" not in df.columns or "anno" not in df.columns:
        logger.warning(
            "Colonne 'mese' e/o 'anno' non trovate nel foglio %s. "
            "Impossibile filtrare per periodo. Colonne disponibili: %s",
            nome_foglio,
            list(df.columns),
        )
        return df

    try:
        parti = periodo.strip().split("/")
        mese_filtro = int(parti[0])
        anno_filtro = int(parti[1])
    except (ValueError, IndexError):
        logger.error(
            "Formato periodo non valido: '%s'. Atteso 'MM/YYYY'. "
            "Restituzione dati senza filtro.",
            periodo,
        )
        return df

    # Assicura che mese e anno siano numerici
    df["mese"] = pd.to_numeric(df["mese"], errors="coerce").fillna(0).astype(int)
    df["anno"] = pd.to_numeric(df["anno"], errors="coerce").fillna(0).astype(int)

    df_filtrato = df[
        (df["mese"] == mese_filtro) & (df["anno"] == anno_filtro)
    ].copy()

    if df_filtrato.empty:
        logger.warning(
            "Nessun dato trovato nel foglio %s per il periodo %s. "
            "Periodi disponibili: mesi %s, anni %s",
            nome_foglio,
            periodo,
            sorted(df["mese"].unique().tolist()),
            sorted(df["anno"].unique().tolist()),
        )

    return df_filtrato
