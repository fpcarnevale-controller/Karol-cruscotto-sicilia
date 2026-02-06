"""
Gestione alert e notifiche per il sistema di controllo di gestione.

Genera, filtra, formatta e salva alert basati su soglie configurabili
per indicatori economici, finanziari e operativi.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from karol_cdg.config import (
    ALERT_CONFIG,
    SOGLIE_SEMAFORO,
    LivelliAlert,
)
from karol_cdg.utils.format_utils import (
    formatta_percentuale,
    formatta_valuta,
    formatta_numero,
    colore_semaforo,
)
from karol_cdg.utils.date_utils import periodo_corrente


# ============================================================================
# DATACLASS ALERT
# ============================================================================

@dataclass
class Alert:
    """
    Rappresenta un singolo alert generato dal sistema.

    Attributes:
        codice: Codice identificativo dell'alert (es. "ECO_MOL_001").
        livello: Livello di gravita' - "verde", "giallo" o "rosso".
        messaggio: Descrizione testuale dell'alert.
        valore_attuale: Valore numerico dell'indicatore al momento della
                        valutazione.
        soglia: Valore soglia di riferimento.
        unita_operativa: Codice UO interessata. None se l'alert e'
                         a livello consolidato.
        periodo: Periodo di riferimento nel formato "MM/YYYY".
        timestamp: Data e ora di generazione dell'alert.
    """
    codice: str
    livello: str
    messaggio: str
    valore_attuale: float
    soglia: float
    unita_operativa: Optional[str] = None
    periodo: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validazione post-inizializzazione."""
        livelli_validi = {l.value for l in LivelliAlert}
        if self.livello not in livelli_validi:
            raise ValueError(
                f"Livello alert non valido: '{self.livello}'. "
                f"Valori ammessi: {livelli_validi}"
            )
        if not self.periodo:
            self.periodo = periodo_corrente()


# ============================================================================
# VALUTAZIONE KPI GENERICA
# ============================================================================

def valuta_alert_kpi(nome_kpi: str, valore: float, config: dict) -> Alert:
    """
    Valuta un indicatore KPI rispetto alle soglie e genera un alert.

    La configurazione deve contenere le chiavi:
      - "soglia_verde": soglia per livello verde
      - "soglia_gialla": soglia per livello giallo
      - "inverso" (opzionale, default False): se True valori bassi sono migliori
      - "codice" (opzionale): codice alert personalizzato
      - "unita_operativa" (opzionale): codice UO
      - "periodo" (opzionale): periodo di riferimento
      - "formato" (opzionale): "percentuale", "valuta" o "numero"

    Args:
        nome_kpi: Nome descrittivo dell'indicatore.
        valore: Valore attuale dell'indicatore.
        config: Dizionario di configurazione con soglie e parametri.

    Returns:
        Oggetto Alert con il livello calcolato.

    Raises:
        KeyError: Se le soglie non sono presenti nella configurazione.
    """
    soglia_verde = config["soglia_verde"]
    soglia_gialla = config["soglia_gialla"]
    inverso = config.get("inverso", False)
    codice = config.get("codice", f"KPI_{nome_kpi.upper().replace(' ', '_')}")
    uo = config.get("unita_operativa", None)
    periodo = config.get("periodo", periodo_corrente())
    formato = config.get("formato", "numero")

    livello = colore_semaforo(valore, soglia_verde, soglia_gialla, inverso)

    # Formattazione del valore per il messaggio
    valore_formattato = _formatta_valore(valore, formato)
    soglia_rif = soglia_gialla if livello == "rosso" else soglia_verde
    soglia_formattata = _formatta_valore(soglia_rif, formato)

    # Costruzione messaggio
    if livello == LivelliAlert.VERDE.value:
        messaggio = (
            f"{nome_kpi}: valore {valore_formattato} nella norma "
            f"(soglia: {soglia_formattata})."
        )
    elif livello == LivelliAlert.GIALLO.value:
        messaggio = (
            f"ATTENZIONE - {nome_kpi}: valore {valore_formattato} "
            f"sotto la soglia ottimale ({soglia_formattata})."
        )
    else:
        messaggio = (
            f"CRITICO - {nome_kpi}: valore {valore_formattato} "
            f"sotto la soglia minima ({soglia_formattata})."
        )

    return Alert(
        codice=codice,
        livello=livello,
        messaggio=messaggio,
        valore_attuale=valore,
        soglia=soglia_rif,
        unita_operativa=uo,
        periodo=periodo,
    )


