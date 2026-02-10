"""
Componenti grafici riutilizzabili per la webapp Streamlit.

Ogni funzione accetta dizionari di dati (output dei moduli core) e restituisce
figure Plotly pronte per st.plotly_chart().

Schema colori Karol CDG:
    BLU_SCURO  = #1F4E79
    BLU        = #2E75B6
    TEAL       = #4BACC6
    VERDE      = #9BBB59
    ARANCIONE  = #F79646
    ROSSO      = #C0504D

Autore: Karol CDG
"""

from typing import Dict, List, Optional

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from karol_cdg.config import UNITA_OPERATIVE, MESI_BREVI_IT

# ============================================================================
# COSTANTI COLORI
# ============================================================================

BLU_SCURO = "#1F4E79"
BLU = "#2E75B6"
TEAL = "#4BACC6"
VERDE = "#9BBB59"
ARANCIONE = "#F79646"
ROSSO = "#C0504D"

# Palette blu per torta costi sede
PALETTE_BLU = ["#1F4E79", "#2E75B6", "#4BACC6", "#8DB4E2"]

# Palette completa per più UO
PALETTE_UO = [
    BLU_SCURO, BLU, TEAL, VERDE, ARANCIONE, ROSSO,
    "#7030A0", "#00B050", "#FFC000", "#808080",
]

# ============================================================================
# FORMATTAZIONE HELPER
# ============================================================================


def _formato_migliaia(valore: float) -> str:
    """
    Formatta un valore numerico con separatore migliaia italiano.
    Esempio: 1234567.89 -> '1.234.568'
    """
    if abs(valore) >= 1_000_000:
        return f"{valore / 1_000_000:,.1f}M".replace(",", ".")
    elif abs(valore) >= 1_000:
        return f"{valore:,.0f}".replace(",", ".")
    else:
        return f"{valore:,.0f}".replace(",", ".")


def _layout_base(titolo: str, altezza: int = 500) -> dict:
    """
    Restituisce un dizionario di layout base coerente per tutti i grafici.

    Parametri:
        titolo: titolo del grafico
        altezza: altezza in pixel

    Ritorna:
        Dizionario kwargs per fig.update_layout()
    """
    return dict(
        title=dict(
            text=titolo,
            font=dict(size=16, color=BLU_SCURO),
            x=0.5,
        ),
        height=altezza,
        font=dict(family="Segoe UI, sans-serif", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=40, t=60, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
    )


# ============================================================================
# 1. GRAFICO BARRE MOL INDUSTRIALE vs GESTIONALE
# ============================================================================


def grafico_barre_mol(
    ce_industriale: dict,
    ce_gestionale: dict,
) -> go.Figure:
    """
    Grafico a barre raggruppate che confronta MOL Industriale (MOL-I) e
    MOL Gestionale (MOL-G) per ogni Unità Operativa.

    Parametri:
        ce_industriale: dict {codice_uo: {"mol_industriale": float, ...}}
        ce_gestionale: dict {codice_uo: {"mol_gestionale": float, ...}}

    Ritorna:
        Figura Plotly con barre raggruppate
    """
    codici_uo = list(ce_industriale.keys())
    nomi_uo = []
    valori_mol_i = []
    valori_mol_g = []

    for codice in codici_uo:
        uo_info = UNITA_OPERATIVE.get(codice)
        nome = uo_info.nome if uo_info else codice
        nomi_uo.append(nome)
        valori_mol_i.append(ce_industriale[codice].get("mol_industriale", 0.0))
        valori_mol_g.append(ce_gestionale.get(codice, {}).get("mol_gestionale", 0.0))

    fig = go.Figure()

    # Barre MOL Industriale (verde)
    fig.add_trace(go.Bar(
        name="MOL Industriale",
        x=nomi_uo,
        y=valori_mol_i,
        marker_color=VERDE,
        text=[_formato_migliaia(v) for v in valori_mol_i],
        textposition="outside",
        textfont=dict(size=10),
    ))

    # Barre MOL Gestionale (blu)
    fig.add_trace(go.Bar(
        name="MOL Gestionale",
        x=nomi_uo,
        y=valori_mol_g,
        marker_color=BLU,
        text=[_formato_migliaia(v) for v in valori_mol_g],
        textposition="outside",
        textfont=dict(size=10),
    ))

    layout = _layout_base("Confronto MOL Industriale vs Gestionale per UO")
    layout["barmode"] = "group"
    layout["yaxis"] = dict(
        title="Euro (€)",
        gridcolor="#E0E0E0",
        zerolinecolor="#B0B0B0",
        tickformat=",.0f",
    )
    layout["xaxis"] = dict(title="Unità Operativa", tickangle=-30)

    fig.update_layout(**layout)

    return fig


# ============================================================================
# 2. GRAFICO TORTA COSTI SEDE PER CATEGORIA
# ============================================================================


def grafico_torta_sede(riepilogo_categorie: dict) -> go.Figure:
    """
    Grafico a torta della composizione dei costi di sede per categoria
    di allocazione (SERVIZI, GOVERNANCE, SVILUPPO, STORICO).

    Parametri:
        riepilogo_categorie: dizionario {nome_categoria: importo}
            Esempio: {
                'Servizi alle U.O.': 800000,
                'Governance e Coordinamento': 600000,
                'Sviluppo': 400000,
                'Costi storici': 300000,
            }

    Ritorna:
        Figura Plotly con grafico a torta
    """
    categorie = list(riepilogo_categorie.keys())
    valori = list(riepilogo_categorie.values())
    totale = sum(valori) if valori else 1

    # Etichette con importo e percentuale
    etichette_custom = [
        f"{cat}<br>€ {_formato_migliaia(val)} ({val / totale * 100:.1f}%)"
        for cat, val in zip(categorie, valori)
    ]

    fig = go.Figure(data=[go.Pie(
        labels=categorie,
        values=valori,
        marker=dict(colors=PALETTE_BLU[:len(categorie)]),
        textinfo="label+percent",
        textposition="auto",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Importo: € %{value:,.0f}<br>"
            "Quota: %{percent}<extra></extra>"
        ),
        hole=0.35,  # ciambella per estetica
    )])

    layout = _layout_base("Composizione Costi di Sede per Categoria", altezza=450)
    layout["showlegend"] = True

    fig.update_layout(**layout)

    return fig


