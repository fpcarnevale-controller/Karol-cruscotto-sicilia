# CLAUDE.md - Karol CDG Project Guide

## Project Overview

**Karol CDG** (Controllo di Gestione) is a healthcare financial management and control system for Gruppo Karol S.p.A., an Italian healthcare provider operating 8+ medical structures across Sicily, Calabria, Lazio, and Piemonte.

The system provides:
- Industrial and managed P&L analysis with cost allocation across operating units
- KPI dashboards with traffic-light alerts (green/yellow/red)
- Cash flow projections with optimistic/base/pessimistic scenarios
- Board reports (Word) and benchmark analysis (Excel)
- Scenario modeling for restructuring decisions

**Version:** 0.1.0 (early development)

## Tech Stack

- **Language:** Python 3.x
- **CLI Framework:** Click (>=8.1.0)
- **Data Processing:** pandas (>=2.0.0), numpy (>=1.24.0)
- **Excel I/O:** openpyxl (>=3.1.0)
- **Reports:** python-docx (>=0.8.11), reportlab (>=4.0.0)
- **Visualization:** matplotlib (>=3.7.0), seaborn (>=0.12.0)
- **Frontend:** React + Recharts (single-page dashboard in `index.html`)
- **Deployment:** GitHub Pages (static content via GitHub Actions)

## Repository Structure

```
├── index.html                  # React dashboard (standalone SPA)
├── dati/                       # Data directory
│   └── KAROL_CDG_MASTER.xlsx   # Central Excel data store
├── karol_cdg/                  # Main Python package
│   ├── __init__.py             # Package init (version)
│   ├── config.py               # Central configuration (~470 lines)
│   ├── main.py                 # CLI entry point (Click commands)
│   ├── requirements.txt        # Python dependencies
│   ├── core/                   # Business logic
│   │   ├── ce_industriale.py   # Industrial P&L
│   │   ├── ce_gestionale.py    # Managed P&L (post cost allocation)
│   │   ├── allocazione.py      # Cost allocation to operating units
│   │   ├── cash_flow.py        # Cash flow calculations
│   │   ├── kpi.py              # KPI engine
│   │   └── scenari.py          # Scenario simulation
│   ├── data/                   # Data import & validation
│   │   ├── import_esolver.py   # E-Solver accounting import
│   │   ├── import_zucchetti.py # Zucchetti payroll import
│   │   ├── import_produzione.py# Healthcare production import
│   │   └── validators.py       # Data validation rules
│   ├── excel/                  # Excel generation
│   │   ├── dashboard.py        # Excel dashboard
│   │   ├── genera_master.py    # Master file generation
│   │   ├── reader.py           # Excel reading utilities
│   │   └── writer.py           # Excel writing utilities
│   ├── reports/                # Report generation
│   │   ├── report_cda.py       # Board report (Word .docx)
│   │   └── report_benchmark.py # Benchmark analysis
│   └── utils/                  # Utilities
│       ├── date_utils.py       # Date/period helpers
│       ├── format_utils.py     # Number/currency formatting
│       └── alert_utils.py      # Alert generation
├── .github/workflows/
│   └── static.yml              # GitHub Pages deployment
└── .gitignore
```

## Architecture

The system follows a **layered architecture**:

1. **CLI Layer** (`main.py`) - Click commands: `importa`, `elabora`, `report`, `dashboard`, `backup`, `valida`
2. **Business Logic Layer** (`core/`) - P&L calculations, allocation, KPI, scenarios, cash flow
3. **Data Access Layer** (`data/`) - Import from E-Solver, Zucchetti, production systems; validation
4. **Export Layer** (`excel/`, `reports/`) - Excel dashboards, Word board reports, benchmark analysis

**Data flows file-based** (no database). The central data store is `dati/KAROL_CDG_MASTER.xlsx`.

## CLI Commands

```bash
# Import data from external systems
python -m karol_cdg.main importa --tipo esolver --file dati/export.csv --periodo 01/2026

# Process P&L for a period
python -m karol_cdg.main elabora --periodo 01/2026

# Generate reports
python -m karol_cdg.main report --tipo cda --periodo 01/2026
python -m karol_cdg.main report --tipo benchmark --periodo 01/2026

# Update dashboard
python -m karol_cdg.main dashboard --periodo 01/2026

# Backup data
python -m karol_cdg.main backup

# Validate data
python -m karol_cdg.main valida --periodo 01/2026

# Verbose mode (any command)
python -m karol_cdg.main --verboso elabora --periodo 01/2026
```

## Key Configuration (config.py)

### Operating Units (Unita Operative)