# ============================================================================
# GENERAZIONE ALERT ECONOMICI
# ============================================================================

def genera_alert_economici(ce_data: dict, config: dict) -> List[Alert]:
    """
    Genera alert sugli indicatori economici dal conto economico.

    Indicatori valutati:
      - MOL (Margine Operativo Lordo) % per UO e consolidato
      - Incidenza costo personale su ricavi
      - Peso costi sede su ricavi
      - Scostamento rispetto al budget

    Args:
        ce_data: Dizionario con i dati del conto economico. Chiavi attese:
            - "ricavi_totali": float
            - "mol": float (margine operativo lordo)
            - "costo_personale": float
            - "costi_sede": float
            - "budget_ricavi" (opzionale): float
            - "budget_costi" (opzionale): float
            - "unita_operativa" (opzionale): str
            - "periodo" (opzionale): str
        config: Dizionario di configurazione alert (ALERT_CONFIG).

    Returns:
        Lista di Alert generati.
    """
    alerts: List[Alert] = []
    uo = ce_data.get("unita_operativa", None)
    periodo = ce_data.get("periodo", periodo_corrente())
    ricavi = ce_data.get("ricavi_totali", 0)

    if ricavi == 0:
        # Nessun ricavo: impossibile calcolare indicatori percentuali
        alerts.append(Alert(
            codice="ECO_RICAVI_000",
            livello=LivelliAlert.ROSSO.value,
            messaggio=f"Ricavi totali pari a zero per il periodo {periodo}.",
            valore_attuale=0.0,
            soglia=0.0,
            unita_operativa=uo,
            periodo=periodo,
        ))
        return alerts

    # --- MOL % ---
    mol = ce_data.get("mol", 0)
    mol_pct = mol / ricavi

    # Determina soglia MOL in base a UO o consolidato
    if uo:
        soglie_mol = SOGLIE_SEMAFORO.get("mol_industriale", (0.15, 0.10))
        codice_mol = f"ECO_MOL_{uo}"
        nome_mol = f"MOL industriale UO {uo}"
    else:
        soglie_mol = SOGLIE_SEMAFORO.get("mol_consolidato", (0.12, 0.08))
        codice_mol = "ECO_MOL_CONS"
        nome_mol = "MOL consolidato"

    alerts.append(valuta_alert_kpi(
        nome_kpi=nome_mol,
        valore=mol_pct,
        config={
            "soglia_verde": soglie_mol[0],
            "soglia_gialla": soglie_mol[1],
            "codice": codice_mol,
            "unita_operativa": uo,
            "periodo": periodo,
            "formato": "percentuale",
        },
    ))

    # --- Costo personale % ---
    costo_personale = ce_data.get("costo_personale", 0)
    cp_pct = costo_personale / ricavi

    soglie_cp = SOGLIE_SEMAFORO.get("costo_personale_pct", (0.55, 0.60))
    alerts.append(valuta_alert_kpi(
        nome_kpi=f"Costo personale / ricavi{' UO ' + uo if uo else ''}",
        valore=cp_pct,
        config={
            "soglia_verde": soglie_cp[0],
            "soglia_gialla": soglie_cp[1],
            "inverso": True,
            "codice": f"ECO_CP_{'UO_' + uo if uo else 'CONS'}",
            "unita_operativa": uo,
            "periodo": periodo,
            "formato": "percentuale",
        },
    ))

    # --- Peso costi sede ---
    costi_sede = ce_data.get("costi_sede", 0)
    if costi_sede > 0:
        sede_pct = costi_sede / ricavi
        soglia_sede_max = config.get("peso_costi_sede_max_pct", 0.20)
        alerts.append(valuta_alert_kpi(
            nome_kpi="Peso costi sede su ricavi",
            valore=sede_pct,
            config={
                "soglia_verde": soglia_sede_max * 0.80,
                "soglia_gialla": soglia_sede_max,
                "inverso": True,
                "codice": "ECO_SEDE_PCT",
                "unita_operativa": uo,
                "periodo": periodo,
                "formato": "percentuale",
            },
        ))

    # --- Scostamento budget ricavi ---
    budget_ricavi = ce_data.get("budget_ricavi", None)
    if budget_ricavi and budget_ricavi > 0:
        scostamento_ricavi = (ricavi - budget_ricavi) / budget_ricavi
        soglia_sco_max = config.get("scostamento_budget_max", 0.10)
        # Lo scostamento negativo e' critico
        livello_sco = colore_semaforo(
            scostamento_ricavi,
            soglia_verde=0.0,
            soglia_gialla=-soglia_sco_max,
        )
        alerts.append(Alert(
            codice=f"ECO_BUDGET_{'UO_' + uo if uo else 'CONS'}",
            livello=livello_sco,
            messaggio=(
                f"Scostamento ricavi vs budget: "
                f"{scostamento_ricavi * 100:+.1f}% "
                f"(soglia: {soglia_sco_max * 100:.0f}%)."
            ),
            valore_attuale=scostamento_ricavi,
            soglia=-soglia_sco_max,
            unita_operativa=uo,
            periodo=periodo,
        ))

    return alerts