# ============================================================================
# 3. GRAFICO WATERFALL CE (da Ricavi a MOL-G)
# ============================================================================


def grafico_waterfall_ce(
    uo_code: str,
    ce_industriale: dict,
    ce_gestionale: dict,
) -> go.Figure:
    """
    Grafico a cascata (waterfall) per una singola Unità Operativa che mostra
    il passaggio da Ricavi a MOL Gestionale:

        Ricavi -> -Costi Diretti -> MOL-I -> -Costi Sede -> MOL-G

    Parametri:
        uo_code: codice dell'Unità Operativa (es. "VLB")
        ce_industriale: dict {codice_uo: {"totale_ricavi", "totale_costi", "mol_industriale"}}
        ce_gestionale: dict {codice_uo: {"costi_sede_allocati", "mol_gestionale"}}

    Ritorna:
        Figura Plotly con grafico waterfall
    """
    uo_info = UNITA_OPERATIVE.get(uo_code)
    nome_uo = uo_info.nome if uo_info else uo_code

    ce_i = ce_industriale.get(uo_code, {})
    ce_g = ce_gestionale.get(uo_code, {})

    ricavi = ce_i.get("totale_ricavi", 0.0)
    costi_diretti = ce_i.get("totale_costi", 0.0)
    mol_i = ce_i.get("mol_industriale", 0.0)
    costi_sede = ce_g.get("costi_sede_allocati", 0.0)
    mol_g = ce_g.get("mol_gestionale", 0.0)

    fig = go.Figure(go.Waterfall(
        name="CE",
        orientation="v",
        measure=["absolute", "relative", "total", "relative", "total"],
        x=[
            "Ricavi",
            "Costi Diretti",
            "MOL Industriale",
            "Costi Sede",
            "MOL Gestionale",
        ],
        y=[
            ricavi,
            -costi_diretti,
            0,  # subtotale: calcolato automaticamente come total
            -costi_sede,
            0,  # totale finale
        ],
        text=[
            f"€ {_formato_migliaia(ricavi)}",
            f"-€ {_formato_migliaia(costi_diretti)}",
            f"€ {_formato_migliaia(mol_i)}",
            f"-€ {_formato_migliaia(costi_sede)}",
            f"€ {_formato_migliaia(mol_g)}",
        ],
        textposition="outside",
        textfont=dict(size=11),
        connector=dict(line=dict(color="#B0B0B0", width=1, dash="dot")),
        increasing=dict(marker=dict(color=VERDE)),
        decreasing=dict(marker=dict(color=ROSSO)),
        totals=dict(marker=dict(color=BLU)),
    ))

    layout = _layout_base(f"Waterfall CE - {nome_uo} ({uo_code})")
    layout["yaxis"] = dict(
        title="Euro (€)",
        gridcolor="#E0E0E0",
        tickformat=",.0f",
    )
    layout["xaxis"] = dict(title="")
    layout["showlegend"] = False

    fig.update_layout(**layout)

    return fig


