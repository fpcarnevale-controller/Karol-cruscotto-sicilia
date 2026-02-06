"""
Import dati produzione sanitaria.

Modulo per la lettura dei dati di produzione sanitaria da diverse fonti:
  - Caremed/INNOGEA (Excel): produzione per Casa di Cura, Laboratorio, Betania
  - HT Sang (Excel): produzione RSA, FKT, CTA
  - Template manuali (Excel): per dati non disponibili dai gestionali

Fornisce inoltre funzioni per il calcolo delle giornate di degenza
e del tasso di occupazione (occupancy).

Tutte le funzioni restituiscono un DataFrame vuoto in caso di errore,
registrando l'anomalia tramite il modulo logging.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from karol_cdg.config import (
    ALERT_CONFIG,
    FONTI_DATI,
    FORMATO_DATA,
    SEPARATORE_DECIMALI,
    SEPARATORE_MIGLIAIA,
    SOGLIE_SEMAFORO,
    UNITA_OPERATIVE,
)

logger = logging.getLogger(__name__)

# ============================================================================
# COSTANTI INTERNE
# ============================================================================

# Colonne standard per il DataFrame di produzione unificato
_COLONNE_PRODUZIONE = [
    "tipo_prestazione",
    "codice",
    "descrizione",
    "quantita",
    "tariffa",
    "importo",
    "data",
    "paziente_id",
    "unita_operativa",
    "fonte",
]

# Colonne attese nell'export Caremed
_COLONNE_CAREMED = [
    "tipo_prestazione",
    "codice",
    "descrizione",
    "quantita",
    "tariffa",
    "importo",
    "data",
    "paziente_id",
]

# Colonne attese nell'export HT Sang
_COLONNE_HTSANG = [
    "tipo_prestazione",
    "codice",
    "descrizione",
    "quantita",
    "tariffa",
    "importo",
    "data",
    "paziente_id",
]

# Colonne per il template manuale
_COLONNE_TEMPLATE_MANUALE = [
    "tipo_prestazione",
    "codice",
    "descrizione",
    "quantita",
    "tariffa",
    "importo",
    "data",
    "paziente_id",
]

# Colonne risultato giornate di degenza
_COLONNE_GIORNATE_DEGENZA = [
    "paziente_id",
    "data_ingresso",
    "data_dimissione",
    "giornate",
    "unita_operativa",
]


# ============================================================================
# FUNZIONI AUSILIARIE
# ============================================================================


def _leggi_excel(
    file_path: Path, foglio: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Legge un file Excel (.xlsx / .xls) con gestione errori.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel.
    foglio : str, opzionale
        Nome del foglio da leggere. Se None, legge il primo foglio.

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

    estensioni_valide = {".xlsx", ".xls", ".xlsm"}
    if percorso.suffix.lower() not in estensioni_valide:
        logger.error(
            "Estensione file non supportata: '%s'. Attese: %s",
            percorso.suffix,
            estensioni_valide,
        )
        return None

    try:
        kwargs = {"dtype": str, "keep_default_na": False}
        if foglio is not None:
            kwargs["sheet_name"] = foglio

        df = pd.read_excel(percorso, **kwargs)
        logger.info(
            "File Excel letto: %s (foglio: %s, %d righe)",
            percorso.name,
            foglio or "primo",
            len(df),
        )
        return df
    except ValueError as exc:
        logger.error(
            "Foglio '%s' non trovato nel file %s: %s", foglio, percorso.name, exc
        )
        return None
    except Exception as exc:
        logger.error(
            "Errore nella lettura del file Excel %s: %s", percorso.name, exc
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
    """
    if not valore or pd.isna(valore):
        return 0.0

    valore_pulito = str(valore).strip()
    if not valore_pulito:
        return 0.0

    try:
        valore_pulito = valore_pulito.replace(SEPARATORE_MIGLIAIA, "")
        valore_pulito = valore_pulito.replace(SEPARATORE_DECIMALI, ".")
        return float(valore_pulito)
    except (ValueError, TypeError):
        logger.warning("Impossibile convertire l'importo: '%s'", valore)
        return 0.0


def _valida_unita_operativa(codice_uo: str) -> bool:
    """
    Verifica che il codice unita' operativa esista nell'anagrafica.
    """
    return codice_uo.strip().upper() in UNITA_OPERATIVE


