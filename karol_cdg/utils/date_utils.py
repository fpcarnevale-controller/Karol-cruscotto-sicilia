"""
Utilità per date e periodi in formato italiano.

Gestisce periodi nel formato "MM/YYYY" usato nel sistema di controllo
di gestione Karol CDG.
"""

import calendar
from datetime import datetime, date
from typing import List, Optional

from karol_cdg.config import (
    FORMATO_DATA,
    FORMATO_MESE,
    MESI_IT,
    MESI_BREVI_IT,
)


# ============================================================================
# FUNZIONI SUL PERIODO CORRENTE
# ============================================================================

def periodo_corrente() -> str:
    """
    Restituisce il periodo corrente nel formato "MM/YYYY".

    Returns:
        Stringa con mese e anno corrente, es. "01/2026".
    """
    oggi = date.today()
    return f"{oggi.month:02d}/{oggi.year}"


def periodo_precedente(periodo: str) -> str:
    """
    Dato un periodo "MM/YYYY", restituisce il mese precedente.

    Args:
        periodo: Stringa nel formato "MM/YYYY".

    Returns:
        Periodo del mese precedente nel formato "MM/YYYY".

    Raises:
        ValueError: Se il formato del periodo non e' valido.
    """
    mese, anno = _parse_periodo(periodo)
    if mese == 1:
        mese = 12
        anno -= 1
    else:
        mese -= 1
    return f"{mese:02d}/{anno}"


# ============================================================================
# LISTA PERIODI E INTERVALLI
# ============================================================================

def lista_periodi(da: str, a: str) -> List[str]:
    """
    Genera la lista di tutti i periodi compresi tra due estremi (inclusi).

    Args:
        da: Periodo iniziale nel formato "MM/YYYY".
        a: Periodo finale nel formato "MM/YYYY".

    Returns:
        Lista di stringhe "MM/YYYY" ordinate cronologicamente.

    Raises:
        ValueError: Se il periodo iniziale e' successivo al finale.
    """
    mese_da, anno_da = _parse_periodo(da)
    mese_a, anno_a = _parse_periodo(a)

    if (anno_da, mese_da) > (anno_a, mese_a):
        raise ValueError(
            f"Il periodo iniziale ({da}) non puo' essere successivo "
            f"al periodo finale ({a})."
        )

    periodi: List[str] = []
    mese_corrente, anno_corrente = mese_da, anno_da

    while (anno_corrente, mese_corrente) <= (anno_a, mese_a):
        periodi.append(f"{mese_corrente:02d}/{anno_corrente}")
        if mese_corrente == 12:
            mese_corrente = 1
            anno_corrente += 1
        else:
            mese_corrente += 1

    return periodi


def giorni_nel_mese(mese: int, anno: int) -> int:
    """
    Restituisce il numero di giorni in un determinato mese/anno.

    Gestisce correttamente gli anni bisestili.

    Args:
        mese: Numero del mese (1-12).
        anno: Anno a quattro cifre.

    Returns:
        Numero di giorni nel mese indicato.

    Raises:
        ValueError: Se il mese non e' compreso tra 1 e 12.
    """
    if not 1 <= mese <= 12:
        raise ValueError(f"Mese non valido: {mese}. Deve essere tra 1 e 12.")
    return calendar.monthrange(anno, mese)[1]


def giorni_nel_periodo(da: str, a: str) -> int:
    """
    Calcola il numero totale di giorni sommando i giorni di ciascun mese
    nell'intervallo di periodi indicato (estremi inclusi).

    Args:
        da: Periodo iniziale nel formato "MM/YYYY".
        a: Periodo finale nel formato "MM/YYYY".

    Returns:
        Numero totale di giorni nell'intervallo.
    """
    periodi = lista_periodi(da, a)
    totale = 0
    for periodo in periodi:
        m, y = _parse_periodo(periodo)
        totale += giorni_nel_mese(m, y)
    return totale


# ============================================================================
# ESTRAZIONI DA PERIODO
# ============================================================================

def trimestre(periodo: str) -> int:
    """
    Restituisce il numero del trimestre (1-4) a cui appartiene il periodo.

    Args:
        periodo: Stringa nel formato "MM/YYYY".

    Returns:
        Numero del trimestre: 1 (Gen-Mar), 2 (Apr-Giu),
        3 (Lug-Set), 4 (Ott-Dic).
    """
    mese = mese_da_periodo(periodo)
    return (mese - 1) // 3 + 1