# ============================================================================
# 4. GRAFICO TREND MENSILE RICAVI
# ============================================================================


def grafico_trend_mensile(
    df_produzione: pd.DataFrame,
    uo_selezionate: List[str],
) -> go.Figure:
    """
    Grafico a linee del trend mensile dei ricavi per le UO selezionate.

    Parametri:
        df_produzione: DataFrame con colonne:
            - 'codice_uo': codice dell'Unità Operativa
            - 'mese': numero del mese (1-12)
            - 'anno': anno di riferimento
            - 'ricavi': importo ricavi del mese
        uo_selezionate: lista codici UO da visualizzare (es. ["VLB", "COS"])

    Ritorna:
        Figura Plotly con linee trend mensile
    """
    fig = go.Figure()

    if df_produzione is None or df_produzione.empty:
        layout = _layout_base("Trend Mensile Ricavi per Unità Operativa")
        fig.update_layout(**layout)
        fig.add_annotation(
            text="Nessun dato disponibile",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#808080"),
        )
        return fig

    for idx, codice_uo in enumerate(uo_selezionate):
        dati_uo = df_produzione[
            df_produzione["codice_uo"] == codice_uo
        ].sort_values(by=["anno", "mese"])

        if dati_uo.empty:
            continue

        # Etichette mese abbreviate in italiano
        etichette_mese = [
            MESI_BREVI_IT.get(m, str(m))
            for m in dati_uo["mese"]
        ]

        # Se c'è la colonna anno, combina per etichetta x
        if "anno" in dati_uo.columns:
            etichette_x = [
                f"{MESI_BREVI_IT.get(row['mese'], str(row['mese']))} {int(row['anno'])}"
                for _, row in dati_uo.iterrows()
            ]
        else:
            etichette_x = etichette_mese

        uo_info = UNITA_OPERATIVE.get(codice_uo)
        nome_uo = uo_info.nome if uo_info else codice_uo
        colore = PALETTE_UO[idx % len(PALETTE_UO)]

        fig.add_trace(go.Scatter(
            x=etichette_x,
            y=dati_uo["ricavi"].values,
            name=f"{codice_uo} - {nome_uo}",
            mode="lines+markers",
            line=dict(color=colore, width=2),
            marker=dict(size=6),
            hovertemplate=(
                f"<b>{nome_uo}</b><br>"
                "Mese: %{x}<br>"
                "Ricavi: € %{y:,.0f}<extra></extra>"
            ),
        ))

    layout = _layout_base("Trend Mensile Ricavi per Unità Operativa")
    layout["yaxis"] = dict(
        title="Ricavi (€)",
        gridcolor="#E0E0E0",
        tickformat=",.0f",
    )
    layout["xaxis"] = dict(
        title="Mese",
        tickangle=-45,
    )
    layout["hovermode"] = "x unified"

    fig.update_layout(**layout)

    return fig


# ============================================================================
# 5. GRAFICO RADAR KPI
# ============================================================================


