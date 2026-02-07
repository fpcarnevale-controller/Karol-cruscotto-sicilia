"""
Logiche di allocazione / ribaltamento costi sede sulle Unità Operative.

Il modulo implementa il processo di ribaltamento dei costi di sede
(holding Karol S.p.A.) sulle singole Unità Operative, secondo regole
di allocazione basate su driver specifici.

I costi sede sono classificati in 4 categorie:
    1. SERVIZI    - allocati per driver specifici
                    (n.fatture, n.cedolini, euro acquisti, n.postazioni, PL)
    2. GOVERNANCE - allocati pro-quota ricavi
    3. SVILUPPO   - NON allocati (restano a livello holding)
    4. STORICO    - da valutare caso per caso

Principio guida: ogni costo di sede deve essere classificato e, ove possibile,
allocato con un driver che rifletta l'effettivo consumo di risorse della UO.

Autore: Karol CDG
"""

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    CategoriaCostoSede,
    DriverAllocazione,
    DRIVER_PREDEFINITI,
    VOCI_COSTI_SEDE,
    UNITA_OPERATIVE,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class RegolaDiAllocazione:
    """
    Definisce la regola di allocazione per una singola voce di costo sede.

    Attributi:
        voce_costo: codice della voce di costo sede (es. "CS01")
        importo: importo totale da allocare (euro)
        categoria: categoria del costo sede (SERVIZI, GOVERNANCE, SVILUPPO, STORICO)
        driver: driver di allocazione da utilizzare
        valori_driver_per_uo: dizionario {codice_uo: valore_driver} con i valori
                              del driver per ogni UO (es. numero fatture, PL, ecc.)
        note: note esplicative sulla regola
    """
    voce_costo: str
    importo: float
    categoria: CategoriaCostoSede
    driver: DriverAllocazione
    valori_driver_per_uo: Dict[str, float] = field(default_factory=dict)
    note: str = ""


# ============================================================================
# FUNZIONI DI CALCOLO DRIVER
# ============================================================================


def calcola_driver_percentuali(valori_driver: Dict[str, float]) -> Dict[str, float]:
    """
    Converte i valori assoluti di un driver nelle percentuali di allocazione.

    Esempio: se VLB ha 100 fatture, COS ha 200 e CTA ha 100,
    il totale è 400 e le percentuali saranno:
    VLB=25%, COS=50%, CTA=25%

    Parametri:
        valori_driver: dizionario {codice_uo: valore_assoluto_driver}

    Ritorna:
        Dizionario {codice_uo: percentuale} dove la somma delle percentuali = 1.0
    """
    totale = sum(valori_driver.values())

    if totale == 0.0:
        logger.warning(
            "Totale driver pari a zero, allocazione equidistribuita tra %d UO",
            len(valori_driver),
        )
        n_uo = len(valori_driver)
        if n_uo == 0:
            return {}
        quota_uguale = 1.0 / n_uo
        return {uo: quota_uguale for uo in valori_driver}

    percentuali = {}
    for codice_uo, valore in valori_driver.items():
        percentuali[codice_uo] = valore / totale

    return percentuali


def alloca_per_driver(
    importo: float,
    driver: DriverAllocazione,
    valori_per_uo: Dict[str, float],
) -> Dict[str, float]:
    """
    Alloca un singolo importo sulle UO in base al driver specificato.

    Parametri:
        importo: importo totale da allocare (euro)
        driver: tipo di driver di allocazione
        valori_per_uo: dizionario {codice_uo: valore_driver}

    Ritorna:
        Dizionario {codice_uo: importo_allocato}
    """
    if driver == DriverAllocazione.NON_ALLOCABILE:
        logger.debug(
            "Costo non allocabile (%.2f euro), non distribuito", importo
        )
        return {}

    if not valori_per_uo:
        logger.warning(
            "Nessun valore driver fornito per allocazione di %.2f euro "
            "con driver '%s'",
            importo,
            driver.value,
        )
        return {}

    percentuali = calcola_driver_percentuali(valori_per_uo)

    allocazione = {}
    for codice_uo, pct in percentuali.items():
        allocazione[codice_uo] = round(importo * pct, 2)

    # Gestione arrotondamento: assegna la differenza residua alla UO più grande
    somma_allocata = sum(allocazione.values())
    differenza = round(importo - somma_allocata, 2)
    if differenza != 0.0 and allocazione:
        uo_maggiore = max(allocazione, key=allocazione.get)
        allocazione[uo_maggiore] += differenza
        allocazione[uo_maggiore] = round(allocazione[uo_maggiore], 2)

    return allocazione


