"""
Helper per schede metriche KPI nella webapp Streamlit.

Fornisce funzioni per visualizzare metriche singole (st.metric),
indicatori semaforo, righe di KPI consolidati e pannelli alert.

Le funzioni ricevono un container Streamlit (st, colonna, expander, ecc.)
e vi scrivono direttamente i widget.

Autore: Karol CDG
"""

from typing import List, Optional, Union
import math

from karol_cdg.config import LivelliAlert

# ============================================================================
# COSTANTI
# ============================================================================

# Mappa livello semaforo -> icona + colore CSS
MAPPA_SEMAFORO = {
    LivelliAlert.VERDE: {"icona": "🟢", "etichetta": "VERDE", "colore": "#27AE60"},
    LivelliAlert.GIALLO: {"icona": "🟡", "etichetta": "GIALLO", "colore": "#F39C12"},
    LivelliAlert.ROSSO: {"icona": "🔴", "etichetta": "ROSSO", "colore": "#E74C3C"},
}

# Livello semaforo dalla stringa (per compatibilita')
MAPPA_STRINGA_LIVELLO = {
    "verde": LivelliAlert.VERDE,
    "giallo": LivelliAlert.GIALLO,
    "rosso": LivelliAlert.ROSSO,
    "VERDE": LivelliAlert.VERDE,
    "GIALLO": LivelliAlert.GIALLO,
    "ROSSO": LivelliAlert.ROSSO,
}


# ============================================================================
# FORMATTAZIONE HELPER
# ============================================================================


def _formatta_valore(valore: Union[float, int, None], formato: str) -> str:
    """
    Formatta un valore numerico secondo il formato richiesto.

    Formati supportati:
        'euro'          -> '€ 1.234.567'
        'euro_k'        -> '€ 1.235K'
        'euro_m'        -> '€ 1,2M'
        'percentuale'   -> '22,9%'
        'numero'        -> '1.234'
        'decimale'      -> '1,23'
        'giorni'        -> '120 gg'
        'mesi'          -> '2,5 mesi'

    Parametri:
        valore: valore numerico o None
        formato: stringa indicante il formato desiderato

    Ritorna:
        Stringa formattata
    """
    if valore is None or (isinstance(valore, float) and math.isnan(valore)):
        return "-"

    valore = float(valore)

    if formato == "euro":
        negativo = valore < 0
        v_abs = abs(valore)
        testo = f"{v_abs:,.0f}".replace(",", ".")
        return f"-€ {testo}" if negativo else f"€ {testo}"

    elif formato == "euro_k":
        negativo = valore < 0
        v_abs = abs(valore)
        testo = f"{v_abs / 1000:,.0f}K".replace(",", ".")
        return f"-€ {testo}" if negativo else f"€ {testo}"

    elif formato == "euro_m":
        negativo = valore < 0
        v_abs = abs(valore)
        testo = f"{v_abs / 1_000_000:,.1f}M".replace(".", ",")
        return f"-€ {testo}" if negativo else f"€ {testo}"

    elif formato == "percentuale":
        pct = valore * 100
        testo = f"{pct:.1f}%".replace(".", ",")
        return testo

    elif formato == "numero":
        testo = f"{valore:,.0f}".replace(",", ".")
        return testo

    elif formato == "decimale":
        testo = f"{valore:,.2f}"
        # Converti da formato americano a italiano
        testo = testo.replace(",", "_").replace(".", ",").replace("_", ".")
        return testo

    elif formato == "giorni":
        return f"{valore:.0f} gg"

    elif formato == "mesi":
        testo = f"{valore:.1f}".replace(".", ",")
        return f"{testo} mesi"

    else:
        return str(valore)


