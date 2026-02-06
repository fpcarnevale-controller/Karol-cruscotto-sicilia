"""
Utilità di formattazione numeri, valuta e percentuali per il locale italiano.

Tutte le funzioni producono stringhe nel formato italiano standard:
  - Separatore migliaia: punto (.)
  - Separatore decimali: virgola (,)
  - Simbolo valuta: euro (EUR)
"""

import math
from typing import Optional

from karol_cdg.config import (
    SEPARATORE_MIGLIAIA,
    SEPARATORE_DECIMALI,
    SIMBOLO_VALUTA,
)


# ============================================================================
# FORMATTAZIONE VALUTA
# ============================================================================

def formatta_valuta(importo: float, decimali: int = 2) -> str:
    """
    Formatta un importo come valuta italiana con il simbolo euro.

    Args:
        importo: Valore numerico da formattare.
        decimali: Numero di cifre decimali (default: 2).

    Returns:
        Stringa formattata, es. "€ 1.234.567,89".
        Gli importi negativi sono preceduti dal segno meno, es. "€ -1.234,56".

    Examples:
        >>> formatta_valuta(1234567.89)
        '€ 1.234.567,89'
        >>> formatta_valuta(-500.5, decimali=0)
        '€ -501'
    """
    segno = ""
    if importo < 0:
        segno = "-"
        importo = abs(importo)

    parte_formattata = _formatta_numero_base(importo, decimali)
    return f"{SIMBOLO_VALUTA} {segno}{parte_formattata}"


# ============================================================================
# FORMATTAZIONE PERCENTUALI
# ============================================================================

def formatta_percentuale(valore: float, decimali: int = 1) -> str:
    """
    Formatta un valore come percentuale italiana.

    Il valore in ingresso e' gia' espresso come percentuale
    (es. 12.5 viene formattato come "12,5%").

    Args:
        valore: Valore percentuale (non decimale).
        decimali: Numero di cifre decimali (default: 1).

    Returns:
        Stringa formattata, es. "12,5%".

    Examples:
        >>> formatta_percentuale(12.5)
        '12,5%'
        >>> formatta_percentuale(100.0, decimali=0)
        '100%'
    """
    testo = _formatta_numero_base(abs(valore), decimali)
    segno = "-" if valore < 0 else ""
    return f"{segno}{testo}%"


def formatta_variazione(valore: float, decimali: int = 1) -> str:
    """
    Formatta una variazione percentuale con segno esplicito (+ o -).

    Args:
        valore: Valore della variazione percentuale.
        decimali: Numero di cifre decimali (default: 1).

    Returns:
        Stringa con segno, es. "+12,5%" o "-3,2%".
        Il valore zero viene formattato come "0,0%" senza segno.

    Examples:
        >>> formatta_variazione(12.5)
        '+12,5%'
        >>> formatta_variazione(-3.2)
        '-3,2%'
        >>> formatta_variazione(0.0)
        '0,0%'
    """
    testo = _formatta_numero_base(abs(valore), decimali)
    if valore > 0:
        return f"+{testo}%"
    elif valore < 0:
        return f"-{testo}%"
    else:
        return f"{testo}%"


# ============================================================================
# FORMATTAZIONE NUMERI GENERICI
# ============================================================================

def formatta_numero(valore: float, decimali: int = 0) -> str:
    """
    Formatta un numero con separatore di migliaia italiano (punto).

    Args:
        valore: Valore numerico da formattare.
        decimali: Numero di cifre decimali (default: 0).

    Returns:
        Stringa formattata, es. "1.234.567" oppure "1.234,56".

    Examples:
        >>> formatta_numero(1234567)
        '1.234.567'
        >>> formatta_numero(1234.567, decimali=2)
        '1.234,57'
    """
    segno = ""
    if valore < 0:
        segno = "-"
        valore = abs(valore)
    return f"{segno}{_formatta_numero_base(valore, decimali)}"


# ============================================================================
# PARSING NUMERI ITALIANI
# ============================================================================