def _prepara_df_produzione(
    df: pd.DataFrame,
    colonne_attese: list,
    unita_operativa: str,
    fonte: str,
) -> pd.DataFrame:
    """
    Prepara e normalizza un DataFrame di produzione da qualsiasi fonte.

    - Normalizza i nomi colonne
    - Verifica la presenza delle colonne obbligatorie
    - Aggiunge colonne mancanti
    - Converte importi e quantita'
    - Aggiunge colonne unita_operativa e fonte

    Ritorna un DataFrame normalizzato oppure un DataFrame vuoto.
    """
    df = _normalizza_nomi_colonne(df)

    # Colonne minime obbligatorie
    colonne_minime = ["descrizione", "quantita"]
    mancanti = [c for c in colonne_minime if c not in df.columns]
    if mancanti:
        logger.error(
            "Colonne minime obbligatorie mancanti (%s): %s. Colonne trovate: %s",
            fonte,
            mancanti,
            list(df.columns),
        )
        return pd.DataFrame(columns=_COLONNE_PRODUZIONE)

    # Aggiunge colonne mancanti con valori vuoti
    for col in colonne_attese:
        if col not in df.columns:
            df[col] = ""
            logger.debug(
                "Colonna '%s' non presente in %s, aggiunta con valori vuoti.",
                col,
                fonte,
            )

    # Seleziona solo le colonne attese
    df = df[colonne_attese].copy()

    # Conversione campi numerici
    for col_num in ["quantita", "tariffa", "importo"]:
        if col_num in df.columns:
            df[col_num] = df[col_num].apply(_converti_importo)

    # Conversione data
    if "data" in df.columns:
        valori_data = df["data"]
        if valori_data.notna().any() and (valori_data != "").any():
            try:
                df["data"] = pd.to_datetime(
                    df["data"], format=FORMATO_DATA, errors="coerce"
                )
            except Exception:
                # Tenta formato ISO come fallback
                try:
                    df["data"] = pd.to_datetime(df["data"], errors="coerce")
                except Exception:
                    logger.warning(
                        "Impossibile convertire la colonna 'data' (%s).", fonte
                    )

    # Ricalcola importo se mancante ma tariffa e quantita' presenti
    if "importo" in df.columns and "tariffa" in df.columns and "quantita" in df.columns:
        maschera_ricalcolo = (df["importo"] == 0) & (
            (df["tariffa"] > 0) & (df["quantita"] > 0)
        )
        if maschera_ricalcolo.any():
            df.loc[maschera_ricalcolo, "importo"] = (
                df.loc[maschera_ricalcolo, "quantita"]
                * df.loc[maschera_ricalcolo, "tariffa"]
            )
            logger.info(
                "Ricalcolato importo per %d righe (quantita' x tariffa) in %s.",
                maschera_ricalcolo.sum(),
                fonte,
            )

    # Pulizia campi testo
    for col_testo in ["tipo_prestazione", "codice", "descrizione", "paziente_id"]:
        if col_testo in df.columns and df[col_testo].dtype == object:
            df[col_testo] = df[col_testo].str.strip()

    # Aggiunge metadati
    df["unita_operativa"] = unita_operativa.strip().upper()
    df["fonte"] = fonte

    return df


# ============================================================================
# FUNZIONI PUBBLICHE
# ============================================================================


def importa_produzione_caremed(
    file_path: Path, unita_operativa: str
) -> pd.DataFrame:
    """
    Importa dati di produzione sanitaria dall'export Excel di Caremed/INNOGEA.

    Utilizzato per le strutture: COS (Cosentino), LAB (Laboratorio), BET (Betania).

    Il file deve contenere le colonne:
      tipo_prestazione, codice, descrizione, quantita, tariffa,
      importo, data, paziente_id

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel esportato da Caremed.
    unita_operativa : str
        Codice dell'unita' operativa (es. "COS", "LAB").

    Ritorna
    -------
    pd.DataFrame
        DataFrame con la produzione normalizzata.
        DataFrame vuoto in caso di errore.
    """
    logger.info(
        "Importazione produzione Caremed da: %s (UO: %s)", file_path, unita_operativa
    )

    if not _valida_unita_operativa(unita_operativa):
        logger.warning(
            "Codice UO '%s' non presente nell'anagrafica. "
            "L'importazione prosegue ma il dato potrebbe non essere coerente.",
            unita_operativa,
        )

    # Verifica che la UO sia tra quelle gestite da Caremed
    strutture_caremed = FONTI_DATI.get("Caremed_INNOGEA", {}).get("strutture", [])
    if (
        isinstance(strutture_caremed, list)
        and unita_operativa.strip().upper() not in strutture_caremed
    ):
        logger.warning(
            "UO '%s' non e' tra le strutture previste per Caremed: %s. "
            "L'importazione prosegue comunque.",
            unita_operativa,
            strutture_caremed,
        )

    df = _leggi_excel(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_PRODUZIONE)

    risultato = _prepara_df_produzione(
        df=df,
        colonne_attese=_COLONNE_CAREMED,
        unita_operativa=unita_operativa,
        fonte="Caremed_INNOGEA",
    )

    logger.info(
        "Produzione Caremed importata per UO %s: %d prestazioni, "
        "importo totale: %.2f euro",
        unita_operativa,
        len(risultato),
        risultato["importo"].sum() if not risultato.empty else 0.0,
    )

    return risultato