def grafico_radar_kpi(
    kpi_list: list,
    uo_code: str,
) -> go.Figure:
    """
    Grafico radar (spider chart) dei KPI per una singola Unità Operativa.
    I valori vengono normalizzati su scala 0-100 rispetto al target.

    Parametri:
        kpi_list: lista di oggetti KPI (dataclass dal modulo kpi.py)
                  filtrati per la UO desiderata. Ogni KPI ha attributi:
                  codice, nome, valore, target, alert_livello
        uo_code: codice UO per il titolo del grafico

    Ritorna:
        Figura Plotly con grafico radar
    """
    uo_info = UNITA_OPERATIVE.get(uo_code)
    nome_uo = uo_info.nome if uo_info else uo_code

    if not kpi_list:
        fig = go.Figure()
        layout = _layout_base(f"Radar KPI - {nome_uo} ({uo_code})")
        fig.update_layout(**layout)
        fig.add_annotation(
            text="Nessun KPI disponibile",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#808080"),
        )
        return fig

    nomi_kpi = []
    valori_normalizzati = []
    valori_target = []

    for kpi in kpi_list:
        nome = kpi.get("kpi", "") if isinstance(kpi, dict) else kpi.nome
        valore = kpi.get("valore", 0) if isinstance(kpi, dict) else kpi.valore
        target = kpi.get("target", 0) if isinstance(kpi, dict) else kpi.target
        nomi_kpi.append(nome)

        # Normalizzazione 0-100: valore / target * 100
        if target and target != 0:
            normalizzato = min((valore / target) * 100, 120)
        else:
            normalizzato = 50.0  # valore neutro se target non definito

        valori_normalizzati.append(round(normalizzato, 1))
        valori_target.append(100.0)  # linea target sempre a 100

    # Chiudi il poligono ripetendo il primo valore
    nomi_kpi_chiuso = nomi_kpi + [nomi_kpi[0]]
    valori_chiuso = valori_normalizzati + [valori_normalizzati[0]]
    target_chiuso = valori_target + [valori_target[0]]

    fig = go.Figure()

    # Area valori effettivi
    fig.add_trace(go.Scatterpolar(
        r=valori_chiuso,
        theta=nomi_kpi_chiuso,
        fill="toself",
        fillcolor=f"rgba(46, 117, 182, 0.25)",
        line=dict(color=BLU, width=2),
        name="Valori effettivi",
        hovertemplate="<b>%{theta}</b><br>Score: %{r:.0f}/100<extra></extra>",
    ))

    # Linea target (cerchio a 100)
    fig.add_trace(go.Scatterpolar(
        r=target_chiuso,
        theta=nomi_kpi_chiuso,
        fill=None,
        line=dict(color=ARANCIONE, width=1.5, dash="dash"),
        name="Target (100)",
    ))

    layout = _layout_base(f"Radar KPI - {nome_uo} ({uo_code})", altezza=500)
    layout["polar"] = dict(
        radialaxis=dict(
            visible=True,
            range=[0, 120],
            ticksuffix="",
            gridcolor="#E0E0E0",
        ),
        angularaxis=dict(
            gridcolor="#E0E0E0",
        ),
    )

    fig.update_layout(**layout)

    return fig


# ============================================================================
# 6. GRAFICO BARRE CONFRONTO UO (stacked + linea ricavi)
# ============================================================================