def _formatta_delta(delta: Union[float, None], formato: str) -> Optional[str]:
    """
    Formatta il delta (variazione) per st.metric().
    Streamlit mostra il delta con freccia verde (positivo) o rossa (negativo).

    Parametri:
        delta: variazione numerica o None
        formato: formato del valore principale (per coerenza formattazione)

    Ritorna:
        Stringa formattata del delta o None se non applicabile
    """
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        return None

    delta = float(delta)

    if formato in ("euro", "euro_k", "euro_m"):
        # Delta in euro: mostra con segno
        testo = f"{abs(delta):,.0f}".replace(",", ".")
        segno = "+" if delta >= 0 else "-"
        return f"{segno}€ {testo}"

    elif formato == "percentuale":
        # Delta in punti percentuali
        pct = delta * 100
        testo = f"{abs(pct):.1f} pp".replace(".", ",")
        segno = "+" if pct >= 0 else "-"
        return f"{segno}{testo}"

    elif formato in ("numero", "giorni", "mesi", "decimale"):
        segno = "+" if delta >= 0 else ""
        testo = f"{delta:.1f}".replace(".", ",")
        return f"{segno}{testo}"

    else:
        return str(delta)


# ============================================================================
# 1. MOSTRA KPI CARD
# ============================================================================


def mostra_kpi_card(
    st_container,
    titolo: str,
    valore: Union[float, int],
    delta: Optional[Union[float, int]] = None,
    formato: str = "euro",
    help_text: str = "",
) -> None:
    """
    Visualizza una scheda metrica KPI usando st.metric() con formattazione
    appropriata.

    Parametri:
        st_container: container Streamlit (st, colonna, expander) dove
                      scrivere la metrica
        titolo: etichetta della metrica (es. 'Ricavi Totali')
        valore: valore numerico della metrica
        delta: variazione rispetto al periodo precedente (opzionale)
        formato: tipo di formattazione tra 'euro', 'euro_k', 'euro_m',
                 'percentuale', 'numero', 'decimale', 'giorni', 'mesi'
        help_text: testo di aiuto mostrato come tooltip (opzionale)

    Ritorna:
        None (scrive direttamente nel container)
    """
    valore_fmt = _formatta_valore(valore, formato)
    delta_fmt = _formatta_delta(delta, formato)

    # Determina la direzione del delta per st.metric
    # (Streamlit colora verde il positivo e rosso il negativo di default)
    kwargs_metrica = {
        "label": titolo,
        "value": valore_fmt,
    }

    if delta_fmt is not None:
        kwargs_metrica["delta"] = delta_fmt

    if help_text:
        kwargs_metrica["help"] = help_text

    st_container.metric(**kwargs_metrica)


# ============================================================================
# 2. MOSTRA SEMAFORO
# ============================================================================


def mostra_semaforo(
    st_container,
    livello: Union[LivelliAlert, str],
) -> None:
    """
    Visualizza un indicatore semaforo colorato nel container Streamlit.

    Utilizza st.markdown() con HTML per mostrare l'icona del semaforo
    con il testo del livello.

    Parametri:
        st_container: container Streamlit dove scrivere l'indicatore
        livello: livello semaforo come LivelliAlert o stringa
                 ('verde', 'giallo', 'rosso')

    Ritorna:
        None (scrive direttamente nel container)
    """
    # Converti stringa in enum se necessario
    if isinstance(livello, str):
        livello_enum = MAPPA_STRINGA_LIVELLO.get(livello)
        if livello_enum is None:
            st_container.write(f"Livello sconosciuto: {livello}")
            return
    else:
        livello_enum = livello

    info = MAPPA_SEMAFORO.get(livello_enum)
    if info is None:
        st_container.write("Livello non valido")
        return

    html_semaforo = (
        f'<span style="font-size: 1.5em;">{info["icona"]}</span> '
        f'<span style="color: {info["colore"]}; font-weight: bold; '
        f'font-size: 1.1em;">{info["etichetta"]}</span>'
    )

    st_container.markdown(html_semaforo, unsafe_allow_html=True)


# ============================================================================
# 3. RIGA KPI CONSOLIDATI
# ============================================================================


