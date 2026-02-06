"""
Import dati contabili da E-Solver (SISTEMI).

Modulo per la lettura e validazione dei dati esportati dal gestionale
E-Solver in formato CSV:
  - Piano dei conti (anagrafica conti)
  - Saldi contabili per centro di costo e conto
  - Movimenti contabili (prima nota)

Tutte le funzioni restituiscono un DataFrame vuoto in caso di errore,
registrando l'anomalia tramite il modulo logging.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from karol_cdg.config import (
    FORMATO_MESE,
    SEPARATORE_DECIMALI,
    SEPARATORE_MIGLIAIA,
    UNITA_OPERATIVE,
    VOCI_COSTI_DIRETTI,
    VOCI_COSTI_SEDE,
    VOCI_RICAVI,
)

logger = logging.getLogger(__name__)

# ============================================================================
# COSTANTI INTERNE
# ============================================================================

# Colonne attese nel CSV piano dei conti E-Solver
_COLONNE_PIANO_CONTI = [
    "codice_conto",
    "descrizione",
    "tipo",
    "centro_costo",
]

# Colonne attese nel CSV saldi E-Solver
_COLONNE_SALDI = [
    "codice_conto",
    "descrizione",
    "dare",
    "avere",
    "saldo",
    "centro_costo",
    "mese",
    "anno",
]

# Colonne attese nel CSV movimenti E-Solver
_COLONNE_MOVIMENTI = [
    "numero_registrazione",
    "data_registrazione",
    "codice_conto",
    "descrizione",
    "dare",
    "avere",
    "centro_costo",
    "causale",
    "numero_documento",
    "data_documento",
]

# Codifiche da tentare in ordine di preferenza
_ENCODING_FALLBACK = ["utf-8", "latin-1", "cp1252"]


# ============================================================================
# FUNZIONI AUSILIARIE
# ============================================================================


def _leggi_csv(file_path: Path, separatore: str = ";") -> Optional[pd.DataFrame]:
    """
    Legge un file CSV tentando diverse codifiche.

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV.
    separatore : str
        Separatore di colonne (default ";", tipico di E-Solver).

    Ritorna
    -------
    pd.DataFrame oppure None se la lettura fallisce.
    """
    percorso = Path(file_path)

    if not percorso.exists():
        logger.error("File non trovato: %s", percorso)
        return None

    if not percorso.is_file():
        logger.error("Il percorso non punta a un file: %s", percorso)
        return None

    for codifica in _ENCODING_FALLBACK:
        try:
            df = pd.read_csv(
                percorso,
                sep=separatore,
                encoding=codifica,
                dtype=str,
                keep_default_na=False,
            )
            logger.info(
                "File letto correttamente con codifica %s: %s (%d righe)",
                codifica,
                percorso.name,
                len(df),
            )
            return df
        except UnicodeDecodeError:
            logger.debug(
                "Codifica %s non valida per %s, tentativo successivo...",
                codifica,
                percorso.name,
            )
        except Exception as exc:
            logger.error(
                "Errore imprevisto nella lettura di %s (codifica %s): %s",
                percorso.name,
                codifica,
                exc,
            )
            return None

    logger.error(
        "Impossibile leggere %s con nessuna delle codifiche supportate.", percorso.name
    )
    return None


def _normalizza_nomi_colonne(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizza i nomi delle colonne: minuscolo, senza spazi laterali,
    spazi interni sostituiti da underscore.
    """
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace(".", "_", regex=False)
    )
    return df


def _converti_importo(valore: str) -> float:
    """
    Converte un importo in formato italiano (1.234,56) in float.

    Gestisce i separatori di migliaia e decimali come da config.
    """
    if not valore or pd.isna(valore):
        return 0.0

    valore_pulito = str(valore).strip()
    if not valore_pulito:
        return 0.0

    try:
        # Rimuove il separatore delle migliaia e sostituisce quello decimale
        valore_pulito = valore_pulito.replace(SEPARATORE_MIGLIAIA, "")
        valore_pulito = valore_pulito.replace(SEPARATORE_DECIMALI, ".")
        return float(valore_pulito)
    except (ValueError, TypeError):
        logger.warning("Impossibile convertire l'importo: '%s'", valore)
        return 0.0


# ============================================================================
# FUNZIONI PUBBLICHE
# ============================================================================