def grafico_barre_confronto_uo(
    ce_industriale: dict,
) -> go.Figure:
    """
    Grafico a barre orizzontali impilate con la composizione dei costi
    diretti per ogni UO (Personale, Acquisti, Servizi, Ammortamenti),
    con sovrapposta una linea dei ricavi per confronto visivo.

    Parametri:
        ce_industriale: dict {codice_uo: {"costi_personale", "costi_acquisti",
                        "costi_servizi", "costi_ammort", "totale_ricavi"}}

    Ritorna:
        Figura Plotly con barre impilate orizzontali e linea ricavi
    """
    nomi_uo = []
    personale = []
    acquisti = []
    servizi = []
    ammortamenti = []
    ricavi = []

    for codice, ce in ce_industriale.items():
        uo_info = UNITA_OPERATIVE.get(codice)
        nome = uo_info.nome if uo_info else codice

        nomi_uo.append(nome)
        personale.append(ce.get("costi_personale", 0.0))
        acquisti.append(ce.get("costi_acquisti", 0.0))
        servizi.append(ce.get("costi_servizi", 0.0))
        ammortamenti.append(ce.get("costi_ammort", 0.0))
        ricavi.append(ce.get("totale_ricavi", 0.0))

    fig = go.Figure()

    # Barre impilate (orizzontali)
    fig.add_trace(go.Bar(
        name="Costi Personale",
        y=nomi_uo,
        x=personale,
        orientation="h",
        marker_color=BLU_SCURO,
        hovertemplate="<b>%{y}</b><br>Personale: € %{x:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Acquisti Diretti",
        y=nomi_uo,
        x=acquisti,
        orientation="h",
        marker_color=BLU,
        hovertemplate="<b>%{y}</b><br>Acquisti: € %{x:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Servizi Diretti",
        y=nomi_uo,
        x=servizi,
        orientation="h",
        marker_color=TEAL,
        hovertemplate="<b>%{y}</b><br>Servizi: € %{x:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Ammortamenti",
        y=nomi_uo,
        x=ammortamenti,
        orientation="h",
        marker_color=ARANCIONE,
        hovertemplate="<b>%{y}</b><br>Ammortamenti: € %{x:,.0f}<extra></extra>",
    ))

    # Linea ricavi sovrapposta (asse secondario simulato con scatter)
    fig.add_trace(go.Scatter(
        name="Ricavi",
        y=nomi_uo,
        x=ricavi,
        mode="markers+lines",
        marker=dict(color=ROSSO, size=10, symbol="diamond"),
        line=dict(color=ROSSO, width=2),
        hovertemplate="<b>%{y}</b><br>Ricavi: € %{x:,.0f}<extra></extra>",
    ))

    layout = _layout_base(
        "Composizione Costi Diretti e Ricavi per UO",
        altezza=max(400, len(nomi_uo) * 60 + 120),
    )
    layout["barmode"] = "stack"
    layout["xaxis"] = dict(
        title="Euro (€)",
        gridcolor="#E0E0E0",
        tickformat=",.0f",
    )
    layout["yaxis"] = dict(
        title="",
        autorange="reversed",  # prima UO in alto
    )

    fig.update_layout(**layout)

    return fig


def grafico_barre_confronto_benchmark(righe_benchmark: list) -> go.Figure:
    """
    Grafico a barre raggruppate: MOL % effettivo vs benchmark min/max per UO.

    Parametri:
        righe_benchmark: lista di dict con chiavi UO, Tipologia,
            MOL % (Effettivo), MOL % (Bench. Min), MOL % (Bench. Max)

    Ritorna:
        Figura Plotly con confronto benchmark
    """
    if not righe_benchmark:
        fig = go.Figure()
        fig.add_annotation(text="Nessun benchmark disponibile", showarrow=False)
        return fig

    nomi = [r.get("UO", "") for r in righe_benchmark]
    effettivo = [r.get("MOL % (Effettivo)", 0) for r in righe_benchmark]
    bench_min = [r.get("MOL % (Bench. Min)", 0) for r in righe_benchmark]
    bench_max = [r.get("MOL % (Bench. Max)", 0) for r in righe_benchmark]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="MOL % Effettivo",
        x=nomi,
        y=effettivo,
        marker_color=BLU,
        text=[f"{v:.1f}%" for v in effettivo],
        textposition="outside",
    ))

    fig.add_trace(go.Bar(
        name="Benchmark Min",
        x=nomi,
        y=bench_min,
        marker_color=VERDE,
        opacity=0.5,
        text=[f"{v:.1f}%" for v in bench_min],
        textposition="outside",
    ))

    fig.add_trace(go.Bar(
        name="Benchmark Max",
        x=nomi,
        y=bench_max,
        marker_color=TEAL,
        opacity=0.5,
        text=[f"{v:.1f}%" for v in bench_max],
        textposition="outside",
    ))

    layout = _layout_base("Confronto MOL % con Benchmark di Settore", altezza=450)
    layout["barmode"] = "group"
    layout["yaxis"] = dict(title="MOL %", ticksuffix="%")

    fig.update_layout(**layout)

    return fig


# ============================================================================
# 8. WATERFALL LIQUIDITA' (Cash Flow)
# ============================================================================


