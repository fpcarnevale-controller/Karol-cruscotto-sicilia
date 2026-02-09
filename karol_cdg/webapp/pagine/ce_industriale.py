"""
Pagina Conto Economico Industriale.

Mostra il CE Industriale per le Unita' Operative selezionate,
con dettaglio voci ricavi e costi diretti, grafici di composizione
costi e waterfall per singola UO.

Autore: Karol CDG
"""

import pandas as pd
import streamlit as st

from karol_cdg.config import (
    UNITA_OPERATIVE,
    UO_OPERATIVE,
    VOCI_RICAVI,
    VOCI_COSTI_DIRETTI,
)
from karol_cdg.webapp.componenti.grafici import (
    grafico_barre_confronto_uo,
    grafico_waterfall_ce,
)
from karol_cdg.webapp.componenti.tabelle import (
    formatta_euro,
    formatta_percentuale,
    tabella_ce_industriale,
)
from karol_cdg.webapp.componenti.metriche import (
    mostra_kpi_card,
    mostra_semaforo,
)


def _opzioni_uo() -> list:
    """
    Genera la lista di opzioni per il selettore delle Unita' Operative
    con formato 'CODICE - Nome'.

    Ritorna:
        Lista di stringhe con codice e nome UO
    """
    opzioni = []
    for codice_uo in UO_OPERATIVE:
        if codice_uo in UNITA_OPERATIVE:
            nome = UNITA_OPERATIVE[codice_uo].nome
            opzioni.append(f"{codice_uo} - {nome}")
        else:
            opzioni.append(codice_uo)
    return opzioni


def _estrai_codice_uo(opzione: str) -> str:
    """
    Estrae il codice UO dalla stringa di opzione 'CODICE - Nome'.

    Parametri:
        opzione: stringa nel formato 'CODICE - Nome'

    Ritorna:
        Codice UO (es. 'VLB')
    """
    return opzione.split(" - ")[0].strip()


def _costruisci_tabella_ce(
    ce_industriale: dict,
    uo_selezionate: list,
) -> pd.DataFrame:
    """
    Costruisce la tabella completa del CE Industriale con tutte le voci
    di ricavi e costi diretti per le UO selezionate.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        uo_selezionate: lista dei codici UO da includere

    Ritorna:
        DataFrame con le voci CE e i valori per ogni UO
    """
    righe = []

    # --- Sezione Ricavi ---
    righe.append({
        "Sezione": "RICAVI",
        "Codice": "",
        "Voce": "RICAVI",
        **{uo: "" for uo in uo_selezionate},
        "Totale": "",
    })

    for codice_voce, descrizione in VOCI_RICAVI.items():
        riga = {
            "Sezione": "RICAVI",
            "Codice": codice_voce,
            "Voce": descrizione,
        }
        totale = 0.0
        for codice_uo in uo_selezionate:
            ce = ce_industriale.get(codice_uo, {})
            ricavi = ce.get("ricavi", {})
            valore = ricavi.get(codice_voce, 0.0)
            riga[codice_uo] = valore
            totale += valore
        riga["Totale"] = totale
        righe.append(riga)

    # Totale Ricavi
    riga_tot_ricavi = {
        "Sezione": "RICAVI",
        "Codice": "",
        "Voce": "TOTALE RICAVI",
    }
    totale_generale_ricavi = 0.0
    for codice_uo in uo_selezionate:
        ce = ce_industriale.get(codice_uo, {})
        valore = ce.get("totale_ricavi", 0.0)
        riga_tot_ricavi[codice_uo] = valore
        totale_generale_ricavi += valore
    riga_tot_ricavi["Totale"] = totale_generale_ricavi
    righe.append(riga_tot_ricavi)

    # --- Sezione Costi Diretti ---
    righe.append({
        "Sezione": "COSTI",
        "Codice": "",
        "Voce": "COSTI DIRETTI",
        **{uo: "" for uo in uo_selezionate},
        "Totale": "",
    })

    # Sotto-sezioni costi
    sotto_sezioni = {
        "Personale diretto": ["CD01", "CD02", "CD03", "CD04", "CD05"],
        "Acquisti diretti": ["CD10", "CD11", "CD12", "CD13"],
        "Servizi diretti": ["CD20", "CD21", "CD22", "CD23", "CD24"],
        "Ammortamenti diretti": ["CD30"],
    }

    for nome_sotto, codici in sotto_sezioni.items():
        # Intestazione sotto-sezione
        righe.append({
            "Sezione": "COSTI",
            "Codice": "",
            "Voce": f"  {nome_sotto}",
            **{uo: "" for uo in uo_selezionate},
            "Totale": "",
        })

        for codice_voce in codici:
            if codice_voce not in VOCI_COSTI_DIRETTI:
                continue
            descrizione = VOCI_COSTI_DIRETTI[codice_voce]
            riga = {
                "Sezione": "COSTI",
                "Codice": codice_voce,
                "Voce": f"    {descrizione}",
            }
            totale = 0.0
            for codice_uo in uo_selezionate:
                ce = ce_industriale.get(codice_uo, {})
                costi = ce.get("costi", {})
                valore = costi.get(codice_voce, 0.0)
                riga[codice_uo] = valore
                totale += valore
            riga["Totale"] = totale
            righe.append(riga)

    # Totale Costi Diretti
    riga_tot_costi = {
        "Sezione": "COSTI",
        "Codice": "",
        "Voce": "TOTALE COSTI DIRETTI",
    }
    totale_generale_costi = 0.0
    for codice_uo in uo_selezionate:
        ce = ce_industriale.get(codice_uo, {})
        valore = ce.get("totale_costi", 0.0)
        riga_tot_costi[codice_uo] = valore
        totale_generale_costi += valore
    riga_tot_costi["Totale"] = totale_generale_costi
    righe.append(riga_tot_costi)

    # --- MOL Industriale ---
    riga_mol = {
        "Sezione": "MOL",
        "Codice": "",
        "Voce": "MOL INDUSTRIALE",
    }
    totale_mol = 0.0
    for codice_uo in uo_selezionate:
        ce = ce_industriale.get(codice_uo, {})
        valore = ce.get("mol_industriale", 0.0)
        riga_mol[codice_uo] = valore
        totale_mol += valore
    riga_mol["Totale"] = totale_mol
    righe.append(riga_mol)

    # Margine % Industriale
    riga_pct = {
        "Sezione": "MOL",
        "Codice": "",
        "Voce": "MARGINE % INDUSTRIALE",
    }
    for codice_uo in uo_selezionate:
        ce = ce_industriale.get(codice_uo, {})
        riga_pct[codice_uo] = ce.get("mol_pct", 0.0)
    riga_pct["Totale"] = totale_mol / totale_generale_ricavi if totale_generale_ricavi > 0 else 0.0
    righe.append(riga_pct)

    return pd.DataFrame(righe)


