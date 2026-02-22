"""
CLI for sheetmaskymizer.

Commands:
    analyze       - Analyze an Excel file, generate LLM prompt
    analyze-multi - Analyze multiple Excel files for schema patterns
    process       - Anonymize an Excel file using a config file
"""

import importlib.util
import typer
from pathlib import Path
from rich.console import Console
from sheetmask.analyzer import analyze_excel_for_anonymization
from sheetmask.multi_analyzer import analyze_multiple_files
from sheetmask.executor import AnonymizationExecutor

app = typer.Typer(
    name="sheetmask",
    help="Create PII-safe Excel test fixtures",
    no_args_is_help=True,
)

console = Console()


@app.command()
def analyze(
    input_file: Path = typer.Argument(
        ...,
        help="Excel file to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    sheet: str = typer.Option(
        None,
        "--sheet",
        "-s",
        help="Sheet name to analyze (default: all sheets)",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Save prompt to file (default: print to console)",
    ),
):
    """
    Generate LLM prompt for analyzing Excel columns.

    Analyzes column names, types, and sample values. Paste the output into
    Claude or ChatGPT to get anonymization config recommendations.

    Workflow:
        1. sheetmask analyze input.xlsx
        2. Copy the prompt into Claude or ChatGPT
        3. Save the recommended config dict to config.py
        4. sheetmask process input.xlsx --config config.py
    """

    try:
        console.print("[cyan]Analyzing Excel file...[/cyan]\n")
        prompt = analyze_excel_for_anonymization(input_file, sheet_name=sheet)

        if output:
            output.write_text(prompt)
            console.print(f"[green]Prompt saved to:[/green] {output}")
            console.print("\n[bold]Next steps:[/bold]")
            console.print(f"1. Open {output}")
            console.print("2. Copy the entire prompt")
            console.print("3. Paste into Claude or ChatGPT")
            console.print("4. Save the config dict to config.py")
            console.print("5. Run: sheetmask process input.xlsx --config config.py\n")
        else:
            console.print(prompt)
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("1. Copy the prompt above into Claude or ChatGPT")
            console.print("2. Save the config dict to config.py")
            console.print("3. Run: sheetmask process input.xlsx --config config.py\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="analyze-multi")
def analyze_multi(
    input_files: list[Path] = typer.Argument(
        ...,
        help="Excel files to analyze (space-separated)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Save prompt to file (default: print to console)",
    ),
):
    """
    Analyze multiple Excel files to detect schema patterns.

    Useful for understanding how a report varies across months before
    writing an anonymization config.
    """

    try:
        if len(input_files) < 2:
            msg = "[yellow]Warning: Only 1 file provided. Works best with 2+ files.[/yellow]"
            console.print(msg + "\n")

        console.print(f"[cyan]Analyzing {len(input_files)} files...[/cyan]\n")
        prompt = analyze_multiple_files(input_files)

        if output:
            output.write_text(prompt)
            console.print(f"[green]Analysis saved to:[/green] {output}")
        else:
            console.print(prompt)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def process(
    input_file: Path = typer.Argument(
        ...,
        help="Excel file to anonymize",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_file: Path = typer.Argument(
        None,
        help="Output path (default: {input_stem}_SYNTHETIC.xlsx in same directory)",
    ),
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Python config file containing a 'config' dict",
        exists=True,
        file_okay=True,
        readable=True,
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        "-s",
        help="Random seed for reproducible anonymization",
    ),
    export_mapping: Path = typer.Option(
        None,
        "--export-mapping",
        "-m",
        help="Export entity mapping report to JSON",
    ),
):
    """
    Anonymize an Excel file using a config file.

    The config file must be a Python file containing a 'config' dict.
    Get a config by running 'sheetmask analyze' first, then pasting
    the prompt into Claude or ChatGPT.

    Examples:
        sheetmask process input.xlsx --config my_config.py
        sheetmask process input.xlsx output.xlsx --config my_config.py
        sheetmask process input.xlsx --config config.py --seed 123
    """

    try:
        # Load config from Python file
        anon_config = _load_config(config)

        # Resolve output path
        output_path = _resolve_output_path(input_file, output_file)
        console.print(f"[cyan]Output:[/cyan] {output_path}")
        console.print(f"[cyan]Config:[/cyan] {config}")
        console.print(f"[cyan]Seed:[/cyan] {seed}\n")

        # Run anonymization
        executor = AnonymizationExecutor(anon_config, seed=seed)
        stats = executor.anonymize_file(input_file, output_path, auto_suffix=False)

        if export_mapping:
            executor.export_mapping_report(export_mapping)

        console.print("\n[bold green]Anonymization complete![/bold green]")
        console.print(f"  Input:    {input_file}")
        console.print(f"  Output:   {output_path}")
        console.print(f"  Sheets:   {stats['sheets_processed']}")
        console.print(f"  Rows:     {stats['total_rows']}")
        console.print(f"  Entities: {stats['entity_mappings']['total_mappings']}")

        if export_mapping:
            console.print(f"  Mapping:  {export_mapping}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _load_config(config_path: Path) -> dict:
    """Load anonymization config from a Python file."""
    spec = importlib.util.spec_from_file_location("_anon_config", config_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load config file: {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "config"):
        raise ValueError(
            f"{config_path} must define a 'config' dict. "
            "Run 'sheetmask analyze' to generate a starter config."
        )
    return module.config


def _resolve_output_path(input_file: Path, output_file: Path | None) -> Path:
    """Resolve output path. Defaults to {stem}_SYNTHETIC.xlsx in the same directory."""
    if output_file is not None:
        return output_file
    return input_file.parent / f"{input_file.stem}_SYNTHETIC.xlsx"