def riga_kpi_consolidati(
    st,
    totale_ricavi: float,
    mol_i: float,
    mol_i_pct: float,
    mol_g: float,
    mol_g_pct: float,
    costi_sede: float,
) -> None:
    """
    Visualizza una riga di 6 schede metriche con i KPI consolidati principali
    del gruppo, disposti in colonne equidistanti.

    Le metriche mostrate sono:
        1. Ricavi Totali (€)
        2. MOL Industriale (€) con delta = margine %
        3. MOL Ind. % (percentuale)
        4. Costi Sede (€)
        5. MOL Gestionale (€) con delta = margine %
        6. MOL Gest. % (percentuale)

    Parametri:
        st: modulo streamlit (import streamlit as st)
        totale_ricavi: ricavi consolidati totali in euro
        mol_i: MOL Industriale consolidato in euro
        mol_i_pct: margine % industriale (decimale, es. 0.15 = 15%)
        mol_g: MOL Gestionale consolidato in euro
        mol_g_pct: margine % gestionale (decimale, es. 0.08 = 8%)
        costi_sede: totale costi sede allocati in euro

    Ritorna:
        None (scrive direttamente nell'interfaccia Streamlit)
    """
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    mostra_kpi_card(
        col1,
        titolo="Ricavi Totali",
        valore=totale_ricavi,
        formato="euro_m",
        help_text="Ricavi consolidati di tutte le Unità Operative",
    )

    mostra_kpi_card(
        col2,
        titolo="MOL Industriale",
        valore=mol_i,
        formato="euro_m",
        help_text="Margine Operativo Lordo prima dei costi di sede",
    )

    mostra_kpi_card(
        col3,
        titolo="MOL Ind. %",
        valore=mol_i_pct,
        formato="percentuale",
        help_text="MOL Industriale / Ricavi Totali",
    )

    mostra_kpi_card(
        col4,
        titolo="Costi Sede",
        valore=costi_sede,
        formato="euro_m",
        help_text="Totale costi di sede allocati alle U.O.",
    )

    mostra_kpi_card(
        col5,
        titolo="MOL Gestionale",
        valore=mol_g,
        formato="euro_m",
        help_text="Margine Operativo Lordo dopo ribaltamento costi sede",
    )

    mostra_kpi_card(
        col6,
        titolo="MOL Gest. %",
        valore=mol_g_pct,
        formato="percentuale",
        help_text="MOL Gestionale / Ricavi Totali",
    )


# ============================================================================
# 4. PANNELLO ALERT
# ============================================================================


def pannello_alert(
    st_container,
    kpi_list: list,
) -> None:
    """
    Visualizza un pannello di alert con tutti i KPI in stato ROSSO o GIALLO.

    I KPI sono raggruppati per livello (prima ROSSO, poi GIALLO) e mostrati
    con icona semaforo, nome KPI, valore, target e UO di appartenenza.

    Se non ci sono alert, mostra un messaggio positivo.

    Parametri:
        st_container: container Streamlit dove scrivere il pannello
        kpi_list: lista di oggetti KPI (dataclass dal modulo kpi.py).
                  Ogni KPI ha attributi: codice, nome, valore, target,
                  alert_livello (LivelliAlert), unita_operativa

    Ritorna:
        None (scrive direttamente nel container)
    """
    # Filtra solo KPI con alert ROSSO o GIALLO
    kpi_rossi = [
        kpi for kpi in kpi_list
        if kpi.alert_livello == LivelliAlert.ROSSO
    ]
    kpi_gialli = [
        kpi for kpi in kpi_list
        if kpi.alert_livello == LivelliAlert.GIALLO
    ]

    totale_alert = len(kpi_rossi) + len(kpi_gialli)

    if totale_alert == 0:
        st_container.success(
            "Tutti i KPI sono nella norma. Nessun alert attivo."
        )
        return

    # Intestazione pannello
    st_container.markdown(
        f"### Pannello Alert ({totale_alert} "
        f"{'alert attivo' if totale_alert == 1 else 'alert attivi'})"
    )

    # --- SEZIONE ROSSO (critici) ---
    if kpi_rossi:
        st_container.markdown(
            f"#### 🔴 Alert Critici ({len(kpi_rossi)})"
        )

        for kpi in kpi_rossi:
            uo_testo = kpi.unita_operativa if kpi.unita_operativa else "Consolidato"

            # Determina formato valore per la presentazione
            valore_fmt = _formatta_valore_kpi(kpi)
            target_fmt = _formatta_target_kpi(kpi)

            st_container.markdown(
                f"- **{kpi.nome}** ({uo_testo}): "
                f"**{valore_fmt}** (target: {target_fmt})"
            )

    # --- SEZIONE GIALLO (attenzione) ---
    if kpi_gialli:
        st_container.markdown(
            f"#### 🟡 Attenzione ({len(kpi_gialli)})"
        )

        for kpi in kpi_gialli:
            uo_testo = kpi.unita_operativa if kpi.unita_operativa else "Consolidato"

            valore_fmt = _formatta_valore_kpi(kpi)
            target_fmt = _formatta_target_kpi(kpi)

            st_container.markdown(
                f"- **{kpi.nome}** ({uo_testo}): "
                f"**{valore_fmt}** (target: {target_fmt})"
            )