def parse_numero_italiano(testo: str) -> float:
    """
    Interpreta una stringa numerica in formato italiano e la converte in float.

    Gestisce:
      - Separatore migliaia: punto (.)
      - Separatore decimali: virgola (,)
      - Simbolo euro e segno percentuale
      - Spazi e segni +/-

    Args:
        testo: Stringa in formato italiano, es. "1.234,56" o "€ 1.234,56".

    Returns:
        Valore float corrispondente.

    Raises:
        ValueError: Se la stringa non puo' essere convertita.

    Examples:
        >>> parse_numero_italiano("1.234,56")
        1234.56
        >>> parse_numero_italiano("€ -1.234.567,89")
        -1234567.89
        >>> parse_numero_italiano("12,5%")
        12.5
    """
    if not isinstance(testo, str):
        raise ValueError(
            f"Attesa una stringa, ricevuto {type(testo).__name__}: {testo}"
        )

    # Rimuovi simboli e spazi non significativi
    pulito = testo.strip()
    pulito = pulito.replace(SIMBOLO_VALUTA, "")
    pulito = pulito.replace("%", "")
    pulito = pulito.replace(" ", "")
    pulito = pulito.replace("\xa0", "")  # spazio non interrompibile

    if not pulito:
        raise ValueError(f"Stringa vuota dopo la pulizia: '{testo}'")

    # Gestione segno
    negativo = False
    if pulito.startswith("-"):
        negativo = True
        pulito = pulito[1:]
    elif pulito.startswith("+"):
        pulito = pulito[1:]

    # Converti formato italiano -> formato standard
    # Rimuovi i punti (separatore migliaia) e sostituisci la virgola
    pulito = pulito.replace(SEPARATORE_MIGLIAIA, "")
    pulito = pulito.replace(SEPARATORE_DECIMALI, ".")

    try:
        valore = float(pulito)
    except ValueError:
        raise ValueError(
            f"Impossibile convertire '{testo}' in numero. "
            f"Valore dopo pulizia: '{pulito}'"
        )

    return -valore if negativo else valore


# ============================================================================
# SEMAFORO (VERDE / GIALLO / ROSSO)
# ============================================================================

def colore_semaforo(
    valore: float,
    soglia_verde: float,
    soglia_gialla: float,
    inverso: bool = False,
) -> str:
    """
    Determina il colore del semaforo in base alle soglie.

    Logica normale (inverso=False):
      - valore >= soglia_verde  ->  "verde"
      - valore >= soglia_gialla ->  "giallo"
      - altrimenti              ->  "rosso"

    Logica inversa (inverso=True) - usata per indicatori dove
    un valore piu' basso e' migliore (es. costo personale %):
      - valore <= soglia_verde  ->  "verde"
      - valore <= soglia_gialla ->  "giallo"
      - altrimenti              ->  "rosso"

    Args:
        valore: Valore dell'indicatore da valutare.
        soglia_verde: Soglia per il livello verde.
        soglia_gialla: Soglia per il livello giallo.
        inverso: Se True, un valore piu' basso e' migliore.

    Returns:
        Stringa: "verde", "giallo" oppure "rosso".

    Examples:
        >>> colore_semaforo(0.95, 0.90, 0.80)
        'verde'
        >>> colore_semaforo(0.85, 0.90, 0.80)
        'giallo'
        >>> colore_semaforo(0.55, 0.55, 0.60, inverso=True)
        'verde'
    """
    if inverso:
        if valore <= soglia_verde:
            return "verde"
        elif valore <= soglia_gialla:
            return "giallo"
        else:
            return "rosso"
    else:
        if valore >= soglia_verde:
            return "verde"
        elif valore >= soglia_gialla:
            return "giallo"
        else:
            return "rosso"


# ============================================================================
# FUNZIONI INTERNE
# ============================================================================

def _formatta_numero_base(valore: float, decimali: int) -> str:
    """
    Formatta un valore numerico (positivo) con separatori italiani.

    Args:
        valore: Valore positivo da formattare.
        decimali: Numero di cifre decimali.

    Returns:
        Stringa con punto come separatore migliaia e virgola
        come separatore decimali.
    """
    # Arrotonda al numero di decimali richiesto
    valore_arrotondato = round(valore, decimali)

    # Separa parte intera e decimale
    if decimali > 0:
        formato = f"{{:.{decimali}f}}"
        testo = formato.format(valore_arrotondato)
        parte_intera, parte_decimale = testo.split(".")
    else:
        parte_intera = str(int(round(valore_arrotondato)))
        parte_decimale = ""

    # Aggiungi separatore migliaia alla parte intera
    parte_intera_formattata = ""
    for i, cifra in enumerate(reversed(parte_intera)):
        if i > 0 and i % 3 == 0:
            parte_intera_formattata = SEPARATORE_MIGLIAIA + parte_intera_formattata
        parte_intera_formattata = cifra + parte_intera_formattata

    # Componi il risultato
    if decimali > 0:
        return f"{parte_intera_formattata}{SEPARATORE_DECIMALI}{parte_decimale}"
    else:
        return parte_intera_formattata
