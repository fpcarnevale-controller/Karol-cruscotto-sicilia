"""
Import dati personale da Zucchetti.

Modulo per la lettura e l'elaborazione dei dati esportati dal sistema
paghe Zucchetti in formato CSV:
  - Costi del personale per matricola, struttura e qualifica
  - Presenze e ore lavorate

Fornisce inoltre funzioni di aggregazione per unita' operativa e qualifica
e il calcolo degli FTE (Full Time Equivalent).

Tutte le funzioni restituiscono un DataFrame vuoto in caso di errore,
registrando l'anomalia tramite il modulo logging.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from karol_cdg.config import (
    FORMATO_MESE,
    MESI_IT,
    QualificaPersonale,
    SEPARATORE_DECIMALI,
    SEPARATORE_MIGLIAIA,
    UNITA_OPERATIVE,
)

logger = logging.getLogger(__name__)

# ============================================================================
# COSTANTI INTERNE
# ============================================================================

# Ore contrattuali mensili di riferimento per calcolo FTE
ORE_CONTRATTUALI_MENSILI = 156.0  # 36 ore/settimana * 4.33 settimane

# Colonne attese nel CSV costi del personale Zucchetti
_COLONNE_COSTI_PERSONALE = [
    "matricola",
    "cognome",
    "nome",
    "qualifica",
    "unita_operativa",
    "costo_lordo",
    "contributi",
    "tfr",
    "costo_totale",
    "ore_ordinarie",
    "ore_straordinarie",
    "mese",
    "anno",
]

# Colonne attese nel CSV presenze Zucchetti
_COLONNE_PRESENZE = [
    "matricola",
    "cognome",
    "nome",
    "qualifica",
    "unita_operativa",
    "data",
    "ore_presenza",
    "ore_assenza",
    "tipo_assenza",
    "ore_straordinario",
    "mese",
    "anno",
]

# Codifiche da tentare in ordine di preferenza
_ENCODING_FALLBACK = ["utf-8", "latin-1", "cp1252"]


# ============================================================================
# FUNZIONI AUSILIARIE
# ============================================================================


def _leggi_csv_zucchetti(
    file_path: Path, separatore: str = ";"
) -> Optional[pd.DataFrame]:
    """
    Legge un file CSV Zucchetti tentando diverse codifiche.

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV.
    separatore : str
        Separatore di colonne (default ";").

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
                "File Zucchetti letto con codifica %s: %s (%d righe)",
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


def _converti_ore(valore: str) -> float:
    """
    Converte un valore ore in formato stringa a float.

    Gestisce sia il formato decimale italiano (es. "7,50")
    sia il formato con due punti (es. "7:30").
    """
    if not valore or pd.isna(valore):
        return 0.0

    valore_pulito = str(valore).strip()
    if not valore_pulito:
        return 0.0

    # Formato HH:MM
    if ":" in valore_pulito:
        try:
            parti = valore_pulito.split(":")
            ore = int(parti[0])
            minuti = int(parti[1]) if len(parti) > 1 else 0
            return ore + minuti / 60.0
        except (ValueError, IndexError):
            logger.warning("Impossibile convertire le ore in formato HH:MM: '%s'", valore)
            return 0.0

    # Formato decimale italiano
    return _converti_importo(valore_pulito)


def _valida_qualifica(qualifica: str) -> str:
    """
    Normalizza e valida la qualifica del personale rispetto all'enum
    QualificaPersonale definito in config.py.

    Ritorna la qualifica normalizzata oppure 'Altro' se non riconosciuta.
    """
    qualifica_pulita = qualifica.strip().upper()

    # Mappatura abbreviazioni comuni -> enum
    mappatura = {
        "MED": QualificaPersonale.MEDICO.value,
        "MEDICO": QualificaPersonale.MEDICO.value,
        "INF": QualificaPersonale.INFERMIERE.value,
        "INFERMIERE": QualificaPersonale.INFERMIERE.value,
        "INFERMIERA": QualificaPersonale.INFERMIERE.value,
        "OSS": QualificaPersonale.OSS.value,
        "AUSILIARIO": QualificaPersonale.OSS.value,
        "AUSILIARIA": QualificaPersonale.OSS.value,
        "TEC LAB": QualificaPersonale.TECNICO_LAB.value,
        "TECNICO LABORATORIO": QualificaPersonale.TECNICO_LAB.value,
        "TEC RAD": QualificaPersonale.TECNICO_RAD.value,
        "TECNICO RADIOLOGIA": QualificaPersonale.TECNICO_RAD.value,
        "FKT": QualificaPersonale.FISIOTERAPISTA.value,
        "FISIOTERAPISTA": QualificaPersonale.FISIOTERAPISTA.value,
        "AMM": QualificaPersonale.AMMINISTRATIVO.value,
        "AMMINISTRATIVO": QualificaPersonale.AMMINISTRATIVO.value,
        "AMMINISTRATIVA": QualificaPersonale.AMMINISTRATIVO.value,
        "DIR": QualificaPersonale.DIRIGENTE.value,
        "DIRIGENTE": QualificaPersonale.DIRIGENTE.value,
    }

    valore_mappato = mappatura.get(qualifica_pulita)
    if valore_mappato:
        return valore_mappato

    # Tentativo di corrispondenza parziale
    for chiave, valore in mappatura.items():
        if chiave in qualifica_pulita:
            return valore

    logger.debug(
        "Qualifica non riconosciuta: '%s'. Assegnata come '%s'.",
        qualifica,
        QualificaPersonale.ALTRO.value,
    )
    return QualificaPersonale.ALTRO.value


