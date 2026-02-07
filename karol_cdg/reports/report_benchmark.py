"""
Generazione report di benchmark per Unita' Operative.

Confronta i dati economici di ciascuna U.O. con i benchmark di settore
definiti nella configurazione, producendo:
  - Tabelle comparative (valori U.O. vs benchmark min/max)
  - Analisi degli scostamenti (gap)
  - Posizionamento nel settore (sopra/sotto/in linea)
  - Raccomandazioni operative basate sui gap rilevati

I benchmark di riferimento sono specifici per tipologia di struttura
(RSA, Riabilitazione, CTA, Day Surgery, Laboratorio, ecc.).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from karol_cdg.config import (
    BenchmarkSettore,
    BENCHMARK,
    UNITA_OPERATIVE,
    TipologiaStruttura,
    SIMBOLO_VALUTA,
)
from karol_cdg.utils.format_utils import (
    formatta_valuta,
    formatta_percentuale,
    formatta_numero,
)
from karol_cdg.utils.date_utils import formatta_periodo_esteso

logger = logging.getLogger(__name__)

# ============================================================================
# COSTANTI
# ============================================================================

# Soglia di tolleranza per considerare un valore "in linea" con il benchmark
_TOLLERANZA_PERCENTUALE = 2.0  # punti percentuali


# ============================================================================
# FUNZIONE PRINCIPALE
# ============================================================================


def genera_report_benchmark(
    codice_uo: str,
    periodo: str,
    ce_industriale: dict,
    benchmark: dict,
    output_path: Path,
) -> Path:
    """
    Genera il report di benchmark per una singola Unita' Operativa.

    Il report confronta i principali indicatori economici dell'U.O.
    con i valori di riferimento del settore e produce un file Excel
    con tabelle comparative e raccomandazioni.

    Parametri
    ---------
    codice_uo : str
        Codice dell'Unita' Operativa (es. "VLB", "COS").
    periodo : str
        Periodo di riferimento nel formato "MM/YYYY".
    ce_industriale : dict
        Dati del Conto Economico industriale dell'U.O. Attese chiavi:
        - "ricavi" (float): ricavi totali del periodo
        - "costi_personale" (float): costo totale del personale
        - "costi_diretti" (float): costi diretti totali
        - "mol_industriale" (float): margine operativo lordo industriale
        - "giornate_degenza" (int): giornate di degenza erogate
        - "costo_giornata" (float): costo medio per giornata di degenza
    benchmark : dict
        Dizionario dei benchmark di settore (normalmente da config.BENCHMARK).
    output_path : Path
        Percorso del file di output (Excel .xlsx).

    Ritorna
    -------
    Path
        Percorso del file generato.

    Raises
    ------
    ValueError
        Se il codice_uo non e' presente nell'anagrafica.
    IOError
        Se non e' possibile scrivere il file di output.
    """
    logger.info(
        "Generazione report benchmark per U.O. %s, periodo %s",
        codice_uo, periodo,
    )

    # Verifica che l'U.O. esista nell'anagrafica
    uo_info = UNITA_OPERATIVE.get(codice_uo)
    if not uo_info:
        msg = f"Unita' Operativa '{codice_uo}' non trovata nell'anagrafica."
        logger.error(msg)
        raise ValueError(msg)

    # Identifica il benchmark di riferimento per la tipologia dell'U.O.
    benchmark_uo = _trova_benchmark_per_uo(codice_uo, benchmark)
    if not benchmark_uo:
        logger.warning(
            "Nessun benchmark disponibile per la tipologia di %s (%s). "
            "Il report conterra' solo i dati dell'U.O.",
            codice_uo,
            [t.value for t in uo_info.tipologia],
        )

    # Confronto con benchmark
    confronto = confronta_con_benchmark(ce_industriale, benchmark_uo)

    # Genera tabella DataFrame
    df_benchmark = genera_tabella_benchmark(confronto)

    # Posizionamento
    testo_posizionamento = posizionamento_settore(ce_industriale, benchmark_uo)

    # Raccomandazioni
    lista_raccomandazioni = raccomandazioni_da_benchmark(confronto)

    # Assicura directory di output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Scrivi il file Excel con piu' fogli
    try:
        with pd.ExcelWriter(str(output_path), engine="openpyxl") as writer:
            # Foglio 1: Confronto benchmark
            df_benchmark.to_excel(
                writer,
                sheet_name="Confronto Benchmark",
                index=False,
            )

            # Foglio 2: Posizionamento e raccomandazioni
            dati_riepilogo = {
                "Campo": [
                    "Unita' Operativa",
                    "Codice",
                    "Periodo",
                    "Tipologia",
                    "Posizionamento",
                    "",
                    "--- RACCOMANDAZIONI ---",
                ] + [f"Raccomandazione {i+1}" for i in range(len(lista_raccomandazioni))],
                "Valore": [
                    uo_info.nome,
                    codice_uo,
                    formatta_periodo_esteso(periodo),
                    ", ".join(t.value for t in uo_info.tipologia),
                    testo_posizionamento,
                    "",
                    "",
                ] + lista_raccomandazioni,
            }
            df_riepilogo = pd.DataFrame(dati_riepilogo)
            df_riepilogo.to_excel(
                writer,
                sheet_name="Riepilogo",
                index=False,
            )

        logger.info("Report benchmark salvato in: %s", output_path)

    except Exception as exc:
        logger.error(
            "Errore nel salvataggio del report benchmark: %s", exc
        )
        raise IOError(
            f"Impossibile salvare il report benchmark in {output_path}: {exc}"
        )

    return output_path


# ============================================================================
# CONFRONTO CON BENCHMARK
# ============================================================================


def confronta_con_benchmark(
    ce_data: dict,
    benchmark: Optional[BenchmarkSettore],
) -> dict:
    """
    Confronta i dati del CE con i benchmark di settore.

    Per ciascun indicatore calcola:
      - Il valore corrente dell'U.O.
      - L'intervallo di benchmark (min-max)
      - Il gap rispetto al benchmark (positivo = sopra, negativo = sotto)
      - La valutazione ("sopra", "sotto", "in_linea")

    Parametri
    ---------
    ce_data : dict
        Dati del Conto Economico industriale dell'U.O.
    benchmark : BenchmarkSettore o None
        Benchmark di settore per la tipologia della struttura.

    Ritorna
    -------
    dict
        Dizionario con il risultato del confronto per ciascun indicatore:
        {
            "costo_personale_su_ricavi": {
                "valore_uo": float,
                "benchmark_min": float,
                "benchmark_max": float,
                "gap": float,
                "valutazione": str,
            },
            "mol_percentuale": { ... },
            "costo_giornata_degenza": { ... },
        }
    """
    risultato = {}
    ricavi = ce_data.get("ricavi", 0.0)
    costi_personale = ce_data.get("costi_personale", 0.0)
    mol_industriale = ce_data.get("mol_industriale", 0.0)
    costo_giornata = ce_data.get("costo_giornata", None)

    # --- Indicatore 1: Costo personale su ricavi ---
    pct_personale = (costi_personale / ricavi * 100) if ricavi else 0.0
    indicatore_personale = {
        "nome": "Costo personale / Ricavi",
        "valore_uo": round(pct_personale, 2),
        "unita_misura": "%",
        "benchmark_min": None,
        "benchmark_max": None,
        "gap": None,
        "valutazione": "non_disponibile",
    }

    if benchmark:
        bm_min = benchmark.costo_personale_su_ricavi_min
        bm_max = benchmark.costo_personale_su_ricavi_max
        indicatore_personale["benchmark_min"] = bm_min
        indicatore_personale["benchmark_max"] = bm_max

        # Per il costo personale: sotto il min e' meglio, sopra il max e' critico
        if pct_personale <= bm_min:
            indicatore_personale["gap"] = round(pct_personale - bm_min, 2)
            indicatore_personale["valutazione"] = "sopra"  # meglio del benchmark
        elif pct_personale <= bm_max:
            indicatore_personale["gap"] = 0.0
            indicatore_personale["valutazione"] = "in_linea"
        else:
            indicatore_personale["gap"] = round(pct_personale - bm_max, 2)
            indicatore_personale["valutazione"] = "sotto"  # peggio del benchmark

    risultato["costo_personale_su_ricavi"] = indicatore_personale

    # --- Indicatore 2: MOL % su ricavi ---
    pct_mol = (mol_industriale / ricavi * 100) if ricavi else 0.0
    indicatore_mol = {
        "nome": "MOL Industriale / Ricavi",
        "valore_uo": round(pct_mol, 2),
        "unita_misura": "%",
        "benchmark_min": None,
        "benchmark_max": None,
        "gap": None,
        "valutazione": "non_disponibile",
    }

    if benchmark:
        bm_min = benchmark.mol_percentuale_target_min
        bm_max = benchmark.mol_percentuale_target_max
        indicatore_mol["benchmark_min"] = bm_min
        indicatore_mol["benchmark_max"] = bm_max

        # Per il MOL: sopra il max e' meglio, sotto il min e' critico
        if pct_mol >= bm_max:
            indicatore_mol["gap"] = round(pct_mol - bm_max, 2)
            indicatore_mol["valutazione"] = "sopra"
        elif pct_mol >= bm_min:
            indicatore_mol["gap"] = 0.0
            indicatore_mol["valutazione"] = "in_linea"
        else:
            indicatore_mol["gap"] = round(pct_mol - bm_min, 2)
            indicatore_mol["valutazione"] = "sotto"

    risultato["mol_percentuale"] = indicatore_mol

    # --- Indicatore 3: Costo giornata degenza (se applicabile) ---
    if costo_giornata is not None and costo_giornata > 0:
        indicatore_giornata = {
            "nome": "Costo giornata degenza",
            "valore_uo": round(costo_giornata, 2),
            "unita_misura": SIMBOLO_VALUTA,
            "benchmark_min": None,
            "benchmark_max": None,
            "gap": None,
            "valutazione": "non_disponibile",
        }

        if benchmark and benchmark.costo_giornata_degenza_min is not None:
            bm_min = benchmark.costo_giornata_degenza_min
            bm_max = benchmark.costo_giornata_degenza_max
            indicatore_giornata["benchmark_min"] = bm_min
            indicatore_giornata["benchmark_max"] = bm_max

            # Per il costo giornata: sotto il min e' meglio, sopra il max e' critico
            if costo_giornata <= bm_min:
                indicatore_giornata["gap"] = round(costo_giornata - bm_min, 2)
                indicatore_giornata["valutazione"] = "sopra"
            elif costo_giornata <= bm_max:
                indicatore_giornata["gap"] = 0.0
                indicatore_giornata["valutazione"] = "in_linea"
            else:
                indicatore_giornata["gap"] = round(costo_giornata - bm_max, 2)
                indicatore_giornata["valutazione"] = "sotto"

        risultato["costo_giornata_degenza"] = indicatore_giornata

    logger.debug("Confronto benchmark completato: %d indicatori", len(risultato))
    return risultato


# ============================================================================
# GENERAZIONE TABELLA
# ============================================================================


def genera_tabella_benchmark(confronto: dict) -> pd.DataFrame:
    """
    Crea un DataFrame con la tabella comparativa benchmark.

    Ogni riga rappresenta un indicatore con il valore dell'U.O.,
    l'intervallo di benchmark e la valutazione.

    Parametri
    ---------
    confronto : dict
        Risultato di confronta_con_benchmark().

    Ritorna
    -------
    pd.DataFrame
        DataFrame con colonne:
        ["Indicatore", "Valore U.O.", "Benchmark Min", "Benchmark Max",
         "Gap", "Valutazione"]
    """
    righe = []

    for chiave, dati in confronto.items():
        nome = dati.get("nome", chiave)
        valore_uo = dati.get("valore_uo", 0.0)
        um = dati.get("unita_misura", "")
        bm_min = dati.get("benchmark_min")
        bm_max = dati.get("benchmark_max")
        gap = dati.get("gap")
        valutazione = dati.get("valutazione", "non_disponibile")

        # Formattazione valori
        if um == "%":
            valore_fmt = formatta_percentuale(valore_uo)
            bm_min_fmt = formatta_percentuale(bm_min) if bm_min is not None else "-"
            bm_max_fmt = formatta_percentuale(bm_max) if bm_max is not None else "-"
            gap_fmt = formatta_percentuale(gap) if gap is not None else "-"
        elif um == SIMBOLO_VALUTA:
            valore_fmt = formatta_valuta(valore_uo)
            bm_min_fmt = formatta_valuta(bm_min) if bm_min is not None else "-"
            bm_max_fmt = formatta_valuta(bm_max) if bm_max is not None else "-"
            gap_fmt = formatta_valuta(gap) if gap is not None else "-"
        else:
            valore_fmt = formatta_numero(valore_uo)
            bm_min_fmt = formatta_numero(bm_min) if bm_min is not None else "-"
            bm_max_fmt = formatta_numero(bm_max) if bm_max is not None else "-"
            gap_fmt = formatta_numero(gap) if gap is not None else "-"

        # Traduzione valutazione
        valutazione_it = _traduci_valutazione(valutazione)

        righe.append({
            "Indicatore": nome,
            "Valore U.O.": valore_fmt,
            "Benchmark Min": bm_min_fmt,
            "Benchmark Max": bm_max_fmt,
            "Gap": gap_fmt,
            "Valutazione": valutazione_it,
        })

    df = pd.DataFrame(righe)
    logger.debug("Tabella benchmark generata: %d righe", len(df))
    return df


# ============================================================================
# POSIZIONAMENTO E RACCOMANDAZIONI
# ============================================================================


def posizionamento_settore(
    dati_uo: dict,
    benchmark: Optional[BenchmarkSettore],
) -> str:
    """
    Fornisce una valutazione testuale del posizionamento dell'U.O.
    rispetto ai benchmark di settore.

    La valutazione considera congiuntamente il costo personale su
    ricavi e il MOL percentuale per restituire un giudizio complessivo.

    Parametri
    ---------
    dati_uo : dict
        Dati economici dell'U.O. (ricavi, costi_personale, mol_industriale).
    benchmark : BenchmarkSettore o None
        Benchmark di riferimento per la tipologia della struttura.

    Ritorna
    -------
    str
        Testo descrittivo del posizionamento:
        - "Sopra la media di settore" se entrambi gli indicatori sono positivi
        - "In linea con il settore" se gli indicatori sono nell'intervallo
        - "Sotto la media di settore" se ci sono gap negativi significativi
        - "Benchmark non disponibile" se mancano i dati di confronto
    """
    if not benchmark:
        return "Benchmark non disponibile per questa tipologia di struttura."

    ricavi = dati_uo.get("ricavi", 0.0)
    if ricavi == 0:
        return "Impossibile determinare il posizionamento: ricavi pari a zero."

    costi_personale = dati_uo.get("costi_personale", 0.0)
    mol_industriale = dati_uo.get("mol_industriale", 0.0)

    pct_personale = costi_personale / ricavi * 100
    pct_mol = mol_industriale / ricavi * 100

    # Valutazione costo personale (piu' basso e' meglio)
    personale_ok = pct_personale <= (
        benchmark.costo_personale_su_ricavi_max + _TOLLERANZA_PERCENTUALE
    )

    # Valutazione MOL (piu' alto e' meglio)
    mol_ok = pct_mol >= (
        benchmark.mol_percentuale_target_min - _TOLLERANZA_PERCENTUALE
    )

    # Eccellenza: personale sotto il minimo E mol sopra il massimo
    personale_eccellente = pct_personale <= benchmark.costo_personale_su_ricavi_min
    mol_eccellente = pct_mol >= benchmark.mol_percentuale_target_max

    if personale_eccellente and mol_eccellente:
        posizione = (
            f"Sopra la media di settore. "
            f"L'U.O. presenta un costo del personale ({formatta_percentuale(pct_personale)}) "
            f"inferiore alla fascia di benchmark "
            f"({formatta_percentuale(benchmark.costo_personale_su_ricavi_min)}-"
            f"{formatta_percentuale(benchmark.costo_personale_su_ricavi_max)}) "
            f"e un MOL industriale ({formatta_percentuale(pct_mol)}) "
            f"superiore al target massimo "
            f"({formatta_percentuale(benchmark.mol_percentuale_target_max)})."
        )
    elif personale_ok and mol_ok:
        posizione = (
            f"In linea con il settore. "
            f"Il costo del personale ({formatta_percentuale(pct_personale)}) "
            f"e il MOL industriale ({formatta_percentuale(pct_mol)}) "
            f"rientrano nell'intervallo di benchmark atteso."
        )
    elif not personale_ok and not mol_ok:
        posizione = (
            f"Sotto la media di settore. "
            f"CRITICITA': il costo del personale ({formatta_percentuale(pct_personale)}) "
            f"supera il benchmark massimo "
            f"({formatta_percentuale(benchmark.costo_personale_su_ricavi_max)}) "
            f"e il MOL industriale ({formatta_percentuale(pct_mol)}) "
            f"e' inferiore al target minimo "
            f"({formatta_percentuale(benchmark.mol_percentuale_target_min)})."
        )
    elif not personale_ok:
        posizione = (
            f"Sotto la media di settore per il costo del personale. "
            f"Il costo del personale ({formatta_percentuale(pct_personale)}) "
            f"supera il benchmark massimo "
            f"({formatta_percentuale(benchmark.costo_personale_su_ricavi_max)}), "
            f"mentre il MOL industriale ({formatta_percentuale(pct_mol)}) "
            f"risulta in linea."
        )
    else:
        posizione = (
            f"Sotto la media di settore per la redditivita'. "
            f"Il MOL industriale ({formatta_percentuale(pct_mol)}) "
            f"e' inferiore al target minimo "
            f"({formatta_percentuale(benchmark.mol_percentuale_target_min)}), "
            f"mentre il costo del personale ({formatta_percentuale(pct_personale)}) "
            f"risulta in linea."
        )

    logger.debug("Posizionamento settore determinato: %s", posizione[:80])
    return posizione


def raccomandazioni_da_benchmark(confronto: dict) -> List[str]:
    """
    Genera una lista di raccomandazioni operative basate sugli
    scostamenti rilevati rispetto ai benchmark di settore.

    Per ogni indicatore con valutazione "sotto" viene generata una
    raccomandazione specifica con suggerimenti di intervento.

    Parametri
    ---------
    confronto : dict
        Risultato di confronta_con_benchmark().

    Ritorna
    -------
    list[str]
        Lista di raccomandazioni testuali. Lista vuota se tutti gli
        indicatori sono in linea o sopra i benchmark.
    """
    raccomandazioni = []

    for chiave, dati in confronto.items():
        valutazione = dati.get("valutazione", "non_disponibile")
        gap = dati.get("gap")
        valore_uo = dati.get("valore_uo", 0.0)
        nome = dati.get("nome", chiave)

        if valutazione == "sotto":
            if chiave == "costo_personale_su_ricavi":
                raccomandazioni.append(
                    f"COSTO PERSONALE: il rapporto costo personale/ricavi "
                    f"({formatta_percentuale(valore_uo)}) eccede il benchmark di "
                    f"{formatta_percentuale(abs(gap))} punti percentuali. "
                    f"Si raccomanda di: (a) verificare i livelli di organico per "
                    f"qualifica, (b) analizzare il ricorso a straordinari e "
                    f"cooperative, (c) valutare la riorganizzazione dei turni."
                )
            elif chiave == "mol_percentuale":
                raccomandazioni.append(
                    f"REDDITIVITA': il MOL industriale "
                    f"({formatta_percentuale(valore_uo)}) e' inferiore al "
                    f"target minimo di {formatta_percentuale(abs(gap))} punti "
                    f"percentuali. Si raccomanda di: (a) verificare la corretta "
                    f"applicazione delle tariffe, (b) analizzare il mix di "
                    f"prestazioni erogate, (c) controllare l'andamento "
                    f"dell'occupancy."
                )
            elif chiave == "costo_giornata_degenza":
                raccomandazioni.append(
                    f"COSTO GIORNATA: il costo medio per giornata di degenza "
                    f"({formatta_valuta(valore_uo)}) supera il benchmark "
                    f"di {formatta_valuta(abs(gap))}. "
                    f"Si raccomanda di: (a) analizzare le principali voci di "
                    f"costo per giornata, (b) confrontare con il periodo "
                    f"precedente per identificare derive, (c) verificare "
                    f"eventuali costi straordinari."
                )
            else:
                raccomandazioni.append(
                    f"Indicatore '{nome}' sotto benchmark di "
                    f"{formatta_percentuale(abs(gap)) if gap else 'N/D'} punti. "
                    f"Si consiglia un approfondimento."
                )

        elif valutazione == "non_disponibile":
            raccomandazioni.append(
                f"Indicatore '{nome}': benchmark di settore non disponibile. "
                f"Si consiglia di definire i parametri di riferimento."
            )

    if not raccomandazioni:
        raccomandazioni.append(
            "Tutti gli indicatori rientrano nell'intervallo di benchmark. "
            "Nessuna azione correttiva necessaria."
        )

    logger.debug(
        "Generate %d raccomandazioni da benchmark.", len(raccomandazioni)
    )
    return raccomandazioni


# ============================================================================
# FUNZIONI INTERNE
# ============================================================================


def _trova_benchmark_per_uo(
    codice_uo: str,
    benchmark_dict: dict,
) -> Optional[BenchmarkSettore]:
    """
    Individua il benchmark di settore applicabile a una U.O.

    La ricerca avviene sulla prima tipologia della struttura per cui
    esiste un benchmark definito. Se l'U.O. ha piu' tipologie (es.
    Casa di Cura + Riabilitazione), viene utilizzata la prima per
    cui e' disponibile un benchmark.

    Parametri
    ---------
    codice_uo : str
        Codice dell'Unita' Operativa.
    benchmark_dict : dict
        Dizionario dei benchmark (chiave = nome tipologia, valore = BenchmarkSettore).

    Ritorna
    -------
    BenchmarkSettore o None
        Benchmark applicabile, None se non trovato.
    """
    uo_info = UNITA_OPERATIVE.get(codice_uo)
    if not uo_info:
        logger.warning("U.O. '%s' non trovata nell'anagrafica.", codice_uo)
        return None

    for tipologia in uo_info.tipologia:
        # La chiave nel dizionario benchmark corrisponde al nome dell'enum
        chiave_benchmark = tipologia.name
        if chiave_benchmark in benchmark_dict:
            logger.debug(
                "Benchmark trovato per %s: tipologia %s",
                codice_uo, chiave_benchmark,
            )
            return benchmark_dict[chiave_benchmark]

    logger.debug(
        "Nessun benchmark trovato per %s (tipologie: %s)",
        codice_uo,
        [t.name for t in uo_info.tipologia],
    )
    return None


def _traduci_valutazione(valutazione: str) -> str:
    """
    Traduce il codice di valutazione nella descrizione italiana.

    Parametri
    ---------
    valutazione : str
        Codice valutazione: "sopra", "sotto", "in_linea", "non_disponibile".

    Ritorna
    -------
    str
        Descrizione in italiano.
    """
    mappa = {
        "sopra": "Sopra benchmark",
        "sotto": "Sotto benchmark",
        "in_linea": "In linea",
        "non_disponibile": "N/D",
    }
    return mappa.get(valutazione, valutazione)