def _prepara_dati_costi_per_categoria(
    ce_industriale: dict,
    uo_selezionate: list,
) -> pd.DataFrame:
    """
    Prepara i dati dei costi raggruppati per categoria
    (Personale, Acquisti, Servizi, Ammortamenti) per ogni UO.
    Usato per il grafico a barre impilate.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        uo_selezionate: lista dei codici UO

    Ritorna:
        DataFrame con colonne [UO, Personale, Acquisti, Servizi, Ammortamenti]
    """
    righe = []
    for codice_uo in uo_selezionate:
        if codice_uo not in ce_industriale:
            continue
        ce = ce_industriale[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        righe.append({
            "UO": f"{codice_uo}\n{nome_uo}",
            "Personale": ce.get("costi_personale", 0.0),
            "Acquisti": ce.get("costi_acquisti", 0.0),
            "Servizi": ce.get("costi_servizi", 0.0),
            "Ammortamenti": ce.get("costi_ammort", 0.0),
        })

    return pd.DataFrame(righe)


def _prepara_dati_waterfall(ce_industriale: dict, codice_uo: str) -> dict:
    """
    Prepara i dati per il grafico waterfall di una singola UO.
    Mostra il flusso: Ricavi -> -Personale -> -Acquisti ->
    -Servizi -> -Ammortamenti -> = MOL-I.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        codice_uo: codice dell'UO selezionata

    Ritorna:
        Dizionario con etichette e valori per il waterfall
    """
    ce = ce_industriale.get(codice_uo, {})

    return {
        "etichette": [
            "Ricavi",
            "Personale",
            "Acquisti",
            "Servizi",
            "Ammortamenti",
            "MOL-I",
        ],
        "valori": [
            ce.get("totale_ricavi", 0.0),
            -ce.get("costi_personale", 0.0),
            -ce.get("costi_acquisti", 0.0),
            -ce.get("costi_servizi", 0.0),
            -ce.get("costi_ammort", 0.0),
            ce.get("mol_industriale", 0.0),
        ],
        "tipo": ["totale", "relativo", "relativo", "relativo", "relativo", "totale"],
    }


def _mostra_dettaglio_per_uo(ce_industriale: dict, uo_selezionate: list) -> None:
    """
    Mostra il dettaglio voci per ogni UO selezionata all'interno
    di un expander, con metriche principali e tabella voci.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        uo_selezionate: lista dei codici UO
    """
    for codice_uo in uo_selezionate:
        if codice_uo not in ce_industriale:
            continue

        ce = ce_industriale[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        st.markdown(f"#### {codice_uo} - {nome_uo}")

        # Metriche principali UO
        col1, col2, col3, col4 = st.columns(4)
        mostra_kpi_card(col1, "Ricavi", ce["totale_ricavi"], formato="euro")
        mostra_kpi_card(col2, "Costi Diretti", ce["totale_costi"], formato="euro")
        mostra_kpi_card(col3, "MOL-I", ce["mol_industriale"], formato="euro")
        mostra_kpi_card(col4, "MOL-I %", ce["mol_pct"], formato="percentuale")
        livello = "VERDE" if ce["mol_pct"] >= 0.15 else ("GIALLO" if ce["mol_pct"] >= 0.08 else "ROSSO")
        mostra_semaforo(col4, livello)

        # Dettaglio ricavi
        st.markdown("**Dettaglio ricavi:**")
        righe_ricavi = []
        for codice_voce, descrizione in VOCI_RICAVI.items():
            importo = ce.get("ricavi", {}).get(codice_voce, 0.0)
            if importo != 0:
                righe_ricavi.append({
                    "Codice": codice_voce,
                    "Voce": descrizione,
                    "Importo": importo,
                })
        if righe_ricavi:
            df_ricavi = pd.DataFrame(righe_ricavi)
            st.dataframe(
                df_ricavi.style.format({"Importo": lambda x: formatta_euro(x)}),
                use_container_width=True,
                hide_index=True,
            )

        # Dettaglio costi diretti
        st.markdown("**Dettaglio costi diretti:**")
        righe_costi = []
        for codice_voce, descrizione in VOCI_COSTI_DIRETTI.items():
            importo = ce.get("costi", {}).get(codice_voce, 0.0)
            if importo != 0:
                righe_costi.append({
                    "Codice": codice_voce,
                    "Voce": descrizione,
                    "Importo": importo,
                })
        if righe_costi:
            df_costi = pd.DataFrame(righe_costi)
            st.dataframe(
                df_costi.style.format({"Importo": lambda x: formatta_euro(x)}),
                use_container_width=True,
                hide_index=True,
            )

        # Giornate degenza
        giornate = ce.get("giornate_degenza", 0)
        if giornate > 0:
            st.caption(f"Giornate di degenza: **{giornate:,}**".replace(",", "."))

        st.divider()


def mostra_ce_industriale(risultati: dict, dati: dict) -> None:
    """
    Pagina del Conto Economico Industriale.

    Mostra:
    - Selettore UO (multiselect, default tutte le operative)
    - Tabella CE Industriale completa con voci ricavi e costi diretti
    - Grafici: barre impilate costi per categoria e waterfall per UO
    - Selettore per dettaglio waterfall di una singola UO
    - Expander con dettaglio voci per ogni UO

    Parametri:
        risultati: dizionario con le chiavi:
            ce_industriale, ce_gestionale, kpi, allocazione,
            non_allocati, riepilogo_cat
        dati: dizionario con i DataFrame sorgente
    """
    # --- Estrazione dati ---
    ce_industriale = risultati.get("ce_industriale", {})

    # --- Titolo ---
    st.title("Conto Economico Industriale")
    st.markdown(
        "Il CE Industriale mostra la performance economica di ogni Unita' Operativa "
        "considerando **solo ricavi e costi diretti**, prima del ribaltamento dei costi sede."
    )
    st.divider()

    # --- Selettore UO ---
    opzioni = _opzioni_uo()
    selezione = st.multiselect(
        "Seleziona Unita' Operative",
        options=opzioni,
        default=opzioni,
        help="Seleziona le UO da visualizzare nel CE Industriale",
    )
    uo_selezionate = [_estrai_codice_uo(s) for s in selezione]

    if not uo_selezionate:
        st.warning("Seleziona almeno una Unita' Operativa.")
        return

    # --- Tabella CE Industriale completa ---
    st.subheader("Tabella CE Industriale")

    tabella_ce_industriale(ce_industriale, uo_selezionate)

    st.divider()

    # --- Grafici: barre impilate e waterfall ---
    colonna_sinistra, colonna_destra = st.columns(2)

    with colonna_sinistra:
        st.subheader("Composizione costi per UO")
        df_costi_cat = _prepara_dati_costi_per_categoria(ce_industriale, uo_selezionate)
        if not df_costi_cat.empty:
            grafico_barre_confronto_uo(df_costi_cat)
        else:
            st.info("Nessun dato costi disponibile per le UO selezionate.")

    with colonna_destra:
        st.subheader("Waterfall CE Industriale")

        # Selettore per UO singola nel waterfall
        opzioni_singola = [
            f"{uo} - {UNITA_OPERATIVE[uo].nome}" if uo in UNITA_OPERATIVE else uo
            for uo in uo_selezionate
        ]
        if opzioni_singola:
            uo_waterfall = st.selectbox(
                "Seleziona UO per il waterfall",
                options=opzioni_singola,
                key="waterfall_uo_select",
            )
            codice_waterfall = _estrai_codice_uo(uo_waterfall)

            dati_waterfall = _prepara_dati_waterfall(ce_industriale, codice_waterfall)
            grafico_waterfall_ce(dati_waterfall)
        else:
            st.info("Seleziona almeno una UO per visualizzare il waterfall.")

    st.divider()

    # --- Expander dettaglio voci per UO ---
    with st.expander("Dettaglio voci per UO", expanded=False):
        _mostra_dettaglio_per_uo(ce_industriale, uo_selezionate)