# ============================================================================
# GENERAZIONE ALERT FINANZIARI
# ============================================================================

def genera_alert_finanziari(cf_data: dict, config: dict) -> List[Alert]:
    """
    Genera alert sugli indicatori finanziari dal cash flow.

    Indicatori valutati:
      - Cassa disponibile vs soglia minima
      - Copertura cassa in mesi
      - DSO (Days Sales Outstanding) crediti ASP
      - DSO crediti privati
      - DSCR (Debt Service Coverage Ratio)

    Args:
        cf_data: Dizionario con i dati finanziari. Chiavi attese:
            - "cassa_disponibile": float
            - "costi_mensili_medi": float
            - "crediti_asp": float (opzionale)
            - "ricavi_asp_mensili": float (opzionale)
            - "crediti_privati": float (opzionale)
            - "ricavi_privati_mensili": float (opzionale)
            - "dscr": float (opzionale)
            - "periodo": str (opzionale)
        config: Dizionario di configurazione alert (ALERT_CONFIG).

    Returns:
        Lista di Alert generati.
    """
    alerts: List[Alert] = []
    periodo = cf_data.get("periodo", periodo_corrente())

    # --- Cassa minima ---
    cassa = cf_data.get("cassa_disponibile", 0)
    cassa_minima = config.get("cassa_minima", 200_000)
    livello_cassa = colore_semaforo(
        cassa,
        soglia_verde=cassa_minima * 2,
        soglia_gialla=cassa_minima,
    )
    alerts.append(Alert(
        codice="FIN_CASSA",
        livello=livello_cassa,
        messaggio=(
            f"Cassa disponibile: {formatta_valuta(cassa)} "
            f"(minimo: {formatta_valuta(cassa_minima)})."
        ),
        valore_attuale=cassa,
        soglia=cassa_minima,
        periodo=periodo,
    ))

    # --- Copertura cassa in mesi ---
    costi_mensili = cf_data.get("costi_mensili_medi", 0)
    if costi_mensili > 0:
        copertura_mesi = cassa / costi_mensili
        soglie_cop = SOGLIE_SEMAFORO.get("copertura_cassa_mesi", (2.0, 1.0))
        alerts.append(valuta_alert_kpi(
            nome_kpi="Copertura cassa",
            valore=copertura_mesi,
            config={
                "soglia_verde": soglie_cop[0],
                "soglia_gialla": soglie_cop[1],
                "codice": "FIN_COPERTURA",
                "periodo": periodo,
                "formato": "numero",
            },
        ))

    # --- DSO crediti ASP ---
    crediti_asp = cf_data.get("crediti_asp", None)
    ricavi_asp_mensili = cf_data.get("ricavi_asp_mensili", None)
    if crediti_asp is not None and ricavi_asp_mensili and ricavi_asp_mensili > 0:
        dso_asp = crediti_asp / (ricavi_asp_mensili / 30)
        soglie_dso = SOGLIE_SEMAFORO.get("dso_asp", (120, 150))
        dso_max = config.get("dso_massimo_asp", 150)
        alerts.append(valuta_alert_kpi(
            nome_kpi="DSO crediti ASP",
            valore=dso_asp,
            config={
                "soglia_verde": soglie_dso[0],
                "soglia_gialla": soglie_dso[1],
                "inverso": True,
                "codice": "FIN_DSO_ASP",
                "periodo": periodo,
                "formato": "numero",
            },
        ))

    # --- DSO crediti privati ---
    crediti_priv = cf_data.get("crediti_privati", None)
    ricavi_priv_mensili = cf_data.get("ricavi_privati_mensili", None)
    if (crediti_priv is not None and ricavi_priv_mensili
            and ricavi_priv_mensili > 0):
        dso_priv = crediti_priv / (ricavi_priv_mensili / 30)
        dso_max_priv = config.get("dso_massimo_privati", 60)
        alerts.append(valuta_alert_kpi(
            nome_kpi="DSO crediti privati",
            valore=dso_priv,
            config={
                "soglia_verde": dso_max_priv * 0.75,
                "soglia_gialla": dso_max_priv,
                "inverso": True,
                "codice": "FIN_DSO_PRIV",
                "periodo": periodo,
                "formato": "numero",
            },
        ))

    # --- DSCR ---
    dscr = cf_data.get("dscr", None)
    if dscr is not None:
        soglie_dscr = SOGLIE_SEMAFORO.get("dscr", (1.2, 1.0))
        alerts.append(valuta_alert_kpi(
            nome_kpi="DSCR",
            valore=dscr,
            config={
                "soglia_verde": soglie_dscr[0],
                "soglia_gialla": soglie_dscr[1],
                "codice": "FIN_DSCR",
                "periodo": periodo,
                "formato": "numero",
            },
        ))

    return alerts