# ============================================================================
# FUNZIONI PUBBLICHE
# ============================================================================


def importa_costi_personale(file_path: Path, periodo: str) -> pd.DataFrame:
    """
    Importa i costi del personale da un export CSV di Zucchetti.

    Il file deve contenere le colonne:
      matricola, cognome, nome, qualifica, unita_operativa,
      costo_lordo, contributi, tfr, costo_totale,
      ore_ordinarie, ore_straordinarie, mese, anno

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV esportato da Zucchetti.
    periodo : str
        Periodo di riferimento nel formato MM/YYYY (es. "03/2025").

    Ritorna
    -------
    pd.DataFrame
        DataFrame con i costi del personale normalizzati.
        DataFrame vuoto in caso di errore.
    """
    logger.info(
        "Importazione costi personale Zucchetti da: %s (periodo: %s)",
        file_path,
        periodo,
    )

    df = _leggi_csv_zucchetti(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_COSTI_PERSONALE)

    df = _normalizza_nomi_colonne(df)

    # Verifica colonne obbligatorie
    colonne_mancanti = [c for c in _COLONNE_COSTI_PERSONALE if c not in df.columns]
    if colonne_mancanti:
        logger.error(
            "Colonne mancanti nei costi personale: %s. Colonne trovate: %s",
            colonne_mancanti,
            list(df.columns),
        )
        return pd.DataFrame(columns=_COLONNE_COSTI_PERSONALE)

    df = df[_COLONNE_COSTI_PERSONALE].copy()

    # Conversione campi numerici - importi
    colonne_importo = ["costo_lordo", "contributi", "tfr", "costo_totale"]
    for col in colonne_importo:
        df[col] = df[col].apply(_converti_importo)

    # Conversione campi numerici - ore
    colonne_ore = ["ore_ordinarie", "ore_straordinarie"]
    for col in colonne_ore:
        df[col] = df[col].apply(_converti_ore)

    # Conversione mese e anno
    try:
        df["mese"] = pd.to_numeric(df["mese"], errors="coerce").fillna(0).astype(int)
        df["anno"] = pd.to_numeric(df["anno"], errors="coerce").fillna(0).astype(int)
    except Exception as exc:
        logger.error("Errore nella conversione di mese/anno: %s", exc)
        return pd.DataFrame(columns=_COLONNE_COSTI_PERSONALE)

    # Pulizia campi testo
    df["matricola"] = df["matricola"].str.strip()
    df["cognome"] = df["cognome"].str.strip().str.upper()
    df["nome"] = df["nome"].str.strip().str.title()
    df["unita_operativa"] = df["unita_operativa"].str.strip().str.upper()

    # Normalizzazione qualifica
    df["qualifica"] = df["qualifica"].apply(_valida_qualifica)

    # Filtra per il periodo richiesto
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
                    "Nessun dato costi personale per il periodo %s.", periodo
                )
            else:
                logger.info(
                    "Costi personale filtrati per %s: %d righe",
                    periodo,
                    len(df_filtrato),
                )
            df = df_filtrato
        except ValueError:
            logger.error(
                "Formato periodo non valido: '%s'. Atteso MM/YYYY.", periodo
            )

    # Validazione: se costo_totale e' zero ma ci sono componenti, ricalcola
    maschera_ricalcolo = (df["costo_totale"] == 0) & (
        (df["costo_lordo"] > 0) | (df["contributi"] > 0) | (df["tfr"] > 0)
    )
    if maschera_ricalcolo.any():
        n_ricalcolati = maschera_ricalcolo.sum()
        df.loc[maschera_ricalcolo, "costo_totale"] = (
            df.loc[maschera_ricalcolo, "costo_lordo"]
            + df.loc[maschera_ricalcolo, "contributi"]
            + df.loc[maschera_ricalcolo, "tfr"]
        )
        logger.info(
            "Ricalcolato costo_totale per %d dipendenti "
            "(somma di lordo + contributi + TFR).",
            n_ricalcolati,
        )

    logger.info(
        "Costi personale importati: %d dipendenti, costo totale: %.2f euro",
        len(df),
        df["costo_totale"].sum(),
    )

    return df