def anno_da_periodo(periodo: str) -> int:
    """
    Estrae l'anno da un periodo "MM/YYYY".

    Args:
        periodo: Stringa nel formato "MM/YYYY".

    Returns:
        Anno come intero a quattro cifre.
    """
    _, anno = _parse_periodo(periodo)
    return anno


def mese_da_periodo(periodo: str) -> int:
    """
    Estrae il numero del mese da un periodo "MM/YYYY".

    Args:
        periodo: Stringa nel formato "MM/YYYY".

    Returns:
        Numero del mese (1-12).
    """
    mese, _ = _parse_periodo(periodo)
    return mese


# ============================================================================
# FORMATTAZIONE E NOMI
# ============================================================================

def nome_mese(mese: int) -> str:
    """
    Restituisce il nome italiano del mese.

    Args:
        mese: Numero del mese (1-12).

    Returns:
        Nome completo del mese in italiano, es. "Gennaio".

    Raises:
        ValueError: Se il mese non e' compreso tra 1 e 12.
    """
    if mese not in MESI_IT:
        raise ValueError(f"Mese non valido: {mese}. Deve essere tra 1 e 12.")
    return MESI_IT[mese]


def nome_mese_breve(mese: int) -> str:
    """
    Restituisce il nome abbreviato italiano del mese (3 lettere).

    Args:
        mese: Numero del mese (1-12).

    Returns:
        Nome abbreviato del mese, es. "Gen".

    Raises:
        ValueError: Se il mese non e' compreso tra 1 e 12.
    """
    if mese not in MESI_BREVI_IT:
        raise ValueError(f"Mese non valido: {mese}. Deve essere tra 1 e 12.")
    return MESI_BREVI_IT[mese]


def formatta_data(data: datetime, formato: Optional[str] = None) -> str:
    """
    Formatta una data secondo il formato italiano.

    Args:
        data: Oggetto datetime da formattare.
        formato: Stringa di formato personalizzata. Se None, usa
                 il formato predefinito "GG/MM/AAAA" da configurazione.

    Returns:
        Data formattata come stringa.
    """
    if formato is None:
        formato = FORMATO_DATA
    return data.strftime(formato)


def formatta_periodo_esteso(periodo: str) -> str:
    """
    Converte un periodo "MM/YYYY" nella forma estesa italiana,
    es. "01/2026" -> "Gennaio 2026".

    Args:
        periodo: Stringa nel formato "MM/YYYY".

    Returns:
        Stringa con nome mese e anno, es. "Gennaio 2026".
    """
    mese, anno = _parse_periodo(periodo)
    return f"{nome_mese(mese)} {anno}"


# ============================================================================
# FUNZIONI INTERNE
# ============================================================================

def _parse_periodo(periodo: str) -> tuple:
    """
    Interpreta una stringa "MM/YYYY" e restituisce (mese, anno).

    Args:
        periodo: Stringa nel formato "MM/YYYY".

    Returns:
        Tupla (mese: int, anno: int).

    Raises:
        ValueError: Se il formato non e' valido o i valori non sono coerenti.
    """
    if not isinstance(periodo, str) or "/" not in periodo:
        raise ValueError(
            f"Formato periodo non valido: '{periodo}'. "
            f"Atteso 'MM/YYYY'."
        )
    parti = periodo.strip().split("/")
    if len(parti) != 2:
        raise ValueError(
            f"Formato periodo non valido: '{periodo}'. "
            f"Atteso 'MM/YYYY'."
        )
    try:
        mese = int(parti[0])
        anno = int(parti[1])
    except ValueError:
        raise ValueError(
            f"Formato periodo non valido: '{periodo}'. "
            f"Mese e anno devono essere numeri interi."
        )
    if not 1 <= mese <= 12:
        raise ValueError(
            f"Mese non valido nel periodo '{periodo}': {mese}. "
            f"Deve essere compreso tra 1 e 12."
        )
    if anno < 2000 or anno > 2100:
        raise ValueError(
            f"Anno non valido nel periodo '{periodo}': {anno}. "
            f"Deve essere compreso tra 2000 e 2100."
        )
    return mese, anno
