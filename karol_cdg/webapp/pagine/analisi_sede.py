"""
Pagina Analisi Costi Sede.

Mostra l'analisi dettagliata dei costi di sede (~2.5M), la ripartizione
per categoria, l'allocazione per UO tramite driver, il confronto tra
il vecchio metodo (ribaltamento a % su fatturato) e il nuovo metodo
(allocazione per driver) e il dettaglio dei driver utilizzati.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from karol_cdg.config import (
    UNITA_OPERATIVE,
    UO_OPERATIVE,
    VOCI_COSTI_SEDE,
    RICAVI_RIFERIMENTO,
    DRIVER_PREDEFINITI,
    CategoriaCostoSede,
)
from karol_cdg.webapp.componenti.grafici import (
    grafico_torta_sede,
)
from karol_cdg.webapp.componenti.tabelle import (
    formatta_euro,
    formatta_percentuale,
)
from karol_cdg.webapp.componenti.metriche import (
    mostra_kpi_card,
)


# ============================================================================
# COSTANTI COLORI (coerenti con componenti/grafici.py)
# ============================================================================

_BLU_SCURO = "#1F4E79"
_BLU = "#2E75B6"
_VERDE = "#9BBB59"
_ROSSO = "#C0504D"


# ============================================================================
# GRAFICI INLINE PER ANALISI SEDE
# ============================================================================


def _grafico_barre_allocazione(
    etichette: list,
    valori: list,
    titolo: str,
    etichetta_y: str = "Euro",
) -> None:
    """
    Grafico a barre verticali per l'allocazione dei costi sede per UO.

    Parametri:
        etichette: lista di etichette asse x (codice + nome UO)
        valori: lista di importi in euro
        titolo: titolo del grafico
        etichetta_y: etichetta dell'asse y
    """
    fig = go.Figure(go.Bar(
        x=etichette,
        y=valori,
        marker_color=_BLU,
        text=[f"\u20ac {v:,.0f}".replace(",", ".") for v in valori],
        textposition="outside",
        textfont=dict(size=10),
    ))

    fig.update_layout(
        title=dict(
            text=titolo,
            font=dict(size=16, color=_BLU_SCURO),
            x=0.5,
        ),
        height=500,
        font=dict(family="Segoe UI, sans-serif", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=40, t=60, b=80),
        yaxis=dict(
            title=etichetta_y,
            gridcolor="#E0E0E0",
            tickformat=",.0f",
        ),
        xaxis=dict(tickangle=-30),
    )

    st.plotly_chart(fig, use_container_width=True)


def _grafico_barre_confronto_metodi(
    etichette: list,
    valori_gruppo_1: list,
    valori_gruppo_2: list,
    nome_gruppo_1: str,
    nome_gruppo_2: str,
    titolo: str,
) -> None:
    """
    Grafico a barre raggruppate per confrontare il vecchio metodo
    di allocazione costi sede (% piatta) con il nuovo metodo (driver).

    Parametri:
        etichette: lista di codici UO
        valori_gruppo_1: valori del primo gruppo (vecchio metodo)
        valori_gruppo_2: valori del secondo gruppo (nuovo metodo)
        nome_gruppo_1: etichetta legenda primo gruppo
        nome_gruppo_2: etichetta legenda secondo gruppo
        titolo: titolo del grafico
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name=nome_gruppo_1,
        x=etichette,
        y=valori_gruppo_1,
        marker_color=_VERDE,
        text=[f"\u20ac {v:,.0f}".replace(",", ".") for v in valori_gruppo_1],
        textposition="outside",
        textfont=dict(size=9),
    ))

    fig.add_trace(go.Bar(
        name=nome_gruppo_2,
        x=etichette,
        y=valori_gruppo_2,
        marker_color=_BLU,
        text=[f"\u20ac {v:,.0f}".replace(",", ".") for v in valori_gruppo_2],
        textposition="outside",
        textfont=dict(size=9),
    ))

    fig.update_layout(
        title=dict(
            text=titolo,
            font=dict(size=16, color=_BLU_SCURO),
            x=0.5,
        ),
        height=500,
        font=dict(family="Segoe UI, sans-serif", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=40, t=60, b=60),
        barmode="group",
        yaxis=dict(
            title="Euro (\u20ac)",
            gridcolor="#E0E0E0",
            tickformat=",.0f",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


def mostra_analisi_sede(risultati: dict, dati: dict):
    """
    Pagina di analisi dei costi di sede.

    Parametri:
        risultati: dizionario con i risultati dell'elaborazione completa
                   (ce_industriale, ce_gestionale, allocazione, kpi)
        dati: dizionario con i DataFrame sorgente
              (produzione, costi, costi_sede, driver, personale)
    """
    st.title("Analisi Costi Sede")
    st.markdown("---")

    # Recupera dati necessari
    ce_industriale = risultati.get("ce_industriale", {})
    ce_gestionale = risultati.get("ce_gestionale", {})
    allocazione = risultati.get("allocazione", {})
    riepilogo_cat = risultati.get("riepilogo_cat", {})
    non_allocati = risultati.get("non_allocati", 0)

    if not ce_gestionale:
        st.warning(
            "Dati non disponibili. Eseguire prima l'elaborazione completa."
        )
        return

    # Calcolo aggregati
    totale_ricavi = sum(
        ce_industriale[uo]["totale_ricavi"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_sede_allocati = sum(
        ce_gestionale[uo]["costi_sede_allocati"] for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )
    totale_sede = totale_sede_allocati + non_allocati
    pct_sede_su_ricavi = totale_sede / totale_ricavi if totale_ricavi > 0 else 0

    # =========================================================================
    # METRICHE PRINCIPALI
    # =========================================================================
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        mostra_kpi_card(
            col_m1,
            "Totale Sede",
            totale_sede,
            formato="euro",
        )

    with col_m2:
        mostra_kpi_card(
            col_m2,
            "% su Ricavi",
            pct_sede_su_ricavi,
            formato="percentuale",
        )

    with col_m3:
        mostra_kpi_card(
            col_m3,
            "Allocati",
            totale_sede_allocati,
            formato="euro",
        )

    with col_m4:
        mostra_kpi_card(
            col_m4,
            "Non Allocati",
            non_allocati,
            formato="euro",
        )

    st.markdown("---")

    # =========================================================================
    # GRAFICO TORTA PER CATEGORIA
    # =========================================================================
    st.subheader("Ripartizione per Categoria")

    if riepilogo_cat:
        col_torta, col_dettaglio = st.columns([3, 2])

        with col_torta:
            fig_torta = grafico_torta_sede(riepilogo_cat)
            st.plotly_chart(fig_torta, use_container_width=True)

        with col_dettaglio:
            st.markdown("**Dettaglio per categoria:**")
            for categoria, importo in riepilogo_cat.items():
                pct_su_sede = importo / totale_sede if totale_sede > 0 else 0
                pct_su_ricavi = importo / totale_ricavi if totale_ricavi > 0 else 0
                st.markdown(
                    f"- **{categoria}**: {formatta_euro(importo)} "
                    f"({formatta_percentuale(pct_su_sede)} della sede, "
                    f"{formatta_percentuale(pct_su_ricavi)} dei ricavi)"
                )
    else:
        st.info("Dati di riepilogo per categoria non disponibili.")

    st.markdown("---")

    # =========================================================================
    # GRAFICO BARRE: ALLOCAZIONE PER UO
    # =========================================================================
    st.subheader("Allocazione Costi Sede per UO")

    etichette_uo = []
    valori_allocazione_uo = []

    for codice_uo in UO_OPERATIVE:
        if codice_uo not in ce_gestionale:
            continue

        nome_uo = (
            UNITA_OPERATIVE[codice_uo].nome
            if codice_uo in UNITA_OPERATIVE else codice_uo
        )
        costi_sede_uo = ce_gestionale[codice_uo]["costi_sede_allocati"]
        etichette_uo.append(f"{codice_uo}\n{nome_uo}")
        valori_allocazione_uo.append(costi_sede_uo)

    if etichette_uo:
        _grafico_barre_allocazione(
            etichette=etichette_uo,
            valori=valori_allocazione_uo,
            titolo="Costi Sede Allocati per Unita' Operativa",
            etichetta_y="Euro",
        )

    st.markdown("---")

    # =========================================================================
    # TABELLA DETTAGLIO VOCI COSTI SEDE
    # =========================================================================
    st.subheader("Dettaglio Voci Costi Sede")

    df_sede = dati.get("costi_sede")

    if df_sede is not None and not df_sede.empty:
        # Costruisci tabella dettagliata
        righe_dettaglio = []

        for _, riga in df_sede.iterrows():
            codice = str(riga.iloc[0]) if pd.notna(riga.iloc[0]) else ""
            descrizione = str(riga.iloc[1]) if pd.notna(riga.iloc[1]) else ""
            importo = float(riga.iloc[2]) if pd.notna(riga.iloc[2]) else 0
            categoria = str(riga.iloc[3]) if pd.notna(riga.iloc[3]) else ""
            # Colonna 4: sotto_categoria (potrebbe non esserci)
            driver = str(riga.iloc[5]) if len(riga) > 5 and pd.notna(riga.iloc[5]) else ""

            if importo <= 0:
                continue

            righe_dettaglio.append({
                "Codice": codice,
                "Descrizione": descrizione,
                "Categoria": categoria,
                "Driver": driver,
                "Importo": importo,
            })

        if righe_dettaglio:
            df_dettaglio = pd.DataFrame(righe_dettaglio)

            # Formattazione importo
            df_display = df_dettaglio.copy()
            df_display["Importo"] = df_display["Importo"].apply(formatta_euro)

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
            )

            # Totale
            totale_voci = sum(r["Importo"] for r in righe_dettaglio)
            st.markdown(f"**Totale voci: {formatta_euro(totale_voci)}**")
        else:
            st.info("Nessuna voce di costo sede con importo positivo.")
    else:
        st.info(
            "DataFrame costi sede non disponibile. "
            "Verificare il caricamento dei dati."
        )

    st.markdown("---")

    # =========================================================================
    # CONFRONTO: VECCHIO METODO VS NUOVO METODO
    # =========================================================================
    st.subheader("Confronto: Vecchio Metodo vs Nuovo Metodo")

    st.markdown(
        """
        **Vecchio metodo**: ribaltamento a percentuale fissa (19.6%) sul
        fatturato di ogni UO.

        **Nuovo metodo**: allocazione basata su driver specifici (numero
        fatture, cedolini, posti letto, ricavi, ecc.) che riflette il
        reale assorbimento di risorse di sede da parte di ogni UO.
        """
    )

    pct_vecchio_metodo = RICAVI_RIFERIMENTO.get("pct_costi_sede_su_ricavi", 0.196)

    righe_confronto = []
    for codice_uo in UO_OPERATIVE:
        if codice_uo not in ce_industriale or codice_uo not in ce_gestionale:
            continue

        nome_uo = (
            UNITA_OPERATIVE[codice_uo].nome
            if codice_uo in UNITA_OPERATIVE else codice_uo
        )
        ricavi_uo = ce_industriale[codice_uo]["totale_ricavi"]
        costi_sede_nuovo = ce_gestionale[codice_uo]["costi_sede_allocati"]

        # Vecchio metodo: % fissa su ricavi UO
        costi_sede_vecchio = ricavi_uo * pct_vecchio_metodo

        delta = costi_sede_nuovo - costi_sede_vecchio
        effetto = "Paga di piu'" if delta > 0 else "Paga di meno"

        righe_confronto.append({
            "UO": codice_uo,
            "Nome": nome_uo,
            "Ricavi": ricavi_uo,
            "Vecchio Metodo (19.6%)": costi_sede_vecchio,
            "Nuovo Metodo (driver)": costi_sede_nuovo,
            "Delta": delta,
            "Effetto": effetto,
        })

    if righe_confronto:
        df_confronto = pd.DataFrame(righe_confronto)

        # Formattazione colonne euro
        df_confronto_display = df_confronto.copy()
        for colonna in ["Ricavi", "Vecchio Metodo (19.6%)", "Nuovo Metodo (driver)", "Delta"]:
            df_confronto_display[colonna] = df_confronto_display[colonna].apply(
                formatta_euro
            )

        st.dataframe(
            df_confronto_display,
            use_container_width=True,
            hide_index=True,
        )

        # Grafico confronto vecchio vs nuovo
        etichette_confronto = [r["UO"] for r in righe_confronto]
        valori_vecchio = [r["Vecchio Metodo (19.6%)"] for r in righe_confronto]
        valori_nuovo = [r["Nuovo Metodo (driver)"] for r in righe_confronto]

        _grafico_barre_confronto_metodi(
            etichette=etichette_confronto,
            valori_gruppo_1=valori_vecchio,
            valori_gruppo_2=valori_nuovo,
            nome_gruppo_1="Vecchio metodo (19.6%)",
            nome_gruppo_2="Nuovo metodo (driver)",
            titolo="Confronto allocazione costi sede per UO",
        )

        # Riepilogo chi paga di piu'/meno
        st.markdown("---")
        st.markdown("**Chi paga di piu' e chi paga di meno con il nuovo metodo:**")

        col_paga_piu, col_paga_meno = st.columns(2)

        with col_paga_piu:
            st.markdown("**Pagano di piu':**")
            for riga in sorted(righe_confronto, key=lambda x: x["Delta"], reverse=True):
                if riga["Delta"] > 0:
                    st.markdown(
                        f"- {riga['UO']} ({riga['Nome']}): "
                        f"+{formatta_euro(riga['Delta'])}"
                    )

        with col_paga_meno:
            st.markdown("**Pagano di meno:**")
            for riga in sorted(righe_confronto, key=lambda x: x["Delta"]):
                if riga["Delta"] < 0:
                    st.markdown(
                        f"- {riga['UO']} ({riga['Nome']}): "
                        f"{formatta_euro(riga['Delta'])}"
                    )

    st.markdown("---")

    # =========================================================================
    # EXPANDER: DETTAGLIO DRIVER DI ALLOCAZIONE
    # =========================================================================
    with st.expander("Dettaglio driver di allocazione", expanded=False):
        st.markdown("### Driver utilizzati per l'allocazione dei costi sede")
        st.markdown(
            "Ogni voce di costo sede viene allocata alle UO in base a "
            "un driver specifico che riflette il consumo effettivo della "
            "risorsa centralizzata."
        )

        righe_driver = []
        for codice_sede, descrizione in VOCI_COSTI_SEDE.items():
            driver = DRIVER_PREDEFINITI.get(codice_sede)
            driver_nome = driver.value if driver else "Non definito"

            # Categoria della voce
            if codice_sede.startswith("CS0"):
                categoria = CategoriaCostoSede.SERVIZI.value
            elif codice_sede.startswith("CS1"):
                categoria = CategoriaCostoSede.GOVERNANCE.value
            elif codice_sede.startswith("CS2"):
                categoria = CategoriaCostoSede.DA_CLASSIFICARE.value
            else:
                categoria = "Altro"

            righe_driver.append({
                "Codice": codice_sede,
                "Voce di Costo": descrizione,
                "Categoria": categoria,
                "Driver": driver_nome,
            })

        if righe_driver:
            df_driver = pd.DataFrame(righe_driver)
            st.dataframe(df_driver, use_container_width=True, hide_index=True)

        st.markdown("### Logica dei driver")
        st.markdown(
            """
            - **Numero fatture**: le UO che generano piu' fatture assorbono
              piu' costi di contabilita'
            - **Numero cedolini**: le UO con piu' dipendenti assorbono piu'
              costi di elaborazione paghe
            - **Euro acquistato**: le UO con piu' acquisti assorbono piu'
              costi dell'ufficio acquisti
            - **Posti letto**: le UO piu' grandi assorbono piu' costi di
              qualita'/compliance
            - **Ricavi**: allocazione proporzionale al peso economico della UO
            - **Numero postazioni IT**: le UO con piu' postazioni informatiche
              assorbono piu' costi IT
            - **Quota fissa**: ripartizione in parti uguali tra le UO
              (es. costi legali)
            - **Non allocabile**: costi non ribaltabili (sviluppo, storici)
              che restano a livello di gruppo
            """
        )

        st.markdown("### Nota metodologica")
        st.markdown(
            "Il passaggio dal vecchio metodo (ribaltamento a % fissa del 19.6% "
            "sul fatturato) al nuovo metodo (driver-based allocation) permette "
            "di rappresentare piu' fedelmente il costo reale di ogni UO, "
            "evitando che strutture ad alto fatturato ma basso assorbimento "
            "di servizi centralizzati vengano penalizzate ingiustamente."
        )
