"""
Modulo di simulazione scenari per ristrutturazione organizzativa.

Permette di simulare l'impatto economico e finanziario di interventi
organizzativi sul Gruppo Karol, sia a livello sede che a livello UO.

LEVE DISPONIBILI - SEDE:
    - Riduzione FTE (eliminare posizione, non sostituire uscita)
    - Eliminazione costo (rinegoziazione, internalizzazione)
    - Esternalizzazione servizio (outsourcing)
    - Riallocazione personale (da sede a UO produttiva)

LEVE DISPONIBILI - UO:
    - Modifica organico (aggiunta/riduzione personale)
    - Cambio mix produttivo (più ambulatoriale, meno degenza, ecc.)
    - Chiusura/apertura struttura
    - Variazione tariffe/prezzi
    - Variazione target occupancy

WORKFLOW:
    1. Definizione interventi (lista di Intervento)
    2. Raggruppamento in Scenario (con nome, descrizione, stato)
    3. Calcolo impatto economico (delta ricavi, costi, MOL)
    4. Calcolo impatto finanziario (investimento, payback, impatto cassa)
    5. Confronto scenari alternativi
    6. Generazione report

Autore: Karol CDG
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    StatoScenario,
    UNITA_OPERATIVE,
    MESI_IT,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class Intervento:
    """
    Singolo intervento di ristrutturazione all'interno di uno scenario.

    Attributi:
        tipo: ambito dell'intervento ('SEDE' o 'UO')
        unita_operativa: codice UO coinvolta (None se intervento sede)
        leva: tipo di leva utilizzata (es. 'riduzione_fte',
              'elimina_costo', 'variazione_occupancy', ecc.)
        valore_attuale: valore corrente del parametro modificato
        valore_target: valore target dopo l'intervento
        costo_implementazione: costo una tantum per implementare l'intervento
        tempo_implementazione_mesi: mesi necessari per la piena implementazione
        note: note esplicative
    """
    tipo: str  # 'SEDE' o 'UO'
    unita_operativa: Optional[str]
    leva: str
    valore_attuale: float
    valore_target: float
    costo_implementazione: float = 0.0
    tempo_implementazione_mesi: int = 0
    note: str = ""


@dataclass
class Scenario:
    """
    Insieme organico di interventi che formano uno scenario di ristrutturazione.

    Attributi:
        nome: nome dello scenario (es. "Piano Efficienza Sede 2025")
        descrizione: descrizione dettagliata dello scenario
        stato: stato corrente dello scenario (BOZZA, VALUTATO, ecc.)
        interventi: lista degli interventi previsti
        data_creazione: data di creazione dello scenario
    """
    nome: str
    descrizione: str
    stato: StatoScenario = StatoScenario.BOZZA
    interventi: List[Intervento] = field(default_factory=list)
    data_creazione: date = field(default_factory=date.today)


# ============================================================================
# LEVE DISPONIBILI (costanti per validazione)
# ============================================================================

LEVE_SEDE = [
    "riduzione_fte",
    "elimina_costo",
    "esternalizza_servizio",
    "riallocazione_personale",
]

LEVE_UO = [
    "modifica_organico",
    "cambio_mix_produttivo",
    "chiusura_struttura",
    "apertura_struttura",
    "variazione_prezzi",
    "variazione_occupancy",
]


# ============================================================================
# CALCOLO IMPATTO ECONOMICO
# ============================================================================


def calcola_impatto_economico(
    scenario: Scenario, dati_attuali: dict
) -> dict:
    """
    Calcola l'impatto economico complessivo di uno scenario,
    sommando gli effetti di tutti gli interventi previsti.

    Per ogni tipo di leva, calcola:
    - Delta ricavi (aumento o riduzione)
    - Delta costi (risparmio o nuovo costo)
    - Delta MOL
    - Delta MOL %

    Parametri:
        scenario: lo scenario da valutare
        dati_attuali: dizionario con i dati economici attuali:
            {
                'totale_ricavi': float,
                'totale_costi': float,
                'mol': float,
                'costi_personale_sede': float,
                'costi_servizi_sede': float,
                'dati_uo': {codice_uo: {'ricavi': float, 'costi': float, ...}}
            }

    Ritorna:
        Dizionario con l'impatto economico:
        {
            'scenario_nome': str,
            'delta_ricavi': float,
            'delta_costi': float,
            'delta_mol': float,
            'delta_mol_pct': float,
            'mol_attuale': float,
            'mol_proiettato': float,
            'margine_attuale_pct': float,
            'margine_proiettato_pct': float,
            'dettaglio_interventi': list[dict],
            'costo_implementazione_totale': float,
        }
    """
    logger.info(
        "Calcolo impatto economico scenario '%s': %d interventi",
        scenario.nome,
        len(scenario.interventi),
    )

    totale_ricavi = dati_attuali.get("totale_ricavi", 0.0)
    totale_costi = dati_attuali.get("totale_costi", 0.0)
    mol_attuale = dati_attuali.get("mol", 0.0)

    delta_ricavi_totale = 0.0
    delta_costi_totale = 0.0
    costo_implementazione_totale = 0.0
    dettaglio_interventi = []

    for intervento in scenario.interventi:
        delta_ricavi = 0.0
        delta_costi = 0.0
        descrizione_effetto = ""

        if intervento.leva == "riduzione_fte":
            # Riduzione personale: risparmio = valore_attuale - valore_target
            # (dove valore_attuale è il costo FTE, valore_target è 0 o costo ridotto)
            risparmio = intervento.valore_attuale - intervento.valore_target
            delta_costi = -risparmio  # Costo si riduce
            descrizione_effetto = (
                f"Riduzione FTE: risparmio annuo {risparmio:,.2f} euro"
            )

        elif intervento.leva == "elimina_costo":
            # Eliminazione voce di costo
            risparmio = intervento.valore_attuale - intervento.valore_target
            delta_costi = -risparmio
            descrizione_effetto = (
                f"Eliminazione costo: risparmio annuo {risparmio:,.2f} euro"
            )

        elif intervento.leva == "esternalizza_servizio":
            # Esternalizzazione: costo attuale sostituito da costo esterno
            # valore_attuale = costo interno, valore_target = costo esterno
            delta_costi = intervento.valore_target - intervento.valore_attuale
            if delta_costi < 0:
                descrizione_effetto = (
                    f"Esternalizzazione: risparmio annuo {abs(delta_costi):,.2f} euro"
                )
            else:
                descrizione_effetto = (
                    f"Esternalizzazione: costo aggiuntivo annuo "
                    f"{delta_costi:,.2f} euro"
                )

        elif intervento.leva == "riallocazione_personale":
            # Riallocazione da sede a UO: costo sede si riduce,
            # ma costo UO non cambia (la persona resta nel gruppo)
            # L'effetto è migliorare il CE delle UO tramite ribaltamento minore
            risparmio_sede = intervento.valore_attuale - intervento.valore_target
            delta_costi = -risparmio_sede
            descrizione_effetto = (
                f"Riallocazione: riduzione costi sede {risparmio_sede:,.2f} euro/anno"
            )

        elif intervento.leva == "variazione_occupancy":
            # Variazione occupancy: impatto sui ricavi
            # valore_attuale = occupancy attuale %, valore_target = occupancy target %
            uo_code = intervento.unita_operativa
            dati_uo = dati_attuali.get("dati_uo", {}).get(uo_code, {})
            ricavi_uo = dati_uo.get("ricavi", 0.0)
            occupancy_attuale = intervento.valore_attuale

            if occupancy_attuale > 0:
                ricavo_per_punto_occ = ricavi_uo / occupancy_attuale
                delta_occ = intervento.valore_target - occupancy_attuale
                delta_ricavi = ricavo_per_punto_occ * delta_occ
            descrizione_effetto = (
                f"Variazione occupancy UO '{uo_code}': "
                f"da {intervento.valore_attuale:.1%} a {intervento.valore_target:.1%}, "
                f"delta ricavi {delta_ricavi:,.2f} euro"
            )

        elif intervento.leva == "variazione_prezzi":
            # Variazione prezzi: impatto diretto sui ricavi
            delta_ricavi = intervento.valore_target - intervento.valore_attuale
            descrizione_effetto = (
                f"Variazione prezzi: delta ricavi {delta_ricavi:,.2f} euro/anno"
            )

        elif intervento.leva == "modifica_organico":
            # Modifica organico UO: aumento o riduzione costi personale
            delta_costi = intervento.valore_target - intervento.valore_attuale
            descrizione_effetto = (
                f"Modifica organico: delta costi {delta_costi:,.2f} euro/anno"
            )

        elif intervento.leva == "cambio_mix_produttivo":
            # Cambio mix: impatto su ricavi (mix più remunerativo o meno)
            delta_ricavi = intervento.valore_target - intervento.valore_attuale
            descrizione_effetto = (
                f"Cambio mix produttivo: delta ricavi {delta_ricavi:,.2f} euro/anno"
            )

        elif intervento.leva == "chiusura_struttura":
            # Chiusura: perdita ricavi ma risparmio costi
            uo_code = intervento.unita_operativa
            dati_uo = dati_attuali.get("dati_uo", {}).get(uo_code, {})
            delta_ricavi = -dati_uo.get("ricavi", 0.0)
            delta_costi = -dati_uo.get("costi", 0.0)
            descrizione_effetto = (
                f"Chiusura UO '{uo_code}': ricavi persi {abs(delta_ricavi):,.2f}, "
                f"costi risparmiati {abs(delta_costi):,.2f}"
            )

        elif intervento.leva == "apertura_struttura":
            # Apertura: nuovi ricavi e nuovi costi
            delta_ricavi = intervento.valore_target  # ricavi previsti
            delta_costi = intervento.valore_attuale  # costi previsti
            descrizione_effetto = (
                f"Apertura nuova struttura: ricavi previsti {delta_ricavi:,.2f}, "
                f"costi previsti {delta_costi:,.2f}"
            )

        else:
            logger.warning(
                "Leva non riconosciuta: '%s'", intervento.leva
            )
            descrizione_effetto = f"Leva '{intervento.leva}' non gestita"

        delta_ricavi_totale += delta_ricavi
        delta_costi_totale += delta_costi
        costo_implementazione_totale += intervento.costo_implementazione

        dettaglio_interventi.append({
            "tipo": intervento.tipo,
            "unita_operativa": intervento.unita_operativa,
            "leva": intervento.leva,
            "delta_ricavi": round(delta_ricavi, 2),
            "delta_costi": round(delta_costi, 2),
            "delta_mol": round(delta_ricavi - delta_costi, 2),
            "costo_implementazione": intervento.costo_implementazione,
            "tempo_mesi": intervento.tempo_implementazione_mesi,
            "effetto": descrizione_effetto,
        })

    # Calcolo MOL proiettato
    delta_mol = delta_ricavi_totale - delta_costi_totale
    mol_proiettato = mol_attuale + delta_mol

    ricavi_proiettati = totale_ricavi + delta_ricavi_totale
    if totale_ricavi > 0:
        margine_attuale_pct = mol_attuale / totale_ricavi
    else:
        margine_attuale_pct = 0.0

    if ricavi_proiettati > 0:
        margine_proiettato_pct = mol_proiettato / ricavi_proiettati
    else:
        margine_proiettato_pct = 0.0

    delta_mol_pct = margine_proiettato_pct - margine_attuale_pct

    logger.info(
        "Impatto economico scenario '%s': delta_ricavi=%.2f, delta_costi=%.2f, "
        "delta_MOL=%.2f, MOL attuale=%.1f%% -> proiettato=%.1f%%",
        scenario.nome,
        delta_ricavi_totale,
        delta_costi_totale,
        delta_mol,
        margine_attuale_pct * 100,
        margine_proiettato_pct * 100,
    )

    return {
        "scenario_nome": scenario.nome,
        "delta_ricavi": round(delta_ricavi_totale, 2),
        "delta_costi": round(delta_costi_totale, 2),
        "delta_mol": round(delta_mol, 2),
        "delta_mol_pct": round(delta_mol_pct, 4),
        "mol_attuale": round(mol_attuale, 2),
        "mol_proiettato": round(mol_proiettato, 2),
        "margine_attuale_pct": round(margine_attuale_pct, 4),
        "margine_proiettato_pct": round(margine_proiettato_pct, 4),
        "dettaglio_interventi": dettaglio_interventi,
        "costo_implementazione_totale": round(costo_implementazione_totale, 2),
    }


# ============================================================================
# CALCOLO IMPATTO FINANZIARIO
# ============================================================================


def calcola_impatto_finanziario(
    scenario: Scenario, dati_attuali: dict
) -> dict:
    """
    Calcola l'impatto finanziario di uno scenario, focalizzato su
    investimento richiesto, payback e impatto sulla cassa.

    Parametri:
        scenario: lo scenario da valutare
        dati_attuali: dizionario con i dati economici/finanziari attuali
            (stesso formato di calcola_impatto_economico)

    Ritorna:
        Dizionario con l'impatto finanziario:
        {
            'scenario_nome': str,
            'investimento_richiesto': float,
            'payback_mesi': float,        # mesi per recuperare l'investimento
            'impatto_cassa_anno1': float,  # impatto netto cassa primo anno
            'risparmio_annuo_regime': float,
            'roi_annuo': float,           # risparmio regime / investimento
        }
    """
    logger.info(
        "Calcolo impatto finanziario scenario '%s'", scenario.nome
    )

    # Calcola prima l'impatto economico per avere i delta
    impatto_eco = calcola_impatto_economico(scenario, dati_attuali)

    investimento_totale = impatto_eco["costo_implementazione_totale"]
    delta_mol = impatto_eco["delta_mol"]

    # Risparmio annuo a regime (quando tutti gli interventi sono implementati)
    risparmio_annuo_regime = delta_mol

    # Payback: mesi per recuperare l'investimento
    if risparmio_annuo_regime > 0 and investimento_totale > 0:
        risparmio_mensile = risparmio_annuo_regime / 12
        payback_mesi = investimento_totale / risparmio_mensile
    elif investimento_totale == 0:
        payback_mesi = 0.0
    else:
        payback_mesi = float("inf")  # Non recuperabile

    # Impatto cassa anno 1: tiene conto del tempo di implementazione
    # Gli interventi producono effetti parziali nel primo anno
    impatto_anno1 = 0.0
    for intervento in scenario.interventi:
        mesi_impl = intervento.tempo_implementazione_mesi
        if mesi_impl >= 12:
            # L'intervento non è a regime nel primo anno
            mesi_effetto = max(0, 12 - mesi_impl)
        else:
            mesi_effetto = 12 - mesi_impl

        # Quota di risparmio/impatto proporzionale ai mesi effettivi
        # Approssimazione lineare dell'entrata a regime
        dettaglio = None
        for d in impatto_eco["dettaglio_interventi"]:
            if (
                d["leva"] == intervento.leva
                and d["unita_operativa"] == intervento.unita_operativa
            ):
                dettaglio = d
                break

        if dettaglio:
            effetto_annuo = dettaglio["delta_mol"]
            effetto_anno1 = effetto_annuo * (mesi_effetto / 12)
            impatto_anno1 += effetto_anno1

    # Sottrai il costo di implementazione dall'impatto anno 1
    impatto_cassa_anno1 = impatto_anno1 - investimento_totale

    # ROI annuo
    if investimento_totale > 0:
        roi_annuo = risparmio_annuo_regime / investimento_totale
    else:
        roi_annuo = float("inf") if risparmio_annuo_regime > 0 else 0.0

    logger.info(
        "Impatto finanziario scenario '%s': investimento=%.2f, "
        "payback=%.1f mesi, impatto cassa anno1=%.2f, ROI=%.1f%%",
        scenario.nome,
        investimento_totale,
        payback_mesi if payback_mesi != float("inf") else -1,
        impatto_cassa_anno1,
        roi_annuo * 100 if roi_annuo != float("inf") else 999,
    )

    return {
        "scenario_nome": scenario.nome,
        "investimento_richiesto": round(investimento_totale, 2),
        "payback_mesi": round(payback_mesi, 1) if payback_mesi != float("inf") else None,
        "impatto_cassa_anno1": round(impatto_cassa_anno1, 2),
        "risparmio_annuo_regime": round(risparmio_annuo_regime, 2),
        "roi_annuo": round(roi_annuo, 4) if roi_annuo != float("inf") else None,
    }


# ============================================================================
# CONFRONTO SCENARI
# ============================================================================


def confronta_scenari(
    scenari: List[Scenario], dati_attuali: dict
) -> pd.DataFrame:
    """
    Confronto affiancato di più scenari alternativi.

    Parametri:
        scenari: lista di Scenario da confrontare
        dati_attuali: dati economici/finanziari attuali

    Ritorna:
        DataFrame con righe = metriche e colonne = scenari
    """
    logger.info("Confronto %d scenari", len(scenari))

    righe_dati = {}

    for scenario in scenari:
        impatto_eco = calcola_impatto_economico(scenario, dati_attuali)
        impatto_fin = calcola_impatto_finanziario(scenario, dati_attuali)

        nome = scenario.nome

        righe_dati[nome] = {
            "N. interventi": len(scenario.interventi),
            "Stato": scenario.stato.value,
            "Delta ricavi": impatto_eco["delta_ricavi"],
            "Delta costi": impatto_eco["delta_costi"],
            "Delta MOL": impatto_eco["delta_mol"],
            "MOL attuale": impatto_eco["mol_attuale"],
            "MOL proiettato": impatto_eco["mol_proiettato"],
            "Margine attuale %": impatto_eco["margine_attuale_pct"],
            "Margine proiettato %": impatto_eco["margine_proiettato_pct"],
            "Investimento richiesto": impatto_fin["investimento_richiesto"],
            "Payback (mesi)": impatto_fin["payback_mesi"],
            "Impatto cassa anno 1": impatto_fin["impatto_cassa_anno1"],
            "Risparmio annuo a regime": impatto_fin["risparmio_annuo_regime"],
            "ROI annuo": impatto_fin["roi_annuo"],
        }

    df = pd.DataFrame(righe_dati)
    df.index.name = "Metrica"
    return df


# ============================================================================
# SIMULAZIONI SPECIFICHE
# ============================================================================


def simula_riduzione_fte(
    uo: str, qualifica: str, n_fte: int, costo_medio: float
) -> dict:
    """
    Simula la riduzione di FTE (Full-Time Equivalent) in una UO o sede.

    Parametri:
        uo: codice UO ('SEDE' per la sede)
        qualifica: qualifica del personale (es. "Amministrativo", "Infermiere")
        n_fte: numero di FTE da ridurre
        costo_medio: costo medio annuo per FTE (lordo azienda)

    Ritorna:
        Dizionario con:
        {
            'uo': str,
            'qualifica': str,
            'n_fte_ridotti': int,
            'costo_medio_fte': float,
            'risparmio_annuo': float,
            'costo_tfr_stimato': float,    # stima TFR/incentivo uscita
            'tempo_implementazione_mesi': int,
            'note': str,
        }
    """
    risparmio_annuo = n_fte * costo_medio

    # Stima costo TFR/incentivo: circa 50% del costo annuo per FTE
    costo_tfr_stimato = n_fte * costo_medio * 0.5

    # Tempo implementazione: 3-6 mesi per processi di riorganizzazione
    tempo_mesi = 3 if n_fte <= 2 else 6

    logger.info(
        "Simulazione riduzione %d FTE '%s' in '%s': "
        "risparmio annuo=%.2f, costo TFR=%.2f",
        n_fte,
        qualifica,
        uo,
        risparmio_annuo,
        costo_tfr_stimato,
    )

    return {
        "uo": uo,
        "qualifica": qualifica,
        "n_fte_ridotti": n_fte,
        "costo_medio_fte": costo_medio,
        "risparmio_annuo": round(risparmio_annuo, 2),
        "costo_tfr_stimato": round(costo_tfr_stimato, 2),
        "tempo_implementazione_mesi": tempo_mesi,
        "note": (
            f"Riduzione di {n_fte} FTE {qualifica} in {uo}. "
            f"Risparmio annuo a regime: {risparmio_annuo:,.2f} euro. "
            f"Costo una tantum stimato (TFR/incentivo): {costo_tfr_stimato:,.2f} euro."
        ),
    }


def simula_variazione_occupancy(
    uo: str, delta_pct: float, ricavo_giornata: float, posti_letto: int
) -> dict:
    """
    Simula la variazione del tasso di occupazione di una UO.

    Parametri:
        uo: codice UO
        delta_pct: variazione percentuale dell'occupancy
                   (es. 0.05 = +5 punti percentuali)
        ricavo_giornata: ricavo medio per giornata di degenza (euro)
        posti_letto: numero posti letto della struttura

    Ritorna:
        Dizionario con:
        {
            'uo': str,
            'posti_letto': int,
            'delta_occupancy_pct': float,
            'giornate_aggiuntive_annue': int,
            'ricavi_aggiuntivi_annui': float,
            'costi_variabili_aggiuntivi': float,  # stima costi variabili marginali
            'margine_contribuzione': float,
            'note': str,
        }
    """
    # Giornate aggiuntive annue = PL * delta_occupancy% * 365
    giornate_aggiuntive = round(posti_letto * delta_pct * 365)

    # Ricavi aggiuntivi
    ricavi_aggiuntivi = giornate_aggiuntive * ricavo_giornata

    # Costi variabili marginali: circa 25-30% del ricavo aggiuntivo
    # (vitto, lavanderia, materiale consumo - il personale è spesso fisso)
    percentuale_costi_variabili = 0.25
    costi_variabili = ricavi_aggiuntivi * percentuale_costi_variabili

    # Margine di contribuzione
    margine = ricavi_aggiuntivi - costi_variabili

    logger.info(
        "Simulazione variazione occupancy UO '%s': delta=%.1f%%, "
        "giornate aggiuntive=%d, ricavi aggiuntivi=%.2f, margine=%.2f",
        uo,
        delta_pct * 100,
        giornate_aggiuntive,
        ricavi_aggiuntivi,
        margine,
    )

    segno = "+" if delta_pct >= 0 else ""
    return {
        "uo": uo,
        "posti_letto": posti_letto,
        "delta_occupancy_pct": delta_pct,
        "giornate_aggiuntive_annue": giornate_aggiuntive,
        "ricavi_aggiuntivi_annui": round(ricavi_aggiuntivi, 2),
        "costi_variabili_aggiuntivi": round(costi_variabili, 2),
        "margine_contribuzione": round(margine, 2),
        "note": (
            f"Variazione occupancy UO '{uo}': {segno}{delta_pct:.1%} "
            f"({posti_letto} PL). "
            f"Giornate {segno}{giornate_aggiuntive}/anno. "
            f"Ricavi aggiuntivi: {ricavi_aggiuntivi:,.2f} euro/anno. "
            f"Margine di contribuzione: {margine:,.2f} euro/anno."
        ),
    }


# ============================================================================
# GENERAZIONE REPORT
# ============================================================================


def genera_report_scenario(
    scenario: Scenario, impatto_eco: dict, impatto_fin: dict
) -> str:
    """
    Genera un report testuale dello scenario con tutti i dettagli
    dell'impatto economico e finanziario.

    Parametri:
        scenario: lo scenario analizzato
        impatto_eco: output di calcola_impatto_economico()
        impatto_fin: output di calcola_impatto_finanziario()

    Ritorna:
        Stringa con il report formattato
    """
    linea = "=" * 72
    linea_sottile = "-" * 72

    righe = [
        linea,
        f"REPORT SCENARIO: {scenario.nome.upper()}",
        linea,
        f"Descrizione: {scenario.descrizione}",
        f"Stato: {scenario.stato.value}",
        f"Data creazione: {scenario.data_creazione.strftime('%d/%m/%Y')}",
        f"Numero interventi: {len(scenario.interventi)}",
        "",
        linea_sottile,
        "IMPATTO ECONOMICO",
        linea_sottile,
        f"  MOL attuale:                {impatto_eco['mol_attuale']:>15,.2f} euro",
        f"  Margine attuale:            {impatto_eco['margine_attuale_pct']:>14.1%}",
        "",
        f"  Delta ricavi:               {impatto_eco['delta_ricavi']:>+15,.2f} euro",
        f"  Delta costi:                {impatto_eco['delta_costi']:>+15,.2f} euro",
        f"  Delta MOL:                  {impatto_eco['delta_mol']:>+15,.2f} euro",
        "",
        f"  MOL proiettato:             {impatto_eco['mol_proiettato']:>15,.2f} euro",
        f"  Margine proiettato:         {impatto_eco['margine_proiettato_pct']:>14.1%}",
        f"  Variazione margine:         {impatto_eco['delta_mol_pct']:>+14.1%}",
        "",
        linea_sottile,
        "IMPATTO FINANZIARIO",
        linea_sottile,
        f"  Investimento richiesto:     {impatto_fin['investimento_richiesto']:>15,.2f} euro",
    ]

    payback = impatto_fin.get("payback_mesi")
    if payback is not None:
        righe.append(
            f"  Payback:                    {payback:>12.1f} mesi"
        )
    else:
        righe.append(
            "  Payback:                       non recuperabile"
        )

    righe.extend([
        f"  Impatto cassa anno 1:       {impatto_fin['impatto_cassa_anno1']:>+15,.2f} euro",
        f"  Risparmio annuo a regime:   {impatto_fin['risparmio_annuo_regime']:>15,.2f} euro",
    ])

    roi = impatto_fin.get("roi_annuo")
    if roi is not None:
        righe.append(
            f"  ROI annuo:                  {roi:>14.1%}"
        )
    else:
        righe.append(
            "  ROI annuo:                       N/A"
        )

    # Dettaglio interventi
    righe.extend([
        "",
        linea_sottile,
        "DETTAGLIO INTERVENTI",
        linea_sottile,
    ])

    for i, det in enumerate(impatto_eco.get("dettaglio_interventi", []), 1):
        righe.extend([
            f"  {i}. [{det['tipo']}] {det['leva']}",
            f"     UO: {det['unita_operativa'] or 'SEDE'}",
            f"     Effetto: {det['effetto']}",
            f"     Delta MOL: {det['delta_mol']:+,.2f} euro",
            f"     Costo implementazione: {det['costo_implementazione']:,.2f} euro",
            f"     Tempo: {det['tempo_mesi']} mesi",
            "",
        ])

    righe.append(linea)

    report = "\n".join(righe)
    logger.info(
        "Report generato per scenario '%s': %d righe", scenario.nome, len(righe)
    )
    return report
