"""
Pagina Conto Economico Gestionale.

Mostra il CE Gestionale che parte dal MOL Industriale e sottrae
i costi di sede allocati per ottenere il MOL Gestionale.
Include il confronto tra metodo vecchio (% piatta sul fatturato)
e metodo nuovo (allocazione per driver).

Autore: Karol CDG
"""

import pandas as pd
import streamlit as st

from karol_cdg.config import (
    UNITA_OPERATIVE,
    UO_OPERATIVE,
    VOCI_COSTI_SEDE,
    RICAVI_RIFERIMENTO,
)
from karol_cdg.webapp.componenti.grafici import (
    grafico_barre_confronto_uo,
)
from karol_cdg.webapp.componenti.tabelle import (
    formatta_euro,
    formatta_percentuale,
    tabella_ce_gestionale,
)
from karol_cdg.webapp.componenti.metriche import (
    mostra_kpi_card,
    mostra_semaforo,
)


# Percentuale storica di ribaltamento costi sede (metodo vecchio)
PERCENTUALE_RIBALTAMENTO_STORICA = RICAVI_RIFERIMENTO.get("pct_costi_sede_su_ricavi", 0.196)


def _costruisci_flusso_mol(ce_industriale: dict, ce_gestionale: dict) -> dict:
    """
    Calcola i valori aggregati per il flusso MOL-I -> Costi Sede -> MOL-G.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        ce_gestionale: dizionario CE Gestionale per UO

    Ritorna:
        Dizionario con i valori consolidati del flusso
    """
    mol_i_totale = sum(
        ce_industriale[uo]["mol_industriale"]
        for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    costi_sede_totali = sum(
        ce_gestionale[uo]["costi_sede_allocati"]
        for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )
    mol_g_totale = sum(
        ce_gestionale[uo]["mol_gestionale"]
        for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )
    ricavi_totali = sum(
        ce_industriale[uo]["totale_ricavi"]
        for uo in UO_OPERATIVE
        if uo in ce_industriale
    )

    mol_i_pct = mol_i_totale / ricavi_totali if ricavi_totali > 0 else 0.0
    sede_pct = costi_sede_totali / ricavi_totali if ricavi_totali > 0 else 0.0
    mol_g_pct = mol_g_totale / ricavi_totali if ricavi_totali > 0 else 0.0

    return {
        "mol_i_totale": mol_i_totale,
        "mol_i_pct": mol_i_pct,
        "costi_sede_totali": costi_sede_totali,
        "sede_pct": sede_pct,
        "mol_g_totale": mol_g_totale,
        "mol_g_pct": mol_g_pct,
        "ricavi_totali": ricavi_totali,
    }


def _costruisci_tabella_confronto_metodi(
    ce_industriale: dict,
    ce_gestionale: dict,
) -> pd.DataFrame:
    """
    Costruisce la tabella di confronto tra metodo vecchio (% piatta 19.6%)
    e metodo nuovo (allocazione per driver) per ogni UO.

    Il metodo vecchio ripartisce i costi sede in proporzione fissa sul
    fatturato di ciascuna UO. Il metodo nuovo usa driver specifici
    (fatture, cedolini, acquisti, postazioni, ecc.).

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        ce_gestionale: dizionario CE Gestionale per UO

    Ritorna:
        DataFrame con colonne: UO, Nome, Ricavi, Sede Vecchio Metodo,
        Sede Nuovo Metodo, Differenza, MOL-G Vecchio, MOL-G Nuovo
    """
    righe = []

    # Calcola il totale costi sede effettivo (per proporzionare il vecchio metodo)
    totale_sede_effettivo = sum(
        ce_gestionale[uo]["costi_sede_allocati"]
        for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )

    for codice_uo in UO_OPERATIVE:
        if codice_uo not in ce_industriale or codice_uo not in ce_gestionale:
            continue

        ce_i = ce_industriale[codice_uo]
        ce_g = ce_gestionale[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        ricavi_uo = ce_i["totale_ricavi"]
        mol_i = ce_i["mol_industriale"]

        # Metodo vecchio: % piatta sul fatturato
        sede_vecchio = ricavi_uo * PERCENTUALE_RIBALTAMENTO_STORICA
        mol_g_vecchio = mol_i - sede_vecchio

        # Metodo nuovo: allocazione per driver (dati effettivi)
        sede_nuovo = ce_g["costi_sede_allocati"]
        mol_g_nuovo = ce_g["mol_gestionale"]

        differenza = sede_nuovo - sede_vecchio

        righe.append({
            "UO": codice_uo,
            "Nome": nome_uo,
            "Ricavi": ricavi_uo,
            "Sede (% piatta)": sede_vecchio,
            "Sede (driver)": sede_nuovo,
            "Differenza": differenza,
            "MOL-G (% piatta)": mol_g_vecchio,
            "MOL-G (driver)": mol_g_nuovo,
        })

    df = pd.DataFrame(righe)

    # Riga di totale
    if not df.empty:
        riga_totale = {
            "UO": "TOTALE",
            "Nome": "Consolidato",
            "Ricavi": df["Ricavi"].sum(),
            "Sede (% piatta)": df["Sede (% piatta)"].sum(),
            "Sede (driver)": df["Sede (driver)"].sum(),
            "Differenza": df["Differenza"].sum(),
            "MOL-G (% piatta)": df["MOL-G (% piatta)"].sum(),
            "MOL-G (driver)": df["MOL-G (driver)"].sum(),
        }
        df = pd.concat([df, pd.DataFrame([riga_totale])], ignore_index=True)

    return df


def _colora_differenza(valore: float) -> str:
    """
    Restituisce il colore CSS per la cella di differenza
    nell'allocazione costi sede.

    Positivo = la UO paga di piu' col nuovo metodo (sfavorevole)
    Negativo = la UO paga di meno col nuovo metodo (favorevole)

    Parametri:
        valore: differenza tra metodo nuovo e metodo vecchio

    Ritorna:
        Stringa CSS con il colore di sfondo
    """
    if valore > 1000:
        return "background-color: #FFC7CE; color: #CC0000"
    elif valore < -1000:
        return "background-color: #C6EFCE; color: #006600"
    else:
        return "background-color: #FFEB9C; color: #9C5700"


def _prepara_dati_grafico_mol_sede(
    ce_industriale: dict,
    ce_gestionale: dict,
) -> pd.DataFrame:
    """
    Prepara i dati per il grafico a barre che confronta
    MOL-I, Costi Sede e MOL-G per ogni UO.

    Parametri:
        ce_industriale: dizionario CE Industriale per UO
        ce_gestionale: dizionario CE Gestionale per UO

    Ritorna:
        DataFrame con colonne [UO, MOL-I, Costi Sede, MOL-G]
    """
    righe = []
    for codice_uo in UO_OPERATIVE:
        if codice_uo not in ce_industriale or codice_uo not in ce_gestionale:
            continue

        ce_i = ce_industriale[codice_uo]
        ce_g = ce_gestionale[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        righe.append({
            "UO": f"{codice_uo}\n{nome_uo}",
            "MOL-I": ce_i["mol_industriale"],
            "Costi Sede": ce_g["costi_sede_allocati"],
            "MOL-G": ce_g["mol_gestionale"],
        })

    return pd.DataFrame(righe)


def _mostra_dettaglio_sede_per_uo(
    ce_gestionale: dict,
    allocazione: dict,
) -> None:
    """
    Mostra il dettaglio delle voci di costo sede allocate per ogni UO
    all'interno di un expander Streamlit.

    Parametri:
        ce_gestionale: dizionario CE Gestionale per UO
        allocazione: dizionario {codice_uo: {codice_sede: importo}}
    """
    for codice_uo in UO_OPERATIVE:
        if codice_uo not in ce_gestionale or codice_uo not in allocazione:
            continue

        ce_g = ce_gestionale[codice_uo]
        voci_sede = allocazione[codice_uo]
        nome_uo = UNITA_OPERATIVE[codice_uo].nome if codice_uo in UNITA_OPERATIVE else codice_uo

        st.markdown(f"#### {codice_uo} - {nome_uo}")

        # Metriche di sintesi UO
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            mostra_kpi_card(
                etichetta="MOL-I",
                valore=formatta_euro(ce_g["mol_industriale"]),
            )
        with col2:
            mostra_kpi_card(
                etichetta="Costi Sede",
                valore=formatta_euro(ce_g["costi_sede_allocati"]),
            )
        with col3:
            mostra_kpi_card(
                etichetta="MOL-G",
                valore=formatta_euro(ce_g["mol_gestionale"]),
            )
        with col4:
            livello = "VERDE" if ce_g["mol_gestionale_pct"] >= 0.08 else (
                "GIALLO" if ce_g["mol_gestionale_pct"] >= 0.0 else "ROSSO"
            )
            mostra_semaforo(
                etichetta="MOL-G %",
                valore=formatta_percentuale(ce_g["mol_gestionale_pct"]),
                livello=livello,
            )

        # Tabella voci sede
        if voci_sede:
            righe_voci = []
            for codice_voce, importo in sorted(voci_sede.items()):
                descrizione = VOCI_COSTI_SEDE.get(codice_voce, codice_voce)
                pct_su_sede = importo / ce_g["costi_sede_allocati"] if ce_g["costi_sede_allocati"] > 0 else 0.0
                righe_voci.append({
                    "Codice": codice_voce,
                    "Voce": descrizione,
                    "Importo": importo,
                    "% su Sede UO": pct_su_sede,
                })

            df_voci = pd.DataFrame(righe_voci)
            formato = {
                "Importo": lambda x: formatta_euro(x),
                "% su Sede UO": lambda x: formatta_percentuale(x),
            }
            st.dataframe(
                df_voci.style.format(formato),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("Nessuna voce sede allocata per questa UO.")

        st.divider()


def mostra_ce_gestionale(risultati: dict, dati: dict) -> None:
    """
    Pagina del Conto Economico Gestionale.

    Mostra:
    - Flusso MOL-I -> Costi Sede -> MOL-G con metriche di sintesi
    - Tabella CE Gestionale completa
    - Confronto metodo vecchio (% piatta 19.6%) vs metodo nuovo (driver)
    - Grafico a barre MOL-I vs Costi Sede vs MOL-G per UO
    - Expander con dettaglio voci sede allocate per ogni UO

    Parametri:
        risultati: dizionario con le chiavi:
            ce_industriale, ce_gestionale, kpi, allocazione,
            non_allocati, riepilogo_cat
        dati: dizionario con i DataFrame sorgente
    """
    # --- Estrazione dati ---
    ce_industriale = risultati.get("ce_industriale", {})
    ce_gestionale = risultati.get("ce_gestionale", {})
    allocazione = risultati.get("allocazione", {})
    non_allocati = risultati.get("non_allocati", 0.0)

    # --- Titolo ---
    st.title("Conto Economico Gestionale")
    st.markdown(
        "Il CE Gestionale parte dal **MOL Industriale** e sottrae i "
        "**costi di sede allocati** tramite driver specifici, ottenendo "
        "il **MOL Gestionale** che rappresenta la redditivita' netta "
        "della singola Unita' Operativa."
    )
    st.divider()

    # --- Flusso MOL-I -> Costi Sede -> MOL-G ---
    st.subheader("Flusso: dal MOL Industriale al MOL Gestionale")

    flusso = _costruisci_flusso_mol(ce_industriale, ce_gestionale)

    col_mol_i, col_freccia1, col_sede, col_freccia2, col_mol_g = st.columns(
        [3, 1, 3, 1, 3]
    )

    with col_mol_i:
        st.metric(
            label="MOL Industriale",
            value=formatta_euro(flusso["mol_i_totale"]),
            help=f"Margine: {formatta_percentuale(flusso['mol_i_pct'])}",
        )

    with col_freccia1:
        st.markdown(
            "<div style='text-align:center; padding-top:20px; font-size:28px;'>"
            " - </div>",
            unsafe_allow_html=True,
        )

    with col_sede:
        st.metric(
            label="Costi Sede Allocati",
            value=formatta_euro(flusso["costi_sede_totali"]),
            delta=f"-{formatta_percentuale(flusso['sede_pct'])} su ricavi",
            delta_color="inverse",
            help="Costi sede ribaltati sulle UO tramite driver",
        )

    with col_freccia2:
        st.markdown(
            "<div style='text-align:center; padding-top:20px; font-size:28px;'>"
            " = </div>",
            unsafe_allow_html=True,
        )

    with col_mol_g:
        colore_delta = "normal" if flusso["mol_g_pct"] >= 0.08 else "inverse"
        st.metric(
            label="MOL Gestionale",
            value=formatta_euro(flusso["mol_g_totale"]),
            help=f"Margine: {formatta_percentuale(flusso['mol_g_pct'])}",
        )

    if non_allocati > 0:
        st.info(
            f"Costi sede **non allocati** (Sviluppo + Storici): "
            f"**{formatta_euro(non_allocati)}** - "
            f"Questi costi restano a carico della holding e non impattano le singole UO."
        )

    st.divider()

    # --- Tabella CE Gestionale completa ---
    st.subheader("Tabella CE Gestionale")

    tabella_ce_gestionale(ce_industriale, ce_gestionale, allocazione)

    st.divider()

    # --- Confronto metodo vecchio vs nuovo ---
    st.subheader("Confronto: metodo a % piatta vs allocazione per driver")
    st.markdown(
        f"Il **metodo vecchio** ribaltava i costi sede come percentuale fissa "
        f"(**{formatta_percentuale(PERCENTUALE_RIBALTAMENTO_STORICA)}**) "
        f"sul fatturato di ogni UO. Il **metodo nuovo** utilizza driver specifici "
        f"(numero fatture, cedolini, acquisti, postazioni IT, posti letto, ricavi) "
        f"che riflettono il reale consumo di risorse centralizzate da parte di ciascuna struttura."
    )

    df_confronto = _costruisci_tabella_confronto_metodi(ce_industriale, ce_gestionale)
    if not df_confronto.empty:
        formato_confronto = {
            "Ricavi": lambda x: formatta_euro(x),
            "Sede (% piatta)": lambda x: formatta_euro(x),
            "Sede (driver)": lambda x: formatta_euro(x),
            "Differenza": lambda x: formatta_euro(x),
            "MOL-G (% piatta)": lambda x: formatta_euro(x),
            "MOL-G (driver)": lambda x: formatta_euro(x),
        }

        styler = df_confronto.style.format(formato_confronto)
        styler = styler.applymap(
            _colora_differenza,
            subset=["Differenza"],
        )

        st.dataframe(
            styler,
            use_container_width=True,
            hide_index=True,
            height=min(400, 50 + len(df_confronto) * 35),
        )

        # Nota esplicativa sulla differenza
        differenza_totale = df_confronto[df_confronto["UO"] != "TOTALE"]["Differenza"].sum()
        st.caption(
            "**Differenza positiva**: la UO paga di piu' col metodo driver "
            "(la UO consuma piu' risorse sede rispetto alla media). "
            "**Differenza negativa**: la UO paga di meno "
            "(la UO consumava meno risorse di quanto il fatturato suggerirebbe)."
        )
    else:
        st.warning("Nessun dato disponibile per il confronto dei metodi.")

    st.divider()

    # --- Grafico a barre MOL-I vs Costi Sede vs MOL-G ---
    st.subheader("MOL Industriale vs Costi Sede vs MOL Gestionale per UO")

    df_grafico = _prepara_dati_grafico_mol_sede(ce_industriale, ce_gestionale)
    if not df_grafico.empty:
        grafico_barre_confronto_uo(df_grafico)
    else:
        st.info("Nessun dato disponibile per il grafico.")

    st.divider()

    # --- Expander dettaglio voci sede per UO ---
    with st.expander("Dettaglio voci sede allocate per UO", expanded=False):
        _mostra_dettaglio_sede_per_uo(ce_gestionale, allocazione)