def importa_piano_conti(file_path: Path) -> pd.DataFrame:
    """
    Importa il piano dei conti da un export CSV di E-Solver.

    Il file deve contenere le colonne:
      codice_conto, descrizione, tipo (ricavo/costo), centro_costo

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV esportato da E-Solver.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con il piano dei conti normalizzato.
        DataFrame vuoto in caso di errore.
    """
    logger.info("Importazione piano dei conti da: %s", file_path)

    df = _leggi_csv(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_PIANO_CONTI)

    df = _normalizza_nomi_colonne(df)

    # Verifica colonne obbligatorie
    colonne_mancanti = [c for c in _COLONNE_PIANO_CONTI if c not in df.columns]
    if colonne_mancanti:
        logger.error(
            "Colonne mancanti nel piano dei conti: %s. "
            "Colonne trovate: %s",
            colonne_mancanti,
            list(df.columns),
        )
        return pd.DataFrame(columns=_COLONNE_PIANO_CONTI)

    # Seleziona solo le colonne attese
    df = df[_COLONNE_PIANO_CONTI].copy()

    # Pulizia valori
    df["codice_conto"] = df["codice_conto"].str.strip()
    df["descrizione"] = df["descrizione"].str.strip()
    df["tipo"] = df["tipo"].str.strip().str.lower()
    df["centro_costo"] = df["centro_costo"].str.strip()

    # Validazione tipo: accetta solo "ricavo" o "costo"
    tipi_validi = {"ricavo", "costo"}
    maschera_tipo_invalido = ~df["tipo"].isin(tipi_validi)
    if maschera_tipo_invalido.any():
        n_invalidi = maschera_tipo_invalido.sum()
        logger.warning(
            "%d righe con tipo non valido (atteso 'ricavo' o 'costo'). "
            "Valori trovati: %s",
            n_invalidi,
            df.loc[maschera_tipo_invalido, "tipo"].unique().tolist(),
        )

    logger.info(
        "Piano dei conti importato: %d conti (%d ricavi, %d costi)",
        len(df),
        (df["tipo"] == "ricavo").sum(),
        (df["tipo"] == "costo").sum(),
    )

    return df


def importa_saldi(file_path: Path, periodo: str) -> pd.DataFrame:
    """
    Importa i saldi contabili per centro di costo da un export CSV di E-Solver.

    Il file deve contenere le colonne:
      codice_conto, descrizione, dare, avere, saldo,
      centro_costo, mese, anno

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV esportato da E-Solver.
    periodo : str
        Periodo di riferimento nel formato MM/YYYY (es. "03/2025").
        Utilizzato per filtrare e validare i dati.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con i saldi contabili.
        DataFrame vuoto in caso di errore.
    """
    logger.info("Importazione saldi contabili da: %s (periodo: %s)", file_path, periodo)

    df = _leggi_csv(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_SALDI)

    df = _normalizza_nomi_colonne(df)

    # Verifica colonne obbligatorie
    colonne_mancanti = [c for c in _COLONNE_SALDI if c not in df.columns]
    if colonne_mancanti:
        logger.error(
            "Colonne mancanti nei saldi: %s. Colonne trovate: %s",
            colonne_mancanti,
            list(df.columns),
        )
        return pd.DataFrame(columns=_COLONNE_SALDI)

    df = df[_COLONNE_SALDI].copy()

    # Conversione importi da formato italiano a float
    for col_importo in ["dare", "avere", "saldo"]:
        df[col_importo] = df[col_importo].apply(_converti_importo)

    # Conversione mese e anno a interi
    try:
        df["mese"] = pd.to_numeric(df["mese"], errors="coerce").fillna(0).astype(int)
        df["anno"] = pd.to_numeric(df["anno"], errors="coerce").fillna(0).astype(int)
    except Exception as exc:
        logger.error("Errore nella conversione di mese/anno: %s", exc)
        return pd.DataFrame(columns=_COLONNE_SALDI)

    # Filtra per il periodo richiesto se specificato
    if periodo:
        try:
            mese_filtro, anno_filtro = periodo.split("/")
            mese_filtro = int(mese_filtro)
            anno_filtro = int(anno_filtro)
            df_filtrato = df[
                (df["mese"] == mese_filtro) & (df["anno"] == anno_filtro)
            ].copy()

            if df_filtrato.empty:
                logger.warning(
                    "Nessun saldo trovato per il periodo %s. "
                    "Periodi disponibili: mesi %s, anni %s",
                    periodo,
                    sorted(df["mese"].unique().tolist()),
                    sorted(df["anno"].unique().tolist()),
                )
            else:
                logger.info(
                    "Saldi filtrati per periodo %s: %d righe", periodo, len(df_filtrato)
                )
            df = df_filtrato
        except ValueError:
            logger.error(
                "Formato periodo non valido: '%s'. Atteso MM/YYYY.", periodo
            )

    # Pulizia campi testo
    df["codice_conto"] = df["codice_conto"].str.strip()
    df["descrizione"] = df["descrizione"].str.strip()
    df["centro_costo"] = df["centro_costo"].str.strip()

    logger.info(
        "Saldi importati: %d righe, totale dare=%.2f, totale avere=%.2f",
        len(df),
        df["dare"].sum(),
        df["avere"].sum(),
    )

    return df


