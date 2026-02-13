"""
Pagina Simulazione Scenari.

Permette di simulare scenari what-if variando ricavi, costi personale,
costi acquisti, costi sede e posti letto, mostrando l'impatto sul
MOL Gestionale consolidato con confronto base vs scenario e waterfall.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from karol_cdg.config import (
    UNITA_OPERATIVE,
    UO_OPERATIVE,
)
from karol_cdg.webapp.componenti.tabelle import (
    formatta_euro,
    formatta_percentuale,
)


# ============================================================================
# COSTANTI COLORI (coerenti con componenti/grafici.py)
# ============================================================================

_BLU_SCURO = "#1F4E79"
_BLU = "#2E75B6"
_VERDE = "#9BBB59"
_ROSSO = "#C0504D"


# ============================================================================
# GRAFICO WATERFALL INLINE PER SCENARI
# ============================================================================


def _grafico_waterfall_scenari(
    etichette: list,
    valori: list,
    tipi: list,
    titolo: str,
) -> None:
    """
    Costruisce e visualizza un grafico waterfall personalizzato per
    la simulazione scenari, con barre di tipo base, delta e totale.

    A differenza di grafico_waterfall_ce (che mostra il passaggio
    Ricavi -> MOL-G per una singola UO), questa funzione accetta
    dati arbitrari e classifica ogni barra come 'base', 'delta' o 'totale'.

    Parametri:
        etichette: lista di etichette per l'asse x
        valori: lista di valori numerici corrispondenti
        tipi: lista di tipi barra ('base', 'delta', 'totale')
        titolo: titolo del grafico
    """
    # Converti tipi in measure per plotly waterfall:
    # 'base' e 'totale' -> 'total' (barra assoluta)
    # 'delta' -> 'relative' (barra incrementale)
    measure = []
    for tipo in tipi:
        if tipo == "delta":
            measure.append("relative")
        else:
            measure.append("total")

    fig = go.Figure(go.Waterfall(
        name="Scenario",
        orientation="v",
        measure=measure,
        x=etichette,
        y=valori,
        text=[f"\u20ac {v:,.0f}".replace(",", ".") for v in valori],
        textposition="outside",
        textfont=dict(size=11),
        connector=dict(line=dict(color="#B0B0B0", width=1, dash="dot")),
        increasing=dict(marker=dict(color=_VERDE)),
        decreasing=dict(marker=dict(color=_ROSSO)),
        totals=dict(marker=dict(color=_BLU)),
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
        yaxis=dict(
            title="Euro (\u20ac)",
            gridcolor="#E0E0E0",
            tickformat=",.0f",
        ),
        xaxis=dict(title=""),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


def mostra_scenari(risultati: dict, dati: dict):
    """
    Pagina di simulazione scenari what-if.

    Parametri:
        risultati: dizionario con i risultati dell'elaborazione completa
                   (ce_industriale, ce_gestionale, allocazione, kpi)
        dati: dizionario con i DataFrame sorgente
              (produzione, costi, costi_sede, driver, personale)
    """
    st.title("Simulazione Scenari")
    st.markdown(
        "Simula l'impatto di variazioni su ricavi, costi e struttura "
        "organizzativa sul MOL Gestionale consolidato del Gruppo."
    )
    st.markdown("---")

    # Recupera dati base
    ce_industriale = risultati.get("ce_industriale", {})
    ce_gestionale = risultati.get("ce_gestionale", {})

    if not ce_industriale or not ce_gestionale:
        st.warning(
            "Dati di base non disponibili. "
            "Eseguire prima l'elaborazione completa."
        )
        return

    # =========================================================================
    # CALCOLO VALORI BASE CONSOLIDATI
    # =========================================================================
    totale_ricavi_base = sum(
        ce_industriale[uo]["totale_ricavi"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_costi_personale_base = sum(
        ce_industriale[uo]["costi_personale"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_costi_acquisti_base = sum(
        ce_industriale[uo]["costi_acquisti"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_costi_servizi_base = sum(
        ce_industriale[uo]["costi_servizi"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_costi_ammort_base = sum(
        ce_industriale[uo]["costi_ammort"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_costi_sede_base = sum(
        ce_gestionale[uo]["costi_sede_allocati"] for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )
    totale_mol_i_base = sum(
        ce_industriale[uo]["mol_industriale"] for uo in UO_OPERATIVE
        if uo in ce_industriale
    )
    totale_mol_g_base = sum(
        ce_gestionale[uo]["mol_gestionale"] for uo in UO_OPERATIVE
        if uo in ce_gestionale
    )

    mol_g_pct_base = (
        totale_mol_g_base / totale_ricavi_base
        if totale_ricavi_base > 0 else 0
    )

    # =========================================================================
    # SLIDER DI INPUT (in area principale con colonne)
    # =========================================================================
    st.subheader("Leve di Simulazione")

    col_leva1, col_leva2 = st.columns(2)

    with col_leva1:
        variazione_ricavi_pct = st.slider(
            "Variazione ricavi %",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            format="%.1f%%",
            help="Variazione percentuale sui ricavi totali",
        )

        variazione_costi_personale_pct = st.slider(
            "Variazione costi personale %",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            format="%.1f%%",
            help="Variazione percentuale sui costi del personale",
        )

        variazione_costi_acquisti_pct = st.slider(
            "Variazione costi acquisti %",
            min_value=-20.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            format="%.1f%%",
            help="Variazione percentuale sui costi di acquisto",
        )

    with col_leva2:
        riduzione_costi_sede_pct = st.slider(
            "Riduzione costi sede %",
            min_value=-30.0,
            max_value=0.0,
            value=0.0,
            step=0.5,
            format="%.1f%%",
            help="Riduzione percentuale sui costi di sede allocati",
        )

        nuovi_posti_letto = st.slider(
            "Nuovi posti letto",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            help="Numero di nuovi posti letto (stima ricavo medio per PL)",
        )

    st.markdown("---")

    # =========================================================================
    # CALCOLO SCENARIO
    # =========================================================================
    calcola = st.button(
        "Calcola scenario",
        type="primary",
        use_container_width=True,
    )

    if calcola or any([
        variazione_ricavi_pct != 0,
        variazione_costi_personale_pct != 0,
        variazione_costi_acquisti_pct != 0,
        riduzione_costi_sede_pct != 0,
        nuovi_posti_letto > 0,
    ]):
        # Delta per ogni leva
        delta_ricavi = totale_ricavi_base * (variazione_ricavi_pct / 100)
        delta_costi_personale = totale_costi_personale_base * (
            variazione_costi_personale_pct / 100
        )
        delta_costi_acquisti = totale_costi_acquisti_base * (
            variazione_costi_acquisti_pct / 100
        )
        delta_costi_sede = totale_costi_sede_base * (
            riduzione_costi_sede_pct / 100
        )

        # Stima ricavo per nuovo PL: ricavo medio giornata * 365 * occupancy media
        ricavo_medio_per_pl = 0
        posti_letto_totali = sum(
            UNITA_OPERATIVE[uo].posti_letto for uo in UO_OPERATIVE
            if uo in UNITA_OPERATIVE and UNITA_OPERATIVE[uo].posti_letto > 0
        )
        if posti_letto_totali > 0:
            ricavo_medio_per_pl = totale_ricavi_base / posti_letto_totali
        else:
            # Fallback: stima basata su dati di riferimento
            ricavo_medio_per_pl = 100 * 365 * 0.85  # 100 euro/gg * 365 * 85%

        delta_ricavi_nuovi_pl = nuovi_posti_letto * ricavo_medio_per_pl * 0.85
        # Costi variabili nuovi PL: circa 70% del ricavo aggiuntivo
        delta_costi_nuovi_pl = delta_ricavi_nuovi_pl * 0.70

        # Valori scenario
        ricavi_scenario = totale_ricavi_base + delta_ricavi + delta_ricavi_nuovi_pl
        costi_personale_scenario = totale_costi_personale_base + delta_costi_personale
        costi_acquisti_scenario = totale_costi_acquisti_base + delta_costi_acquisti
        costi_sede_scenario = totale_costi_sede_base + delta_costi_sede

        # Costi totali scenario (servizi e ammortamenti invariati)
        costi_diretti_scenario = (
            costi_personale_scenario
            + costi_acquisti_scenario
            + totale_costi_servizi_base
            + totale_costi_ammort_base
            + delta_costi_nuovi_pl
        )

        mol_i_scenario = ricavi_scenario - costi_diretti_scenario
        mol_g_scenario = mol_i_scenario - costi_sede_scenario

        mol_g_pct_scenario = (
            mol_g_scenario / ricavi_scenario if ricavi_scenario > 0 else 0
        )

        delta_mol_g = mol_g_scenario - totale_mol_g_base

        # =====================================================================
        # MESSAGGI DI AVVISO PER SCENARI ESTREMI
        # =====================================================================
        if abs(variazione_ricavi_pct) >= 15:
            st.warning(
                f"Attenzione: variazione ricavi del {variazione_ricavi_pct:+.1f}% "
                "e' uno scenario estremo. Verificare la fattibilita' commerciale."
            )

        if variazione_costi_personale_pct <= -15:
            st.warning(
                f"Attenzione: riduzione costi personale del "
                f"{variazione_costi_personale_pct:.1f}% e' molto aggressiva. "
                "Valutare impatto su qualita' assistenziale e normativa."
            )

        if riduzione_costi_sede_pct <= -20:
            st.warning(
                f"Attenzione: riduzione costi sede del "
                f"{riduzione_costi_sede_pct:.1f}% richiede una ristrutturazione "
                "organizzativa profonda. Valutare tempi e fattibilita'."
            )

        if nuovi_posti_letto >= 50:
            st.warning(
                f"Attenzione: l'aggiunta di {nuovi_posti_letto} nuovi posti letto "
                "richiede investimenti significativi e tempi di autorizzazione. "
                "Le stime sono indicative."
            )

        # =====================================================================
        # METRICHE DELTA
        # =====================================================================
        st.subheader("Risultati Scenario")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.metric(
                label="Ricavi Scenario",
                value=formatta_euro(ricavi_scenario),
                delta=formatta_euro(ricavi_scenario - totale_ricavi_base),
            )

        with col_m2:
            st.metric(
                label="MOL Industriale",
                value=formatta_euro(mol_i_scenario),
                delta=formatta_euro(mol_i_scenario - totale_mol_i_base),
            )

        with col_m3:
            st.metric(
                label="MOL Gestionale",
                value=formatta_euro(mol_g_scenario),
                delta=formatta_euro(delta_mol_g),
            )

        with col_m4:
            st.metric(
                label="MOL-G %",
                value=formatta_percentuale(mol_g_pct_scenario),
                delta=formatta_percentuale(mol_g_pct_scenario - mol_g_pct_base),
            )

        st.markdown("---")

        # =====================================================================
        # TABELLA CONFRONTO BASE VS SCENARIO
        # =====================================================================
        st.subheader("Confronto Base vs Scenario")

        dati_confronto = pd.DataFrame({
            "Voce": [
                "Ricavi totali",
                "Costi personale",
                "Costi acquisti",
                "Costi servizi",
                "Ammortamenti",
                "Costi nuovi PL",
                "MOL Industriale",
                "Costi sede allocati",
                "MOL Gestionale",
                "MOL Gestionale %",
            ],
            "Base": [
                totale_ricavi_base,
                totale_costi_personale_base,
                totale_costi_acquisti_base,
                totale_costi_servizi_base,
                totale_costi_ammort_base,
                0,
                totale_mol_i_base,
                totale_costi_sede_base,
                totale_mol_g_base,
                mol_g_pct_base,
            ],
            "Scenario": [
                ricavi_scenario,
                costi_personale_scenario,
                costi_acquisti_scenario,
                totale_costi_servizi_base,
                totale_costi_ammort_base,
                delta_costi_nuovi_pl,
                mol_i_scenario,
                costi_sede_scenario,
                mol_g_scenario,
                mol_g_pct_scenario,
            ],
            "Delta": [
                ricavi_scenario - totale_ricavi_base,
                delta_costi_personale,
                delta_costi_acquisti,
                0,
                0,
                delta_costi_nuovi_pl,
                mol_i_scenario - totale_mol_i_base,
                delta_costi_sede,
                delta_mol_g,
                mol_g_pct_scenario - mol_g_pct_base,
            ],
        })

        # Formattazione della tabella
        def _formatta_riga(riga):
            """Formatta una riga della tabella confronto."""
            if riga["Voce"] == "MOL Gestionale %":
                return pd.Series({
                    "Voce": riga["Voce"],
                    "Base": formatta_percentuale(riga["Base"]),
                    "Scenario": formatta_percentuale(riga["Scenario"]),
                    "Delta": formatta_percentuale(riga["Delta"]),
                })
            return pd.Series({
                "Voce": riga["Voce"],
                "Base": formatta_euro(riga["Base"]),
                "Scenario": formatta_euro(riga["Scenario"]),
                "Delta": formatta_euro(riga["Delta"]),
            })

        df_formattato = dati_confronto.apply(_formatta_riga, axis=1)
        st.dataframe(df_formattato, use_container_width=True, hide_index=True)

        st.markdown("---")

        # =====================================================================
        # WATERFALL: IMPATTO DI OGNI LEVA SUL MOL-G
        # =====================================================================
        st.subheader("Impatto per Leva sul MOL-G Consolidato")

        # Prepara dati waterfall
        etichette_waterfall = []
        valori_waterfall = []
        tipi_waterfall = []  # 'base', 'delta', 'totale'

        # Barra iniziale: MOL-G base
        etichette_waterfall.append("MOL-G Base")
        valori_waterfall.append(totale_mol_g_base)
        tipi_waterfall.append("base")

        # Leva: Variazione ricavi
        if delta_ricavi != 0:
            etichette_waterfall.append("Variazione ricavi")
            valori_waterfall.append(delta_ricavi)
            tipi_waterfall.append("delta")

        # Leva: Variazione costi personale (segno invertito: aumento costi = riduzione MOL)
        if delta_costi_personale != 0:
            etichette_waterfall.append("Var. costi personale")
            valori_waterfall.append(-delta_costi_personale)
            tipi_waterfall.append("delta")

        # Leva: Variazione costi acquisti
        if delta_costi_acquisti != 0:
            etichette_waterfall.append("Var. costi acquisti")
            valori_waterfall.append(-delta_costi_acquisti)
            tipi_waterfall.append("delta")

        # Leva: Riduzione costi sede
        if delta_costi_sede != 0:
            etichette_waterfall.append("Riduzione costi sede")
            valori_waterfall.append(-delta_costi_sede)
            tipi_waterfall.append("delta")

        # Leva: Nuovi posti letto (margine netto)
        if nuovi_posti_letto > 0:
            margine_nuovi_pl = delta_ricavi_nuovi_pl - delta_costi_nuovi_pl
            etichette_waterfall.append("Nuovi posti letto")
            valori_waterfall.append(margine_nuovi_pl)
            tipi_waterfall.append("delta")

        # Barra finale: MOL-G scenario
        etichette_waterfall.append("MOL-G Scenario")
        valori_waterfall.append(mol_g_scenario)
        tipi_waterfall.append("totale")

        _grafico_waterfall_scenari(
            etichette=etichette_waterfall,
            valori=valori_waterfall,
            tipi=tipi_waterfall,
            titolo="Waterfall: impatto leve su MOL-G consolidato",
        )

        st.markdown("---")

        # =====================================================================
        # DETTAGLIO IMPATTO PER UO
        # =====================================================================
        with st.expander("Dettaglio impatto per UO", expanded=False):
            st.markdown(
                "L'impatto delle leve e' distribuito proporzionalmente "
                "sulle UO in base ai pesi attuali."
            )

            righe_dettaglio = []
            for codice_uo in UO_OPERATIVE:
                if codice_uo not in ce_industriale or codice_uo not in ce_gestionale:
                    continue

                ce_i = ce_industriale[codice_uo]
                ce_g = ce_gestionale[codice_uo]
                nome = (
                    UNITA_OPERATIVE[codice_uo].nome
                    if codice_uo in UNITA_OPERATIVE else codice_uo
                )

                # Proporziona variazioni in base al peso della UO
                peso_ricavi = (
                    ce_i["totale_ricavi"] / totale_ricavi_base
                    if totale_ricavi_base > 0 else 0
                )

                delta_mol_uo = delta_mol_g * peso_ricavi
                mol_g_uo_scenario = ce_g["mol_gestionale"] + delta_mol_uo

                righe_dettaglio.append({
                    "UO": codice_uo,
                    "Nome": nome,
                    "MOL-G Base": formatta_euro(ce_g["mol_gestionale"]),
                    "Delta Stimato": formatta_euro(delta_mol_uo),
                    "MOL-G Scenario": formatta_euro(mol_g_uo_scenario),
                })

            if righe_dettaglio:
                df_dettaglio = pd.DataFrame(righe_dettaglio)
                st.dataframe(
                    df_dettaglio,
                    use_container_width=True,
                    hide_index=True,
                )

    else:
        st.info(
            "Modifica i parametri sopra e premi 'Calcola scenario' "
            "per visualizzare i risultati."
        )