def importa_produzione_htsang(
    file_path: Path, unita_operativa: str
) -> pd.DataFrame:
    """
    Importa dati di produzione sanitaria dall'export Excel di HT Sang.

    Utilizzato per le strutture: VLB (Villabate), CTA (Ex Stagno), BRG (Borgo Ritrovato).

    Il file deve contenere le colonne:
      tipo_prestazione, codice, descrizione, quantita, tariffa,
      importo, data, paziente_id

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel esportato da HT Sang.
    unita_operativa : str
        Codice dell'unita' operativa (es. "VLB", "CTA").

    Ritorna
    -------
    pd.DataFrame
        DataFrame con la produzione normalizzata.
        DataFrame vuoto in caso di errore.
    """
    logger.info(
        "Importazione produzione HT Sang da: %s (UO: %s)", file_path, unita_operativa
    )

    if not _valida_unita_operativa(unita_operativa):
        logger.warning(
            "Codice UO '%s' non presente nell'anagrafica. "
            "L'importazione prosegue ma il dato potrebbe non essere coerente.",
            unita_operativa,
        )

    # Verifica che la UO sia tra quelle gestite da HT Sang
    strutture_htsang = FONTI_DATI.get("HT_Sang", {}).get("strutture", [])
    if (
        isinstance(strutture_htsang, list)
        and unita_operativa.strip().upper() not in strutture_htsang
    ):
        logger.warning(
            "UO '%s' non e' tra le strutture previste per HT Sang: %s. "
            "L'importazione prosegue comunque.",
            unita_operativa,
            strutture_htsang,
        )

    df = _leggi_excel(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_PRODUZIONE)

    risultato = _prepara_df_produzione(
        df=df,
        colonne_attese=_COLONNE_HTSANG,
        unita_operativa=unita_operativa,
        fonte="HT_Sang",
    )

    logger.info(
        "Produzione HT Sang importata per UO %s: %d prestazioni, "
        "importo totale: %.2f euro",
        unita_operativa,
        len(risultato),
        risultato["importo"].sum() if not risultato.empty else 0.0,
    )

    return risultato


def importa_template_manuale(
    file_path: Path, unita_operativa: str
) -> pd.DataFrame:
    """
    Importa dati di produzione sanitaria da un template Excel compilato
    manualmente.

    Questo formato viene utilizzato per le strutture o le tipologie di
    prestazione non coperte dai gestionali Caremed e HT Sang.

    Parametri
    ---------
    file_path : Path
        Percorso del file Excel con il template compilato.
    unita_operativa : str
        Codice dell'unita' operativa.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con la produzione normalizzata.
        DataFrame vuoto in caso di errore.
    """
    logger.info(
        "Importazione template manuale da: %s (UO: %s)", file_path, unita_operativa
    )

    if not _valida_unita_operativa(unita_operativa):
        logger.warning(
            "Codice UO '%s' non presente nell'anagrafica.", unita_operativa
        )

    df = _leggi_excel(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_PRODUZIONE)

    risultato = _prepara_df_produzione(
        df=df,
        colonne_attese=_COLONNE_TEMPLATE_MANUALE,
        unita_operativa=unita_operativa,
        fonte="Template_Manuale",
    )

    logger.info(
        "Template manuale importato per UO %s: %d prestazioni, "
        "importo totale: %.2f euro",
        unita_operativa,
        len(risultato),
        risultato["importo"].sum() if not risultato.empty else 0.0,
    )

    return risultato


