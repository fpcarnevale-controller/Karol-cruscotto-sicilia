"""
Modulo core: logiche di calcolo CE, allocazione, KPI, scenari.

Sotto-moduli:
    - ce_industriale: Conto Economico Industriale (pre-ribaltamento costi sede)
    - ce_gestionale: Conto Economico Gestionale (post-ribaltamento)
    - allocazione: Logiche di allocazione/ribaltamento costi sede
    - cash_flow: Calcolo flussi di cassa operativi e strategici
    - kpi: Motore di calcolo KPI operativi, economici e finanziari
    - scenari: Simulazione scenari di ristrutturazione
"""

from karol_cdg.core.ce_industriale import (
    calcola_ce_industriale,
    calcola_ce_industriale_multi_periodo,
    confronto_ce_industriale,
    confronto_con_budget,
    riepilogo_ce_tutte_uo,
)

from karol_cdg.core.ce_gestionale import (
    calcola_ce_gestionale,
    calcola_ce_consolidato,
    confronto_industriale_vs_gestionale,
    impatto_sede_per_uo,
)

from karol_cdg.core.allocazione import (
    RegolaDiAllocazione,
    calcola_allocazione,
    calcola_driver_percentuali,
    alloca_per_driver,
    alloca_pro_quota_ricavi,
    riepilogo_allocazione,
    simulazione_what_if,
)

from karol_cdg.core.cash_flow import (
    VoceScadenzario,
    calcola_cash_flow_operativo,
    calcola_cash_flow_strategico,
    applica_scenario,
    calcola_dso,
    calcola_dpo,
    calcola_copertura_cassa,
    genera_alert_cassa,
)

from karol_cdg.core.kpi import (
    KPI,
    calcola_kpi_operativi,
    calcola_kpi_economici,
    calcola_kpi_finanziari,
    calcola_tutti_kpi,
    confronta_kpi_con_benchmark,
    trend_kpi,
    kpi_to_dataframe,
)

from karol_cdg.core.scenari import (
    Intervento,
    Scenario,
    calcola_impatto_economico,
    calcola_impatto_finanziario,
    confronta_scenari,
    simula_riduzione_fte,
    simula_variazione_occupancy,
    genera_report_scenario,
)