# ============================================================================
# GENERAZIONE ALERT OPERATIVI
# ============================================================================

def genera_alert_operativi(prod_data: dict, config: dict) -> List[Alert]:
    """
    Genera alert sugli indicatori di produzione e operativita'.

    Indicatori valutati:
      - Tasso di occupazione posti letto
      - Scostamento ricavo per giornata di degenza
      - Scostamento costo per giornata di degenza

    Args:
        prod_data: Dizionario con i dati operativi. Chiavi attese:
            - "posti_letto": int
            - "giornate_degenza": int
            - "giorni_periodo": int
            - "ricavo_giornata_effettivo": float (opzionale)
            - "ricavo_giornata_budget": float (opzionale)
            - "costo_giornata_effettivo": float (opzionale)
            - "costo_giornata_budget": float (opzionale)
            - "unita_operativa": str (opzionale)
            - "periodo": str (opzionale)
        config: Dizionario di configurazione alert (ALERT_CONFIG).

    Returns:
        Lista di Alert generati.
    """
    alerts: List[Alert] = []
    uo = prod_data.get("unita_operativa", None)
    periodo = prod_data.get("periodo", periodo_corrente())

    # --- Tasso di occupazione ---
    posti_letto = prod_data.get("posti_letto", 0)
    giornate = prod_data.get("giornate_degenza", 0)
    giorni = prod_data.get("giorni_periodo", 0)

    if posti_letto > 0 and giorni > 0:
        capacita_massima = posti_letto * giorni
        occupancy = giornate / capacita_massima
        soglie_occ = SOGLIE_SEMAFORO.get("occupancy", (0.90, 0.80))
        alerts.append(valuta_alert_kpi(
            nome_kpi=f"Tasso occupazione{' UO ' + uo if uo else ''}",
            valore=occupancy,
            config={
                "soglia_verde": soglie_occ[0],
                "soglia_gialla": soglie_occ[1],
                "codice": f"OPR_OCC_{'UO_' + uo if uo else 'CONS'}",
                "unita_operativa": uo,
                "periodo": periodo,
                "formato": "percentuale",
            },
        ))

    # --- Scostamento ricavo per giornata ---
    ric_eff = prod_data.get("ricavo_giornata_effettivo", None)
    ric_bud = prod_data.get("ricavo_giornata_budget", None)
    if ric_eff is not None and ric_bud and ric_bud > 0:
        sco_ric = (ric_eff - ric_bud) / ric_bud
        soglia_sco = config.get("scostamento_ricavo_giornata", 0.10)
        livello_ric = colore_semaforo(
            sco_ric,
            soglia_verde=0.0,
            soglia_gialla=-soglia_sco,
        )
        alerts.append(Alert(
            codice=f"OPR_RIC_GG_{'UO_' + uo if uo else 'CONS'}",
            livello=livello_ric,
            messaggio=(
                f"Scostamento ricavo/giornata"
                f"{' UO ' + uo if uo else ''}: "
                f"{sco_ric * 100:+.1f}% "
                f"(effettivo {formatta_valuta(ric_eff)} vs "
                f"budget {formatta_valuta(ric_bud)})."
            ),
            valore_attuale=sco_ric,
            soglia=-soglia_sco,
            unita_operativa=uo,
            periodo=periodo,
        ))

    # --- Scostamento costo per giornata ---
    cos_eff = prod_data.get("costo_giornata_effettivo", None)
    cos_bud = prod_data.get("costo_giornata_budget", None)
    if cos_eff is not None and cos_bud and cos_bud > 0:
        sco_cos = (cos_eff - cos_bud) / cos_bud
        soglia_sco_cos = config.get("scostamento_costo_giornata", 0.10)
        # Per i costi, un incremento e' negativo -> logica inversa
        livello_cos = colore_semaforo(
            sco_cos,
            soglia_verde=0.0,
            soglia_gialla=soglia_sco_cos,
            inverso=True,
        )
        alerts.append(Alert(
            codice=f"OPR_COS_GG_{'UO_' + uo if uo else 'CONS'}",
            livello=livello_cos,
            messaggio=(
                f"Scostamento costo/giornata"
                f"{' UO ' + uo if uo else ''}: "
                f"{sco_cos * 100:+.1f}% "
                f"(effettivo {formatta_valuta(cos_eff)} vs "
                f"budget {formatta_valuta(cos_bud)})."
            ),
            valore_attuale=sco_cos,
            soglia=soglia_sco_cos,
            unita_operativa=uo,
            periodo=periodo,
        ))

    return alerts


