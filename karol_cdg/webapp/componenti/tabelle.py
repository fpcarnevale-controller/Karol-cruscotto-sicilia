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


def tabella_ce_industriale(
    ce_industriale: Dict[str, dict],
    uo_selezionate: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Genera un DataFrame formattato del Conto Economico Industriale
    per le Unita' Operative selezionate, pronto per st.dataframe().

    Parametri:
        ce_industriale: dizionario CE Industriale indicizzato per codice UO.
                        Ogni valore contiene: totale_ricavi, totale_costi,
                        mol_industriale, mol_pct, costi_personale,
                        costi_acquisti, costi_servizi, costi_ammort,
                        ricavi (dict), costi (dict)
        uo_selezionate: lista opzionale di codici UO da includere.
                        Se None, include tutte le UO presenti.

    Ritorna:
        DataFrame Pandas con righe = UO, colonne = voci CE Industriale
        con formattazione euro e percentuale applicata
    """
    if uo_selezionate is None:
        uo_selezionate = list(ce_industriale.keys())

    righe = []

    for codice in uo_selezionate:
        ce = ce_industriale.get(codice)
        if ce is None:
            continue

        uo_info = UNITA_OPERATIVE.get(codice)
        nome = uo_info.nome if uo_info else codice

        righe.append({
            "Codice UO": codice,
            "Unità Operativa": nome,
            "Ricavi": ce.get("totale_ricavi", 0.0),
            "Personale": ce.get("costi_personale", 0.0),
            "Acquisti": ce.get("costi_acquisti", 0.0),
            "Servizi": ce.get("costi_servizi", 0.0),
            "Ammortamenti": ce.get("costi_ammort", 0.0),
            "Totale Costi": ce.get("totale_costi", 0.0),
            "MOL Industriale": ce.get("mol_industriale", 0.0),
            "Margine %": ce.get("mol_pct", 0.0),
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


def tabella_ce_gestionale(
    ce_industriale: Dict[str, dict],
    ce_gestionale: Optional[Dict[str, dict]] = None,
    allocazione: Optional[Dict[str, dict]] = None,
) -> pd.DataFrame:
    """
    Genera un DataFrame formattato del Conto Economico Gestionale
    per tutte le Unita' Operative, pronto per st.dataframe().

    Parametri:
        ce_industriale: dizionario CE Industriale indicizzato per codice UO.
                        Ogni valore contiene: totale_ricavi, mol_industriale,
                        mol_pct, ecc.
        ce_gestionale: dizionario CE Gestionale indicizzato per codice UO
                       (opzionale). Ogni valore contiene: mol_industriale,
                       costi_sede_allocati, mol_gestionale,
                       mol_gestionale_pct, totale_ricavi, dettaglio_sede
        allocazione: dizionario allocazione indicizzato per codice UO
                     (opzionale, {codice_uo: {codice_sede: importo}})

    Ritorna:
        DataFrame Pandas con righe = UO, colonne = voci CE Gestionale
    """
    if ce_gestionale is None:
        ce_gestionale = {}
    if allocazione is None:
        allocazione = {}

    # Determina le UO da mostrare (unione delle chiavi)
    codici_uo = list(dict.fromkeys(
        list(ce_industriale.keys()) + list(ce_gestionale.keys())
    ))

    righe = []

    for codice in codici_uo:
        ce_i = ce_industriale.get(codice, {})
        ce_g = ce_gestionale.get(codice, {})

        uo_info = UNITA_OPERATIVE.get(codice)
        nome = uo_info.nome if uo_info else codice

        totale_ricavi = ce_g.get("totale_ricavi", ce_i.get("totale_ricavi", 0.0))
        mol_i = ce_g.get("mol_industriale", ce_i.get("mol_industriale", 0.0))
        costi_sede = ce_g.get("costi_sede_allocati", 0.0)
        mol_g = ce_g.get("mol_gestionale", 0.0)
        mol_g_pct = ce_g.get("mol_gestionale_pct", 0.0)

        # Margine % Industriale: da CE Industriale
        mol_i_pct = ce_i.get("mol_pct", 0.0)
        if mol_i_pct == 0.0 and totale_ricavi > 0:
            mol_i_pct = mol_i / totale_ricavi

        righe.append({
            "Codice UO": codice,
            "Unità Operativa": nome,
            "Ricavi": totale_ricavi,
            "MOL Industriale": mol_i,
            "Margine % I": mol_i_pct,
            "Costi Sede": costi_sede,
            "MOL Gestionale": mol_g,
            "Margine % G": mol_g_pct,
        })

    df = pd.DataFrame(righe)

    if df.empty:
        return df

    # Aggiungi riga di totale consolidato
    colonne_euro = [
        "Ricavi", "MOL Industriale", "Costi Sede",
        "MOL Gestionale",
    ]
    colonne_pct = ["Margine % I", "Margine % G"]

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
        kpi_list: lista di dizionari KPI. Ogni dizionario ha le chiavi:
                  "kpi" (nome), "unita_operativa", "valore", "target",
                  "alert" (stringa: "VERDE"/"GIALLO"/"ROSSO"), "formula"

    Ritorna:
        DataFrame Pandas con righe = KPI, colonne = Nome, Valore, Target,
        Alert, UO, Formula
    """
    # Mappa stringa alert -> icona semaforo
    mappa_icone = {
        "VERDE": "🟢",
        "GIALLO": "🟡",
        "ROSSO": "🔴",
    }

    righe = []

    for kpi in kpi_list:
        nome_kpi = kpi.get("kpi", "N/D")
        valore = kpi.get("valore")
        target = kpi.get("target")
        alert = kpi.get("alert", "VERDE")
        uo = kpi.get("unita_operativa") or "Consolidato"
        formula = kpi.get("formula", "")

        # Determina formato in base al nome KPI (euristiche sul nome)
        nome_lower = nome_kpi.lower()

        if any(t in nome_lower for t in (
            "%", "pct", "percentuale", "margine", "incidenza",
            "occupancy", "occupazione",
        )):
            valore_fmt = formatta_percentuale(valore)
            target_fmt = formatta_percentuale(target)
        elif any(t in nome_lower for t in ("ricav", "costo", "cassa", "fattur")):
            valore_fmt = formatta_euro(valore)
            target_fmt = formatta_euro(target)
        elif any(t in nome_lower for t in ("mol",)):
            # MOL senza % -> euro
            valore_fmt = formatta_euro(valore)
            target_fmt = formatta_euro(target)
        else:
            # DSO, DPO, DSCR, ore, copertura cassa: formato numerico
            try:
                valore_fmt = f"{float(valore):,.1f}".replace(",", ".").replace(".", ",", 1) if valore is not None else "-"
                target_fmt = f"{float(target):,.1f}".replace(",", ".").replace(".", ",", 1) if target is not None else "-"
            except (TypeError, ValueError):
                valore_fmt = str(valore) if valore is not None else "-"
                target_fmt = str(target) if target is not None else "-"

        # Icona semaforo
        icona = mappa_icone.get(alert, "⚪")

        righe.append({
            "Nome KPI": nome_kpi,
            "Valore": valore_fmt,
            "Target": target_fmt,
            "Alert": f"{icona} {alert}",
            "UO": uo,
            "Formula": formula,
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