def crea_waterfall_liquidita(dati: dict) -> go.Figure:
    """
    Grafico waterfall della liquidita': da cassa iniziale a cassa finale
    passando per incassi, uscite personale, fornitori, fiscali, investimenti.
    """
    nomi = [
        "Cassa Iniziale", "Incassi Operativi", "Uscite Personale",
        "Uscite Fornitori", "Uscite Fiscali", "Investimenti", "Cassa Finale",
    ]
    valori = [
        dati.get("cassa_iniziale", 0),
        dati.get("incassi_operativi", 0),
        -dati.get("uscite_personale", 0),
        -dati.get("uscite_fornitori", 0),
        -dati.get("uscite_fiscali", 0),
        -dati.get("uscite_investimenti", 0),
        0,
    ]
    misure = ["absolute", "relative", "relative", "relative",
              "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        name="Liquidita'",
        orientation="v",
        measure=misure,
        x=nomi,
        y=valori,
        text=[f"EUR {_formato_migliaia(abs(v))}" for v in valori],
        textposition="outside",
        textfont=dict(size=10),
        connector=dict(line=dict(color="#B0B0B0", width=1, dash="dot")),
        increasing=dict(marker=dict(color=VERDE)),
        decreasing=dict(marker=dict(color=ROSSO)),
        totals=dict(marker=dict(color=BLU)),
    ))

    layout = _layout_base("Waterfall della Liquidita'")
    layout["yaxis"] = dict(title="Euro", gridcolor="#E0E0E0", tickformat=",.0f")
    layout["xaxis"] = dict(tickangle=-30)
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig


# ============================================================================
# 9. BURN RATE & RUNWAY MULTI-SCENARIO
# ============================================================================


def crea_grafico_burn_rate(df_scenari: pd.DataFrame, soglia: float) -> go.Figure:
    """Grafico multi-linea proiezione cassa 3 scenari con soglia sicurezza."""
    fig = go.Figure()

    if "cassa_worst" in df_scenari.columns:
        fig.add_trace(go.Scatter(
            x=df_scenari["mese_anno"], y=df_scenari["cassa_worst"],
            name="Pessimistico", mode="lines",
            line=dict(color=ROSSO, width=2, dash="dash"),
            hovertemplate="<b>Pessimistico</b><br>%{x}<br>EUR %{y:,.0f}<extra></extra>",
        ))

    if "cassa_base" in df_scenari.columns:
        fig.add_trace(go.Scatter(
            x=df_scenari["mese_anno"], y=df_scenari["cassa_base"],
            name="Base", mode="lines+markers",
            line=dict(color=BLU, width=3), marker=dict(size=5),
            hovertemplate="<b>Base</b><br>%{x}<br>EUR %{y:,.0f}<extra></extra>",
        ))

    if "cassa_best" in df_scenari.columns:
        fig.add_trace(go.Scatter(
            x=df_scenari["mese_anno"], y=df_scenari["cassa_best"],
            name="Ottimistico", mode="lines",
            line=dict(color=VERDE, width=2, dash="dash"),
            hovertemplate="<b>Ottimistico</b><br>%{x}<br>EUR %{y:,.0f}<extra></extra>",
        ))

    fig.add_hline(y=soglia, line_dash="dot", line_color=ARANCIONE,
                  annotation_text=f"Soglia sicurezza: EUR {_formato_migliaia(soglia)}",
                  annotation_position="top left")

    layout = _layout_base("Proiezione Cassa - Analisi Scenari", altezza=450)
    layout["yaxis"] = dict(title="Cassa (EUR)", gridcolor="#E0E0E0", tickformat=",.0f")
    layout["xaxis"] = dict(tickangle=-45)
    layout["hovermode"] = "x unified"
    fig.update_layout(**layout)
    return fig


# ============================================================================
# 10. HEATMAP SCADENZE
# ============================================================================