| Code | Name | Type | Region |
|------|------|------|--------|
| VLB | RSA Villabate | RSA Alzheimer (44 beds) | Sicilia |
| CTA | CTA Ex Stagno | CTA Psichiatria (40 beds) | Sicilia |
| COS | Casa di Cura Cosentino | Riabilitazione (50 beds) | Sicilia |
| KMC | Karol Medical Center | Day Surgery / Ambulatorio | Sicilia |
| BRG | Borgo Ritrovato | RSA + Riabilitazione | Piemonte |
| ROM | RSA Roma Santa Margherita | RSA (77 beds) | Lazio |
| LAB | Karol Lab | Laboratorio Analisi | Sicilia |
| BET | Karol Betania | Multi-structure (11 units) | Calabria |
| ZAR | Zaharaziz | Ristorazione (Catering) | Sicilia |

### Alert Thresholds

- Minimum cash: 200,000 EUR
- Max DSO (ASP): 150 days
- Max DPO (suppliers): 120 days
- Min MOL per unit: 5%
- Min occupancy: 80%

### Traffic Light (Semaforo) Thresholds

- Occupancy: green >= 90%, yellow >= 80%, red < 80%
- MOL Industrial: green >= 15%, yellow >= 10%, red < 10%
- Personnel cost ratio: green <= 55%, yellow <= 60%, red > 60% (inverted)

### File Paths

- `BASE_DIR`: project root (parent of `karol_cdg/`)
- `DATA_DIR`: `{BASE_DIR}/dati/`
- `OUTPUT_DIR`: `{BASE_DIR}/output/`
- `BACKUP_DIR`: `{BASE_DIR}/backup/`
- `EXCEL_MASTER`: `{DATA_DIR}/KAROL_CDG_MASTER.xlsx`

### Locale & Formatting

- Locale: `it_IT` (Italian)
- Currency: EUR (€)
- Date format: `%d/%m/%Y`
- Period format: `MM/YYYY`
- Thousands separator: `.` | Decimal separator: `,`

## Coding Conventions

### Language & Naming

- **Business logic** uses Italian names (functions, variables, docstrings) reflecting domain terminology
- **Module and class names** use English conventions (PEP 8)
- **Enums** use Italian uppercase: `TipologiaStruttura`, `DriverAllocazione`, `StatoScenario`
- **Constants** use SCREAMING_SNAKE_CASE with Italian words: `VOCI_RICAVI`, `SOGLIE_SEMAFORO`

### Code Style

- Follows PEP 8 conventions
- Uses Python 3 type hints (`Dict`, `List`, `Optional` from `typing`)
- Uses `dataclasses` for data models
- Uses `Enum` for domain constants
- Uses `pathlib.Path` for file paths (not `os.path`)
- Section separators: `# ====...====` comment blocks
- Detailed docstrings in Italian with parameter documentation

### Patterns

- **Dataclass models** for structured data (e.g., `UnitaOperativa`, `KPI`, `VoceScadenzario`)
- **Pure functions** for calculations (receive data, return results)
- **pandas DataFrames** as primary data structure for tabular data
- **Configuration as code** in `config.py` (no .env or external config files)
- **Logging** via Python `logging` module (dual handler: console + file)

### Import Style

```python
# Standard library
import logging
from datetime import datetime
from pathlib import Path

# Third-party
import click
import pandas as pd

# Internal
from karol_cdg.config import UNITA_OPERATIVE, SOGLIE_SEMAFORO
from karol_cdg.core import calcola_ce_industriale
```

## Data Integration Points

### Input Systems

| System | Data Type | Format | Structures |
|--------|-----------|--------|------------|
| E-Solver (SISTEMI) | Accounting (chart of accounts, balances, transactions) | CSV | All |
| Zucchetti | Payroll (personnel, wages, attendance) | CSV | All |
| Caremed/INNOGEA | Healthcare production | Excel | COS, LAB, BET |
| HT_Sang | RSA/FKT/CTA production | Excel | VLB, CTA, BRG |

### Output Directories

- `output/report_cda/` - Board reports (Word .docx)
- `output/report_benchmark/` - Benchmark analysis (Excel)
- `output/report_cash_flow/` - Cash flow projections
- `output/report_scenario/` - Scenario analysis
- `output/dashboard/` - Excel dashboards

## Deployment

- **GitHub Pages**: Static deployment of `index.html` dashboard via `.github/workflows/static.yml`
- Triggers on push to `main` branch or manual dispatch
- Python CLI is run locally (no server deployment)

## Setup

```bash
# Install dependencies
pip install -r karol_cdg/requirements.txt

# Create required directories
python -m karol_cdg.main backup  # will auto-create dirs on first run

# Verify with data validation
python -m karol_cdg.main valida --periodo 01/2026
```

## Current Limitations

- No test suite (pytest, unittest, etc.)
- No linting/formatting config (flake8, black, ruff, etc.)
- No type checking (mypy)
- No database (file-based only via Excel)
- No authentication/authorization
- No API layer (CLI-only)
- React dashboard (`index.html`) uses hardcoded sample data, not connected to Python backend
- No .env support; paths are relative to package root
- No Docker or containerization