def alloca_pro_quota_ricavi(
    importo: float, ricavi_per_uo: Dict[str, float]
) -> Dict[str, float]:
    """
    Alloca un importo in proporzione ai ricavi di ciascuna UO.

    Questo è il metodo standard per i costi di Governance.

    Parametri:
        importo: importo totale da allocare (euro)
        ricavi_per_uo: dizionario {codice_uo: ricavi_totali}

    Ritorna:
        Dizionario {codice_uo: importo_allocato}
    """
    logger.debug(
        "Allocazione pro-quota ricavi: %.2f euro su %d UO",
        importo,
        len(ricavi_per_uo),
    )
    return alloca_per_driver(
        importo=importo,
        driver=DriverAllocazione.RICAVI,
        valori_per_uo=ricavi_per_uo,
    )


# ============================================================================
# FUNZIONE PRINCIPALE DI ALLOCAZIONE
# ============================================================================


def calcola_allocazione(
    regole: List[RegolaDiAllocazione],
    unita_operative: List[str],
) -> dict:
    """
    Applica tutte le regole di allocazione, restituendo il risultato
    completo del ribaltamento costi sede.

    Per ogni regola:
    - Se la categoria è SERVIZI: alloca con il driver specifico
    - Se la categoria è GOVERNANCE: alloca pro-quota (driver RICAVI)
    - Se la categoria è SVILUPPO: NON alloca (costo resta a holding)
    - Se la categoria è STORICO/DA_CLASSIFICARE: NON alloca (da valutare)

    Parametri:
        regole: lista di RegolaDiAllocazione con le regole per ogni voce
        unita_operative: lista dei codici UO su cui allocare

    Ritorna:
        Dizionario con la struttura:
        {
            'allocato': {codice_uo: {voce_costo: importo_allocato}},
            'non_allocato': {voce_costo: importo},
            'totale_allocato': float,
            'totale_non_allocato': float,
            'dettaglio_regole': list[dict],  # dettaglio per ogni regola applicata
        }
    """
    logger.info(
        "Avvio allocazione: %d regole, %d Unità Operative",
        len(regole),
        len(unita_operative),
    )

    # Inizializza struttura risultato
    allocato = {uo: {} for uo in unita_operative}
    non_allocato = {}
    dettaglio_regole = []

    for regola in regole:
        voce = regola.voce_costo
        importo = regola.importo
        categoria = regola.categoria
        driver = regola.driver

        logger.debug(
            "Elaborazione regola: voce='%s', importo=%.2f, categoria='%s', "
            "driver='%s'",
            voce,
            importo,
            categoria.value,
            driver.value,
        )

        # Categorie non allocabili
        if categoria in (
            CategoriaCostoSede.SVILUPPO,
            CategoriaCostoSede.DA_CLASSIFICARE,
        ):
            non_allocato[voce] = importo
            dettaglio_regole.append({
                "voce_costo": voce,
                "descrizione": VOCI_COSTI_SEDE.get(voce, voce),
                "importo": importo,
                "categoria": categoria.value,
                "driver": driver.value,
                "allocato": False,
                "motivo": f"Categoria '{categoria.value}' non allocabile",
            })
            logger.debug("Voce '%s' non allocata (categoria %s)", voce, categoria.value)
            continue

        # Costi STORICO: non allocati per default (da valutare)
        if categoria == CategoriaCostoSede.STORICO:
            non_allocato[voce] = importo
            dettaglio_regole.append({
                "voce_costo": voce,
                "descrizione": VOCI_COSTI_SEDE.get(voce, voce),
                "importo": importo,
                "categoria": categoria.value,
                "driver": driver.value,
                "allocato": False,
                "motivo": "Costo storico da valutare",
            })
            logger.debug("Voce '%s' non allocata (costo storico)", voce)
            continue

        # Driver non allocabile
        if driver == DriverAllocazione.NON_ALLOCABILE:
            non_allocato[voce] = importo
            dettaglio_regole.append({
                "voce_costo": voce,
                "descrizione": VOCI_COSTI_SEDE.get(voce, voce),
                "importo": importo,
                "categoria": categoria.value,
                "driver": driver.value,
                "allocato": False,
                "motivo": "Driver non allocabile",
            })
            logger.debug("Voce '%s' non allocata (driver non allocabile)", voce)
            continue

        # Allocazione effettiva
        distribuzione = alloca_per_driver(
            importo=importo,
            driver=driver,
            valori_per_uo=regola.valori_driver_per_uo,
        )

        # Assegna gli importi allocati alle UO
        for codice_uo, importo_allocato in distribuzione.items():
            if codice_uo in allocato:
                allocato[codice_uo][voce] = importo_allocato

        dettaglio_regole.append({
            "voce_costo": voce,
            "descrizione": VOCI_COSTI_SEDE.get(voce, voce),
            "importo": importo,
            "categoria": categoria.value,
            "driver": driver.value,
            "allocato": True,
            "distribuzione": distribuzione,
        })

        logger.debug(
            "Voce '%s' allocata con driver '%s': %s",
            voce,
            driver.value,
            {k: f"{v:.2f}" for k, v in distribuzione.items()},
        )

    # Calcola totali
    totale_allocato = sum(
        sum(voci.values()) for voci in allocato.values()
    )
    totale_non_allocato = sum(non_allocato.values())

    logger.info(
        "Allocazione completata: allocato=%.2f, non allocato=%.2f",
        totale_allocato,
        totale_non_allocato,
    )

    return {
        "allocato": allocato,
        "non_allocato": non_allocato,
        "totale_allocato": totale_allocato,
        "totale_non_allocato": totale_non_allocato,
        "dettaglio_regole": dettaglio_regole,
    }