def crea_heatmap_scadenze(df_scadenze: pd.DataFrame) -> go.Figure:
    """Heatmap 12x31 delle uscite previste per giorno del mese."""
    import numpy as np

    matrice = np.zeros((12, 31))

    if not df_scadenze.empty and "data" in df_scadenze.columns:
        for _, row in df_scadenze.iterrows():
            d = row["data"]
            if hasattr(d, "month") and hasattr(d, "day"):
                matrice[d.month - 1][d.day - 1] += row.get("importo", 0)

    nomi_mesi = list(MESI_BREVI_IT.values())
    giorni = [str(g) for g in range(1, 32)]

    fig = go.Figure(data=go.Heatmap(
        z=matrice, x=giorni, y=nomi_mesi,
        colorscale=[[0.0, "#F0F4F8"], [0.3, "#B0D0F0"],
                     [0.6, ARANCIONE], [1.0, ROSSO]],
        hovertemplate="Giorno %{x}<br>Mese: %{y}<br>Uscite: EUR %{z:,.0f}<extra></extra>",
        colorbar=dict(title="EUR"),
    ))

    layout = _layout_base("Mappa di Calore Scadenze (Uscite per Giorno)", altezza=400)
    layout["xaxis"] = dict(title="Giorno del mese", dtick=1)
    layout["yaxis"] = dict(title="")
    fig.update_layout(**layout)
    return fig


# ============================================================================
# 11. DSCR PROSPETTICO
# ============================================================================


def crea_grafico_dscr(
    df_dscr: pd.DataFrame, soglia_warning: float, soglia_critica: float,
) -> go.Figure:
    """Grafico DSCR prospettico con zone colorate verde/giallo/rosso."""
    fig = go.Figure()

    x_col = "mese_anno" if "mese_anno" in df_dscr.columns else df_dscr.index
    x_vals = df_dscr[x_col] if isinstance(x_col, str) else x_col

    fig.add_trace(go.Scatter(
        x=x_vals, y=df_dscr["dscr"], mode="lines+markers", name="DSCR",
        line=dict(color=BLU_SCURO, width=3), marker=dict(size=6),
        hovertemplate="<b>DSCR</b>: %{y:.2f}<br>%{x}<extra></extra>",
    ))

    dscr_max = max(df_dscr["dscr"].max() * 1.2, soglia_warning * 2) if not df_dscr.empty else 3

    fig.add_hrect(y0=0, y1=soglia_critica, fillcolor=ROSSO, opacity=0.1, line_width=0)
    fig.add_hrect(y0=soglia_critica, y1=soglia_warning, fillcolor=ARANCIONE, opacity=0.1, line_width=0)
    fig.add_hrect(y0=soglia_warning, y1=dscr_max, fillcolor=VERDE, opacity=0.1, line_width=0)
    fig.add_hline(y=soglia_critica, line_dash="dot", line_color=ROSSO,
                  annotation_text=f"Critico ({soglia_critica})")
    fig.add_hline(y=soglia_warning, line_dash="dot", line_color=ARANCIONE,
                  annotation_text=f"Warning ({soglia_warning})")

    layout = _layout_base("DSCR Prospettico", altezza=400)
    layout["yaxis"] = dict(title="DSCR", gridcolor="#E0E0E0", range=[0, dscr_max])
    layout["xaxis"] = dict(tickangle=-45)
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig


# ============================================================================
# 12. PIANO CAPEX
# ============================================================================


def crea_grafico_capex(piano: dict, anno_corrente: int) -> go.Figure:
    """Grafico a barre piano CAPEX 2024-2030 con evidenziazione anno corrente."""
    anni = sorted(piano.keys())
    importi = [piano[a] for a in anni]
    colori = [BLU_SCURO if a == anno_corrente else BLU for a in anni]

    fig = go.Figure(go.Bar(
        x=[str(a) for a in anni], y=importi, marker_color=colori,
        text=[f"EUR {_formato_migliaia(v)}" for v in importi],
        textposition="outside", textfont=dict(size=11),
        hovertemplate="<b>Anno %{x}</b><br>CAPEX: EUR %{y:,.0f}<extra></extra>",
    ))

    if anno_corrente in piano:
        fig.add_annotation(
            x=str(anno_corrente), y=piano[anno_corrente],
            text="Anno corrente", showarrow=True, arrowhead=2,
            arrowcolor=ARANCIONE,
            font=dict(color=ARANCIONE, size=11),
        )

    layout = _layout_base("Piano Investimenti (CAPEX)", altezza=400)
    layout["yaxis"] = dict(title="EUR", gridcolor="#E0E0E0", tickformat=",.0f")
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig
