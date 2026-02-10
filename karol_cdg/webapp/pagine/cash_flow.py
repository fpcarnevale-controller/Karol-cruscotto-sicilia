"""
Pagina Cash Flow & Gestione Liquidita' della dashboard Karol CDG.

Modulo Advanced Financial Forecasting & Liquidity Management.

Sezioni:
    1. Header e KPI sintetici (Cassa, Burn Rate, Runway, DSCR)
    2. Waterfall Chart della Liquidita'
    3. Burn Rate & Runway multi-scenario
    4. Heatmap delle Scadenze
    5. Sensitivity Analysis con slider interattivo
    6. Pannello Alert Intelligente
    7. Piano CAPEX
"""

import streamlit as st
import pandas as pd
from datetime import date

from karol_cdg.config import (
    CASH_FLOW_CONFIG,
    EXCEL_MASTER,
    MESI_IT,
    SCENARI_CASH_FLOW,
)
from karol_cdg.core.cash_flow import (
    calcola_burn_rate,
    calcola_cash_flow_diretto_mensile,
    calcola_cash_flow_diretto_settimanale,
    calcola_dscr_prospettico,
    classifica_scadenze_priorita,
    genera_alert_cassa,
    genera_scadenze_fiscali,
    stima_payroll_mensile,
    _converti_scadenzario_df,
)
from karol_cdg.webapp.componenti.grafici import (
    crea_grafico_burn_rate,
    crea_grafico_capex,
    crea_grafico_dscr,
    crea_heatmap_scadenze,
    crea_waterfall_liquidita,
)
from karol_cdg.webapp.componenti.tabelle import formatta_euro


def _formatta_euro_cf(valore: float) -> str:
    """Formattazione euro per la pagina cash flow."""
    if abs(valore) >= 1_000_000:
        return f"EUR {valore / 1_000_000:,.1f}M".replace(",", ".")
    elif abs(valore) >= 1_000:
        return f"EUR {valore:,.0f}".replace(",", ".")
    return f"EUR {valore:,.0f}".replace(",", ".")


