"""Rich terminal output formatting.

Provides styled output for job submission results, hardware defaults,
and error messages using the `rich` library.
"""

import shlex

from rich.console import Console
from rich.markup import escape
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
        f"[dim]Check status:[/]  nomad-r-runner status {result.job_id}\n"
        f"[dim]Raw logs:[/]      nomad alloc logs -job {result.job_id}"
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


def print_resources(
    ram_mb: int,
    cpu_mhz: int,
    was_clamped: bool,
    user_label: str | None = None,
) -> None:
    """Print the resource allocation for the job.

    Args:
        ram_mb: Allocated RAM in MB.
        cpu_mhz: Allocated CPU in MHz.
        was_clamped: Whether values were clamped to defaults.
        user_label: Container user shown alongside the resources. A
            ``"UID:GID"`` string when running as the submitter, or ``None``
            (legacy default) when the container uses its image default
            (typically root) — most often because ``--as-root`` was passed.
    """
    if was_clamped:
        console.print("[yellow]Warning:[/] Requested resources exceeded defaults and were clamped.")
    user_part = f"  |  User: [bold]{user_label}[/]" if user_label else "  |  User: [bold]container default[/]"
    console.print(f"  RAM: [bold]{ram_mb}[/] MB  |  CPU: [bold]{cpu_mhz}[/] MHz{user_part}")


def print_job_options(script_args: tuple[str, ...] | list[str], restarts: int | None) -> None:
    """Print the script arguments and restart limit, when either was given.

    The arguments are shown so that a stray word on the command line, which
    would otherwise be forwarded to the script unnoticed, is visible before
    the job is submitted.

    Args:
        script_args: Arguments that will be passed to the R script.
        restarts: The ``--restarts`` value, or ``None`` for Nomad's default.
    """
    if script_args:
        shown = " ".join(shlex.quote(str(a)) for a in script_args)
        console.print(f"  Script arguments: [bold]{escape(shown)}[/]")
    if restarts is not None:
        console.print(f"  Restarts allowed: [bold]{restarts}[/]")


def print_image_build(tag: str) -> None:
    """Print a styled summary after a successful image build.

    Args:
        tag: The Docker image tag that was built.
    """
    body = (
        f"[bold green]Image:[/] {tag}\n"
        f"\n"
        f"[dim]Use it with:[/]  nomad-r-runner run script.R --image {tag}"
    )
    console.print(Panel(body, title="Image Built", border_style="green"))


def print_status(
    job_id: str,
    status: str,
    stdout: str,
    stderr: str,
    diagnosis: str | None,
) -> None:
    """Print job status with logs and optional diagnosis.

    Args:
        job_id: The Nomad job ID.
        status: Job status string (e.g. "complete", "failed", "running").
        stdout: Standard output from the R script.
        stderr: Standard error from the R script.
        diagnosis: Actionable suggestion from diagnose_logs, or None.
    """
    status_color = {
        "complete": "green",
        "failed": "red",
        "running": "yellow",
        "pending": "yellow",
    }.get(status, "white")

    body = f"[bold {status_color}]Status:[/] {status}\n"

    if stdout.strip():
        body += f"\n[bold]Output:[/]\n{stdout.strip()}\n"

    if stderr.strip():
        body += f"\n[bold red]Errors:[/]\n{stderr.strip()}\n"

    if diagnosis:
        body += f"\n[bold yellow]Suggestion:[/]\n{diagnosis}"

    console.print(Panel(body, title=f"Job {job_id}", border_style=status_color))


def print_error(msg: str) -> None:
    """Print a styled error message.

    Args:
        msg: The error message text.
    """
    console.print(f"[bold red]Error:[/] {msg}")
