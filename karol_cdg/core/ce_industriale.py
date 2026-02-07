"""
Calcolo del Conto Economico Industriale (CE-I).

Il CE Industriale mostra la "verità industriale" di ogni Unità Operativa,
PRIMA del ribaltamento dei costi di sede. Rappresenta la performance
economica reale della struttura considerando solo ricavi e costi diretti.

Struttura CE Industriale:
    RICAVI
    ├── Ricavi da convenzione SSN/ASP (Degenza, Ambulatoriale, Laboratorio)
    ├── Ricavi privati/solvenza
    └── Altri ricavi
    COSTI DIRETTI
    ├── Personale diretto (Medici, Infermieri, OSS, Tecnici, Amministrativi)
    ├── Acquisti diretti (Farmaci, Materiale diagnostico, Vitto, Consumo)
    ├── Servizi diretti (Lavanderia, Pulizie, Manutenzioni, Utenze, Consulenze)
    └── Ammortamenti diretti
    = MOL INDUSTRIALE (MOL-I)
    = MARGINE % INDUSTRIALE

Autore: Karol CDG
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    VOCI_RICAVI,
    VOCI_COSTI_DIRETTI,
    UNITA_OPERATIVE,
    MESI_BREVI_IT,
)

logger = logging.getLogger(__name__)

# ============================================================================
# RAGGRUPPAMENTO VOCI
# ============================================================================

# Sotto-categorie dei ricavi
RICAVI_CONVENZIONE = ["R01", "R02", "R03"]
RICAVI_PRIVATI = ["R04", "R05", "R06"]
RICAVI_ALTRI = ["R07"]

# Sotto-categorie dei costi diretti
COSTI_PERSONALE = ["CD01", "CD02", "CD03", "CD04", "CD05"]
COSTI_ACQUISTI = ["CD10", "CD11", "CD12", "CD13"]
COSTI_SERVIZI = ["CD20", "CD21", "CD22", "CD23", "CD24"]
COSTI_AMMORTAMENTI = ["CD30"]


def _somma_voci(dati: pd.DataFrame, codici_voce: List[str]) -> float:
    """
    Somma gli importi delle voci specificate dal DataFrame.

    Il DataFrame deve avere colonne 'codice_voce' e 'importo'.

    Parametri:
        dati: DataFrame con le voci contabili
        codici_voce: lista dei codici voce da sommare

    Ritorna:
        Somma degli importi corrispondenti ai codici voce
    """
    if dati is None or dati.empty:
        return 0.0

    maschera = dati["codice_voce"].isin(codici_voce)
    return float(dati.loc[maschera, "importo"].sum())


def _estrai_dettaglio_voci(
    dati: pd.DataFrame, codici_voce: List[str], dizionario_nomi: Dict[str, str]
) -> Dict[str, float]:
    """
    Estrae il dettaglio importo per ogni voce specificata.

    Parametri:
        dati: DataFrame con le voci contabili
        codici_voce: lista dei codici voce da estrarre
        dizionario_nomi: dizionario {codice: descrizione} per i nomi

    Ritorna:
        Dizionario {codice_voce: importo}
    """
    dettaglio = {}
    if dati is None or dati.empty:
        for codice in codici_voce:
            dettaglio[codice] = 0.0
        return dettaglio

    for codice in codici_voce:
        maschera = dati["codice_voce"] == codice
        importo = float(dati.loc[maschera, "importo"].sum()) if maschera.any() else 0.0
        dettaglio[codice] = importo

    return dettaglio


def _calcola_margine_percentuale(mol: float, ricavi: float) -> float:
    """
    Calcola il margine percentuale evitando divisione per zero.

    Parametri:
        mol: Margine Operativo Lordo
        ricavi: Totale ricavi

    Ritorna:
        Margine percentuale (es. 0.15 = 15%)
    """
    if ricavi == 0.0:
        logger.warning("Ricavi pari a zero, margine percentuale non calcolabile")
        return 0.0
    return mol / ricavi


# ============================================================================
# FUNZIONI PRINCIPALI
# ============================================================================


def calcola_ce_industriale(
    codice_uo: str,
    periodo: str,
    ricavi: pd.DataFrame,
    costi_diretti: pd.DataFrame,
    personale: pd.DataFrame,
) -> dict:
    """
    Calcola il Conto Economico Industriale completo per una Unità Operativa
    in un determinato periodo.

    Il CE Industriale considera SOLO i costi diretti della struttura,
    escludendo qualsiasi ribaltamento di costi sede.

    Parametri:
        codice_uo: codice identificativo dell'Unità Operativa (es. "VLB", "COS")
        periodo: periodo di riferimento (es. "2025-01", "2025-Q1", "2025")
        ricavi: DataFrame con colonne ['codice_voce', 'importo'] dei ricavi
        costi_diretti: DataFrame con colonne ['codice_voce', 'importo'] dei costi diretti
        personale: DataFrame con colonne ['codice_voce', 'importo'] dei costi del personale

    Ritorna:
        Dizionario con la struttura completa del CE Industriale:
        {
            'codice_uo': str,
            'periodo': str,
            'nome_uo': str,
            'dettaglio_ricavi': {codice: importo, ...},
            'ricavi_convenzione': float,
            'ricavi_privati': float,
            'ricavi_altri': float,
            'totale_ricavi': float,
            'dettaglio_costi_diretti': {codice: importo, ...},
            'costi_personale': float,
            'costi_acquisti': float,
            'costi_servizi': float,
            'costi_ammortamenti': float,
            'totale_costi_diretti': float,
            'mol_industriale': float,
            'margine_pct_industriale': float,
        }
    """
    logger.info(
        "Calcolo CE Industriale per UO '%s', periodo '%s'", codice_uo, periodo
    )

    # Recupera il nome dell'Unità Operativa dall'anagrafica
    uo_info = UNITA_OPERATIVE.get(codice_uo)
    nome_uo = uo_info.nome if uo_info else codice_uo

    # --- SEZIONE RICAVI ---

    # Dettaglio per voce di ricavo
    dettaglio_ricavi = _estrai_dettaglio_voci(ricavi, list(VOCI_RICAVI.keys()), VOCI_RICAVI)

    # Subtotali ricavi per macro-categoria
    ricavi_convenzione = _somma_voci(ricavi, RICAVI_CONVENZIONE)
    ricavi_privati = _somma_voci(ricavi, RICAVI_PRIVATI)
    ricavi_altri = _somma_voci(ricavi, RICAVI_ALTRI)
    totale_ricavi = ricavi_convenzione + ricavi_privati + ricavi_altri

    # --- SEZIONE COSTI DIRETTI ---

    # Unisci costi diretti e personale per estrazione dettaglio completo
    tutti_costi = pd.DataFrame(columns=["codice_voce", "importo"])
    frames_costi = []
    if personale is not None and not personale.empty:
        frames_costi.append(personale)
    if costi_diretti is not None and not costi_diretti.empty:
        frames_costi.append(costi_diretti)
    if frames_costi:
        tutti_costi = pd.concat(frames_costi, ignore_index=True)

    # Dettaglio per voce di costo diretto
    dettaglio_costi = _estrai_dettaglio_voci(
        tutti_costi, list(VOCI_COSTI_DIRETTI.keys()), VOCI_COSTI_DIRETTI
    )

    # Subtotali costi per macro-categoria
    costi_personale = _somma_voci(tutti_costi, COSTI_PERSONALE)
    costi_acquisti = _somma_voci(tutti_costi, COSTI_ACQUISTI)
    costi_servizi = _somma_voci(tutti_costi, COSTI_SERVIZI)
    costi_ammortamenti = _somma_voci(tutti_costi, COSTI_AMMORTAMENTI)
    totale_costi_diretti = (
        costi_personale + costi_acquisti + costi_servizi + costi_ammortamenti
    )

    # --- CALCOLO MOL INDUSTRIALE ---

    mol_industriale = totale_ricavi - totale_costi_diretti
    margine_pct_industriale = _calcola_margine_percentuale(
        mol_industriale, totale_ricavi
    )

    logger.info(
        "CE Industriale UO '%s': Ricavi=%.2f, Costi=%.2f, MOL-I=%.2f (%.1f%%)",
        codice_uo,
        totale_ricavi,
        totale_costi_diretti,
        mol_industriale,
        margine_pct_industriale * 100,
    )

    return {
        "codice_uo": codice_uo,
        "periodo": periodo,
        "nome_uo": nome_uo,
        # Dettaglio ricavi
        "dettaglio_ricavi": dettaglio_ricavi,
        "ricavi_convenzione": ricavi_convenzione,
        "ricavi_privati": ricavi_privati,
        "ricavi_altri": ricavi_altri,
        "totale_ricavi": totale_ricavi,
        # Dettaglio costi
        "dettaglio_costi_diretti": dettaglio_costi,
        "costi_personale": costi_personale,
        "costi_acquisti": costi_acquisti,
        "costi_servizi": costi_servizi,
        "costi_ammortamenti": costi_ammortamenti,
        "totale_costi_diretti": totale_costi_diretti,
        # Risultato
        "mol_industriale": mol_industriale,
        "margine_pct_industriale": margine_pct_industriale,
    }


def calcola_ce_industriale_multi_periodo(
    codice_uo: str, periodi: List[str], dati: dict
) -> pd.DataFrame:
    """
    Calcola il CE Industriale per una UO su più periodi, restituendo
    un DataFrame con le colonne corrispondenti ai periodi.

    Utile per visualizzare l'andamento mensile o trimestrale della struttura.

    Parametri:
        codice_uo: codice UO
        periodi: lista di periodi (es. ["2025-01", "2025-02", ...])
        dati: dizionario {periodo: {'ricavi': DataFrame, 'costi_diretti': DataFrame,
              'personale': DataFrame}}

    Ritorna:
        DataFrame con indice = voci CE e colonne = periodi
    """
    logger.info(
        "Calcolo CE Industriale multi-periodo per UO '%s': %d periodi",
        codice_uo,
        len(periodi),
    )

    risultati = {}

    for periodo in periodi:
        dati_periodo = dati.get(periodo, {})
        ce = calcola_ce_industriale(
            codice_uo=codice_uo,
            periodo=periodo,
            ricavi=dati_periodo.get("ricavi", pd.DataFrame()),
            costi_diretti=dati_periodo.get("costi_diretti", pd.DataFrame()),
            personale=dati_periodo.get("personale", pd.DataFrame()),
        )
        risultati[periodo] = ce

    # Costruisci DataFrame con le righe principali del CE
    righe_ce = [
        ("Ricavi da convenzione", "ricavi_convenzione"),
        ("Ricavi privati/solvenza", "ricavi_privati"),
        ("Altri ricavi", "ricavi_altri"),
        ("TOTALE RICAVI", "totale_ricavi"),
        ("Costi personale diretto", "costi_personale"),
        ("Acquisti diretti", "costi_acquisti"),
        ("Servizi diretti", "costi_servizi"),
        ("Ammortamenti diretti", "costi_ammortamenti"),
        ("TOTALE COSTI DIRETTI", "totale_costi_diretti"),
        ("MOL INDUSTRIALE", "mol_industriale"),
        ("MARGINE % INDUSTRIALE", "margine_pct_industriale"),
    ]

    dati_tabella = {}
    for etichetta, chiave in righe_ce:
        dati_tabella[etichetta] = {
            periodo: risultati[periodo][chiave] for periodo in periodi
        }

    df = pd.DataFrame(dati_tabella).T
    df.columns.name = "Periodo"
    df.index.name = "Voce CE Industriale"

    return df


def confronto_ce_industriale(ce_corrente: dict, ce_precedente: dict) -> dict:
    """
    Confronta due Conti Economici Industriali (tipicamente anno corrente vs precedente)
    calcolando le variazioni assolute e percentuali per ogni voce.

    Parametri:
        ce_corrente: CE Industriale del periodo corrente
        ce_precedente: CE Industriale del periodo di confronto

    Ritorna:
        Dizionario con le variazioni:
        {
            'codice_uo': str,
            'periodo_corrente': str,
            'periodo_precedente': str,
            'confronto': {
                voce: {
                    'corrente': float,
                    'precedente': float,
                    'delta': float,
                    'delta_pct': float
                }
            }
        }
    """
    logger.info(
        "Confronto CE Industriale UO '%s': %s vs %s",
        ce_corrente.get("codice_uo", "N/D"),
        ce_corrente.get("periodo", "N/D"),
        ce_precedente.get("periodo", "N/D"),
    )

    voci_da_confrontare = [
        "ricavi_convenzione",
        "ricavi_privati",
        "ricavi_altri",
        "totale_ricavi",
        "costi_personale",
        "costi_acquisti",
        "costi_servizi",
        "costi_ammortamenti",
        "totale_costi_diretti",
        "mol_industriale",
        "margine_pct_industriale",
    ]

    confronto = {}
    for voce in voci_da_confrontare:
        valore_corrente = ce_corrente.get(voce, 0.0)
        valore_precedente = ce_precedente.get(voce, 0.0)
        delta = valore_corrente - valore_precedente

        if valore_precedente != 0.0:
            delta_pct = delta / abs(valore_precedente)
        else:
            delta_pct = 0.0

        confronto[voce] = {
            "corrente": valore_corrente,
            "precedente": valore_precedente,
            "delta": delta,
            "delta_pct": delta_pct,
        }

    return {
        "codice_uo": ce_corrente.get("codice_uo", "N/D"),
        "periodo_corrente": ce_corrente.get("periodo", "N/D"),
        "periodo_precedente": ce_precedente.get("periodo", "N/D"),
        "confronto": confronto,
    }


def confronto_con_budget(ce_attuale: dict, ce_budget: dict) -> dict:
    """
    Confronta il CE Industriale attuale con il budget previsto,
    evidenziando gli scostamenti per ogni voce.

    Parametri:
        ce_attuale: CE Industriale con dati consuntivi
        ce_budget: CE Industriale con dati di budget

    Ritorna:
        Dizionario con gli scostamenti:
        {
            'codice_uo': str,
            'periodo': str,
            'scostamenti': {
                voce: {
                    'attuale': float,
                    'budget': float,
                    'scostamento': float,         # attuale - budget
                    'scostamento_pct': float,     # scostamento / budget
                    'favorevole': bool            # True se lo scostamento è positivo
                                                  # (ricavi) o negativo (costi)
                }
            }
        }
    """
    logger.info(
        "Confronto con budget CE Industriale UO '%s', periodo '%s'",
        ce_attuale.get("codice_uo", "N/D"),
        ce_attuale.get("periodo", "N/D"),
    )

    # Voci di ricavo: scostamento favorevole se attuale > budget
    voci_ricavi = [
        "ricavi_convenzione",
        "ricavi_privati",
        "ricavi_altri",
        "totale_ricavi",
        "mol_industriale",
        "margine_pct_industriale",
    ]

    # Voci di costo: scostamento favorevole se attuale < budget
    voci_costi = [
        "costi_personale",
        "costi_acquisti",
        "costi_servizi",
        "costi_ammortamenti",
        "totale_costi_diretti",
    ]

    scostamenti = {}

    for voce in voci_ricavi + voci_costi:
        valore_attuale = ce_attuale.get(voce, 0.0)
        valore_budget = ce_budget.get(voce, 0.0)
        scostamento = valore_attuale - valore_budget

        if valore_budget != 0.0:
            scostamento_pct = scostamento / abs(valore_budget)
        else:
            scostamento_pct = 0.0

        # Per i ricavi è favorevole se positivo, per i costi se negativo
        if voce in voci_ricavi:
            favorevole = scostamento >= 0
        else:
            favorevole = scostamento <= 0

        scostamenti[voce] = {
            "attuale": valore_attuale,
            "budget": valore_budget,
            "scostamento": scostamento,
            "scostamento_pct": scostamento_pct,
            "favorevole": favorevole,
        }

    return {
        "codice_uo": ce_attuale.get("codice_uo", "N/D"),
        "periodo": ce_attuale.get("periodo", "N/D"),
        "scostamenti": scostamenti,
    }


def riepilogo_ce_tutte_uo(periodo: str, dati_uo: dict) -> pd.DataFrame:
    """
    Genera una tabella riepilogativa del CE Industriale per tutte le UO
    in un determinato periodo.

    Utile per confronto orizzontale delle performance delle strutture.

    Parametri:
        periodo: periodo di riferimento
        dati_uo: dizionario {codice_uo: {'ricavi': DataFrame,
                 'costi_diretti': DataFrame, 'personale': DataFrame}}

    Ritorna:
        DataFrame con indice = codice UO e colonne = voci principali CE
    """
    logger.info(
        "Riepilogo CE Industriale tutte le UO, periodo '%s'", periodo
    )

    righe = []

    for codice_uo, dati in dati_uo.items():
        ce = calcola_ce_industriale(
            codice_uo=codice_uo,
            periodo=periodo,
            ricavi=dati.get("ricavi", pd.DataFrame()),
            costi_diretti=dati.get("costi_diretti", pd.DataFrame()),
            personale=dati.get("personale", pd.DataFrame()),
        )

        righe.append({
            "Codice UO": codice_uo,
            "Nome UO": ce["nome_uo"],
            "Ricavi Convenzione": ce["ricavi_convenzione"],
            "Ricavi Privati": ce["ricavi_privati"],
            "Altri Ricavi": ce["ricavi_altri"],
            "Totale Ricavi": ce["totale_ricavi"],
            "Costi Personale": ce["costi_personale"],
            "Costi Acquisti": ce["costi_acquisti"],
            "Costi Servizi": ce["costi_servizi"],
            "Ammortamenti": ce["costi_ammortamenti"],
            "Totale Costi Diretti": ce["totale_costi_diretti"],
            "MOL Industriale": ce["mol_industriale"],
            "Margine % Industriale": ce["margine_pct_industriale"],
        })

    df = pd.DataFrame(righe)

    if not df.empty:
        df = df.set_index("Codice UO")

        # Aggiungi riga di totale consolidato
        riga_totale = df.select_dtypes(include="number").sum()
        # Ricalcola il margine % sul totale (non somma dei margini)
        if riga_totale.get("Totale Ricavi", 0) != 0:
            riga_totale["Margine % Industriale"] = (
                riga_totale["MOL Industriale"] / riga_totale["Totale Ricavi"]
            )
        else:
            riga_totale["Margine % Industriale"] = 0.0
        riga_totale["Nome UO"] = "TOTALE CONSOLIDATO"
        df.loc["TOTALE"] = riga_totale

    df.index.name = "Codice UO"
    return df
