"""
Funzioni di formattazione tabelle per la webapp Streamlit.

Fornisce utilità per formattare valori in euro, percentuali, applicare
stili semaforo e generare DataFrame stilizzati pronti per st.dataframe().

Le funzioni lavorano con i dizionari prodotti dai moduli core
(ce_industriale, ce_gestionale, kpi).

Autore: Karol CDG
"""

from typing import Dict, List, Optional, Union
import math

import pandas as pd
import numpy as np

from karol_cdg.config import (
    UNITA_OPERATIVE,
    VOCI_RICAVI,
    VOCI_COSTI_DIRETTI,
    VOCI_COSTI_SEDE,
    SOGLIE_SEMAFORO,
    ALERT_CONFIG,
    LivelliAlert,
)

# ============================================================================
# COSTANTI COLORI SEMAFORO
# ============================================================================

COLORE_VERDE = "#27AE60"
COLORE_GIALLO = "#F39C12"
COLORE_ROSSO = "#E74C3C"
COLORE_GRIGIO = "#95A5A6"

# Sfondo leggero per righe colorate
SFONDO_VERDE = "background-color: rgba(39, 174, 96, 0.10)"
SFONDO_GIALLO = "background-color: rgba(243, 156, 18, 0.10)"
SFONDO_ROSSO = "background-color: rgba(231, 76, 60, 0.10)"
SFONDO_TOTALE = "background-color: rgba(31, 78, 121, 0.08); font-weight: bold"

# ============================================================================
# 1. FORMATTAZIONE EURO
# ============================================================================


def formatta_euro(valore: Union[float, int, None]) -> str:
    """
    Formatta un valore numerico come importo in euro con separatore migliaia
    italiano e simbolo valuta.

    Esempi:
        1234567.89  -> '€ 1.234.568'
        -50000      -> '-€ 50.000'
        0           -> '€ 0'
        None        -> '-'

    Parametri:
        valore: importo numerico o None

    Ritorna:
        Stringa formattata in euro
    """
    if valore is None or (isinstance(valore, float) and math.isnan(valore)):
        return "-"

    valore = float(valore)
    negativo = valore < 0
    valore_abs = abs(valore)

    # Formatta con separatore migliaia (virgola americana) poi sostituisci
    testo = f"{valore_abs:,.0f}"
    # Converti da formato americano (1,234,567) a italiano (1.234.567)
    testo = testo.replace(",", ".")

    if negativo:
        return f"-€ {testo}"
    else:
        return f"€ {testo}"


# ============================================================================
# 2. FORMATTAZIONE PERCENTUALE
# ============================================================================


def formatta_percentuale(valore: Union[float, int, None]) -> str:
    """
    Formatta un valore numerico come percentuale con virgola decimale italiana.

    Il valore in input e' atteso come decimale (es. 0.229 = 22,9%).

    Esempi:
        0.229   -> '22,9%'
        0.15    -> '15,0%'
        -0.035  -> '-3,5%'
        None    -> '-'

    Parametri:
        valore: valore decimale (0.229 = 22.9%) o None

    Ritorna:
        Stringa formattata come percentuale
    """
    if valore is None or (isinstance(valore, float) and math.isnan(valore)):
        return "-"

    valore = float(valore)
    percentuale = valore * 100
    testo = f"{percentuale:.1f}%"
    # Sostituisci punto decimale con virgola italiana
    testo = testo.replace(".", ",")
    return testo


# ============================================================================
# 3. COLORE SEMAFORO
# ============================================================================