def mostra_cash_flow(risultati: dict, dati: dict):
    """
    Entry point della pagina Cash Flow & Gestione Liquidita'.

    Parametri:
        risultati: dizionario con i risultati dell'elaborazione
        dati: dizionario con i DataFrame sorgente dal Master Excel
    """
    st.title("Cash Flow & Gestione Liquidita'")
    st.markdown(
        "Analisi avanzata dei flussi di cassa, proiezioni multi-scenario "
        "e gestione della liquidita' aziendale."
    )

    # ------------------------------------------------------------------
    # Preparazione dati
    # ------------------------------------------------------------------

    oggi = date.today()
    mese_corrente = oggi.month
    anno_corrente = oggi.year

    # Leggi dati dal dizionario sorgente
    scadenzario_df = dati.get("Scadenzario", pd.DataFrame()) if dati else pd.DataFrame()
    costi_mensili_df = dati.get("Costi_Mensili", pd.DataFrame()) if dati else pd.DataFrame()
    anagrafiche_pers_df = dati.get("Anagrafiche_Personale", pd.DataFrame()) if dati else pd.DataFrame()

    # Verifica dati scadenzario
    colonne_attese_scad = ["Data Scadenza", "Tipo (Incasso/Pagamento)", "Importo"]
    scadenzario_valido = (
        not scadenzario_df.empty
        and all(c in scadenzario_df.columns for c in colonne_attese_scad)
        and len(scadenzario_df.dropna(subset=["Data Scadenza"])) > 0
    )

    if not scadenzario_valido:
        st.warning(
            "Il foglio **Scadenzario** nel Master Excel e' vuoto o non ha le "
            "colonne attese. I calcoli utilizzeranno stime basate sui parametri "
            "di default. Per risultati accurati, popolare il foglio Scadenzario."
        )

    # Parametri da config
    cassa_iniziale = CASH_FLOW_CONFIG["cassa_iniziale_default"]
    soglia_hard = CASH_FLOW_CONFIG["soglia_hard_alert"]
    dscr_warning = CASH_FLOW_CONFIG["dscr_warning"]
    dscr_critico = CASH_FLOW_CONFIG["dscr_critico"]
    servizio_debito = CASH_FLOW_CONFIG["servizio_debito_annuale"]
    capex_piano = CASH_FLOW_CONFIG["capex_piano_industriale"]

    # ------------------------------------------------------------------
    # Sidebar - Parametri Cash Flow
    # ------------------------------------------------------------------

    with st.sidebar:
        st.markdown("---")
        st.markdown("### Parametri Cash Flow")
        ritardo_incassi = st.slider(
            "Ritardo incassi (giorni)",
            min_value=0, max_value=90, value=0, step=15,
            help="Simula un ritardo negli incassi per analisi di sensitivity",
        )
        cassa_input = st.number_input(
            "Cassa iniziale (EUR)",
            min_value=0, max_value=5_000_000, value=cassa_iniziale, step=50_000,
            help="Saldo di cassa iniziale per le proiezioni",
        )
        cassa_iniziale = cassa_input

    # ------------------------------------------------------------------
    # Calcoli backend
    # ------------------------------------------------------------------

    payroll = stima_payroll_mensile(anagrafiche_pers_df, mese_corrente, anno_corrente)
    scadenze_fiscali = genera_scadenze_fiscali(anno_corrente)
    scadenze_fiscali += genera_scadenze_fiscali(anno_corrente + 1)

    cf_settimanale = calcola_cash_flow_diretto_settimanale(
        scadenzario_df=scadenzario_df, payroll=payroll,
        scadenze_fiscali=scadenze_fiscali, cassa_iniziale=cassa_iniziale,
        costi_mensili_df=costi_mensili_df, settimane=12,
        ritardo_incassi_giorni=ritardo_incassi,
    )

    cf_mensile = calcola_cash_flow_diretto_mensile(
        scadenzario_df=scadenzario_df, payroll=payroll,
        scadenze_fiscali=scadenze_fiscali, cassa_iniziale=cassa_iniziale,
        costi_mensili_df=costi_mensili_df, mesi=24,
        ritardo_incassi_giorni=ritardo_incassi,
    )

    cf_con_dscr = calcola_dscr_prospettico(cf_mensile, servizio_debito)
    burn_info = calcola_burn_rate(cassa_iniziale, cf_mensile)

    tutte_voci = _converti_scadenzario_df(scadenzario_df) + scadenze_fiscali
    df_priorita = classifica_scadenze_priorita(tutte_voci)
    alert_list = genera_alert_cassa(cf_settimanale)

    # ------------------------------------------------------------------
    # Calcoli multi-scenario
    # ------------------------------------------------------------------

    df_scenari = cf_mensile[["periodo", "mese_anno", "cassa_finale"]].copy()
    df_scenari = df_scenari.rename(columns={"cassa_finale": "cassa_base"})

    cf_worst = calcola_cash_flow_diretto_mensile(
        scadenzario_df=scadenzario_df,
        payroll={
            "stipendi_lordi": payroll["stipendi_lordi"] * 1.05,
            "oneri_contributivi": payroll["oneri_contributivi"] * 1.05,
            "totale_payroll": payroll["totale_payroll"] * 1.05,
        },
        scadenze_fiscali=scadenze_fiscali, cassa_iniziale=cassa_iniziale,
        costi_mensili_df=costi_mensili_df, mesi=24,
        ritardo_incassi_giorni=ritardo_incassi + 30,
    )
    df_scenari["cassa_worst"] = cf_worst["cassa_finale"].values

    cf_best = calcola_cash_flow_diretto_mensile(
        scadenzario_df=scadenzario_df, payroll=payroll,
        scadenze_fiscali=scadenze_fiscali, cassa_iniziale=cassa_iniziale,
        costi_mensili_df=costi_mensili_df, mesi=24,
        ritardo_incassi_giorni=max(0, ritardo_incassi - 15),
    )
    df_scenari["cassa_best"] = cf_best["cassa_finale"].values

    # ------------------------------------------------------------------
    # 1. Header e KPI sintetici
    # ------------------------------------------------------------------

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    cassa_finale_sett = cf_settimanale["cassa_finale"].iloc[-1] if not cf_settimanale.empty else cassa_iniziale
    delta_cassa = cassa_finale_sett - cassa_iniziale

    with col1:
        colore = "normal" if delta_cassa >= 0 else "inverse"
        st.metric("Cassa Attuale", _formatta_euro_cf(cassa_iniziale),
                  delta=f"{_formatta_euro_cf(delta_cassa)} (12 sett.)", delta_color=colore)

    with col2:
        burn = burn_info["burn_rate_mensile"]
        st.metric("Burn Rate Mensile", _formatta_euro_cf(abs(burn)),
                  delta="genera cassa" if burn < 0 else "consumo netto",
                  delta_color="normal" if burn < 0 else "inverse")

    with col3:
        runway = burn_info["runway_mesi"]
        runway_str = f"{runway:.1f} mesi" if runway != float("inf") else "infinito"
        st.metric("Runway", runway_str)

    with col4:
        dscr_medio = cf_con_dscr["dscr"].mean() if not cf_con_dscr.empty else 0
        st.metric("DSCR Medio", f"{dscr_medio:.2f}",
                  delta="adeguato" if dscr_medio >= dscr_warning else "sotto soglia",
                  delta_color="normal" if dscr_medio >= dscr_warning else "inverse")

    # ------------------------------------------------------------------
    # 2. Waterfall Chart della Liquidita'
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Waterfall della Liquidita' (prossime 12 settimane)")

    if not cf_settimanale.empty:
        dati_waterfall = {
            "cassa_iniziale": cassa_iniziale,
            "incassi_operativi": cf_settimanale["incassi_operativi"].sum(),
            "uscite_personale": cf_settimanale["uscite_personale"].sum(),
            "uscite_fornitori": cf_settimanale["uscite_fornitori"].sum(),
            "uscite_fiscali": cf_settimanale["uscite_fiscali"].sum(),
            "uscite_investimenti": cf_settimanale["uscite_investimenti"].sum(),
            "cassa_finale": cf_settimanale["cassa_finale"].iloc[-1],
        }
        fig_waterfall = crea_waterfall_liquidita(dati_waterfall)
        st.plotly_chart(fig_waterfall, use_container_width=True, config={"displayModeBar": True})
    else:
        st.info("Dati insufficienti per il grafico Waterfall.")

    # ------------------------------------------------------------------
    # 3. Burn Rate & Runway multi-scenario
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Proiezione Cassa - Analisi Scenari (24 mesi)")

    fig_burn = crea_grafico_burn_rate(df_scenari, soglia_hard)
    st.plotly_chart(fig_burn, use_container_width=True, config={"displayModeBar": True})

    with st.expander("Dettaglio numerico proiezione mensile"):
        cols_mostra = ["mese_anno", "cassa_worst", "cassa_base", "cassa_best"]
        df_mostra = df_scenari[cols_mostra].copy()
        df_mostra.columns = ["Mese", "Pessimistico (EUR)", "Base (EUR)", "Ottimistico (EUR)"]
        for c in ["Pessimistico (EUR)", "Base (EUR)", "Ottimistico (EUR)"]:
            df_mostra[c] = df_mostra[c].apply(lambda x: f"EUR {x:,.0f}".replace(",", "."))
        st.dataframe(df_mostra, use_container_width=True, height=400)

    # ------------------------------------------------------------------
    # 4. Heatmap delle Scadenze
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Mappa di Calore Scadenze")

    righe_heatmap = []
    for voce in tutte_voci:
        if voce.tipo == "pagamento":
            righe_heatmap.append({
                "data": voce.data_scadenza,
                "importo": voce.importo,
                "categoria": voce.categoria,
            })

    df_heatmap = pd.DataFrame(righe_heatmap)
    fig_heatmap = crea_heatmap_scadenze(df_heatmap)
    st.plotly_chart(fig_heatmap, use_container_width=True, config={"displayModeBar": True})

    st.caption(
        "Intensita' = importo totale uscite previste per giorno. "
        "I giorni critici sono il 16 (F24) e il 27-31 (stipendi)."
    )

    # ------------------------------------------------------------------
    # 5. Sensitivity Analysis
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Sensitivity Analysis")

    if ritardo_incassi > 0:
        st.info(
            f"Simulazione con **{ritardo_incassi} giorni** di ritardo incassi. "
            "Tutti i grafici sono aggiornati con questo parametro."
        )

        col_s1, col_s2, col_s3 = st.columns(3)

        cf_base_no_ritardo = calcola_cash_flow_diretto_mensile(
            scadenzario_df=scadenzario_df, payroll=payroll,
            scadenze_fiscali=scadenze_fiscali, cassa_iniziale=cassa_iniziale,
            costi_mensili_df=costi_mensili_df, mesi=12, ritardo_incassi_giorni=0,
        )
        cassa_senza = cf_base_no_ritardo["cassa_finale"].iloc[-1] if not cf_base_no_ritardo.empty else 0
        cassa_con = cf_mensile["cassa_finale"].iloc[11] if len(cf_mensile) > 11 else 0
        impatto = cassa_con - cassa_senza

        with col_s1:
            st.metric("Cassa senza ritardo (12m)", _formatta_euro_cf(cassa_senza))
        with col_s2:
            st.metric("Cassa con ritardo (12m)", _formatta_euro_cf(cassa_con))
        with col_s3:
            st.metric("Impatto ritardo", _formatta_euro_cf(impatto),
                      delta_color="inverse" if impatto < 0 else "normal")
    else:
        st.success(
            "Nessun ritardo incassi simulato. "
            "Usa lo slider nella sidebar per analizzare l'impatto di ritardi."
        )

    # ------------------------------------------------------------------
    # DSCR Prospettico
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("DSCR Prospettico")

    fig_dscr = crea_grafico_dscr(cf_con_dscr, dscr_warning, dscr_critico)
    st.plotly_chart(fig_dscr, use_container_width=True, config={"displayModeBar": True})

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.metric("DSCR Minimo", f"{cf_con_dscr['dscr'].min():.2f}")
    with col_d2:
        periodi_critico = (cf_con_dscr["dscr"] < dscr_critico).sum()
        st.metric("Periodi con DSCR < 1.0", str(periodi_critico))

    # ------------------------------------------------------------------
    # 6. Pannello Alert Intelligente
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Alert Intelligente")

    if cassa_finale_sett < soglia_hard:
        st.error(
            f"CRITICO: Cassa prevista (EUR {cassa_finale_sett:,.0f}) "
            f"sotto soglia di sicurezza (EUR {soglia_hard:,.0f})"
        )
    elif cassa_finale_sett < soglia_hard * 1.5:
        st.warning(
            f"ATTENZIONE: Cassa prevista (EUR {cassa_finale_sett:,.0f}) "
            f"vicina alla soglia di sicurezza (EUR {soglia_hard:,.0f})"
        )
    else:
        st.success(
            f"Cassa prevista (EUR {cassa_finale_sett:,.0f}) adeguata. "
            f"Soglia di sicurezza: EUR {soglia_hard:,.0f}"
        )

    if dscr_medio < dscr_critico:
        st.error(
            f"DSCR Critico: {dscr_medio:.2f} (soglia: {dscr_critico}). "
            "Rischio insolvenza sul servizio del debito."
        )
    elif dscr_medio < dscr_warning:
        st.warning(
            f"Rischio Tensione Finanziaria: DSCR {dscr_medio:.2f} "
            f"(soglia warning: {dscr_warning}). Monitorare attentamente."
        )
    else:
        st.success(f"DSCR adeguato: {dscr_medio:.2f} (soglia: {dscr_warning})")

    for alert in alert_list:
        livello = alert.get("livello", "")
        messaggio = alert.get("messaggio", "")
        if livello == "rosso":
            st.error(messaggio)
        elif livello == "giallo":
            st.warning(messaggio)

    if not alert_list and cassa_finale_sett >= soglia_hard and dscr_medio >= dscr_warning:
        st.success("Nessun alert attivo. Situazione finanziaria sotto controllo.")

    # Classificazione Scadenze
    st.markdown("#### Classificazione Scadenze per Priorita'")

    if not df_priorita.empty:
        col_p1, col_p2 = st.columns(2)
        df_indiff = df_priorita[df_priorita["priorita"] == "Indifferibile"]
        df_diff = df_priorita[df_priorita["priorita"] == "Differibile"]

        with col_p1:
            st.markdown("**Indifferibili** (stipendi, F24, contributi, mutui)")
            if not df_indiff.empty:
                totale_indiff = df_indiff["importo"].sum()
                st.metric("Totale Indifferibili", _formatta_euro_cf(totale_indiff))
                st.dataframe(
                    df_indiff[["data", "categoria", "importo", "controparte"]].head(15),
                    use_container_width=True, height=300,
                )
            else:
                st.info("Nessuna scadenza indifferibile nel periodo.")

        with col_p2:
            st.markdown("**Differibili** (fornitori, investimenti)")
            if not df_diff.empty:
                totale_diff = df_diff["importo"].sum()
                st.metric("Totale Differibili", _formatta_euro_cf(totale_diff))
                st.dataframe(
                    df_diff[["data", "categoria", "importo", "suggerimento_azione"]].head(15),
                    use_container_width=True, height=300,
                )
            else:
                st.info("Nessuna scadenza differibile nel periodo.")
    else:
        st.info("Nessuna scadenza disponibile per la classificazione.")

    # ------------------------------------------------------------------
    # 7. Piano CAPEX
    # ------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Piano Investimenti (CAPEX) 2024-2030")

    col_c1, col_c2 = st.columns([2, 1])

    with col_c1:
        fig_capex = crea_grafico_capex(capex_piano, anno_corrente)
        st.plotly_chart(fig_capex, use_container_width=True, config={"displayModeBar": True})

    with col_c2:
        st.markdown("**Dettaglio Piano Investimenti**")
        totale_piano = sum(capex_piano.values())
        st.metric("Totale Piano", _formatta_euro_cf(totale_piano))
        st.metric("CAPEX Anno Corrente", _formatta_euro_cf(capex_piano.get(anno_corrente, 0)))

        df_capex = pd.DataFrame([
            {"Anno": anno, "CAPEX (EUR)": f"EUR {importo:,.0f}".replace(",", ".")}
            for anno, importo in sorted(capex_piano.items())
        ])
        st.dataframe(df_capex, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------
    # Dettaglio Cash Flow Settimanale
    # ------------------------------------------------------------------

    st.markdown("---")
    with st.expander("Dettaglio Cash Flow Settimanale (12 settimane)"):
        if not cf_settimanale.empty:
            df_sett_mostra = cf_settimanale[[
                "settimana", "data_inizio", "data_fine",
                "cassa_iniziale", "incassi_operativi",
                "uscite_personale", "uscite_fornitori",
                "uscite_fiscali", "uscite_investimenti",
                "flusso_netto", "cassa_finale",
            ]].copy()

            cols_euro = [
                "cassa_iniziale", "incassi_operativi",
                "uscite_personale", "uscite_fornitori",
                "uscite_fiscali", "uscite_investimenti",
                "flusso_netto", "cassa_finale",
            ]
            for c in cols_euro:
                df_sett_mostra[c] = df_sett_mostra[c].apply(
                    lambda x: f"EUR {x:,.0f}".replace(",", ".")
                )

            st.dataframe(df_sett_mostra, use_container_width=True, height=450)
        else:
            st.info("Nessun dato settimanale disponibile.")
