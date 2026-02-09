"""
Pagina Home - Dashboard Controllo di Gestione.

Mostra il cruscotto principale con KPI consolidati, grafici di riepilogo,
tabella comparativa delle Unita' Operative e dettaglio allocazione sede.

Autore: Karol CDG
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from karol_cdg.config import (
    UNITA_OPERATIVE,
    UO_OPERATIVE,
    VOCI_COSTI_SEDE,
    RICAVI_RIFERIMENTO,
)
from karol_cdg.webapp.componenti.grafici import (
    grafico_barre_mol,
    grafico_torta_sede,
)
from karol_cdg.webapp.componenti.tabelle import (
    formatta_euro,
    formatta_percentuale,
)
from karol_cdg.webapp.componenti.metriche import (
    riga_kpi_consolidati,
    pannello_alert,
    mostra_semaforo,
)


def _calcola_kpi_consolidati(ce_industriale: dict, ce_gestionale: dict) -> dict:
    """
    Calcola i 6 KPI consolidati per la riga di metriche in testa alla pagina.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        ce_gestionale: dizionario CE Gestionale per UO

    Ritorna:
        Dizionario con i valori aggregati di gruppo
    """
    ricavi_totali = sum(
        ce_industriale[uo]["totale_ricavi"]
        for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    costi_totali = sum(
        ce_industriale[uo]["totale_costi"]
        for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    mol_i_totale = sum(
        ce_industriale[uo]["mol_industriale"]
        for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    mol_g_totale = sum(
        ce_gestionale[uo]["mol_gestionale"]
        for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )
    costi_sede_totali = sum(
        ce_gestionale[uo]["costi_sede_allocati"]
        for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )

    mol_i_pct = mol_i_totale / ricavi_totali if ricavi_totali > 0 else 0.0
    mol_g_pct = mol_g_totale / ricavi_totali if ricavi_totali > 0 else 0.0

    return {
        "ricavi_totali": ricavi_totali,
        "mol_i_totale": mol_i_totale,
        "mol_i_pct": mol_i_pct,
        "mol_g_totale": mol_g_totale,
        "mol_g_pct": mol_g_pct,
        "costi_sede_totali": costi_sede_totali,
    }


def _costruisci_tabella_uo(ce_industriale: dict, ce_gestionale: dict) -> pd.DataFrame:
    """
    Costruisce la tabella comparativa di tutte le Unita' Operative
    con le colonne: UO, Nome, Ricavi, Costi, MOL-I, MOL-I%, Sede, MOL-G, MOL-G%.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        ce_gestionale: dizionario CE Gestionale per UO

    Ritorna:
        DataFrame formattato con i dati di riepilogo
    """
    righe = []

    for codice_uo in UO_OPERATIVE:
        if codice_uo not in ce_industriale or codice_uo not in ce_gestionale:
            continue

        ce_i = ce_industriale[codice_uo]
        ce_g = ce_gestionale[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        righe.append({
            "UO": codice_uo,
            "Nome": nome_uo,
            "Ricavi": ce_i["totale_ricavi"],
            "Costi": ce_i["totale_costi"],
            "MOL-I": ce_i["mol_industriale"],
            "MOL-I %": ce_i["mol_pct"],
            "Sede": ce_g["costi_sede_allocati"],
            "MOL-G": ce_g["mol_gestionale"],
            "MOL-G %": ce_g["mol_gestionale_pct"],
        })

    df = pd.DataFrame(righe)

    # Riga di totale consolidato
    if not df.empty:
        ricavi_tot = df["Ricavi"].sum()
        costi_tot = df["Costi"].sum()
        mol_i_tot = df["MOL-I"].sum()
        sede_tot = df["Sede"].sum()
        mol_g_tot = df["MOL-G"].sum()

        riga_totale = {
            "UO": "TOTALE",
            "Nome": "Consolidato Gruppo",
            "Ricavi": ricavi_tot,
            "Costi": costi_tot,
            "MOL-I": mol_i_tot,
            "MOL-I %": mol_i_tot / ricavi_tot if ricavi_tot > 0 else 0.0,
            "Sede": sede_tot,
            "MOL-G": mol_g_tot,
            "MOL-G %": mol_g_tot / ricavi_tot if ricavi_tot > 0 else 0.0,
        }
        df = pd.concat([df, pd.DataFrame([riga_totale])], ignore_index=True)

    return df


def _colora_mol_percentuale(valore: float) -> str:
    """
    Restituisce il colore di sfondo CSS per una cella MOL %.

    Parametri:
        valore: valore percentuale del MOL (es. 0.15 = 15%)

    Ritorna:
        Stringa CSS con il colore di sfondo
    """
    if valore >= 0.15:
        return "background-color: #C6EFCE; color: #006600"
    elif valore >= 0.08:
        return "background-color: #FFEB9C; color: #9C5700"
    elif valore >= 0.0:
        return "background-color: #FFC7CE; color: #CC0000"
    else:
        return "background-color: #CC0000; color: #FFFFFF"


def _formatta_tabella_uo(df: pd.DataFrame):
    """
    Applica la formattazione alla tabella delle Unita' Operative
    con colori condizionali sulle colonne MOL %.

    Parametri:
        df: DataFrame con i dati delle UO

    Ritorna:
        Styler di pandas con la formattazione applicata
    """
    formato = {
        "Ricavi": lambda x: formatta_euro(x),
        "Costi": lambda x: formatta_euro(x),
        "MOL-I": lambda x: formatta_euro(x),
        "MOL-I %": lambda x: formatta_percentuale(x),
        "Sede": lambda x: formatta_euro(x),
        "MOL-G": lambda x: formatta_euro(x),
        "MOL-G %": lambda x: formatta_percentuale(x),
    }

    styler = df.style.format(formato)

    # Colori condizionali su MOL-I % e MOL-G %
    styler = styler.applymap(
        _colora_mol_percentuale,
        subset=["MOL-I %", "MOL-G %"],
    )

    return styler


def _mostra_dettaglio_allocazione(
    allocazione: dict,
    riepilogo_cat: dict,
    non_allocati: float,
) -> None:
    """
    Mostra il dettaglio dell'allocazione dei costi sede per UO
    all'interno di un expander Streamlit.

    Parametri:
        allocazione: dizionario {codice_uo: {codice_sede: importo}}
        riepilogo_cat: dizionario per categoria {nome_cat: totale}
        non_allocati: importo totale dei costi sede non allocati
    """
    # Riepilogo per categoria
    st.subheader("Riepilogo per categoria")
    colonne_cat = st.columns(len(riepilogo_cat))
    for idx, (categoria, importo) in enumerate(riepilogo_cat.items()):
        with colonne_cat[idx]:
            st.metric(
                label=categoria,
                value=formatta_euro(importo),
            )

    if non_allocati > 0:
        st.info(
            f"Costi sede non allocati (Sviluppo + Storici): "
            f"**{formatta_euro(non_allocati)}**"
        )

    # Tabella dettaglio per UO
    st.subheader("Dettaglio per Unita' Operativa")

    righe_alloc = []
    for codice_uo in UO_OPERATIVE:
        if codice_uo not in allocazione:
            continue

        voci_uo = allocazione[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        riga = {"UO": codice_uo, "Nome": nome_uo}
        totale_uo = 0.0
        for codice_voce, importo in sorted(voci_uo.items()):
            descrizione = VOCI_COSTI_SEDE.get(codice_voce, codice_voce)
            riga[descrizione] = importo
            totale_uo += importo
        riga["Totale Sede"] = totale_uo
        righe_alloc.append(riga)

    if righe_alloc:
        df_alloc = pd.DataFrame(righe_alloc)
        # Formatta tutte le colonne numeriche come euro
        colonne_numeriche = df_alloc.select_dtypes(include="number").columns
        formato_alloc = {col: lambda x: formatta_euro(x) for col in colonne_numeriche}
        st.dataframe(
            df_alloc.style.format(formato_alloc),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Nessun dato di allocazione disponibile.")


def mostra_home(risultati: dict, dati: dict) -> None:
    """
    Pagina principale della Dashboard Controllo di Gestione.

    Mostra:
    - Riga di 6 KPI consolidati
    - Pannello alert per KPI in stato ROSSO/GIALLO
    - Grafici: barre MOL-I vs MOL-G e torta costi sede
    - Tabella comparativa di tutte le UO
    - Expander con dettaglio allocazione sede

    Parametri:
        risultati: dizionario con le chiavi:
            ce_industriale, ce_gestionale, kpi, allocazione,
            non_allocati, riepilogo_cat
        dati: dizionario con i DataFrame sorgente
            (produzione, costi, costi_sede, driver, personale)
    """
    # --- Estrazione dati ---
    ce_industriale = risultati.get("ce_industriale", {})
    ce_gestionale = risultati.get("ce_gestionale", {})
    kpi_list = risultati.get("kpi", [])
    allocazione = risultati.get("allocazione", {})
    non_allocati = risultati.get("non_allocati", 0.0)
    riepilogo_cat = risultati.get("riepilogo_cat", {})

    # --- Titolo e sottotitolo ---
    st.title("Dashboard Controllo di Gestione")

    periodo_corrente = datetime.now().strftime("%B %Y").capitalize()
    st.markdown(
        f"**Periodo di riferimento:** {periodo_corrente} | "
        f"**Gruppo Karol S.p.A.**"
    )
    st.divider()

    # --- Riga di 6 KPI consolidati ---
    kpi_consolidati = _calcola_kpi_consolidati(ce_industriale, ce_gestionale)

    riga_kpi_consolidati(
        ricavi_totali=kpi_consolidati["ricavi_totali"],
        mol_i=kpi_consolidati["mol_i_totale"],
        mol_i_pct=kpi_consolidati["mol_i_pct"],
        mol_g=kpi_consolidati["mol_g_totale"],
        mol_g_pct=kpi_consolidati["mol_g_pct"],
        costi_sede=kpi_consolidati["costi_sede_totali"],
    )

    st.divider()

    # --- Pannello alert ---
    kpi_critici = [
        kpi for kpi in kpi_list
        if kpi.get("alert") in ("ROSSO", "GIALLO")
    ]

    if kpi_critici:
        pannello_alert(kpi_critici)
        st.divider()

    # --- Grafici: MOL-I vs MOL-G e Torta costi sede ---
    colonna_sinistra, colonna_destra = st.columns(2)

    with colonna_sinistra:
        st.subheader("MOL Industriale vs MOL Gestionale")
        dati_mol = {}
        for codice_uo in UO_OPERATIVE:
            if codice_uo in ce_industriale and codice_uo in ce_gestionale:
                dati_mol[codice_uo] = {
                    "mol_industriale": ce_industriale[codice_uo]["mol_industriale"],
                    "mol_gestionale": ce_gestionale[codice_uo]["mol_gestionale"],
                }
        grafico_barre_mol(dati_mol)

    with colonna_destra:
        st.subheader("Composizione costi sede")
        if riepilogo_cat:
            grafico_torta_sede(riepilogo_cat)
        else:
            st.info("Dati di riepilogo costi sede non disponibili.")

    st.divider()

    # --- Tabella comparativa di tutte le UO ---
    st.subheader("Riepilogo CE per Unita' Operativa")

    df_tabella = _costruisci_tabella_uo(ce_industriale, ce_gestionale)
    if not df_tabella.empty:
        styler = _formatta_tabella_uo(df_tabella)
        st.dataframe(
            styler,
            use_container_width=True,
            hide_index=True,
            height=min(400, 50 + len(df_tabella) * 35),
        )
    else:
        st.warning("Nessun dato disponibile per la tabella riepilogativa.")

    # --- Expander dettaglio allocazione sede ---
    with st.expander("Dettaglio allocazione sede per UO", expanded=False):
        _mostra_dettaglio_allocazione(
            allocazione=allocazione,
            riepilogo_cat=riepilogo_cat,
            non_allocati=non_allocati,
        )