def colore_semaforo(
    valore: Union[float, None],
    tipo: str,
) -> str:
    """
    Restituisce il colore CSS corrispondente al livello semaforo per un valore
    in base al tipo di KPI.

    Tipi supportati:
        - 'mol_pct': MOL % (piu' alto e' meglio)
            Verde: >= 15%, Giallo: >= 10%, Rosso: < 10%
        - 'costo_pers_pct': costo personale su ricavi (piu' basso e' meglio)
            Verde: <= 55%, Giallo: <= 60%, Rosso: > 60%
        - 'occupancy': tasso di occupazione (piu' alto e' meglio)
            Verde: >= 90%, Giallo: >= 80%, Rosso: < 80%

    Parametri:
        valore: valore del KPI (decimale, es. 0.15 = 15%)
        tipo: tipo di KPI tra 'mol_pct', 'costo_pers_pct', 'occupancy'

    Ritorna:
        Stringa con colore CSS esadecimale
    """
    if valore is None or (isinstance(valore, float) and math.isnan(valore)):
        return COLORE_GRIGIO

    valore = float(valore)

    if tipo == "mol_pct":
        # MOL %: piu' alto e' meglio
        soglie = SOGLIE_SEMAFORO.get("mol_industriale", (0.15, 0.10))
        if valore >= soglie[0]:
            return COLORE_VERDE
        elif valore >= soglie[1]:
            return COLORE_GIALLO
        else:
            return COLORE_ROSSO

    elif tipo == "costo_pers_pct":
        # Costo personale %: piu' basso e' meglio (invertito)
        soglie = SOGLIE_SEMAFORO.get("costo_personale_pct", (0.55, 0.60))
        if valore <= soglie[0]:
            return COLORE_VERDE
        elif valore <= soglie[1]:
            return COLORE_GIALLO
        else:
            return COLORE_ROSSO

    elif tipo == "occupancy":
        # Occupazione: piu' alto e' meglio
        soglie = SOGLIE_SEMAFORO.get("occupancy", (0.90, 0.80))
        if valore >= soglie[0]:
            return COLORE_VERDE
        elif valore >= soglie[1]:
            return COLORE_GIALLO
        else:
            return COLORE_ROSSO

    else:
        return COLORE_GRIGIO


# ============================================================================
# 4. TABELLA CE INDUSTRIALE
# ============================================================================


def tabella_ce_industriale(ce_industriale: List[dict]) -> pd.DataFrame:
    """
    Genera un DataFrame formattato del Conto Economico Industriale
    per tutte le Unita' Operative, pronto per st.dataframe().

    Parametri:
        ce_industriale: lista di dizionari CE Industriale (uno per UO),
                        output di calcola_ce_industriale(). Ogni dict contiene:
                        codice_uo, nome_uo, totale_ricavi, costi_personale,
                        costi_acquisti, costi_servizi, costi_ammortamenti,
                        totale_costi_diretti, mol_industriale, margine_pct_industriale

    Ritorna:
        DataFrame Pandas con righe = UO, colonne = voci CE Industriale
        con formattazione euro e percentuale applicata
    """
    righe = []

    for ce in ce_industriale:
        codice = ce.get("codice_uo", "N/D")
        uo_info = UNITA_OPERATIVE.get(codice)
        nome = uo_info.nome if uo_info else ce.get("nome_uo", codice)

        righe.append({
            "Codice UO": codice,
            "Unità Operativa": nome,
            "Ricavi": ce.get("totale_ricavi", 0.0),
            "Personale": ce.get("costi_personale", 0.0),
            "Acquisti": ce.get("costi_acquisti", 0.0),
            "Servizi": ce.get("costi_servizi", 0.0),
            "Ammortamenti": ce.get("costi_ammortamenti", 0.0),
            "Totale Costi": ce.get("totale_costi_diretti", 0.0),
            "MOL Industriale": ce.get("mol_industriale", 0.0),
            "Margine %": ce.get("margine_pct_industriale", 0.0),
        })

    df = pd.DataFrame(righe)

    if df.empty:
        return df

    # Aggiungi riga di totale consolidato
    riga_totale = {
        "Codice UO": "TOTALE",
        "Unità Operativa": "TOTALE CONSOLIDATO",
    }
    colonne_euro = [
        "Ricavi", "Personale", "Acquisti", "Servizi",
        "Ammortamenti", "Totale Costi", "MOL Industriale",
    ]
    for col in colonne_euro:
        riga_totale[col] = df[col].sum()

    # Ricalcola margine % sul totale (non somma dei margini)
    totale_ricavi = riga_totale.get("Ricavi", 0.0)
    totale_mol = riga_totale.get("MOL Industriale", 0.0)
    riga_totale["Margine %"] = (
        totale_mol / totale_ricavi if totale_ricavi != 0 else 0.0
    )

    df = pd.concat([df, pd.DataFrame([riga_totale])], ignore_index=True)
    df = df.set_index("Codice UO")

    # Applica formattazione
    df = stile_dataframe(
        df,
        colonne_euro=colonne_euro,
        colonne_pct=["Margine %"],
    )

    return df


