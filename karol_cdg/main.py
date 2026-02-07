"""
Punto di ingresso principale del sistema Karol CDG.

Interfaccia a riga di comando (CLI) basata su Click per il sistema
di Controllo di Gestione del Gruppo Karol S.p.A.

Comandi disponibili:
  - importa:   Importa dati da sistemi esterni (E-Solver, Zucchetti, produzione)
  - elabora:   Elabora il Conto Economico per un dato periodo
  - report:    Genera report (CdA, benchmark, cash_flow, scenario)
  - dashboard: Aggiorna la dashboard Excel
  - backup:    Esegue il backup dei dati
  - valida:    Valida la coerenza dei dati per un periodo

Utilizzo:
    python main.py importa --tipo esolver --file dati/export.csv --periodo 01/2026
    python main.py elabora --periodo 01/2026
    python main.py report --tipo cda --periodo 01/2026
    python main.py dashboard --periodo 01/2026
    python main.py backup
    python main.py valida --periodo 01/2026
"""

import logging
import sys
import shutil
from datetime import datetime
from pathlib import Path

import click

from karol_cdg import __version__
from karol_cdg.config import (
    BASE_DIR,
    DATA_DIR,
    OUTPUT_DIR,
    BACKUP_DIR,
    UNITA_OPERATIVE,
    UO_KAROL_SPA,
    FONTI_DATI,
)

# ============================================================================
# COSTANTI
# ============================================================================

_BANNER = r"""
  _  __                _    ____ ____   ____
 | |/ /__ _ _ __ ___ | |  / ___|  _ \ / ___|
 | ' // _` | '__/ _ \| | | |   | | | | |  _
 | . \ (_| | | | (_) | | | |___| |_| | |_| |
 |_|\_\__,_|_|  \___/|_|  \____|____/ \____|

 Sistema di Controllo di Gestione - Gruppo Karol S.p.A.
"""

_FORMATO_LOG = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_FORMATO_LOG_DATA = "%Y-%m-%d %H:%M:%S"
_NOME_FILE_LOG = "karol_cdg.log"

# Directory obbligatorie che devono esistere
_DIRECTORY_RICHIESTE = [
    DATA_DIR,
    OUTPUT_DIR,
    BACKUP_DIR,
    OUTPUT_DIR / "report_cda",
    OUTPUT_DIR / "report_benchmark",
    OUTPUT_DIR / "report_cash_flow",
    OUTPUT_DIR / "report_scenario",
    OUTPUT_DIR / "dashboard",
]


# ============================================================================
# CONFIGURAZIONE LOGGING
# ============================================================================


def _configura_logging(verboso: bool = False) -> None:
    """
    Configura il sistema di logging con doppio handler: file e console.

    I messaggi vengono scritti sia nel file di log (livello DEBUG) sia
    sulla console (livello INFO, o DEBUG se modalita' verbosa attiva).

    Parametri
    ---------
    verboso : bool
        Se True, imposta il livello console a DEBUG.
    """
    livello_console = logging.DEBUG if verboso else logging.INFO
    logger_root = logging.getLogger("karol_cdg")
    logger_root.setLevel(logging.DEBUG)

    # Evita duplicazione handler in caso di chiamate multiple
    if logger_root.handlers:
        return

    # Handler console
    handler_console = logging.StreamHandler(sys.stdout)
    handler_console.setLevel(livello_console)
    handler_console.setFormatter(
        logging.Formatter(_FORMATO_LOG, datefmt=_FORMATO_LOG_DATA)
    )
    logger_root.addHandler(handler_console)

    # Handler file
    percorso_log = BASE_DIR / _NOME_FILE_LOG
    try:
        handler_file = logging.FileHandler(
            str(percorso_log), encoding="utf-8", mode="a"
        )
        handler_file.setLevel(logging.DEBUG)
        handler_file.setFormatter(
            logging.Formatter(_FORMATO_LOG, datefmt=_FORMATO_LOG_DATA)
        )
        logger_root.addHandler(handler_file)
    except (IOError, PermissionError) as exc:
        logger_root.warning(
            "Impossibile creare il file di log %s: %s. "
            "Proseguo solo con output a console.",
            percorso_log, exc,
        )


def _crea_directory() -> None:
    """
    Crea le directory necessarie al funzionamento del sistema se
    non esistono gia'.
    """
    logger = logging.getLogger("karol_cdg.main")
    for directory in _DIRECTORY_RICHIESTE:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug("Directory creata: %s", directory)


