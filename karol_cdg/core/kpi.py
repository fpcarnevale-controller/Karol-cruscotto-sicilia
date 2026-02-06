"""
Motore di calcolo KPI (Key Performance Indicators).

Calcola, organizza e valuta i KPI del sistema di controllo di gestione
Karol, suddivisi in tre famiglie:

1. KPI OPERATIVI (per singola Unità Operativa):
   - Tasso di occupazione (%) = Giornate erogate / Giornate disponibili
   - Ricavo medio per giornata = Ricavi degenza / Giornate erogate
   - Costo personale per giornata = Costi personale / Giornate erogate
   - MOL % industriale = MOL-I / Ricavi
   - Ore per paziente (OSS + Infermieri) = Ore lavorate / Giornate erogate

2. KPI ECONOMICI (consolidati):
   - MOL % consolidato
   - Peso costi sede su ricavi %
   - Costo personale su ricavi %
   - DSCR (Debt Service Coverage Ratio)

3. KPI FINANZIARI:
   - DSO clienti ASP (giorni)
   - DSO privati (giorni)
   - DPO fornitori (giorni)
   - Cassa disponibile (euro)
   - Copertura cassa (mesi)

Ogni KPI ha un sistema a semaforo (verde/giallo/rosso) basato sulle
soglie configurate in config.py.

Autore: Karol CDG
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    LivelliAlert,
    SOGLIE_SEMAFORO,
    ALERT_CONFIG,
    BENCHMARK,
    UNITA_OPERATIVE,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class KPI:
    """
    Rappresenta un singolo KPI calcolato.

    Attributi:
        codice: codice univoco del KPI (es. "KPI_OCC", "KPI_MOL_I")
        nome: nome descrittivo in italiano
        valore: valore calcolato del KPI
        target: valore target/benchmark
        alert_livello: livello semaforo (VERDE, GIALLO, ROSSO)
        unita_operativa: codice UO (None se KPI consolidato)
        periodo: periodo di riferimento
        formula_desc: descrizione della formula di calcolo
    """
    codice: str
    nome: str
    valore: float
    target: float
    alert_livello: LivelliAlert
    unita_operativa: Optional[str] = None
    periodo: str = ""
    formula_desc: str = ""


# ============================================================================
# FUNZIONI HELPER PER SEMAFORO
# ============================================================================


def _valuta_semaforo(
    valore: float, soglia_verde: float, soglia_giallo: float, invertito: bool = False
) -> LivelliAlert:
    """
    Valuta il livello semaforo per un KPI.

    Per KPI "normali" (es. occupancy): più alto è meglio
        - >= soglia_verde -> VERDE
        - >= soglia_giallo -> GIALLO
        - < soglia_giallo -> ROSSO

    Per KPI "invertiti" (es. DSO, costo personale %): più basso è meglio
        - <= soglia_verde -> VERDE
        - <= soglia_giallo -> GIALLO
        - > soglia_giallo -> ROSSO

    Parametri:
        valore: valore del KPI
        soglia_verde: soglia per livello verde
        soglia_giallo: soglia per livello giallo
        invertito: True se valori più bassi sono migliori

    Ritorna:
        LivelliAlert (VERDE, GIALLO, ROSSO)
    """
    if invertito:
        if valore <= soglia_verde:
            return LivelliAlert.VERDE
        elif valore <= soglia_giallo:
            return LivelliAlert.GIALLO
        else:
            return LivelliAlert.ROSSO
    else:
        if valore >= soglia_verde:
            return LivelliAlert.VERDE
        elif valore >= soglia_giallo:
            return LivelliAlert.GIALLO
        else:
            return LivelliAlert.ROSSO


# ============================================================================
# KPI OPERATIVI (per singola UO)
# ============================================================================


def calcola_kpi_operativi(
    codice_uo: str, periodo: str, dati: dict
) -> List[KPI]:
    """
    Calcola i KPI operativi per una singola Unità Operativa.

    Parametri:
        codice_uo: codice UO (es. "VLB", "COS")
        periodo: periodo di riferimento (es. "2025-01")
        dati: dizionario con i dati necessari:
            {
                'giornate_erogate': int,
                'giornate_disponibili': int,
                'ricavi_degenza': float,
                'costi_personale': float,
                'ore_lavorate_oss_inf': float,
                'totale_ricavi': float,
                'mol_industriale': float,
                'posti_letto': int,
            }

    Ritorna:
        Lista di KPI calcolati
    """
    logger.info(
        "Calcolo KPI operativi per UO '%s', periodo '%s'", codice_uo, periodo
    )

    kpi_list = []

    giornate_erogate = dati.get("giornate_erogate", 0)
    giornate_disponibili = dati.get("giornate_disponibili", 0)
    ricavi_degenza = dati.get("ricavi_degenza", 0.0)
    costi_personale = dati.get("costi_personale", 0.0)
    ore_lavorate = dati.get("ore_lavorate_oss_inf", 0.0)
    totale_ricavi = dati.get("totale_ricavi", 0.0)
    mol_industriale = dati.get("mol_industriale", 0.0)

    # --- 1. Tasso di occupazione ---
    if giornate_disponibili > 0:
        occupancy = giornate_erogate / giornate_disponibili
    else:
        occupancy = 0.0

    soglie_occ = SOGLIE_SEMAFORO.get("occupancy", (0.90, 0.80))
    kpi_list.append(KPI(
        codice="KPI_OCC",
        nome="Tasso di occupazione",
        valore=round(occupancy, 4),
        target=soglie_occ[0],
        alert_livello=_valuta_semaforo(occupancy, soglie_occ[0], soglie_occ[1]),
        unita_operativa=codice_uo,
        periodo=periodo,
        formula_desc="Giornate erogate / Giornate disponibili",
    ))

    # --- 2. Ricavo medio per giornata ---
    if giornate_erogate > 0:
        ricavo_giornata = ricavi_degenza / giornate_erogate
    else:
        ricavo_giornata = 0.0

    # Il target del ricavo giornata dipende dalla tipologia struttura
    uo_info = UNITA_OPERATIVE.get(codice_uo)
    target_ricavo = 0.0
    if uo_info and uo_info.tipologia:
        tip_nome = uo_info.tipologia[0].name
        benchmark = BENCHMARK.get(tip_nome)
        if benchmark and benchmark.costo_giornata_degenza_max:
            # Usiamo il valore massimo del benchmark come riferimento ricavo
            target_ricavo = benchmark.costo_giornata_degenza_max

    kpi_list.append(KPI(
        codice="KPI_RIC_GG",
        nome="Ricavo medio per giornata",
        valore=round(ricavo_giornata, 2),
        target=target_ricavo,
        alert_livello=_valuta_semaforo(
            ricavo_giornata, target_ricavo * 0.9, target_ricavo * 0.8
        ) if target_ricavo > 0 else LivelliAlert.GIALLO,
        unita_operativa=codice_uo,
        periodo=periodo,
        formula_desc="Ricavi degenza / Giornate erogate",
    ))

    # --- 3. Costo personale per giornata ---
    if giornate_erogate > 0:
        costo_pers_gg = costi_personale / giornate_erogate
    else:
        costo_pers_gg = 0.0

    target_costo_gg = 0.0
    if uo_info and uo_info.tipologia:
        tip_nome = uo_info.tipologia[0].name
        benchmark = BENCHMARK.get(tip_nome)
        if benchmark and benchmark.costo_giornata_degenza_max:
            # Target costo giornata: quota personale del benchmark
            target_costo_gg = (
                benchmark.costo_giornata_degenza_max
                * benchmark.costo_personale_su_ricavi_max
                / 100
            )

    kpi_list.append(KPI(
        codice="KPI_CPERS_GG",
        nome="Costo personale per giornata",
        valore=round(costo_pers_gg, 2),
        target=round(target_costo_gg, 2),
        alert_livello=_valuta_semaforo(
            costo_pers_gg, target_costo_gg * 0.9, target_costo_gg, invertito=True
        ) if target_costo_gg > 0 else LivelliAlert.GIALLO,
        unita_operativa=codice_uo,
        periodo=periodo,
        formula_desc="Costi personale / Giornate erogate",
    ))

    # --- 4. MOL % industriale ---
    if totale_ricavi > 0:
        mol_pct = mol_industriale / totale_ricavi
    else:
        mol_pct = 0.0

    soglie_mol = SOGLIE_SEMAFORO.get("mol_industriale", (0.15, 0.10))
    kpi_list.append(KPI(
        codice="KPI_MOL_I",
        nome="MOL % industriale",
        valore=round(mol_pct, 4),
        target=soglie_mol[0],
        alert_livello=_valuta_semaforo(mol_pct, soglie_mol[0], soglie_mol[1]),
        unita_operativa=codice_uo,
        periodo=periodo,
        formula_desc="MOL industriale / Totale ricavi",
    ))

    # --- 5. Ore per paziente (OSS + Infermieri) ---
    if giornate_erogate > 0:
        ore_paziente = ore_lavorate / giornate_erogate
    else:
        ore_paziente = 0.0

    # Target ore/paziente: standard di settore per RSA circa 2.5-3.0 ore/gg
    target_ore = 2.5
    kpi_list.append(KPI(
        codice="KPI_ORE_PAZ",
        nome="Ore per paziente (OSS + Infermieri)",
        valore=round(ore_paziente, 2),
        target=target_ore,
        alert_livello=_valuta_semaforo(
            ore_paziente, target_ore, target_ore * 0.8
        ),
        unita_operativa=codice_uo,
        periodo=periodo,
        formula_desc="Ore lavorate (OSS + Inf) / Giornate erogate",
    ))

    logger.info(
        "KPI operativi UO '%s': occupancy=%.1f%%, MOL-I=%.1f%%, %d KPI calcolati",
        codice_uo,
        occupancy * 100,
        mol_pct * 100,
        len(kpi_list),
    )

    return kpi_list


# ============================================================================
# KPI ECONOMICI (consolidati)
# ============================================================================


def calcola_kpi_economici(
    periodo: str, dati_consolidati: dict
) -> List[KPI]:
    """
    Calcola i KPI economici consolidati di gruppo.

    Parametri:
        periodo: periodo di riferimento
        dati_consolidati: dizionario con i dati consolidati:
            {
                'totale_ricavi': float,
                'mol_gestionale': float,
                'totale_costi_sede': float,
                'costi_personale_totali': float,
                'ebitda': float,
                'servizio_debito_annuale': float,
            }

    Ritorna:
        Lista di KPI calcolati
    """
    logger.info("Calcolo KPI economici consolidati, periodo '%s'", periodo)

    kpi_list = []

    totale_ricavi = dati_consolidati.get("totale_ricavi", 0.0)
    mol_gestionale = dati_consolidati.get("mol_gestionale", 0.0)
    totale_costi_sede = dati_consolidati.get("totale_costi_sede", 0.0)
    costi_personale = dati_consolidati.get("costi_personale_totali", 0.0)
    ebitda = dati_consolidati.get("ebitda", 0.0)
    servizio_debito = dati_consolidati.get("servizio_debito_annuale", 0.0)

    # --- 1. MOL % consolidato ---
    if totale_ricavi > 0:
        mol_pct_consolidato = mol_gestionale / totale_ricavi
    else:
        mol_pct_consolidato = 0.0

    soglie = SOGLIE_SEMAFORO.get("mol_consolidato", (0.12, 0.08))
    kpi_list.append(KPI(
        codice="KPI_MOL_C",
        nome="MOL % consolidato",
        valore=round(mol_pct_consolidato, 4),
        target=soglie[0],
        alert_livello=_valuta_semaforo(mol_pct_consolidato, soglie[0], soglie[1]),
        periodo=periodo,
        formula_desc="MOL gestionale / Totale ricavi consolidato",
    ))

    # --- 2. Peso costi sede su ricavi % ---
    if totale_ricavi > 0:
        peso_sede = totale_costi_sede / totale_ricavi
    else:
        peso_sede = 0.0

    soglia_sede_max = ALERT_CONFIG.get("peso_costi_sede_max_pct", 0.20)
    kpi_list.append(KPI(
        codice="KPI_SEDE_PCT",
        nome="Peso costi sede su ricavi",
        valore=round(peso_sede, 4),
        target=soglia_sede_max,
        alert_livello=_valuta_semaforo(
            peso_sede, soglia_sede_max * 0.8, soglia_sede_max, invertito=True
        ),
        periodo=periodo,
        formula_desc="Costi sede totali / Ricavi consolidati",
    ))

    # --- 3. Costo personale su ricavi % ---
    if totale_ricavi > 0:
        pers_pct = costi_personale / totale_ricavi
    else:
        pers_pct = 0.0

    soglie_pers = SOGLIE_SEMAFORO.get("costo_personale_pct", (0.55, 0.60))
    kpi_list.append(KPI(
        codice="KPI_PERS_PCT",
        nome="Costo personale su ricavi",
        valore=round(pers_pct, 4),
        target=soglie_pers[0],
        alert_livello=_valuta_semaforo(
            pers_pct, soglie_pers[0], soglie_pers[1], invertito=True
        ),
        periodo=periodo,
        formula_desc="Costi personale totali / Ricavi consolidati",
    ))

    # --- 4. DSCR (Debt Service Coverage Ratio) ---
    if servizio_debito > 0:
        dscr = ebitda / servizio_debito
    else:
        dscr = float("inf") if ebitda > 0 else 0.0

    soglie_dscr = SOGLIE_SEMAFORO.get("dscr", (1.2, 1.0))
    kpi_list.append(KPI(
        codice="KPI_DSCR",
        nome="DSCR (Debt Service Coverage Ratio)",
        valore=round(dscr, 2) if dscr != float("inf") else 999.99,
        target=soglie_dscr[0],
        alert_livello=_valuta_semaforo(dscr, soglie_dscr[0], soglie_dscr[1]),
        periodo=periodo,
        formula_desc="EBITDA / Servizio debito annuale",
    ))

    logger.info(
        "KPI economici: MOL%%=%.1f%%, Peso sede=%.1f%%, Pers%%=%.1f%%, DSCR=%.2f",
        mol_pct_consolidato * 100,
        peso_sede * 100,
        pers_pct * 100,
        dscr if dscr != float("inf") else 999.99,
    )

    return kpi_list


# ============================================================================
# KPI FINANZIARI
# ============================================================================


def calcola_kpi_finanziari(
    periodo: str, dati_finanziari: dict
) -> List[KPI]:
    """
    Calcola i KPI finanziari.

    Parametri:
        periodo: periodo di riferimento
        dati_finanziari: dizionario con i dati finanziari:
            {
                'crediti_asp': float,
                'crediti_privati': float,
                'debiti_fornitori': float,
                'ricavi_asp_periodo': float,
                'ricavi_privati_periodo': float,
                'acquisti_periodo': float,
                'giorni_periodo': int,
                'cassa_disponibile': float,
                'uscite_medie_mensili': float,
            }

    Ritorna:
        Lista di KPI calcolati
    """
    logger.info("Calcolo KPI finanziari, periodo '%s'", periodo)

    kpi_list = []

    crediti_asp = dati_finanziari.get("crediti_asp", 0.0)
    crediti_privati = dati_finanziari.get("crediti_privati", 0.0)
    debiti_fornitori = dati_finanziari.get("debiti_fornitori", 0.0)
    ricavi_asp = dati_finanziari.get("ricavi_asp_periodo", 0.0)
    ricavi_privati = dati_finanziari.get("ricavi_privati_periodo", 0.0)
    acquisti = dati_finanziari.get("acquisti_periodo", 0.0)
    giorni = dati_finanziari.get("giorni_periodo", 365)
    cassa = dati_finanziari.get("cassa_disponibile", 0.0)
    uscite_mensili = dati_finanziari.get("uscite_medie_mensili", 0.0)

    # --- 1. DSO clienti ASP ---
    dso_asp = (crediti_asp / ricavi_asp * giorni) if ricavi_asp > 0 else 0.0
    soglia_dso_asp = ALERT_CONFIG.get("dso_massimo_asp", 150)
    soglie_dso = SOGLIE_SEMAFORO.get("dso_asp", (120, 150))

    kpi_list.append(KPI(
        codice="KPI_DSO_ASP",
        nome="DSO clienti ASP",
        valore=round(dso_asp, 1),
        target=float(soglie_dso[0]),
        alert_livello=_valuta_semaforo(
            dso_asp, float(soglie_dso[0]), float(soglie_dso[1]), invertito=True
        ),
        periodo=periodo,
        formula_desc="Crediti ASP / Ricavi ASP * Giorni periodo",
    ))

    # --- 2. DSO clienti privati ---
    dso_privati = (crediti_privati / ricavi_privati * giorni) if ricavi_privati > 0 else 0.0
    soglia_dso_priv = ALERT_CONFIG.get("dso_massimo_privati", 60)

    kpi_list.append(KPI(
        codice="KPI_DSO_PRIV",
        nome="DSO clienti privati",
        valore=round(dso_privati, 1),
        target=float(soglia_dso_priv),
        alert_livello=_valuta_semaforo(
            dso_privati, soglia_dso_priv * 0.8, float(soglia_dso_priv), invertito=True
        ),
        periodo=periodo,
        formula_desc="Crediti privati / Ricavi privati * Giorni periodo",
    ))

    # --- 3. DPO fornitori ---
    dpo = (debiti_fornitori / acquisti * giorni) if acquisti > 0 else 0.0
    soglia_dpo = ALERT_CONFIG.get("dpo_massimo_fornitori", 120)

    kpi_list.append(KPI(
        codice="KPI_DPO",
        nome="DPO fornitori",
        valore=round(dpo, 1),
        target=float(soglia_dpo),
        alert_livello=_valuta_semaforo(
            dpo, soglia_dpo * 0.8, float(soglia_dpo), invertito=True
        ),
        periodo=periodo,
        formula_desc="Debiti fornitori / Acquisti * Giorni periodo",
    ))

    # --- 4. Cassa disponibile ---
    cassa_minima = ALERT_CONFIG.get("cassa_minima", 200_000)

    kpi_list.append(KPI(
        codice="KPI_CASSA",
        nome="Cassa disponibile",
        valore=round(cassa, 2),
        target=float(cassa_minima),
        alert_livello=_valuta_semaforo(
            cassa, cassa_minima * 1.5, float(cassa_minima)
        ),
        periodo=periodo,
        formula_desc="Saldo cassa e banca disponibile",
    ))

    # --- 5. Copertura cassa (mesi) ---
    if uscite_mensili > 0:
        copertura = cassa / uscite_mensili
    else:
        copertura = float("inf") if cassa > 0 else 0.0

    soglie_cop = SOGLIE_SEMAFORO.get("copertura_cassa_mesi", (2.0, 1.0))
    kpi_list.append(KPI(
        codice="KPI_COP_CASSA",
        nome="Copertura cassa",
        valore=round(copertura, 1) if copertura != float("inf") else 999.9,
        target=soglie_cop[0],
        alert_livello=_valuta_semaforo(copertura, soglie_cop[0], soglie_cop[1]),
        periodo=periodo,
        formula_desc="Cassa disponibile / Uscite medie mensili",
    ))

    logger.info(
        "KPI finanziari: DSO ASP=%.0f gg, DSO Priv=%.0f gg, DPO=%.0f gg, "
        "Cassa=%.2f, Copertura=%.1f mesi",
        dso_asp,
        dso_privati,
        dpo,
        cassa,
        copertura if copertura != float("inf") else 999.9,
    )

    return kpi_list


# ============================================================================
# FUNZIONE AGGREGATA
# ============================================================================


def calcola_tutti_kpi(periodo: str, dati: dict) -> List[KPI]:
    """
    Calcola tutti i KPI (operativi per ogni UO, economici e finanziari).

    Parametri:
        periodo: periodo di riferimento
        dati: dizionario con tutti i dati necessari:
            {
                'operativi': {codice_uo: {dati_uo}},
                'consolidati': {dati_consolidati},
                'finanziari': {dati_finanziari},
            }

    Ritorna:
        Lista completa di tutti i KPI calcolati
    """
    logger.info("Calcolo completo di tutti i KPI, periodo '%s'", periodo)

    tutti_kpi = []

    # KPI operativi per ogni UO
    dati_operativi = dati.get("operativi", {})
    for codice_uo, dati_uo in dati_operativi.items():
        kpi_uo = calcola_kpi_operativi(codice_uo, periodo, dati_uo)
        tutti_kpi.extend(kpi_uo)

    # KPI economici consolidati
    dati_consolidati = dati.get("consolidati", {})
    if dati_consolidati:
        kpi_eco = calcola_kpi_economici(periodo, dati_consolidati)
        tutti_kpi.extend(kpi_eco)

    # KPI finanziari
    dati_finanziari = dati.get("finanziari", {})
    if dati_finanziari:
        kpi_fin = calcola_kpi_finanziari(periodo, dati_finanziari)
        tutti_kpi.extend(kpi_fin)

    logger.info(
        "Totale KPI calcolati: %d (%d rossi, %d gialli, %d verdi)",
        len(tutti_kpi),
        sum(1 for k in tutti_kpi if k.alert_livello == LivelliAlert.ROSSO),
        sum(1 for k in tutti_kpi if k.alert_livello == LivelliAlert.GIALLO),
        sum(1 for k in tutti_kpi if k.alert_livello == LivelliAlert.VERDE),
    )

    return tutti_kpi


# ============================================================================
# CONFRONTO E TREND
# ============================================================================


def confronta_kpi_con_benchmark(
    kpi_list: List[KPI], benchmark: dict
) -> pd.DataFrame:
    """
    Confronta i KPI calcolati con un benchmark esterno.

    Parametri:
        kpi_list: lista di KPI calcolati
        benchmark: dizionario {codice_kpi: valore_benchmark}

    Ritorna:
        DataFrame con colonne:
            - codice: codice KPI
            - nome: nome KPI
            - valore: valore calcolato
            - target: target interno
            - benchmark: valore benchmark esterno
            - delta_vs_benchmark: valore - benchmark
            - alert: livello semaforo
            - uo: unità operativa (se applicabile)
    """
    righe = []

    for kpi in kpi_list:
        valore_bench = benchmark.get(kpi.codice, None)
        delta = (kpi.valore - valore_bench) if valore_bench is not None else None

        righe.append({
            "codice": kpi.codice,
            "nome": kpi.nome,
            "valore": kpi.valore,
            "target": kpi.target,
            "benchmark": valore_bench,
            "delta_vs_benchmark": delta,
            "alert": kpi.alert_livello.value,
            "uo": kpi.unita_operativa or "Consolidato",
            "periodo": kpi.periodo,
        })

    df = pd.DataFrame(righe)
    if not df.empty:
        df = df.set_index("codice")

    return df


def trend_kpi(
    codice_kpi: str, periodi: List[str], dati_storici: dict
) -> pd.DataFrame:
    """
    Calcola il trend di un KPI specifico su più periodi.

    Parametri:
        codice_kpi: codice del KPI da analizzare (es. "KPI_OCC")
        periodi: lista di periodi ordinati cronologicamente
        dati_storici: dizionario {periodo: list[KPI]} con i KPI già calcolati
                      per ogni periodo

    Ritorna:
        DataFrame con colonne:
            - periodo: periodo di riferimento
            - valore: valore del KPI nel periodo
            - target: target del KPI
            - alert: livello semaforo
            - variazione: delta rispetto al periodo precedente
            - variazione_pct: delta % rispetto al periodo precedente
    """
    logger.info(
        "Calcolo trend KPI '%s' su %d periodi", codice_kpi, len(periodi)
    )

    righe = []
    valore_precedente = None

    for periodo in periodi:
        kpi_periodo = dati_storici.get(periodo, [])

        # Cerca il KPI specifico nel periodo
        kpi_trovato = None
        for kpi in kpi_periodo:
            if kpi.codice == codice_kpi:
                kpi_trovato = kpi
                break

        if kpi_trovato is None:
            logger.debug(
                "KPI '%s' non trovato nel periodo '%s'", codice_kpi, periodo
            )
            righe.append({
                "periodo": periodo,
                "valore": None,
                "target": None,
                "alert": None,
                "variazione": None,
                "variazione_pct": None,
            })
            continue

        variazione = None
        variazione_pct = None
        if valore_precedente is not None and valore_precedente != 0:
            variazione = kpi_trovato.valore - valore_precedente
            variazione_pct = variazione / abs(valore_precedente)
        elif valore_precedente is not None:
            variazione = kpi_trovato.valore - valore_precedente

        righe.append({
            "periodo": periodo,
            "valore": kpi_trovato.valore,
            "target": kpi_trovato.target,
            "alert": kpi_trovato.alert_livello.value,
            "variazione": round(variazione, 4) if variazione is not None else None,
            "variazione_pct": round(variazione_pct, 4) if variazione_pct is not None else None,
        })

        valore_precedente = kpi_trovato.valore

    df = pd.DataFrame(righe)
    return df


# ============================================================================
# CONVERSIONE A DATAFRAME
# ============================================================================


def kpi_to_dataframe(kpi_list: List[KPI]) -> pd.DataFrame:
    """
    Converte una lista di KPI in un DataFrame leggibile.

    Parametri:
        kpi_list: lista di KPI

    Ritorna:
        DataFrame con tutte le informazioni dei KPI
    """
    righe = []
    for kpi in kpi_list:
        righe.append({
            "Codice": kpi.codice,
            "Nome": kpi.nome,
            "Valore": kpi.valore,
            "Target": kpi.target,
            "Alert": kpi.alert_livello.value,
            "UO": kpi.unita_operativa or "Consolidato",
            "Periodo": kpi.periodo,
            "Formula": kpi.formula_desc,
        })

    df = pd.DataFrame(righe)
    if not df.empty:
        df = df.set_index("Codice")

    return df