# ============================================================================
# 5. TABELLA CE GESTIONALE
# ============================================================================


def tabella_ce_gestionale(ce_gestionale: List[dict]) -> pd.DataFrame:
    """
    Genera un DataFrame formattato del Conto Economico Gestionale
    per tutte le Unita' Operative, pronto per st.dataframe().

    Parametri:
        ce_gestionale: lista di dizionari CE Gestionale (uno per UO),
                       output di calcola_ce_gestionale(). Ogni dict contiene:
                       codice_uo, nome_uo, totale_ricavi, mol_industriale,
                       totale_costi_sede, mol_gestionale, margine_pct_gestionale,
                       risultato_netto, margine_pct_netto

    Ritorna:
        DataFrame Pandas con righe = UO, colonne = voci CE Gestionale
    """
    righe = []

    for ce in ce_gestionale:
        codice = ce.get("codice_uo", "N/D")
        uo_info = UNITA_OPERATIVE.get(codice)
        nome = uo_info.nome if uo_info else ce.get("nome_uo", codice)

        righe.append({
            "Codice UO": codice,
            "Unità Operativa": nome,
            "Ricavi": ce.get("totale_ricavi", 0.0),
            "MOL Industriale": ce.get("mol_industriale", 0.0),
            "Margine % I": ce.get("margine_pct_industriale", 0.0),
            "Costi Sede": ce.get("totale_costi_sede", 0.0),
            "MOL Gestionale": ce.get("mol_gestionale", 0.0),
            "Margine % G": ce.get("margine_pct_gestionale", 0.0),
            "Altri Costi": ce.get("totale_altri_costi", 0.0),
            "Risultato Netto": ce.get("risultato_netto", 0.0),
            "Margine % Netto": ce.get("margine_pct_netto", 0.0),
        })

    df = pd.DataFrame(righe)

    if df.empty:
        return df

    # Aggiungi riga di totale consolidato
    colonne_euro = [
        "Ricavi", "MOL Industriale", "Costi Sede",
        "MOL Gestionale", "Altri Costi", "Risultato Netto",
    ]
    colonne_pct = ["Margine % I", "Margine % G", "Margine % Netto"]

    riga_totale = {
        "Codice UO": "TOTALE",
        "Unità Operativa": "TOTALE CONSOLIDATO",
    }
    for col in colonne_euro:
        riga_totale[col] = df[col].sum()

    # Ricalcola i margini percentuali sul totale
    tot_ricavi = riga_totale.get("Ricavi", 0.0)
    if tot_ricavi != 0:
        riga_totale["Margine % I"] = riga_totale["MOL Industriale"] / tot_ricavi
        riga_totale["Margine % G"] = riga_totale["MOL Gestionale"] / tot_ricavi
        riga_totale["Margine % Netto"] = riga_totale["Risultato Netto"] / tot_ricavi
    else:
        for col in colonne_pct:
            riga_totale[col] = 0.0

    df = pd.concat([df, pd.DataFrame([riga_totale])], ignore_index=True)
    df = df.set_index("Codice UO")

    # Applica formattazione
    df = stile_dataframe(
        df,
        colonne_euro=colonne_euro,
        colonne_pct=colonne_pct,
    )

    return df