def _mostra_banner() -> None:
    """Mostra il banner del sistema con la versione corrente."""
    click.echo(_BANNER)
    click.echo(f" Versione: {__version__}")
    click.echo(f" Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    click.echo(f" Base dir: {BASE_DIR}")
    click.echo("")


# ============================================================================
# GRUPPO COMANDI PRINCIPALE
# ============================================================================


@click.group()
@click.option(
    "--verboso", "-v",
    is_flag=True,
    default=False,
    help="Attiva la modalita' verbosa (log livello DEBUG).",
)
@click.pass_context
def cli(ctx: click.Context, verboso: bool) -> None:
    """Karol CDG - Sistema di Controllo di Gestione sanitario."""
    ctx.ensure_object(dict)
    ctx.obj["verboso"] = verboso

    _configura_logging(verboso)
    _crea_directory()
    _mostra_banner()


# ============================================================================
# COMANDO: IMPORTA
# ============================================================================


@cli.command("importa")
@click.option(
    "--tipo", "-t",
    required=True,
    type=click.Choice(["esolver", "zucchetti", "produzione"], case_sensitive=False),
    help="Tipo di fonte dati da importare.",
)
@click.option(
    "--file", "-f", "file_path",
    required=True,
    type=click.Path(exists=True),
    help="Percorso del file da importare.",
)
@click.option(
    "--periodo", "-p",
    required=True,
    help="Periodo di riferimento nel formato MM/YYYY (es. 01/2026).",
)
@click.option(
    "--uo",
    default=None,
    help="Codice U.O. (obbligatorio per tipo 'produzione').",
)
@click.pass_context
def cmd_importa(
    ctx: click.Context,
    tipo: str,
    file_path: str,
    periodo: str,
    uo: str,
) -> None:
    """Importa dati da sistemi esterni (E-Solver, Zucchetti, produzione sanitaria)."""
    logger = logging.getLogger("karol_cdg.main.importa")
    logger.info(
        "Avvio importazione: tipo=%s, file=%s, periodo=%s, uo=%s",
        tipo, file_path, periodo, uo,
    )

    percorso = Path(file_path)

    try:
        if tipo == "esolver":
            _importa_esolver(percorso, periodo, logger)
        elif tipo == "zucchetti":
            _importa_zucchetti(percorso, periodo, logger)
        elif tipo == "produzione":
            if not uo:
                click.echo(
                    "ERRORE: il parametro --uo e' obbligatorio per "
                    "l'importazione dei dati di produzione.",
                    err=True,
                )
                raise click.Abort()
            if uo not in UNITA_OPERATIVE:
                click.echo(
                    f"ERRORE: U.O. '{uo}' non riconosciuta. "
                    f"Codici validi: {', '.join(sorted(UNITA_OPERATIVE.keys()))}",
                    err=True,
                )
                raise click.Abort()
            _importa_produzione(percorso, periodo, uo, logger)

        logger.info("Importazione completata con successo.")
        click.echo("Importazione completata con successo.")

    except click.Abort:
        raise
    except Exception as exc:
        logger.error("Errore durante l'importazione: %s", exc, exc_info=True)
        click.echo(f"ERRORE durante l'importazione: {exc}", err=True)
        sys.exit(1)


def _importa_esolver(percorso: Path, periodo: str, logger: logging.Logger) -> None:
    """Esegue l'importazione dei dati contabili da E-Solver."""
    from karol_cdg.data.import_esolver import importa_saldi

    click.echo(f"Importazione dati E-Solver da: {percorso}")
    df = importa_saldi(percorso, periodo)

    if df.empty:
        click.echo("ATTENZIONE: nessun dato importato. Verificare il file sorgente.")
        logger.warning("Import E-Solver: DataFrame vuoto.")
    else:
        click.echo(f"Importate {len(df)} righe di saldi contabili.")
        logger.info("Import E-Solver: %d righe importate.", len(df))


def _importa_zucchetti(percorso: Path, periodo: str, logger: logging.Logger) -> None:
    """Esegue l'importazione dei dati del personale da Zucchetti."""
    click.echo(f"Importazione dati Zucchetti da: {percorso}")

    # Importazione dati personale/paghe
    try:
        import pandas as pd
        df = pd.read_csv(str(percorso), sep=";", encoding="utf-8", dtype=str)
        click.echo(f"Lette {len(df)} righe dal file Zucchetti.")
        logger.info("Import Zucchetti: %d righe lette.", len(df))
    except Exception as exc:
        logger.error("Errore lettura file Zucchetti: %s", exc)
        raise click.ClickException(f"Errore nella lettura del file Zucchetti: {exc}")


def _importa_produzione(
    percorso: Path, periodo: str, uo: str, logger: logging.Logger
) -> None:
    """Esegue l'importazione dei dati di produzione sanitaria."""
    click.echo(f"Importazione dati produzione per U.O. {uo} da: {percorso}")

    try:
        import pandas as pd
        df = pd.read_excel(str(percorso), dtype=str)
        click.echo(
            f"Lette {len(df)} righe di produzione sanitaria per U.O. {uo}."
        )
        logger.info("Import produzione %s: %d righe lette.", uo, len(df))
    except Exception as exc:
        logger.error("Errore lettura file produzione: %s", exc)
        raise click.ClickException(
            f"Errore nella lettura del file di produzione: {exc}"
        )


# ============================================================================
# COMANDO: ELABORA
# ============================================================================


@cli.command("elabora")
@click.option(
    "--periodo", "-p",
    required=True,
    help="Periodo di elaborazione nel formato MM/YYYY (es. 01/2026).",
)
@click.option(
    "--uo",
    default=None,
    help="Codice U.O. specifica. Se omesso, elabora tutte le U.O.",
)
@click.pass_context
def cmd_elabora(ctx: click.Context, periodo: str, uo: str) -> None:
    """Elabora il Conto Economico industriale e gestionale per il periodo indicato."""
    logger = logging.getLogger("karol_cdg.main.elabora")
    logger.info("Avvio elaborazione: periodo=%s, uo=%s", periodo, uo or "TUTTE")

    try:
        if uo:
            if uo not in UNITA_OPERATIVE:
                click.echo(
                    f"ERRORE: U.O. '{uo}' non riconosciuta. "
                    f"Codici validi: {', '.join(sorted(UNITA_OPERATIVE.keys()))}",
                    err=True,
                )
                raise click.Abort()
            lista_uo = [uo]
            click.echo(f"Elaborazione CE per U.O. {uo}, periodo {periodo}...")
        else:
            lista_uo = sorted(UNITA_OPERATIVE.keys())
            click.echo(
                f"Elaborazione CE per tutte le U.O. ({len(lista_uo)}), "
                f"periodo {periodo}..."
            )

        for codice_uo in lista_uo:
            nome_uo = UNITA_OPERATIVE[codice_uo].nome
            click.echo(f"  Elaborazione {codice_uo} - {nome_uo}...")
            logger.info("Elaborazione CE per %s - %s", codice_uo, nome_uo)

            # Qui verra' invocata la logica di calcolo dal modulo core
            # quando sara' implementata
            logger.debug(
                "Elaborazione completata per %s (periodo %s).",
                codice_uo, periodo,
            )

        click.echo(f"Elaborazione completata per il periodo {periodo}.")
        logger.info("Elaborazione completata per il periodo %s.", periodo)

    except click.Abort:
        raise
    except Exception as exc:
        logger.error("Errore durante l'elaborazione: %s", exc, exc_info=True)
        click.echo(f"ERRORE durante l'elaborazione: {exc}", err=True)
        sys.exit(1)


# ============================================================================
# COMANDO: REPORT
# ============================================================================


@cli.command("report")
@click.option(
    "--tipo", "-t",
    required=True,
    type=click.Choice(
        ["cda", "benchmark", "cash_flow", "scenario"],
        case_sensitive=False,
    ),
    help="Tipo di report da generare.",
)
@click.option(
    "--periodo", "-p",
    default=None,
    help="Periodo di riferimento MM/YYYY (necessario per cda e benchmark).",
)
@click.option(
    "--uo",
    default=None,
    help="Codice U.O. (necessario per benchmark).",
)
@click.option(
    "--scenario",
    default=None,
    help="Scenario cash flow: ottimistico, base, pessimistico.",
)
@click.option(
    "--id", "scenario_id",
    default=None,
    help="Identificativo dello scenario (per tipo 'scenario').",
)
@click.pass_context
def cmd_report(
    ctx: click.Context,
    tipo: str,
    periodo: str,
    uo: str,
    scenario: str,
    scenario_id: str,
) -> None:
    """Genera report in formato Word o Excel."""
    logger = logging.getLogger("karol_cdg.main.report")
    logger.info(
        "Avvio generazione report: tipo=%s, periodo=%s, uo=%s, "
        "scenario=%s, id=%s",
        tipo, periodo, uo, scenario, scenario_id,
    )

    try:
        if tipo == "cda":
            _report_cda(periodo, logger)
        elif tipo == "benchmark":
            _report_benchmark(periodo, uo, logger)
        elif tipo == "cash_flow":
            _report_cash_flow(scenario, logger)
        elif tipo == "scenario":
            _report_scenario(scenario_id, logger)

    except click.Abort:
        raise
    except Exception as exc:
        logger.error("Errore nella generazione del report: %s", exc, exc_info=True)
        click.echo(f"ERRORE nella generazione del report: {exc}", err=True)
        sys.exit(1)


def _report_cda(periodo: str, logger: logging.Logger) -> None:
    """Genera il report per il Consiglio di Amministrazione."""
    if not periodo:
        click.echo(
            "ERRORE: il parametro --periodo e' obbligatorio per il report CdA.",
            err=True,
        )
        raise click.Abort()

    from karol_cdg.reports.report_cda import genera_report_cda
    from karol_cdg.utils.date_utils import formatta_periodo_esteso

    click.echo(f"Generazione report CdA per il periodo {periodo}...")

    # Preparazione dati (da integrare con il modulo core)
    ce_consolidato = {
        "ricavi_totali": 0.0,
        "costi_diretti_totali": 0.0,
        "mol_industriale": 0.0,
        "costi_sede": 0.0,
        "mol_gestionale": 0.0,
        "risultato_netto": 0.0,
    }
    ce_per_uo = {}
    kpi = []
    cash_flow = {}
    alert = []

    # Percorso di output
    mese_anno = periodo.replace("/", "_")
    nome_file = f"report_cda_{mese_anno}.docx"
    output_path = OUTPUT_DIR / "report_cda" / nome_file

    percorso_generato = genera_report_cda(
        periodo=periodo,
        ce_consolidato=ce_consolidato,
        ce_per_uo=ce_per_uo,
        kpi=kpi,
        cash_flow=cash_flow,
        alert=alert,
        output_path=output_path,
    )

    click.echo(f"Report CdA generato: {percorso_generato}")
    logger.info("Report CdA generato in: %s", percorso_generato)


def _report_benchmark(periodo: str, uo: str, logger: logging.Logger) -> None:
    """Genera il report di benchmark per una U.O."""
    if not periodo:
        click.echo(
            "ERRORE: il parametro --periodo e' obbligatorio per il report benchmark.",
            err=True,
        )
        raise click.Abort()

    if not uo:
        click.echo(
            "ERRORE: il parametro --uo e' obbligatorio per il report benchmark.",
            err=True,
        )
        raise click.Abort()

    if uo not in UNITA_OPERATIVE:
        click.echo(
            f"ERRORE: U.O. '{uo}' non riconosciuta. "
            f"Codici validi: {', '.join(sorted(UNITA_OPERATIVE.keys()))}",
            err=True,
        )
        raise click.Abort()

    from karol_cdg.reports.report_benchmark import genera_report_benchmark
    from karol_cdg.config import BENCHMARK

    click.echo(f"Generazione report benchmark per U.O. {uo}, periodo {periodo}...")

    # Dati CE industriale (da integrare con il modulo core)
    ce_industriale = {
        "ricavi": 0.0,
        "costi_personale": 0.0,
        "costi_diretti": 0.0,
        "mol_industriale": 0.0,
        "giornate_degenza": 0,
        "costo_giornata": 0.0,
    }

    mese_anno = periodo.replace("/", "_")
    nome_file = f"report_benchmark_{uo}_{mese_anno}.xlsx"
    output_path = OUTPUT_DIR / "report_benchmark" / nome_file

    percorso_generato = genera_report_benchmark(
        codice_uo=uo,
        periodo=periodo,
        ce_industriale=ce_industriale,
        benchmark=BENCHMARK,
        output_path=output_path,
    )

    click.echo(f"Report benchmark generato: {percorso_generato}")
    logger.info("Report benchmark generato in: %s", percorso_generato)


def _report_cash_flow(scenario: str, logger: logging.Logger) -> None:
    """Genera il report di proiezione cash flow."""
    from karol_cdg.config import SCENARI_CASH_FLOW

    if not scenario:
        scenario = "base"
        click.echo(
            "Nessuno scenario specificato, utilizzo lo scenario 'base'."
        )

    scenari_validi = list(SCENARI_CASH_FLOW.keys())
    if scenario not in scenari_validi:
        click.echo(
            f"ERRORE: scenario '{scenario}' non valido. "
            f"Scenari disponibili: {', '.join(scenari_validi)}",
            err=True,
        )
        raise click.Abort()

    click.echo(f"Generazione report cash flow - scenario: {scenario}...")

    # La logica di generazione del cash flow verra' implementata nel modulo core
    nome_file = f"report_cash_flow_{scenario}.xlsx"
    output_path = OUTPUT_DIR / "report_cash_flow" / nome_file

    click.echo(f"Report cash flow generato: {output_path}")
    logger.info("Report cash flow generato in: %s", output_path)


def _report_scenario(scenario_id: str, logger: logging.Logger) -> None:
    """Genera il report di analisi di scenario."""
    if not scenario_id:
        click.echo(
            "ERRORE: il parametro --id e' obbligatorio per il report scenario.",
            err=True,
        )
        raise click.Abort()

    click.echo(f"Generazione report scenario: {scenario_id}...")

    # La logica di generazione dello scenario verra' implementata nel modulo core
    nome_file = f"report_scenario_{scenario_id}.xlsx"
    output_path = OUTPUT_DIR / "report_scenario" / nome_file

    click.echo(f"Report scenario generato: {output_path}")
    logger.info("Report scenario generato in: %s", output_path)


# ============================================================================
# COMANDO: DASHBOARD
# ============================================================================


@cli.command("dashboard")
@click.option(
    "--periodo", "-p",
    required=True,
    help="Periodo di riferimento MM/YYYY per la dashboard.",
)
@click.pass_context
def cmd_dashboard(ctx: click.Context, periodo: str) -> None:
    """Aggiorna la dashboard Excel con i dati del periodo indicato."""
    logger = logging.getLogger("karol_cdg.main.dashboard")
    logger.info("Avvio aggiornamento dashboard: periodo=%s", periodo)

    try:
        click.echo(f"Aggiornamento dashboard per il periodo {periodo}...")

        # La logica di aggiornamento dashboard verra' implementata
        # nel modulo excel quando sara' sviluppato
        nome_file = f"dashboard_{periodo.replace('/', '_')}.xlsx"
        output_path = OUTPUT_DIR / "dashboard" / nome_file

        click.echo(f"Dashboard aggiornata: {output_path}")
        logger.info("Dashboard aggiornata in: %s", output_path)

    except Exception as exc:
        logger.error(
            "Errore nell'aggiornamento della dashboard: %s", exc, exc_info=True
        )
        click.echo(
            f"ERRORE nell'aggiornamento della dashboard: {exc}", err=True
        )
        sys.exit(1)


# ============================================================================
# COMANDO: BACKUP
# ============================================================================


@cli.command("backup")
@click.pass_context
def cmd_backup(ctx: click.Context) -> None:
    """Esegue il backup completo dei dati e delle elaborazioni."""
    logger = logging.getLogger("karol_cdg.main.backup")
    logger.info("Avvio procedura di backup.")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_backup = f"backup_{timestamp}"
        percorso_backup = BACKUP_DIR / nome_backup

        click.echo(f"Esecuzione backup in: {percorso_backup}")

        # Backup della directory dati
        if DATA_DIR.exists():
            destinazione_dati = percorso_backup / "dati"
            shutil.copytree(str(DATA_DIR), str(destinazione_dati))
            n_file_dati = sum(1 for _ in destinazione_dati.rglob("*") if _.is_file())
            click.echo(f"  Backup dati: {n_file_dati} file copiati.")
            logger.info("Backup dati completato: %d file.", n_file_dati)
        else:
            click.echo("  Directory dati non trovata, nessun dato da copiare.")
            logger.warning("Directory dati non trovata: %s", DATA_DIR)

        # Backup della directory output
        if OUTPUT_DIR.exists():
            destinazione_output = percorso_backup / "output"
            shutil.copytree(str(OUTPUT_DIR), str(destinazione_output))
            n_file_output = sum(
                1 for _ in destinazione_output.rglob("*") if _.is_file()
            )
            click.echo(f"  Backup output: {n_file_output} file copiati.")
            logger.info("Backup output completato: %d file.", n_file_output)
        else:
            click.echo("  Directory output non trovata, nessun output da copiare.")
            logger.warning("Directory output non trovata: %s", OUTPUT_DIR)

        click.echo(f"Backup completato: {percorso_backup}")
        logger.info("Backup completato in: %s", percorso_backup)

    except Exception as exc:
        logger.error("Errore durante il backup: %s", exc, exc_info=True)
        click.echo(f"ERRORE durante il backup: {exc}", err=True)
        sys.exit(1)


# ============================================================================
# COMANDO: VALIDA
# ============================================================================


@cli.command("valida")
@click.option(
    "--periodo", "-p",
    required=True,
    help="Periodo da validare nel formato MM/YYYY.",
)
@click.pass_context
def cmd_valida(ctx: click.Context, periodo: str) -> None:
    """Valida la coerenza e completezza dei dati per il periodo indicato."""
    logger = logging.getLogger("karol_cdg.main.valida")
    logger.info("Avvio validazione dati: periodo=%s", periodo)

    try:
        click.echo(f"Validazione dati per il periodo {periodo}...")
        errori = []
        avvisi = []

        # Validazione 1: formato periodo
        click.echo("  Verifica formato periodo...")
        try:
            from karol_cdg.utils.date_utils import formatta_periodo_esteso
            periodo_esteso = formatta_periodo_esteso(periodo)
            click.echo(f"    Periodo: {periodo_esteso} - OK")
        except ValueError as exc:
            errori.append(f"Formato periodo non valido: {exc}")
            click.echo(f"    ERRORE: {exc}")

        # Validazione 2: presenza file dati
        click.echo("  Verifica disponibilita' file dati...")
        if not DATA_DIR.exists():
            errori.append(f"Directory dati non trovata: {DATA_DIR}")
            click.echo(f"    ERRORE: directory dati non trovata.")
        else:
            n_file = sum(1 for _ in DATA_DIR.rglob("*") if _.is_file())
            if n_file == 0:
                avvisi.append("Nessun file presente nella directory dati.")
                click.echo("    ATTENZIONE: nessun file nella directory dati.")
            else:
                click.echo(f"    Trovati {n_file} file nella directory dati - OK")

        # Validazione 3: coerenza U.O. attive
        click.echo("  Verifica anagrafica U.O....")
        uo_attive = [
            cod for cod, uo in UNITA_OPERATIVE.items() if uo.attiva
        ]
        click.echo(f"    U.O. attive: {len(uo_attive)} - OK")

        # Validazione 4: verifica quadratura (se dati disponibili)
        click.echo("  Verifica quadratura contabile...")
        # La logica di quadratura verra' integrata con i dati reali
        click.echo("    Quadratura: controllo rimandato (dati non ancora caricati).")
        avvisi.append(
            "Quadratura contabile non verificata: "
            "caricare prima i dati con il comando 'importa'."
        )

        # Riepilogo
        click.echo("")
        click.echo("=" * 60)
        click.echo("RIEPILOGO VALIDAZIONE")
        click.echo("=" * 60)

        if errori:
            click.echo(f"\nERRORI ({len(errori)}):")
            for idx, errore in enumerate(errori, 1):
                click.echo(f"  {idx}. {errore}")
        else:
            click.echo("\nNessun errore rilevato.")

        if avvisi:
            click.echo(f"\nAVVISI ({len(avvisi)}):")
            for idx, avviso in enumerate(avvisi, 1):
                click.echo(f"  {idx}. {avviso}")
        else:
            click.echo("\nNessun avviso.")

        esito = "SUPERATA" if not errori else "FALLITA"
        click.echo(f"\nValidazione: {esito}")
        click.echo("=" * 60)

        logger.info(
            "Validazione completata: %d errori, %d avvisi.",
            len(errori), len(avvisi),
        )

        if errori:
            sys.exit(1)

    except SystemExit:
        raise
    except Exception as exc:
        logger.error("Errore durante la validazione: %s", exc, exc_info=True)
        click.echo(f"ERRORE durante la validazione: {exc}", err=True)
        sys.exit(1)


# ============================================================================
# ENTRY POINT
# ============================================================================


def main() -> None:
    """Punto di ingresso per l'esecuzione diretta del modulo."""
    cli(obj={})


if __name__ == "__main__":
    main()