def importa_presenze(file_path: Path, periodo: str) -> pd.DataFrame:
    """
    Importa i dati di presenza del personale da un export CSV di Zucchetti.

    Parametri
    ---------
    file_path : Path
        Percorso del file CSV esportato da Zucchetti.
    periodo : str
        Periodo di riferimento nel formato MM/YYYY (es. "03/2025").

    Ritorna
    -------
    pd.DataFrame
        DataFrame con le presenze normalizzate.
        DataFrame vuoto in caso di errore.
    """
    logger.info(
        "Importazione presenze Zucchetti da: %s (periodo: %s)", file_path, periodo
    )

    df = _leggi_csv_zucchetti(file_path)
    if df is None:
        return pd.DataFrame(columns=_COLONNE_PRESENZE)

    df = _normalizza_nomi_colonne(df)

    # Verifica colonne minime
    colonne_minime = ["matricola", "ore_presenza"]
    colonne_mancanti = [c for c in colonne_minime if c not in df.columns]
    if colonne_mancanti:
        logger.error(
            "Colonne obbligatorie mancanti nelle presenze: %s. Colonne trovate: %s",
            colonne_mancanti,
            list(df.columns),
        )
        return pd.DataFrame(columns=_COLONNE_PRESENZE)

    # Aggiunge colonne mancanti con valori vuoti
    for col in _COLONNE_PRESENZE:
        if col not in df.columns:
            df[col] = ""
            logger.debug("Colonna '%s' non presente, aggiunta con valori vuoti.", col)

    df = df[_COLONNE_PRESENZE].copy()

    # Conversione ore
    for col_ore in ["ore_presenza", "ore_assenza", "ore_straordinario"]:
        df[col_ore] = df[col_ore].apply(_converti_ore)

    # Conversione data
    if df["data"].notna().any() and (df["data"] != "").any():
        try:
            df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
        except Exception:
            logger.warning("Impossibile convertire la colonna 'data' in formato data.")

    # Conversione mese e anno
    try:
        df["mese"] = pd.to_numeric(df["mese"], errors="coerce").fillna(0).astype(int)
        df["anno"] = pd.to_numeric(df["anno"], errors="coerce").fillna(0).astype(int)
    except Exception as exc:
        logger.error("Errore nella conversione di mese/anno: %s", exc)

    # Pulizia campi testo
    df["matricola"] = df["matricola"].str.strip()
    df["unita_operativa"] = df["unita_operativa"].str.strip().str.upper()

    # Filtra per il periodo richiesto
    if periodo:
        try:
            mese_filtro, anno_filtro = periodo.split("/")
            mese_filtro = int(mese_filtro)
            anno_filtro = int(anno_filtro)
            df_filtrato = df[
                (df["mese"] == mese_filtro) & (df["anno"] == anno_filtro)
            ].copy()

            if df_filtrato.empty:
                logger.warning("Nessun dato presenze per il periodo %s.", periodo)
            else:
                logger.info(
                    "Presenze filtrate per %s: %d righe", periodo, len(df_filtrato)
                )
            df = df_filtrato
        except ValueError:
            logger.error(
                "Formato periodo non valido: '%s'. Atteso MM/YYYY.", periodo
            )

    logger.info(
        "Presenze importate: %d righe, ore presenza totali: %.1f",
        len(df),
        df["ore_presenza"].sum(),
    )

    return df