# ============================================================================
# 6. TABELLA KPI CON SEMAFORO
# ============================================================================


def tabella_kpi(kpi_list: list) -> pd.DataFrame:
    """
    Genera un DataFrame formattato dei KPI con colonna alert colorata,
    pronto per st.dataframe().

    Parametri:
        kpi_list: lista di oggetti KPI (dataclass dal modulo kpi.py).
                  Ogni KPI ha attributi: codice, nome, valore, target,
                  alert_livello (LivelliAlert), unita_operativa, periodo,
                  formula_desc

    Ritorna:
        DataFrame Pandas con righe = KPI, colonne = Nome, Valore, Target,
        Alert, UO, Formula
    """
    righe = []

    for kpi in kpi_list:
        # Determina formato in base al codice KPI
        if kpi.codice in ("KPI_OCC", "KPI_MOL_I", "KPI_MOL_C",
                          "KPI_SEDE_PCT", "KPI_PERS_PCT"):
            valore_fmt = formatta_percentuale(kpi.valore)
            target_fmt = formatta_percentuale(kpi.target)
        elif kpi.codice in ("KPI_CASSA",):
            valore_fmt = formatta_euro(kpi.valore)
            target_fmt = formatta_euro(kpi.target)
        elif kpi.codice in ("KPI_RIC_GG", "KPI_CPERS_GG"):
            valore_fmt = formatta_euro(kpi.valore)
            target_fmt = formatta_euro(kpi.target)
        else:
            # DSO, DPO, DSCR, ore, copertura cassa: formato numerico
            valore_fmt = f"{kpi.valore:,.1f}".replace(",", ".").replace(".", ",", 1)
            target_fmt = f"{kpi.target:,.1f}".replace(",", ".").replace(".", ",", 1)

        # Icona semaforo
        mappa_icone = {
            LivelliAlert.VERDE: "🟢",
            LivelliAlert.GIALLO: "🟡",
            LivelliAlert.ROSSO: "🔴",
        }
        icona = mappa_icone.get(kpi.alert_livello, "⚪")

        righe.append({
            "Nome KPI": kpi.nome,
            "Valore": valore_fmt,
            "Target": target_fmt,
            "Alert": f"{icona} {kpi.alert_livello.value.upper()}",
            "UO": kpi.unita_operativa or "Consolidato",
            "Formula": kpi.formula_desc,
        })

    df = pd.DataFrame(righe)

    if not df.empty:
        df = df.set_index("Nome KPI")

    return df


# ============================================================================
# 7. STILE DATAFRAME GENERICO
# ============================================================================


def stile_dataframe(
    df: pd.DataFrame,
    colonne_euro: Optional[List[str]] = None,
    colonne_pct: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Applica la formattazione euro e percentuale alle colonne specificate
    di un DataFrame generico. Restituisce un nuovo DataFrame con valori
    stringa formattati.

    Le colonne non specificate restano invariate.

    Parametri:
        df: DataFrame originale con valori numerici
        colonne_euro: lista nomi colonne da formattare come euro
                      (default: lista vuota)
        colonne_pct: lista nomi colonne da formattare come percentuale
                     (default: lista vuota)

    Ritorna:
        DataFrame con colonne formattate come stringhe
    """
    if colonne_euro is None:
        colonne_euro = []
    if colonne_pct is None:
        colonne_pct = []

    df_formattato = df.copy()

    for col in colonne_euro:
        if col in df_formattato.columns:
            df_formattato[col] = df_formattato[col].apply(formatta_euro)

    for col in colonne_pct:
        if col in df_formattato.columns:
            df_formattato[col] = df_formattato[col].apply(formatta_percentuale)

    return df_formattato
