"""Utilità: date, formattazione, alert."""

from karol_cdg.utils.date_utils import (
    periodo_corrente,
    periodo_precedente,
    lista_periodi,
    giorni_nel_mese,
    giorni_nel_periodo,
    trimestre,
    anno_da_periodo,
    mese_da_periodo,
    nome_mese,
    nome_mese_breve,
    formatta_data,
    formatta_periodo_esteso,
)

from karol_cdg.utils.format_utils import (
    formatta_valuta,
    formatta_percentuale,
    formatta_numero,
    formatta_variazione,
    parse_numero_italiano,
    colore_semaforo,
)

from karol_cdg.utils.alert_utils import (
    Alert,
    valuta_alert_kpi,
    genera_alert_economici,
    genera_alert_finanziari,
    genera_alert_operativi,
    filtra_alert,
    formatta_alert_testo,
    salva_log_alert,
)

__all__ = [
    # date_utils
    "periodo_corrente",
    "periodo_precedente",
    "lista_periodi",
    "giorni_nel_mese",
    "giorni_nel_periodo",
    "trimestre",
    "anno_da_periodo",
    "mese_da_periodo",
    "nome_mese",
    "nome_mese_breve",
    "formatta_data",
    "formatta_periodo_esteso",
    # format_utils
    "formatta_valuta",
    "formatta_percentuale",
    "formatta_numero",
    "formatta_variazione",
    "parse_numero_italiano",
    "colore_semaforo",
    # alert_utils
    "Alert",
    "valuta_alert_kpi",
    "genera_alert_economici",
    "genera_alert_finanziari",
    "genera_alert_operativi",
    "filtra_alert",
    "formatta_alert_testo",
    "salva_log_alert",
]