def aggrega_per_uo_qualifica(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggrega i costi del personale per unita' operativa e qualifica.

    Produce un riepilogo con il totale dei costi e delle ore per
    ogni combinazione UO/qualifica.

    Parametri
    ---------
    df : pd.DataFrame
        DataFrame dei costi personale (output di importa_costi_personale).

    Ritorna
    -------
    pd.DataFrame
        DataFrame aggregato con colonne:
        unita_operativa, qualifica, n_dipendenti, costo_lordo,
        contributi, tfr, costo_totale, ore_ordinarie, ore_straordinarie
    """
    colonne_risultato = [
        "unita_operativa",
        "qualifica",
        "n_dipendenti",
        "costo_lordo",
        "contributi",
        "tfr",
        "costo_totale",
        "ore_ordinarie",
        "ore_straordinarie",
    ]

    if df is None or df.empty:
        logger.warning("DataFrame costi personale vuoto, aggregazione non possibile.")
        return pd.DataFrame(columns=colonne_risultato)

    colonne_necessarie = ["unita_operativa", "qualifica", "costo_totale"]
    mancanti = [c for c in colonne_necessarie if c not in df.columns]
    if mancanti:
        logger.error(
            "Colonne necessarie mancanti per l'aggregazione: %s", mancanti
        )
        return pd.DataFrame(columns=colonne_risultato)

    try:
        aggregato = (
            df.groupby(["unita_operativa", "qualifica"], as_index=False)
            .agg(
                n_dipendenti=("matricola", "nunique"),
                costo_lordo=("costo_lordo", "sum"),
                contributi=("contributi", "sum"),
                tfr=("tfr", "sum"),
                costo_totale=("costo_totale", "sum"),
                ore_ordinarie=("ore_ordinarie", "sum"),
                ore_straordinarie=("ore_straordinarie", "sum"),
            )
            .sort_values(["unita_operativa", "qualifica"])
            .reset_index(drop=True)
        )

        logger.info(
            "Aggregazione completata: %d combinazioni UO/qualifica, "
            "costo totale complessivo: %.2f euro",
            len(aggregato),
            aggregato["costo_totale"].sum(),
        )

        return aggregato

    except Exception as exc:
        logger.error("Errore durante l'aggregazione per UO/qualifica: %s", exc)
        return pd.DataFrame(columns=colonne_risultato)


def calcola_fte(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola gli FTE (Full Time Equivalent) per unita' operativa.

    L'FTE e' calcolato come rapporto tra le ore ordinarie effettive
    e le ore contrattuali di riferimento (ORE_CONTRATTUALI_MENSILI).

    Parametri
    ---------
    df : pd.DataFrame
        DataFrame dei costi personale (output di importa_costi_personale).

    Ritorna
    -------
    pd.DataFrame
        DataFrame con colonne:
        unita_operativa, qualifica, n_dipendenti, ore_ordinarie_totali,
        fte, costo_per_fte
    """
    colonne_risultato = [
        "unita_operativa",
        "qualifica",
        "n_dipendenti",
        "ore_ordinarie_totali",
        "fte",
        "costo_per_fte",
    ]

    if df is None or df.empty:
        logger.warning("DataFrame costi personale vuoto, calcolo FTE non possibile.")
        return pd.DataFrame(columns=colonne_risultato)

    colonne_necessarie = ["unita_operativa", "ore_ordinarie"]
    mancanti = [c for c in colonne_necessarie if c not in df.columns]
    if mancanti:
        logger.error("Colonne necessarie mancanti per il calcolo FTE: %s", mancanti)
        return pd.DataFrame(columns=colonne_risultato)

    try:
        # Aggregazione per UO e qualifica
        fte_df = (
            df.groupby(["unita_operativa", "qualifica"], as_index=False)
            .agg(
                n_dipendenti=("matricola", "nunique"),
                ore_ordinarie_totali=("ore_ordinarie", "sum"),
                costo_totale=("costo_totale", "sum"),
            )
            .copy()
        )

        # Calcolo FTE: ore effettive / ore contrattuali
        fte_df["fte"] = (
            fte_df["ore_ordinarie_totali"] / ORE_CONTRATTUALI_MENSILI
        ).round(2)

        # Costo per FTE (evita divisione per zero)
        fte_df["costo_per_fte"] = 0.0
        maschera_fte_positivo = fte_df["fte"] > 0
        fte_df.loc[maschera_fte_positivo, "costo_per_fte"] = (
            fte_df.loc[maschera_fte_positivo, "costo_totale"]
            / fte_df.loc[maschera_fte_positivo, "fte"]
        ).round(2)

        # Rimuove colonna ausiliaria e riordina
        fte_df = fte_df.drop(columns=["costo_totale"])
        fte_df = fte_df.sort_values(
            ["unita_operativa", "qualifica"]
        ).reset_index(drop=True)

        logger.info(
            "Calcolo FTE completato: %.2f FTE totali su %d combinazioni UO/qualifica",
            fte_df["fte"].sum(),
            len(fte_df),
        )

        return fte_df

    except Exception as exc:
        logger.error("Errore durante il calcolo FTE: %s", exc)
        return pd.DataFrame(columns=colonne_risultato)
