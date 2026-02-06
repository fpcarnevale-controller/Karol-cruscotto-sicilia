"""
Configurazione centrale del sistema di Controllo di Gestione.
Contiene anagrafiche, benchmark, soglie alert e parametri generali.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path

# ============================================================================
# PERCORSI
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "dati"
OUTPUT_DIR = BASE_DIR / "output"
BACKUP_DIR = BASE_DIR / "backup"
TEMPLATE_DIR = BASE_DIR / "karol_cdg" / "reports" / "templates"
EXCEL_MASTER = DATA_DIR / "KAROL_CDG_MASTER.xlsx"

# ============================================================================
# ENUMERAZIONI
# ============================================================================

class TipologiaStruttura(Enum):
    RSA_ALZHEIMER = "RSA Alzheimer"
    RSA_NON_AUTOSUFF = "RSA Non Autosufficienti"
    CTA_PSICHIATRIA = "CTA Psichiatria"
    CASA_DI_CURA = "Casa di Cura"
    DAY_SURGERY = "Day Surgery"
    AMBULATORIO = "Ambulatorio"
    LABORATORIO = "Laboratorio Analisi"
    CENTRO_DIURNO = "Centro Diurno"
    FKT = "Fisioterapia"
    RISTORAZIONE = "Ristorazione"
    RIABILITAZIONE = "Riabilitazione"


class Regione(Enum):
    SICILIA = "Sicilia"
    CALABRIA = "Calabria"
    LAZIO = "Lazio"
    PIEMONTE = "Piemonte"


class CategoriaCostoSede(Enum):
    SERVIZI = "Servizi alle U.O."
    GOVERNANCE = "Governance e Coordinamento"
    SVILUPPO = "Sviluppo"
    STORICO = "Costi storici"
    DA_CLASSIFICARE = "Da classificare"


class DriverAllocazione(Enum):
    FATTURE = "Numero fatture"
    CEDOLINI = "Numero cedolini"
    ACQUISTI = "Euro acquistato"
    POSTI_LETTO = "Posti letto"
    RICAVI = "Ricavi"
    POSTAZIONI = "Numero postazioni IT"
    UTENTI = "Numero utenti IT"
    QUOTA_FISSA = "Quota fissa"
    NON_ALLOCABILE = "Non allocabile"


class StatoScenario(Enum):
    BOZZA = "Bozza"
    VALUTATO = "Valutato"
    PRESENTATO = "Presentato"
    APPROVATO = "Approvato"
    SCARTATO = "Scartato"


class QualificaPersonale(Enum):
    MEDICO = "Medico"
    INFERMIERE = "Infermiere"
    OSS = "OSS/Ausiliario"
    TECNICO_LAB = "Tecnico Laboratorio"
    TECNICO_RAD = "Tecnico Radiologia"
    FISIOTERAPISTA = "Fisioterapista"
    AMMINISTRATIVO = "Amministrativo"
    DIRIGENTE = "Dirigente"
    ALTRO = "Altro"


class LivelliAlert(Enum):
    VERDE = "verde"
    GIALLO = "giallo"
    ROSSO = "rosso"


# ============================================================================
# ANAGRAFICHE UNITA' OPERATIVE
# ============================================================================

@dataclass
class UnitaOperativa:
    codice: str
    nome: str
    tipologia: List[TipologiaStruttura]
    regione: Regione
    posti_letto: int = 0
    attiva: bool = True
    societa: str = "Karol S.p.A."
    note: str = ""


UNITA_OPERATIVE: Dict[str, UnitaOperativa] = {
    "VLB": UnitaOperativa(
        codice="VLB",
        nome="RSA Villabate",
        tipologia=[TipologiaStruttura.RSA_ALZHEIMER],
        regione=Regione.SICILIA,
        posti_letto=44,
        note="RSA Alzheimer 44 PL"
    ),
    "CTA": UnitaOperativa(
        codice="CTA",
        nome="CTA Ex Stagno",
        tipologia=[TipologiaStruttura.CTA_PSICHIATRIA],
        regione=Regione.SICILIA,
        posti_letto=40,
        note="Psichiatria - Servizi Intensivi/Estensivi + Permessi Terapeutici"
    ),
    "COS": UnitaOperativa(
        codice="COS",
        nome="Casa di Cura Cosentino",
        tipologia=[TipologiaStruttura.CASA_DI_CURA, TipologiaStruttura.RIABILITAZIONE],
        regione=Regione.SICILIA,
        posti_letto=50,
        note="Ortopedia/Riabilitazione 50 PL"
    ),
    "KMC": UnitaOperativa(
        codice="KMC",
        nome="Karol Medical Center",
        tipologia=[TipologiaStruttura.DAY_SURGERY, TipologiaStruttura.AMBULATORIO],
        regione=Regione.SICILIA,
        posti_letto=0,
        note="Day Surgery + Ambulatori"
    ),
    "BRG": UnitaOperativa(
        codice="BRG",
        nome="Borgo Ritrovato",
        tipologia=[
            TipologiaStruttura.RSA_NON_AUTOSUFF,
            TipologiaStruttura.FKT,
            TipologiaStruttura.CENTRO_DIURNO
        ],
        regione=Regione.SICILIA,
        posti_letto=0,
        note="RSA + FKT + Centro Diurno"
    ),
    "ROM": UnitaOperativa(
        codice="ROM",
        nome="RSA Roma Santa Margherita",
        tipologia=[TipologiaStruttura.RIABILITAZIONE],
        regione=Regione.LAZIO,
        posti_letto=77,
        societa="Karol S.p.A.",
        note="Riabilitazione 77 PL"
    ),
    "LAB": UnitaOperativa(
        codice="LAB",
        nome="Karol Lab",
        tipologia=[TipologiaStruttura.LABORATORIO],
        regione=Regione.SICILIA,
        posti_letto=0,
        note="Laboratori Analisi"
    ),
    "BET": UnitaOperativa(
        codice="BET",
        nome="Karol Betania",
        tipologia=[TipologiaStruttura.RSA_NON_AUTOSUFF, TipologiaStruttura.RIABILITAZIONE],
        regione=Regione.CALABRIA,
        posti_letto=0,
        societa="Karol Betania S.r.l.",
        note="11 strutture RSA/Riabilitazione"
    ),
    "ZAR": UnitaOperativa(
        codice="ZAR",
        nome="Zaharaziz",
        tipologia=[TipologiaStruttura.RISTORAZIONE],
        regione=Regione.SICILIA,
        posti_letto=0,
        note="Servizi ristorazione"
    ),
}

# Lista UO Karol S.p.A. (esclude Betania per consolidato separato)
UO_KAROL_SPA = [cod for cod, uo in UNITA_OPERATIVE.items() if uo.societa == "Karol S.p.A."]
UO_BETANIA = [cod for cod, uo in UNITA_OPERATIVE.items() if uo.societa == "Karol Betania S.r.l."]

# ============================================================================
# STRUTTURA CONTO ECONOMICO
# ============================================================================

# Voci CE Industriale - Ricavi
VOCI_RICAVI = {
    "R01": "Ricavi da convenzione SSN/ASP - Degenza",
    "R02": "Ricavi da convenzione SSN/ASP - Ambulatoriale",
    "R03": "Ricavi da convenzione SSN/ASP - Laboratorio",
    "R04": "Ricavi privati/solvenza - Degenza",
    "R05": "Ricavi privati/solvenza - Pacchetti comfort",
    "R06": "Ricavi privati/solvenza - Ambulatoriale/Laboratorio",
    "R07": "Altri ricavi (affitti, rimborsi, contributi)",
}

# Voci CE Industriale - Costi Diretti
VOCI_COSTI_DIRETTI = {
    # Personale diretto
    "CD01": "Personale - Medici",
    "CD02": "Personale - Infermieri",
    "CD03": "Personale - OSS/Ausiliari",
    "CD04": "Personale - Tecnici (lab, rad, FKT)",
    "CD05": "Personale - Amministrativi di struttura",
    # Acquisti diretti
    "CD10": "Farmaci e presidi sanitari",
    "CD11": "Materiale diagnostico",
    "CD12": "Vitto (gestione interna)",
    "CD13": "Altri materiali di consumo",
    # Servizi diretti
    "CD20": "Lavanderia",
    "CD21": "Pulizie",
    "CD22": "Manutenzioni ordinarie",
    "CD23": "Utenze (quota struttura)",
    "CD24": "Consulenze sanitarie esterne",
    # Ammortamenti diretti
    "CD30": "Ammortamenti attrezzature e arredi",
}

# Voci CE Gestionale - Costi Sede Allocati
VOCI_COSTI_SEDE = {
    # Servizi centralizzati
    "CS01": "Contabilità/Amministrazione",
    "CS02": "Paghe/HR",
    "CS03": "Acquisti centralizzati",
    "CS04": "IT/Sistemi informativi",
    "CS05": "Qualità/Compliance",
    # Governance
    "CS10": "Direzione Generale",
    "CS11": "Affari Legali",
    "CS12": "Strategia/Sviluppo",
    # Costi comuni
    "CS20": "Costi comuni non allocabili",
}

# Voci CE - Altri costi
VOCI_ALTRI_COSTI = {
    "AC01": "Ammortamenti immobili/investimenti centralizzati",
    "AC02": "Oneri finanziari (quota debito)",
    "AC03": "Imposte",
}

# Driver di allocazione predefiniti per costi sede
DRIVER_PREDEFINITI: Dict[str, DriverAllocazione] = {
    "CS01": DriverAllocazione.FATTURE,
    "CS02": DriverAllocazione.CEDOLINI,
    "CS03": DriverAllocazione.ACQUISTI,
    "CS04": DriverAllocazione.POSTAZIONI,
    "CS05": DriverAllocazione.POSTI_LETTO,
    "CS10": DriverAllocazione.RICAVI,
    "CS11": DriverAllocazione.QUOTA_FISSA,
    "CS12": DriverAllocazione.NON_ALLOCABILE,
    "CS20": DriverAllocazione.NON_ALLOCABILE,
}

# ============================================================================
# BENCHMARK DI SETTORE
# ============================================================================

@dataclass
class BenchmarkSettore:
    tipologia: TipologiaStruttura
    costo_personale_su_ricavi_min: float  # %
    costo_personale_su_ricavi_max: float  # %
    mol_percentuale_target_min: float     # %
    mol_percentuale_target_max: float     # %
    costo_giornata_degenza_min: Optional[float] = None  # euro
    costo_giornata_degenza_max: Optional[float] = None  # euro


BENCHMARK: Dict[str, BenchmarkSettore] = {
    "RSA_ALZHEIMER": BenchmarkSettore(
        tipologia=TipologiaStruttura.RSA_ALZHEIMER,
        costo_personale_su_ricavi_min=55.0,
        costo_personale_su_ricavi_max=60.0,
        mol_percentuale_target_min=12.0,
        mol_percentuale_target_max=18.0,
        costo_giornata_degenza_min=90.0,
        costo_giornata_degenza_max=110.0,
    ),
    "RSA_NON_AUTOSUFF": BenchmarkSettore(
        tipologia=TipologiaStruttura.RSA_NON_AUTOSUFF,
        costo_personale_su_ricavi_min=50.0,
        costo_personale_su_ricavi_max=55.0,
        mol_percentuale_target_min=15.0,
        mol_percentuale_target_max=20.0,
        costo_giornata_degenza_min=80.0,
        costo_giornata_degenza_max=100.0,
    ),
    "RIABILITAZIONE": BenchmarkSettore(
        tipologia=TipologiaStruttura.RIABILITAZIONE,
        costo_personale_su_ricavi_min=45.0,
        costo_personale_su_ricavi_max=50.0,
        mol_percentuale_target_min=18.0,
        mol_percentuale_target_max=25.0,
        costo_giornata_degenza_min=150.0,
        costo_giornata_degenza_max=200.0,
    ),
    "CTA_PSICHIATRIA": BenchmarkSettore(
        tipologia=TipologiaStruttura.CTA_PSICHIATRIA,
        costo_personale_su_ricavi_min=55.0,
        costo_personale_su_ricavi_max=60.0,
        mol_percentuale_target_min=10.0,
        mol_percentuale_target_max=15.0,
        costo_giornata_degenza_min=120.0,
        costo_giornata_degenza_max=150.0,
    ),
    "DAY_SURGERY": BenchmarkSettore(
        tipologia=TipologiaStruttura.DAY_SURGERY,
        costo_personale_su_ricavi_min=35.0,
        costo_personale_su_ricavi_max=40.0,
        mol_percentuale_target_min=25.0,
        mol_percentuale_target_max=35.0,
    ),
    "LABORATORIO": BenchmarkSettore(
        tipologia=TipologiaStruttura.LABORATORIO,
        costo_personale_su_ricavi_min=30.0,
        costo_personale_su_ricavi_max=35.0,
        mol_percentuale_target_min=20.0,
        mol_percentuale_target_max=30.0,
    ),
}

# ============================================================================
# CONFIGURAZIONE ALERT
# ============================================================================

ALERT_CONFIG = {
    # Finanziari
    "cassa_minima": 200_000,              # euro
    "copertura_minima_giorni": 30,        # giorni
    "dso_massimo_asp": 150,               # giorni
    "dso_massimo_privati": 60,            # giorni
    "dpo_massimo_fornitori": 120,         # giorni
    "dscr_minimo": 1.0,

    # Economici
    "mol_minimo_uo": 0.05,                # 5%
    "mol_minimo_consolidato": 0.08,       # 8%
    "costo_personale_max_pct": 0.60,      # 60%
    "peso_costi_sede_max_pct": 0.20,      # 20%
    "scostamento_budget_max": 0.10,       # 10%

    # Operativi
    "occupancy_minima": 0.80,             # 80%
    "scostamento_ricavo_giornata": 0.10,  # 10%
    "scostamento_costo_giornata": 0.10,   # 10%
}

# Soglie semaforo: (verde_min, giallo_min) - sotto giallo_min è rosso
SOGLIE_SEMAFORO = {
    "occupancy": (0.90, 0.80),
    "mol_industriale": (0.15, 0.10),
    "mol_consolidato": (0.12, 0.08),
    "costo_personale_pct": (0.55, 0.60),   # invertito: sotto è meglio
    "dscr": (1.2, 1.0),
    "dso_asp": (120, 150),                  # invertito: sotto è meglio
    "copertura_cassa_mesi": (2.0, 1.0),
}

# ============================================================================
# PARAMETRI SCENARI CASH FLOW
# ============================================================================

SCENARI_CASH_FLOW = {
    "ottimistico": {
        "label": "Ottimistico",
        "dso_asp_giorni": 90,
        "occupancy_delta": 0.0,        # nessun delta
        "costi_imprevisti_pct": 0.0,
        "crescita_ricavi_pct": 0.02,   # +2%
    },
    "base": {
        "label": "Base",
        "dso_asp_giorni": 120,
        "occupancy_delta": 0.0,
        "costi_imprevisti_pct": 0.02,
        "crescita_ricavi_pct": 0.0,
    },
    "pessimistico": {
        "label": "Pessimistico",
        "dso_asp_giorni": 150,
        "occupancy_delta": -0.10,       # -10%
        "costi_imprevisti_pct": 0.05,
        "crescita_ricavi_pct": -0.03,   # -3%
    },
}

# ============================================================================
# FONTI DATI
# ============================================================================

FONTI_DATI = {
    "E-Solver": {
        "fornitore": "SISTEMI",
        "dati": ["Ciclo attivo/passivo", "Contabilità generale", "Piano dei conti", "Saldi"],
        "strutture": "Tutte",
        "formato_export": "CSV",
    },
    "Caremed_INNOGEA": {
        "fornitore": "INNOGEA",
        "dati": ["Produzione sanitaria", "DRG", "Prestazioni"],
        "strutture": ["COS", "LAB", "BET"],
        "formato_export": "Excel",
    },
    "HT_Sang": {
        "fornitore": "HT Sang",
        "dati": ["Produzione sanitaria RSA", "FKT", "CTA"],
        "strutture": ["VLB", "CTA", "BRG"],
        "formato_export": "Excel",
    },
    "Zucchetti": {
        "fornitore": "ZUCCHETTI",
        "dati": ["Personale", "Paghe", "Presenze"],
        "strutture": "Tutte",
        "formato_export": "CSV",
    },
}

# ============================================================================
# FORMATTAZIONE
# ============================================================================

FORMATO_DATA = "%d/%m/%Y"
FORMATO_MESE = "%m/%Y"
LOCALE_IT = "it_IT"
SEPARATORE_MIGLIAIA = "."
SEPARATORE_DECIMALI = ","
SIMBOLO_VALUTA = "€"

# ============================================================================
# RICAVI CONSOLIDATI DI RIFERIMENTO
# ============================================================================

RICAVI_RIFERIMENTO = {
    "karol_spa": 13_000_000,     # circa 13M
    "karol_betania": 15_000_000,  # circa 15M
    "gruppo_totale": 28_000_000,  # circa 28-30M
    "costi_sede_attuali": 2_500_000,  # circa 2.5M
    "pct_costi_sede_su_ricavi": 0.196,  # 19.6%
}

# ============================================================================
# MESI ITALIANI
# ============================================================================

MESI_IT = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre",
}

MESI_BREVI_IT = {
    1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "Mag", 6: "Giu", 7: "Lug", 8: "Ago",
    9: "Set", 10: "Ott", 11: "Nov", 12: "Dic",
}
