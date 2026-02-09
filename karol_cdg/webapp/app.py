"""
App principale Streamlit per il Controllo di Gestione Gruppo Karol.
Avvio: streamlit run karol_cdg/webapp/app.py
"""

import sys
from pathlib import Path

# Assicura che la root del progetto sia nel path
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from karol_cdg.config import EXCEL_MASTER, UO_OPERATIVE, UNITA_OPERATIVE
from karol_cdg.elabora import elabora_completo, leggi_dati_master

# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================

st.set_page_config(
    page_title="Karol CDG - Controllo di Gestione",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Stile CSS personalizzato
st.markdown("""
<style>
    /* Header */
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1F4E79;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #1F4E79;
        margin-bottom: 1rem;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F0F4F8;
    }
    [data-testid="stSidebar"] .stRadio > label {
        font-size: 1.1rem;
    }
    /* Metriche */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
    /* Tabelle */
    .dataframe {
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# CARICAMENTO DATI (con cache)
# ============================================================================

@st.cache_data(ttl=300)
def carica_ed_elabora():
    """Carica i dati dal Master ed esegue l'elaborazione completa."""
    if not EXCEL_MASTER.exists():
        return None, None

    dati = leggi_dati_master(EXCEL_MASTER)
    risultati = elabora_completo(EXCEL_MASTER, scrivi_excel=False)
    return risultati, dati


def ricarica_dati():
    """Forza il ricaricamento dei dati svuotando la cache."""
    carica_ed_elabora.clear()
    st.rerun()


# ============================================================================
# SIDEBAR - NAVIGAZIONE
# ============================================================================

with st.sidebar:
    st.image("https://via.placeholder.com/200x60/1F4E79/FFFFFF?text=KAROL+CDG", width=200)
    st.markdown("### Controllo di Gestione")
    st.markdown("**Gruppo Karol S.p.A.**")
    st.divider()

    pagina = st.radio(
        "Navigazione",
        [
            "🏠 Home",
            "📊 CE Industriale",
            "📋 CE Gestionale",
            "🏢 Analisi Sede",
            "🎯 KPI",
            "🔮 Scenari",
            "📁 Gestione Dati",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # Info stato dati
    if EXCEL_MASTER.exists():
        dimensione = EXCEL_MASTER.stat().st_size / 1024
        st.success(f"📄 Master: {dimensione:.0f} KB")
        st.caption(f"UO operative: {len(UO_OPERATIVE)}")
    else:
        st.error("⚠️ File Master non trovato")

    if st.button("🔄 Ricarica dati", use_container_width=True):
        ricarica_dati()

    st.divider()
    st.caption("Karol CDG v1.0")
    st.caption("© 2025 Gruppo Karol S.p.A.")


# ============================================================================
# CARICAMENTO DATI
# ============================================================================

risultati, dati = carica_ed_elabora()

# ============================================================================
# ROUTING PAGINE
# ============================================================================

if risultati is None:
    st.warning("⚠️ File Excel Master non trovato. Vai su **Gestione Dati** per caricarlo.")
    st.info(f"Percorso atteso: `{EXCEL_MASTER}`")

    # Mostra comunque la pagina gestione dati
    from karol_cdg.webapp.pagine.carica_dati import mostra_carica_dati
    mostra_carica_dati()

elif pagina == "🏠 Home":
    from karol_cdg.webapp.pagine.home import mostra_home
    mostra_home(risultati, dati)

elif pagina == "📊 CE Industriale":
    from karol_cdg.webapp.pagine.ce_industriale import mostra_ce_industriale
    mostra_ce_industriale(risultati, dati)

elif pagina == "📋 CE Gestionale":
    from karol_cdg.webapp.pagine.ce_gestionale import mostra_ce_gestionale
    mostra_ce_gestionale(risultati, dati)

elif pagina == "🏢 Analisi Sede":
    from karol_cdg.webapp.pagine.analisi_sede import mostra_analisi_sede
    mostra_analisi_sede(risultati, dati)

elif pagina == "🎯 KPI":
    from karol_cdg.webapp.pagine.kpi import mostra_kpi
    mostra_kpi(risultati, dati)

elif pagina == "🔮 Scenari":
    from karol_cdg.webapp.pagine.scenari import mostra_scenari
    mostra_scenari(risultati, dati)

elif pagina == "📁 Gestione Dati":
    from karol_cdg.webapp.pagine.carica_dati import mostra_carica_dati
    mostra_carica_dati()
