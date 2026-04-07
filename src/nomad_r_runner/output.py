"""Rich terminal output formatting.

Provides styled output for job submission results, hardware defaults,
and error messages using the `rich` library.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .hardware import HardwareDefaults
from .job import SubmitResult

console = Console()


def print_submission(result: SubmitResult) -> None:
    """Print a styled summary after successful job submission.

    Args:
        result: The submission result containing job and eval IDs.
    """
    body = (
        f"[bold green]Job ID:[/]  {result.job_id}\n"
        f"[bold green]Eval ID:[/] {result.eval_id}\n"
        f"\n"
        f"[dim]Check status:[/]  nomad job status {result.job_id}\n"
        f"[dim]View logs:[/]     nomad alloc logs -job {result.job_id}"
    )
    console.print(Panel(body, title="Job Submitted", border_style="green"))


def print_defaults(defaults: HardwareDefaults) -> None:
    """Print a table of detected hardware and default limits.

    Args:
        defaults: The detected hardware defaults.
    """
    table = Table(title="Hardware Defaults")
    table.add_column("Resource", style="bold")
    table.add_column("Total", justify="right")
    table.add_column("Default Max (50%)", justify="right")

    table.add_row("RAM", f"{defaults.total_ram_mb} MB", f"{defaults.max_ram_mb} MB")
    table.add_row("CPU", f"{defaults.total_cpu_mhz} MHz", f"{defaults.max_cpu_mhz} MHz")

    console.print(table)


def print_resources(ram_mb: int, cpu_mhz: int, was_clamped: bool) -> None:
    """Print the resource allocation for the job.

    Args:
        ram_mb: Allocated RAM in MB.
        cpu_mhz: Allocated CPU in MHz.
        was_clamped: Whether values were clamped to defaults.
    """
    if was_clamped:
        console.print("[yellow]Warning:[/] Requested resources exceeded defaults and were clamped.")
    console.print(f"  RAM: [bold]{ram_mb}[/] MB  |  CPU: [bold]{cpu_mhz}[/] MHz")


def print_error(msg: str) -> None:
    """Print a styled error message.

    Args:
        msg: The error message text.
    """
    console.print(f"[bold red]Error:[/] {msg}")