# ============================================================================
# RIEPILOGO E SIMULAZIONE
# ============================================================================


def riepilogo_allocazione(risultati: dict) -> pd.DataFrame:
    """
    Genera una tabella riepilogativa dell'allocazione con dettaglio
    per UO e per voce di costo sede.

    Parametri:
        risultati: output di calcola_allocazione()

    Ritorna:
        DataFrame con:
            - Indice: voce di costo sede
            - Colonne: codici UO + totale allocato + non allocato
    """
    allocato = risultati.get("allocato", {})
    non_allocato = risultati.get("non_allocato", {})

    # Raccolta di tutte le voci presenti
    tutte_voci = set()
    for voci_uo in allocato.values():
        tutte_voci.update(voci_uo.keys())
    tutte_voci.update(non_allocato.keys())

    righe = []
    for voce in sorted(tutte_voci):
        descrizione = VOCI_COSTI_SEDE.get(voce, voce)
        riga = {"Voce": voce, "Descrizione": descrizione}

        totale_voce_allocato = 0.0
        for codice_uo in sorted(allocato.keys()):
            importo = allocato[codice_uo].get(voce, 0.0)
            riga[codice_uo] = importo
            totale_voce_allocato += importo

        riga["Totale Allocato"] = totale_voce_allocato
        riga["Non Allocato"] = non_allocato.get(voce, 0.0)
        righe.append(riga)

    df = pd.DataFrame(righe)

    if not df.empty:
        df = df.set_index("Voce")

        # Aggiungi riga di totale
        colonne_numeriche = df.select_dtypes(include="number").columns
        riga_totale = df[colonne_numeriche].sum()
        riga_totale["Descrizione"] = "TOTALE"
        df.loc["TOTALE"] = riga_totale

    df.index.name = "Voce"
    return df


