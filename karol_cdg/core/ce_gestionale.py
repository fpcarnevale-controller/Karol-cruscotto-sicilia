"""
Calcolo del Conto Economico Gestionale (CE-G).

Il CE Gestionale parte dal MOL Industriale (calcolato in ce_industriale.py)
e aggiunge i costi di sede allocati tramite le logiche di ribaltamento
(definite in allocazione.py), ottenendo il risultato netto per Unità Operativa.

Struttura CE Gestionale:
    = MOL INDUSTRIALE (da ce_industriale)
    COSTI SEDE ALLOCATI
    ├── Servizi centralizzati (allocati per driver specifici)
    ├── Governance (pro-quota ricavi)
    └── Costi comuni non allocabili
    = MOL GESTIONALE (MOL-G)
    ALTRI COSTI
    ├── Ammortamenti centralizzati
    ├── Oneri finanziari (quota debito)
    └── Imposte
    = RISULTATO NETTO UNITA OPERATIVA

Autore: Karol CDG
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    VOCI_COSTI_SEDE,
    VOCI_ALTRI_COSTI,
    UNITA_OPERATIVE,
    CategoriaCostoSede,
)

logger = logging.getLogger(__name__)

# ============================================================================
# RAGGRUPPAMENTO VOCI COSTI SEDE
# ============================================================================

COSTI_SERVIZI_CENTRALIZZATI = ["CS01", "CS02", "CS03", "CS04", "CS05"]
COSTI_GOVERNANCE = ["CS10", "CS11", "CS12"]
COSTI_COMUNI_NON_ALLOCABILI = ["CS20"]


def _somma_voci_sede(costi_allocati: dict, codici: List[str]) -> float:
    """
    Somma gli importi dei costi sede allocati per i codici specificati.

    Parametri:
        costi_allocati: dizionario {codice_voce: importo_allocato}
        codici: lista codici voce da sommare

    Ritorna:
        Somma degli importi allocati
    """
    totale = 0.0
    for codice in codici:
        totale += costi_allocati.get(codice, 0.0)
    return totale


def _somma_altri_costi(altri_costi: dict, codici: List[str]) -> float:
    """
    Somma gli importi degli altri costi per i codici specificati.

    Parametri:
        altri_costi: dizionario {codice_voce: importo}
        codici: lista codici voce da sommare

    Ritorna:
        Somma degli importi
    """
    totale = 0.0
    for codice in codici:
        totale += altri_costi.get(codice, 0.0)
    return totale


# ============================================================================
# FUNZIONI PRINCIPALI
# ============================================================================


def calcola_ce_gestionale(
    ce_industriale: dict,
    costi_sede_allocati: dict,
    altri_costi: dict,
) -> dict:
    """
    Calcola il Conto Economico Gestionale completo per una Unità Operativa.

    Parte dal CE Industriale (pre-ribaltamento) e aggiunge:
    1. Costi sede allocati (servizi, governance, costi comuni)
    2. Altri costi (ammortamenti centralizzati, oneri finanziari, imposte)

    Parametri:
        ce_industriale: dizionario CE Industriale (output di calcola_ce_industriale)
        costi_sede_allocati: dizionario {codice_voce: importo_allocato} risultante
                             dal processo di allocazione per questa UO
        altri_costi: dizionario {codice_voce: importo} di ammortamenti centralizzati,
                     oneri finanziari e imposte attribuiti alla UO

    Ritorna:
        Dizionario con la struttura completa del CE Gestionale:
        {
            'codice_uo': str,
            'periodo': str,
            'nome_uo': str,
            --- sezione CE industriale (riepilogo) ---
            'totale_ricavi': float,
            'totale_costi_diretti': float,
            'mol_industriale': float,
            'margine_pct_industriale': float,
            --- sezione costi sede ---
            'dettaglio_costi_sede': {codice: importo, ...},
            'costi_servizi_centralizzati': float,
            'costi_governance': float,
            'costi_comuni_non_allocabili': float,
            'totale_costi_sede': float,
            --- MOL Gestionale ---
            'mol_gestionale': float,
            'margine_pct_gestionale': float,
            --- altri costi ---
            'dettaglio_altri_costi': {codice: importo, ...},
            'ammortamenti_centralizzati': float,
            'oneri_finanziari': float,
            'imposte': float,
            'totale_altri_costi': float,
            --- risultato netto ---
            'risultato_netto': float,
            'margine_pct_netto': float,
        }
    """
    codice_uo = ce_industriale.get("codice_uo", "N/D")
    periodo = ce_industriale.get("periodo", "N/D")

    logger.info(
        "Calcolo CE Gestionale per UO '%s', periodo '%s'", codice_uo, periodo
    )

    # --- DATI DAL CE INDUSTRIALE ---
    totale_ricavi = ce_industriale.get("totale_ricavi", 0.0)
    totale_costi_diretti = ce_industriale.get("totale_costi_diretti", 0.0)
    mol_industriale = ce_industriale.get("mol_industriale", 0.0)
    margine_pct_industriale = ce_industriale.get("margine_pct_industriale", 0.0)

    # --- SEZIONE COSTI SEDE ALLOCATI ---

    # Assicura che costi_sede_allocati sia un dizionario
    if costi_sede_allocati is None:
        costi_sede_allocati = {}

    dettaglio_costi_sede = {}
    for codice in VOCI_COSTI_SEDE:
        dettaglio_costi_sede[codice] = costi_sede_allocati.get(codice, 0.0)

    costi_servizi_centr = _somma_voci_sede(
        costi_sede_allocati, COSTI_SERVIZI_CENTRALIZZATI
    )
    costi_governance = _somma_voci_sede(costi_sede_allocati, COSTI_GOVERNANCE)
    costi_comuni = _somma_voci_sede(
        costi_sede_allocati, COSTI_COMUNI_NON_ALLOCABILI
    )
    totale_costi_sede = costi_servizi_centr + costi_governance + costi_comuni

    # --- MOL GESTIONALE ---
    mol_gestionale = mol_industriale - totale_costi_sede
    if totale_ricavi != 0.0:
        margine_pct_gestionale = mol_gestionale / totale_ricavi
    else:
        margine_pct_gestionale = 0.0

    # --- SEZIONE ALTRI COSTI ---

    if altri_costi is None:
        altri_costi = {}

    dettaglio_altri_costi = {}
    for codice in VOCI_ALTRI_COSTI:
        dettaglio_altri_costi[codice] = altri_costi.get(codice, 0.0)

    ammortamenti_centralizzati = altri_costi.get("AC01", 0.0)
    oneri_finanziari = altri_costi.get("AC02", 0.0)
    imposte = altri_costi.get("AC03", 0.0)
    totale_altri_costi = ammortamenti_centralizzati + oneri_finanziari + imposte

    # --- RISULTATO NETTO ---
    risultato_netto = mol_gestionale - totale_altri_costi
    if totale_ricavi != 0.0:
        margine_pct_netto = risultato_netto / totale_ricavi
    else:
        margine_pct_netto = 0.0

    logger.info(
        "CE Gestionale UO '%s': MOL-I=%.2f, Costi Sede=%.2f, MOL-G=%.2f (%.1f%%), "
        "Risultato Netto=%.2f (%.1f%%)",
        codice_uo,
        mol_industriale,
        totale_costi_sede,
        mol_gestionale,
        margine_pct_gestionale * 100,
        risultato_netto,
        margine_pct_netto * 100,
    )

    return {
        "codice_uo": codice_uo,
        "periodo": periodo,
        "nome_uo": ce_industriale.get("nome_uo", codice_uo),
        # Riepilogo CE Industriale
        "totale_ricavi": totale_ricavi,
        "totale_costi_diretti": totale_costi_diretti,
        "mol_industriale": mol_industriale,
        "margine_pct_industriale": margine_pct_industriale,
        # Costi sede allocati
        "dettaglio_costi_sede": dettaglio_costi_sede,
        "costi_servizi_centralizzati": costi_servizi_centr,
        "costi_governance": costi_governance,
        "costi_comuni_non_allocabili": costi_comuni,
        "totale_costi_sede": totale_costi_sede,
        # MOL Gestionale
        "mol_gestionale": mol_gestionale,
        "margine_pct_gestionale": margine_pct_gestionale,
        # Altri costi
        "dettaglio_altri_costi": dettaglio_altri_costi,
        "ammortamenti_centralizzati": ammortamenti_centralizzati,
        "oneri_finanziari": oneri_finanziari,
        "imposte": imposte,
        "totale_altri_costi": totale_altri_costi,
        # Risultato netto
        "risultato_netto": risultato_netto,
        "margine_pct_netto": margine_pct_netto,
    }


def calcola_ce_consolidato(
    lista_ce_gestionali: list,
    costi_sede_non_allocati: dict,
) -> dict:
    """
    Calcola il CE Consolidato di gruppo sommando tutti i CE Gestionali
    delle singole UO e aggiungendo i costi sede rimasti non allocati.

    I costi non allocati (tipicamente Sviluppo e costi storici da classificare)
    impattano solo sul consolidato e non sulle singole UO.

    Parametri:
        lista_ce_gestionali: lista di dizionari CE Gestionale (uno per UO)
        costi_sede_non_allocati: dizionario {voce: importo} dei costi sede
                                 non ribaltati sulle UO

    Ritorna:
        Dizionario con il CE Consolidato:
        {
            'tipo': 'consolidato',
            'periodo': str,
            'n_unita_operative': int,
            'totale_ricavi': float,
            'totale_costi_diretti': float,
            'mol_industriale_consolidato': float,
            'totale_costi_sede_allocati': float,
            'mol_gestionale_consolidato': float,
            'costi_sede_non_allocati': float,
            'mol_dopo_costi_non_allocati': float,
            'totale_altri_costi': float,
            'risultato_netto_consolidato': float,
            'margine_pct_netto_consolidato': float,
            'dettaglio_uo': list[dict],
        }
    """
    logger.info(
        "Calcolo CE Consolidato: %d Unità Operative", len(lista_ce_gestionali)
    )

    if not lista_ce_gestionali:
        logger.warning("Nessun CE Gestionale fornito per il consolidato")
        return {
            "tipo": "consolidato",
            "periodo": "N/D",
            "n_unita_operative": 0,
            "totale_ricavi": 0.0,
            "totale_costi_diretti": 0.0,
            "mol_industriale_consolidato": 0.0,
            "totale_costi_sede_allocati": 0.0,
            "mol_gestionale_consolidato": 0.0,
            "costi_sede_non_allocati": 0.0,
            "mol_dopo_costi_non_allocati": 0.0,
            "totale_altri_costi": 0.0,
            "risultato_netto_consolidato": 0.0,
            "margine_pct_netto_consolidato": 0.0,
            "dettaglio_uo": [],
        }

    # Somma per tutte le UO
    totale_ricavi = sum(ce.get("totale_ricavi", 0.0) for ce in lista_ce_gestionali)
    totale_costi_diretti = sum(
        ce.get("totale_costi_diretti", 0.0) for ce in lista_ce_gestionali
    )
    mol_industriale = sum(
        ce.get("mol_industriale", 0.0) for ce in lista_ce_gestionali
    )
    totale_costi_sede_allocati = sum(
        ce.get("totale_costi_sede", 0.0) for ce in lista_ce_gestionali
    )
    mol_gestionale = sum(
        ce.get("mol_gestionale", 0.0) for ce in lista_ce_gestionali
    )
    totale_altri = sum(
        ce.get("totale_altri_costi", 0.0) for ce in lista_ce_gestionali
    )

    # Costi sede non allocati (restano a livello holding)
    if costi_sede_non_allocati is None:
        costi_sede_non_allocati = {}
    importo_non_allocato = sum(costi_sede_non_allocati.values())

    mol_dopo_non_allocati = mol_gestionale - importo_non_allocato
    risultato_netto = mol_dopo_non_allocati - totale_altri

    if totale_ricavi != 0.0:
        margine_pct_netto = risultato_netto / totale_ricavi
    else:
        margine_pct_netto = 0.0

    # Dettaglio per UO (riepilogo sintetico)
    dettaglio_uo = []
    for ce in lista_ce_gestionali:
        dettaglio_uo.append({
            "codice_uo": ce.get("codice_uo"),
            "nome_uo": ce.get("nome_uo"),
            "totale_ricavi": ce.get("totale_ricavi", 0.0),
            "mol_industriale": ce.get("mol_industriale", 0.0),
            "totale_costi_sede": ce.get("totale_costi_sede", 0.0),
            "mol_gestionale": ce.get("mol_gestionale", 0.0),
            "risultato_netto": ce.get("risultato_netto", 0.0),
        })

    periodo = lista_ce_gestionali[0].get("periodo", "N/D")

    logger.info(
        "CE Consolidato: Ricavi=%.2f, MOL-I=%.2f, MOL-G=%.2f, "
        "Non allocati=%.2f, Netto=%.2f (%.1f%%)",
        totale_ricavi,
        mol_industriale,
        mol_gestionale,
        importo_non_allocato,
        risultato_netto,
        margine_pct_netto * 100,
    )

    return {
        "tipo": "consolidato",
        "periodo": periodo,
        "n_unita_operative": len(lista_ce_gestionali),
        "totale_ricavi": totale_ricavi,
        "totale_costi_diretti": totale_costi_diretti,
        "mol_industriale_consolidato": mol_industriale,
        "totale_costi_sede_allocati": totale_costi_sede_allocati,
        "mol_gestionale_consolidato": mol_gestionale,
        "costi_sede_non_allocati": importo_non_allocato,
        "mol_dopo_costi_non_allocati": mol_dopo_non_allocati,
        "totale_altri_costi": totale_altri,
        "risultato_netto_consolidato": risultato_netto,
        "margine_pct_netto_consolidato": margine_pct_netto,
        "dettaglio_uo": dettaglio_uo,
    }


def confronto_industriale_vs_gestionale(
    ce_ind: dict, ce_gest: dict
) -> dict:
    """
    Confronto affiancato tra CE Industriale e CE Gestionale per la stessa UO,
    evidenziando l'impatto dei costi di sede sulla performance.

    Parametri:
        ce_ind: CE Industriale della UO
        ce_gest: CE Gestionale della UO

    Ritorna:
        Dizionario con il confronto:
        {
            'codice_uo': str,
            'periodo': str,
            'totale_ricavi': float,
            'totale_costi_diretti': float,
            'mol_industriale': float,
            'margine_pct_industriale': float,
            'totale_costi_sede': float,
            'mol_gestionale': float,
            'margine_pct_gestionale': float,
            'erosione_mol': float,            # MOL-I - MOL-G
            'erosione_mol_pct': float,        # erosione / MOL-I
            'peso_costi_sede_su_ricavi': float,
        }
    """
    codice_uo = ce_ind.get("codice_uo", ce_gest.get("codice_uo", "N/D"))
    periodo = ce_ind.get("periodo", ce_gest.get("periodo", "N/D"))

    logger.info(
        "Confronto Industriale vs Gestionale per UO '%s', periodo '%s'",
        codice_uo,
        periodo,
    )

    mol_ind = ce_ind.get("mol_industriale", 0.0)
    mol_gest = ce_gest.get("mol_gestionale", 0.0)
    totale_costi_sede = ce_gest.get("totale_costi_sede", 0.0)
    totale_ricavi = ce_ind.get("totale_ricavi", 0.0)

    erosione_mol = mol_ind - mol_gest
    if mol_ind != 0.0:
        erosione_mol_pct = erosione_mol / mol_ind
    else:
        erosione_mol_pct = 0.0

    if totale_ricavi != 0.0:
        peso_sede_su_ricavi = totale_costi_sede / totale_ricavi
    else:
        peso_sede_su_ricavi = 0.0

    return {
        "codice_uo": codice_uo,
        "periodo": periodo,
        "totale_ricavi": totale_ricavi,
        "totale_costi_diretti": ce_ind.get("totale_costi_diretti", 0.0),
        "mol_industriale": mol_ind,
        "margine_pct_industriale": ce_ind.get("margine_pct_industriale", 0.0),
        "totale_costi_sede": totale_costi_sede,
        "mol_gestionale": mol_gest,
        "margine_pct_gestionale": ce_gest.get("margine_pct_gestionale", 0.0),
        "erosione_mol": erosione_mol,
        "erosione_mol_pct": erosione_mol_pct,
        "peso_costi_sede_su_ricavi": peso_sede_su_ricavi,
    }


def impatto_sede_per_uo(costi_allocati: dict) -> pd.DataFrame:
    """
    Mostra l'impatto dei costi di sede per ogni Unità Operativa,
    con dettaglio per voce di costo sede.

    Parametri:
        costi_allocati: dizionario {codice_uo: {codice_voce: importo_allocato}}
                        (output del processo di allocazione)

    Ritorna:
        DataFrame con:
            - Indice: codice UO
            - Colonne: voci di costo sede + totale
    """
    logger.info(
        "Calcolo impatto costi sede per UO: %d UO", len(costi_allocati)
    )

    righe = []
    for codice_uo, voci in costi_allocati.items():
        uo_info = UNITA_OPERATIVE.get(codice_uo)
        nome_uo = uo_info.nome if uo_info else codice_uo

        riga = {"Codice UO": codice_uo, "Nome UO": nome_uo}

        totale = 0.0
        for codice_voce, descrizione in VOCI_COSTI_SEDE.items():
            importo = voci.get(codice_voce, 0.0)
            riga[descrizione] = importo
            totale += importo

        riga["Totale Costi Sede"] = totale
        righe.append(riga)

    df = pd.DataFrame(righe)

    if not df.empty:
        df = df.set_index("Codice UO")

        # Aggiungi riga di totale
        colonne_numeriche = df.select_dtypes(include="number").columns
        riga_totale = df[colonne_numeriche].sum()
        riga_totale["Nome UO"] = "TOTALE"
        df.loc["TOTALE"] = riga_totale

    df.index.name = "Codice UO"
    return df