def calcola_giornate_degenza(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola le giornate di degenza a partire dai dati di produzione.

    Per ogni paziente (identificato da paziente_id) calcola le giornate
    come differenza tra la data massima e minima di erogazione
    prestazioni, considerando almeno 1 giornata per ogni ricovero.

    Parametri
    ---------
    df : pd.DataFrame
        DataFrame di produzione (output di importa_produzione_*).
        Deve contenere le colonne: paziente_id, data, unita_operativa.

    Ritorna
    -------
    pd.DataFrame
        DataFrame con le giornate di degenza per paziente:
        paziente_id, data_ingresso, data_dimissione, giornate, unita_operativa
    """
    if df is None or df.empty:
        logger.warning(
            "DataFrame produzione vuoto, calcolo giornate degenza non possibile."
        )
        return pd.DataFrame(columns=_COLONNE_GIORNATE_DEGENZA)

    colonne_necessarie = ["paziente_id", "data"]
    mancanti = [c for c in colonne_necessarie if c not in df.columns]
    if mancanti:
        logger.error(
            "Colonne necessarie mancanti per il calcolo giornate: %s", mancanti
        )
        return pd.DataFrame(columns=_COLONNE_GIORNATE_DEGENZA)

    # Filtra righe con data e paziente_id validi
    df_valido = df.dropna(subset=["paziente_id", "data"]).copy()
    df_valido = df_valido[df_valido["paziente_id"] != ""]

    if df_valido.empty:
        logger.warning("Nessun dato valido per il calcolo giornate degenza.")
        return pd.DataFrame(columns=_COLONNE_GIORNATE_DEGENZA)

    # Assicura che la colonna data sia di tipo datetime
    if not pd.api.types.is_datetime64_any_dtype(df_valido["data"]):
        try:
            df_valido["data"] = pd.to_datetime(df_valido["data"], errors="coerce")
            df_valido = df_valido.dropna(subset=["data"])
        except Exception as exc:
            logger.error("Errore nella conversione date: %s", exc)
            return pd.DataFrame(columns=_COLONNE_GIORNATE_DEGENZA)

    try:
        # Determina la colonna di raggruppamento
        colonne_gruppo = ["paziente_id"]
        if "unita_operativa" in df_valido.columns:
            colonne_gruppo.append("unita_operativa")

        giornate = (
            df_valido.groupby(colonne_gruppo, as_index=False)
            .agg(
                data_ingresso=("data", "min"),
                data_dimissione=("data", "max"),
            )
            .copy()
        )

        # Calcola giornate (minimo 1)
        giornate["giornate"] = (
            (giornate["data_dimissione"] - giornate["data_ingresso"]).dt.days + 1
        ).clip(lower=1)

        # Aggiunge unita_operativa se mancante
        if "unita_operativa" not in giornate.columns:
            giornate["unita_operativa"] = ""

        giornate = giornate[_COLONNE_GIORNATE_DEGENZA].copy()

        logger.info(
            "Giornate degenza calcolate: %d pazienti, %d giornate totali",
            len(giornate),
            giornate["giornate"].sum(),
        )

        return giornate

    except Exception as exc:
        logger.error("Errore nel calcolo giornate degenza: %s", exc)
        return pd.DataFrame(columns=_COLONNE_GIORNATE_DEGENZA)


def calcola_occupancy(
    giornate: int, posti_letto: int, giorni_periodo: int
) -> float:
    """
    Calcola il tasso di occupazione (occupancy) di una struttura.

    Formula: occupancy = giornate_effettive / (posti_letto * giorni_periodo)

    Parametri
    ---------
    giornate : int
        Numero totale di giornate di degenza effettive nel periodo.
    posti_letto : int
        Numero di posti letto autorizzati della struttura.
    giorni_periodo : int
        Numero di giorni del periodo di riferimento (es. 30 per un mese).

    Ritorna
    -------
    float
        Tasso di occupazione come valore percentuale (0.0 - 1.0+).
        Ritorna 0.0 se i parametri non sono validi.
    """
    if posti_letto <= 0:
        logger.warning(
            "Posti letto non validi (%d): impossibile calcolare l'occupancy.",
            posti_letto,
        )
        return 0.0

    if giorni_periodo <= 0:
        logger.warning(
            "Giorni periodo non validi (%d): impossibile calcolare l'occupancy.",
            giorni_periodo,
        )
        return 0.0

    if giornate < 0:
        logger.warning(
            "Giornate di degenza negative (%d): valore non valido.", giornate
        )
        return 0.0

    capacita_massima = posti_letto * giorni_periodo
    occupancy = giornate / capacita_massima

    # Segnala anomalie
    soglia_occupancy_minima = SOGLIE_SEMAFORO.get("occupancy", (0.90, 0.80))
    if occupancy > 1.0:
        logger.warning(
            "Occupancy superiore al 100%%: %.1f%% "
            "(%d giornate su %d capacita' massima). "
            "Possibile errore nei dati.",
            occupancy * 100,
            giornate,
            capacita_massima,
        )
    elif occupancy < soglia_occupancy_minima[1]:
        logger.info(
            "Occupancy sotto la soglia minima (%.0f%%): %.1f%%",
            soglia_occupancy_minima[1] * 100,
            occupancy * 100,
        )

    logger.debug(
        "Occupancy calcolata: %.1f%% (%d giornate / %d PL x %d gg)",
        occupancy * 100,
        giornate,
        posti_letto,
        giorni_periodo,
    )

    return round(occupancy, 4)