def simulazione_what_if(
    regole: List[RegolaDiAllocazione],
    modifica: dict,
) -> dict:
    """
    Simula l'effetto di una modifica alle regole di allocazione (what-if).

    Permette di simulare scenari come:
    - Eliminazione di un costo sede
    - Modifica dell'importo di un costo
    - Cambio del driver di allocazione
    - Aggiunta di un nuovo costo

    Parametri:
        regole: lista originale di RegolaDiAllocazione
        modifica: dizionario con le modifiche da applicare:
            {
                'tipo': 'elimina' | 'modifica_importo' | 'modifica_driver' | 'aggiungi',
                'voce_costo': str,                  # per elimina/modifica
                'nuovo_importo': float,             # per modifica_importo
                'nuovo_driver': DriverAllocazione,  # per modifica_driver
                'nuova_regola': RegolaDiAllocazione, # per aggiungi
            }

    Ritorna:
        Dizionario con:
        {
            'allocazione_originale': dict,  # risultato con regole originali
            'allocazione_modificata': dict, # risultato con regole modificate
            'delta_per_uo': {codice_uo: float},  # variazione totale per UO
        }
    """
    tipo_modifica = modifica.get("tipo", "")
    voce_target = modifica.get("voce_costo", "")

    logger.info(
        "Simulazione what-if: tipo='%s', voce='%s'", tipo_modifica, voce_target
    )

    # Calcola allocazione originale
    unita_operative = list(UNITA_OPERATIVE.keys())
    allocazione_originale = calcola_allocazione(regole, unita_operative)

    # Prepara regole modificate
    regole_modificate = deepcopy(regole)

    if tipo_modifica == "elimina":
        regole_modificate = [
            r for r in regole_modificate if r.voce_costo != voce_target
        ]
        logger.info("Eliminata voce '%s' dalla simulazione", voce_target)

    elif tipo_modifica == "modifica_importo":
        nuovo_importo = modifica.get("nuovo_importo", 0.0)
        for regola in regole_modificate:
            if regola.voce_costo == voce_target:
                regola.importo = nuovo_importo
                logger.info(
                    "Modificato importo voce '%s' a %.2f", voce_target, nuovo_importo
                )
                break

    elif tipo_modifica == "modifica_driver":
        nuovo_driver = modifica.get("nuovo_driver")
        nuovi_valori = modifica.get("nuovi_valori_driver", {})
        for regola in regole_modificate:
            if regola.voce_costo == voce_target:
                if nuovo_driver is not None:
                    regola.driver = nuovo_driver
                if nuovi_valori:
                    regola.valori_driver_per_uo = nuovi_valori
                logger.info(
                    "Modificato driver voce '%s' a '%s'",
                    voce_target,
                    nuovo_driver.value if nuovo_driver else "invariato",
                )
                break

    elif tipo_modifica == "aggiungi":
        nuova_regola = modifica.get("nuova_regola")
        if nuova_regola is not None:
            regole_modificate.append(nuova_regola)
            logger.info("Aggiunta nuova regola: voce '%s'", nuova_regola.voce_costo)

    else:
        logger.warning("Tipo modifica non riconosciuto: '%s'", tipo_modifica)

    # Calcola allocazione modificata
    allocazione_modificata = calcola_allocazione(regole_modificate, unita_operative)

    # Calcola delta per UO
    delta_per_uo = {}
    for codice_uo in unita_operative:
        totale_orig = sum(
            allocazione_originale["allocato"].get(codice_uo, {}).values()
        )
        totale_mod = sum(
            allocazione_modificata["allocato"].get(codice_uo, {}).values()
        )
        delta_per_uo[codice_uo] = round(totale_mod - totale_orig, 2)

    return {
        "allocazione_originale": allocazione_originale,
        "allocazione_modificata": allocazione_modificata,
        "delta_per_uo": delta_per_uo,
    }