# ============================================================================
# HELPER INTERNI PER PANNELLO ALERT
# ============================================================================


def _formatta_valore_kpi(kpi) -> str:
    """
    Formatta il valore di un KPI in base al suo codice per la visualizzazione
    nel pannello alert.

    Parametri:
        kpi: oggetto KPI con attributi codice e valore

    Ritorna:
        Stringa formattata del valore
    """
    codici_percentuale = (
        "KPI_OCC", "KPI_MOL_I", "KPI_MOL_C",
        "KPI_SEDE_PCT", "KPI_PERS_PCT",
    )
    codici_euro = ("KPI_CASSA", "KPI_RIC_GG", "KPI_CPERS_GG")

    if kpi.codice in codici_percentuale:
        return _formatta_valore(kpi.valore, "percentuale")
    elif kpi.codice in codici_euro:
        return _formatta_valore(kpi.valore, "euro")
    elif kpi.codice in ("KPI_DSO_ASP", "KPI_DSO_PRIV", "KPI_DPO"):
        return _formatta_valore(kpi.valore, "giorni")
    elif kpi.codice == "KPI_COP_CASSA":
        return _formatta_valore(kpi.valore, "mesi")
    elif kpi.codice == "KPI_DSCR":
        return _formatta_valore(kpi.valore, "decimale")
    elif kpi.codice == "KPI_ORE_PAZ":
        return _formatta_valore(kpi.valore, "decimale")
    else:
        return str(kpi.valore)


def _formatta_target_kpi(kpi) -> str:
    """
    Formatta il target di un KPI in base al suo codice per la visualizzazione
    nel pannello alert.

    Parametri:
        kpi: oggetto KPI con attributi codice e target

    Ritorna:
        Stringa formattata del target
    """
    codici_percentuale = (
        "KPI_OCC", "KPI_MOL_I", "KPI_MOL_C",
        "KPI_SEDE_PCT", "KPI_PERS_PCT",
    )
    codici_euro = ("KPI_CASSA", "KPI_RIC_GG", "KPI_CPERS_GG")

    if kpi.codice in codici_percentuale:
        return _formatta_valore(kpi.target, "percentuale")
    elif kpi.codice in codici_euro:
        return _formatta_valore(kpi.target, "euro")
    elif kpi.codice in ("KPI_DSO_ASP", "KPI_DSO_PRIV", "KPI_DPO"):
        return _formatta_valore(kpi.target, "giorni")
    elif kpi.codice == "KPI_COP_CASSA":
        return _formatta_valore(kpi.target, "mesi")
    elif kpi.codice == "KPI_DSCR":
        return _formatta_valore(kpi.target, "decimale")
    elif kpi.codice == "KPI_ORE_PAZ":
        return _formatta_valore(kpi.target, "decimale")
    else:
        return str(kpi.target)
