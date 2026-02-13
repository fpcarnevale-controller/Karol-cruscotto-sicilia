"""
Pagina KPI - Indicatori Chiave di Performance.

Mostra tutti i KPI calcolati con filtri per UO e livello alert,
tabella completa, grafico radar, confronto con benchmark di settore
e dettaglio formule.
"""

import streamlit as st
import pandas as pd

from karol_cdg.config import (
    UNITA_OPERATIVE,
    UO_OPERATIVE,
    BENCHMARK,
)
from karol_cdg.webapp.componenti.grafici import (
    grafico_radar_kpi,
    grafico_barre_confronto_benchmark,
)
from karol_cdg.webapp.componenti.tabelle import (
    formatta_euro,
    formatta_percentuale,
    tabella_kpi,
    colore_semaforo,
)
from karol_cdg.webapp.componenti.metriche import (
    mostra_kpi_card,
    mostra_semaforo,
)


def mostra_kpi(risultati: dict, dati: dict):
    """
    Pagina principale dei KPI - Indicatori Chiave di Performance.

    Parametri:
        risultati: dizionario con i risultati dell'elaborazione completa
                   (ce_industriale, ce_gestionale, allocazione, kpi)
        dati: dizionario con i DataFrame sorgente
              (produzione, costi, costi_sede, driver, personale)
    """
    st.title("KPI - Indicatori Chiave")
    st.markdown("---")

    # Recupera la lista KPI dai risultati
    kpi_list = risultati.get("kpi", [])

    if not kpi_list:
        st.warning("Nessun KPI disponibile. Eseguire prima l'elaborazione dei dati.")
        return

    # =========================================================================
    # FILTRI
    # =========================================================================
    col_filtro_uo, col_filtro_alert = st.columns(2)

    # Elenco UO disponibili nei KPI
    uo_disponibili = sorted(set(k["unita_operativa"] for k in kpi_list))
    # Assicuriamoci che GRUPPO sia presente se c'e' nei dati
    opzioni_uo = ["Tutte"] + uo_disponibili

    with col_filtro_uo:
        uo_selezionata = st.selectbox(
            "Filtra per Unita' Operativa",
            options=opzioni_uo,
            index=0,
            help="Seleziona una UO o 'GRUPPO' per i KPI consolidati",
        )

    with col_filtro_alert:
        livelli_alert = st.multiselect(
            "Filtra per livello alert",
            options=["VERDE", "GIALLO", "ROSSO"],
            default=["VERDE", "GIALLO", "ROSSO"],
            help="Seleziona i livelli di alert da visualizzare",
        )

    # Applica filtri
    kpi_filtrati = kpi_list.copy()

    if uo_selezionata != "Tutte":
        kpi_filtrati = [
            k for k in kpi_filtrati
            if k["unita_operativa"] == uo_selezionata
        ]

    if livelli_alert:
        kpi_filtrati = [
            k for k in kpi_filtrati
            if k.get("alert", "VERDE") in livelli_alert
        ]

    # =========================================================================
    # RIEPILOGO SEMAFORI
    # =========================================================================
    st.subheader("Riepilogo Alert")

    n_verdi = sum(1 for k in kpi_filtrati if k.get("alert") == "VERDE")
    n_gialli = sum(1 for k in kpi_filtrati if k.get("alert") == "GIALLO")
    n_rossi = sum(1 for k in kpi_filtrati if k.get("alert") == "ROSSO")

    col_v, col_g, col_r, col_tot = st.columns(4)
    mostra_kpi_card(col_v, "Verdi", n_verdi, formato="numero")
    mostra_kpi_card(col_g, "Gialli", n_gialli, formato="numero")
    mostra_kpi_card(col_r, "Rossi", n_rossi, formato="numero")
    mostra_kpi_card(col_tot, "Totale KPI", len(kpi_filtrati), formato="numero")

    st.markdown("---")

    # =========================================================================
    # TABELLA KPI COMPLETA
    # =========================================================================
    st.subheader("Tabella KPI")

    if kpi_filtrati:
        tabella_kpi(kpi_filtrati)
    else:
        st.info("Nessun KPI corrispondente ai filtri selezionati.")

    st.markdown("---")

    # =========================================================================
    # GRAFICO RADAR PER UO SELEZIONATA
    # =========================================================================
    st.subheader("Grafico Radar")

    # Per il radar, serve una UO specifica (non "Tutte")
    uo_per_radar = uo_selezionata if uo_selezionata != "Tutte" else None

    if uo_per_radar is None:
        # Selectbox dedicata al radar
        uo_radar_opzioni = [uo for uo in uo_disponibili if uo != "GRUPPO"]
        if uo_radar_opzioni:
            uo_per_radar = st.selectbox(
                "Seleziona UO per il grafico radar",
                options=uo_radar_opzioni,
                key="radar_uo_select",
            )

    if uo_per_radar:
        kpi_radar = [
            k for k in kpi_list
            if k["unita_operativa"] == uo_per_radar
        ]

        if kpi_radar:
            nome_uo = UNITA_OPERATIVE[uo_per_radar].nome if uo_per_radar in UNITA_OPERATIVE else uo_per_radar
            st.markdown(f"**Profilo KPI: {nome_uo} ({uo_per_radar})**")
            fig_radar = grafico_radar_kpi(kpi_radar, uo_per_radar)
            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            st.info(f"Nessun KPI disponibile per {uo_per_radar}.")
    else:
        st.info("Selezionare una UO per visualizzare il grafico radar.")

    st.markdown("---")

    # =========================================================================
    # BENCHMARK DI SETTORE
    # =========================================================================
    st.subheader("Benchmark di Settore")
    st.markdown(
        "Confronto tra i valori effettivi delle UO e i benchmark "
        "di settore per tipologia di struttura."
    )

    ce_industriale = risultati.get("ce_industriale", {})

    # Prepara dati per confronto benchmark
    righe_benchmark = []
    for codice_uo in UO_OPERATIVE:
        if codice_uo not in UNITA_OPERATIVE:
            continue

        uo_info = UNITA_OPERATIVE[codice_uo]
        if not uo_info.tipologia:
            continue

        # Prendi la tipologia principale
        tipologia_principale = uo_info.tipologia[0].name
        benchmark_settore = BENCHMARK.get(tipologia_principale)

        if benchmark_settore is None:
            continue

        ce_uo = ce_industriale.get(codice_uo, {})
        totale_ricavi = ce_uo.get("totale_ricavi", 0)
        costi_personale = ce_uo.get("costi_personale", 0)
        mol_i = ce_uo.get("mol_industriale", 0)

        # Calcola percentuali effettive
        pct_personale_effettivo = (
            (costi_personale / totale_ricavi * 100) if totale_ricavi > 0 else 0
        )
        mol_pct_effettivo = (
            (mol_i / totale_ricavi * 100) if totale_ricavi > 0 else 0
        )

        righe_benchmark.append({
            "UO": codice_uo,
            "Nome": uo_info.nome,
            "Tipologia": uo_info.tipologia[0].value,
            "Costo Pers. % (Effettivo)": round(pct_personale_effettivo, 1),
            "Costo Pers. % (Bench. Min)": benchmark_settore.costo_personale_su_ricavi_min,
            "Costo Pers. % (Bench. Max)": benchmark_settore.costo_personale_su_ricavi_max,
            "MOL % (Effettivo)": round(mol_pct_effettivo, 1),
            "MOL % (Bench. Min)": benchmark_settore.mol_percentuale_target_min,
            "MOL % (Bench. Max)": benchmark_settore.mol_percentuale_target_max,
        })

    if righe_benchmark:
        df_benchmark = pd.DataFrame(righe_benchmark)
        st.dataframe(
            df_benchmark,
            use_container_width=True,
            hide_index=True,
        )

        # Grafico confronto benchmark
        grafico_barre_confronto_benchmark(righe_benchmark)
    else:
        st.info("Nessun benchmark di settore disponibile per le UO correnti.")

    st.markdown("---")

    # =========================================================================
    # DEFINIZIONI E FORMULE (EXPANDER)
    # =========================================================================
    with st.expander("Definizioni e Formule KPI", expanded=False):
        st.markdown("### Glossario KPI")

        # Raccogli definizioni univoche dai KPI
        definizioni_viste = set()
        for kpi in kpi_list:
            nome_kpi = kpi.get("kpi", "")
            formula = kpi.get("formula", "")

            if nome_kpi in definizioni_viste:
                continue
            definizioni_viste.add(nome_kpi)

            st.markdown(f"**{nome_kpi}**")
            st.markdown(f"- *Formula*: `{formula}`")

            # Aggiungi descrizioni specifiche
            if "MOL" in nome_kpi and "Industriale" in nome_kpi:
                st.markdown(
                    "- *Descrizione*: Margine Operativo Lordo Industriale, "
                    "misura la redditivita' operativa della singola UO prima "
                    "dell'allocazione dei costi sede."
                )
            elif "MOL" in nome_kpi and "Gestionale" in nome_kpi:
                st.markdown(
                    "- *Descrizione*: Margine Operativo Lordo Gestionale, "
                    "misura la redditivita' della UO dopo l'allocazione dei "
                    "costi sede tramite driver specifici."
                )
            elif "MOL" in nome_kpi and "Consolidato" in nome_kpi:
                st.markdown(
                    "- *Descrizione*: Margine Operativo Lordo del Gruppo, "
                    "somma dei MOL Gestionali di tutte le UO."
                )
            elif "Personale" in nome_kpi:
                st.markdown(
                    "- *Descrizione*: Incidenza del costo del personale sul "
                    "fatturato. Benchmark settore sanitario: 50-60%."
                )
            elif "Occupancy" in nome_kpi:
                st.markdown(
                    "- *Descrizione*: Tasso di occupazione dei posti letto. "
                    "Target minimo: 80%, ottimale: > 90%."
                )
            elif "Sede" in nome_kpi:
                st.markdown(
                    "- *Descrizione*: Peso dei costi di sede allocati sul "
                    "fatturato totale. Problema critico se > 19%."
                )
            elif "giornata" in nome_kpi.lower():
                st.markdown(
                    "- *Descrizione*: Valore medio per giornata di degenza "
                    "erogata. Dipende dalla tipologia di struttura."
                )

            st.markdown("")

        st.markdown("### Livelli Alert")
        st.markdown(
            "- **VERDE**: KPI entro i valori target, nessuna azione richiesta\n"
            "- **GIALLO**: KPI in area di attenzione, monitoraggio ravvicinato\n"
            "- **ROSSO**: KPI critico, azione correttiva necessaria"
        )

        st.markdown("### Benchmark di Settore")
        st.markdown(
            "I benchmark sono basati su dati di settore per la sanita' privata "
            "italiana, differenziati per tipologia di struttura "
            "(RSA, CTA, Riabilitazione, Laboratorio, Day Surgery)."
        )