def importa_movimenti(file_path: Path) -> pd.DataFrame:
    """
    Importa i movimenti contabili (prima nota) da un export CSV di E-Solver.

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV esportato da E-Solver.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con i movimenti contabili.
        DataFrame vuoto in caso di errore.
    """
    logger.info("Importazione movimenti contabili da: %s", file_path)

    df = _leggi_csv(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_MOVIMENTI)

    df = _normalizza_nomi_colonne(df)

    # Verifica colonne obbligatorie (accetta anche un sottoinsieme minimo)
    colonne_minime = ["codice_conto", "dare", "avere"]
    colonne_mancanti = [c for c in colonne_minime if c not in df.columns]
    if colonne_mancanti:
        logger.error(
            "Colonne obbligatorie mancanti nei movimenti: %s. Colonne trovate: %s",
            colonne_mancanti,
            list(df.columns),
        )
        return pd.DataFrame(columns=_COLONNE_MOVIMENTI)

    # Aggiunge colonne mancanti con valori vuoti
    for col in _COLONNE_MOVIMENTI:
        if col not in df.columns:
            df[col] = ""
            logger.debug("Colonna '%s' non presente, aggiunta con valori vuoti.", col)

    df = df[_COLONNE_MOVIMENTI].copy()

    # Conversione importi
    for col_importo in ["dare", "avere"]:
        df[col_importo] = df[col_importo].apply(_converti_importo)

    # Conversione date
    for col_data in ["data_registrazione", "data_documento"]:
        if df[col_data].notna().any() and (df[col_data] != "").any():
            try:
                df[col_data] = pd.to_datetime(
                    df[col_data], format="%d/%m/%Y", errors="coerce"
                )
            except Exception:
                logger.warning(
                    "Impossibile convertire la colonna '%s' in formato data.", col_data
                )

    # Pulizia campi testo
    for col_testo in ["codice_conto", "descrizione", "centro_costo", "causale"]:
        if df[col_testo].dtype == object:
            df[col_testo] = df[col_testo].str.strip()

    logger.info(
        "Movimenti importati: %d righe, totale dare=%.2f, totale avere=%.2f",
        len(df),
        df["dare"].sum(),
        df["avere"].sum(),
    )

    return df


def valida_quadratura_saldi(saldi_df: pd.DataFrame) -> dict:
    """
    Verifica la quadratura dei saldi contabili (dare == avere).

    Controlla che la somma della colonna 'dare' corrisponda alla somma
    della colonna 'avere'. Una tolleranza di 0.01 euro viene applicata
    per gestire arrotondamenti.

    Parametri
    ---------
    saldi_df : pd.DataFrame
        DataFrame con i saldi contabili (deve contenere colonne 'dare' e 'avere').

    Ritorna
    -------
    dict
        Dizionario con i risultati della validazione:
        - quadra (bool): True se dare == avere entro la tolleranza
        - totale_dare (float): somma colonna dare
        - totale_avere (float): somma colonna avere
        - differenza (float): dare - avere
        - tolleranza (float): tolleranza applicata
        - messaggio (str): descrizione del risultato
    """
    risultato = {
        "quadra": False,
        "totale_dare": 0.0,
        "totale_avere": 0.0,
        "differenza": 0.0,
        "tolleranza": 0.01,
        "messaggio": "",
    }

    if saldi_df is None or saldi_df.empty:
        risultato["messaggio"] = "DataFrame saldi vuoto o nullo."
        logger.warning(risultato["messaggio"])
        return risultato

    if "dare" not in saldi_df.columns or "avere" not in saldi_df.columns:
        risultato["messaggio"] = (
            "Colonne 'dare' e/o 'avere' non presenti nel DataFrame."
        )
        logger.error(risultato["messaggio"])
        return risultato

    totale_dare = saldi_df["dare"].sum()
    totale_avere = saldi_df["avere"].sum()
    differenza = totale_dare - totale_avere

    risultato["totale_dare"] = round(totale_dare, 2)
    risultato["totale_avere"] = round(totale_avere, 2)
    risultato["differenza"] = round(differenza, 2)

    if abs(differenza) <= risultato["tolleranza"]:
        risultato["quadra"] = True
        risultato["messaggio"] = (
            f"Saldi in quadratura. Dare: {totale_dare:,.2f}, "
            f"Avere: {totale_avere:,.2f}."
        )
        logger.info(risultato["messaggio"])
    else:
        risultato["messaggio"] = (
            f"ATTENZIONE: saldi NON in quadratura! "
            f"Dare: {totale_dare:,.2f}, Avere: {totale_avere:,.2f}, "
            f"Differenza: {differenza:,.2f}."
        )
        logger.error(risultato["messaggio"])

    return risultato