# ============================================================================
# FILTRO ALERT
# ============================================================================

def filtra_alert(
    alerts: List[Alert],
    livello: Optional[str] = None,
    uo: Optional[str] = None,
) -> List[Alert]:
    """
    Filtra una lista di alert per livello e/o unita' operativa.

    Args:
        alerts: Lista di Alert da filtrare.
        livello: Se specificato, mantiene solo gli alert con
                 questo livello ("verde", "giallo" o "rosso").
        uo: Se specificato, mantiene solo gli alert relativi a
            questa unita' operativa. Usa None per includere
            anche gli alert a livello consolidato.

    Returns:
        Lista filtrata di Alert.
    """
    risultato = alerts

    if livello is not None:
        risultato = [a for a in risultato if a.livello == livello]

    if uo is not None:
        risultato = [a for a in risultato if a.unita_operativa == uo]

    return risultato


# ============================================================================
# FORMATTAZIONE TESTO
# ============================================================================

def formatta_alert_testo(alert: Alert) -> str:
    """
    Formatta un alert come stringa leggibile per output testuale.

    Formato:
      [ROSSO] ECO_MOL_VLB | MOL industriale UO VLB: valore 8,5% ...
      Periodo: 01/2026 | UO: VLB | 2026-01-15 10:30:00

    Args:
        alert: Oggetto Alert da formattare.

    Returns:
        Stringa formattata su due righe.
    """
    # Simbolo livello
    simbolo = {
        "verde": "[VERDE]",
        "giallo": "[GIALLO]",
        "rosso": "[ROSSO]",
    }.get(alert.livello, "[?????]")

    # Riga principale
    riga1 = f"{simbolo} {alert.codice} | {alert.messaggio}"

    # Riga dettaglio
    parti_dettaglio = [f"Periodo: {alert.periodo}"]
    if alert.unita_operativa:
        parti_dettaglio.append(f"UO: {alert.unita_operativa}")
    parti_dettaglio.append(alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    riga2 = " | ".join(parti_dettaglio)

    return f"{riga1}\n  {riga2}"


# ============================================================================
# SALVATAGGIO LOG
# ============================================================================

def salva_log_alert(alerts: List[Alert], file_path: Path) -> None:
    """
    Salva una lista di alert su file in formato JSON Lines (.jsonl).

    Ogni riga del file contiene un alert serializzato in JSON.
    Se il file esiste gia', i nuovi alert vengono accodati.

    Args:
        alerts: Lista di Alert da salvare.
        file_path: Percorso del file di log. La directory padre viene
                   creata automaticamente se non esiste.
    """
    if not alerts:
        return

    # Crea la directory se non esiste
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Scrivi in modalita' append
    with open(file_path, "a", encoding="utf-8") as f:
        for alert in alerts:
            record = asdict(alert)
            # Serializza il timestamp come stringa ISO
            record["timestamp"] = alert.timestamp.isoformat()
            riga = json.dumps(record, ensure_ascii=False)
            f.write(riga + "\n")


# ============================================================================
# FUNZIONI INTERNE
# ============================================================================

def _formatta_valore(valore: float, formato: str) -> str:
    """
    Formatta un valore numerico secondo il tipo indicato.

    Args:
        valore: Valore da formattare.
        formato: Tipo di formato - "percentuale", "valuta" o "numero".

    Returns:
        Stringa formattata.
    """
    if formato == "percentuale":
        return formatta_percentuale(valore * 100, decimali=1)
    elif formato == "valuta":
        return formatta_valuta(valore)
    else:
        return formatta_numero(valore, decimali=1)
