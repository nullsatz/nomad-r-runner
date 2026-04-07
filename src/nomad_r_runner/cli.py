"""Command-line interface for nomad-r-runner.

Defines the ``nomad-r-runner`` CLI using Click. The main entry point
validates the R script path, detects hardware defaults, clamps resources,
and submits the job to Nomad.
"""

import uuid
from pathlib import Path

import click

from . import __version__
from .hardware import clamp_resources, get_defaults
from .job import DEFAULT_IMAGE, build_job_spec, submit_job
from .output import print_defaults, print_error, print_resources, print_submission


@click.command()
@click.argument("script", type=click.Path(exists=True, readable=True, resolve_path=True))
@click.option("--max-ram", type=int, default=None, help="Max RAM in MB (default: 50% of system RAM).")
@click.option("--max-cpu", type=int, default=None, help="Max CPU in MHz (default: 50% of system CPU).")
@click.option("--image", default=DEFAULT_IMAGE, show_default=True, help="Docker image for R execution.")
@click.option("--name", default=None, help="Job name (default: auto-generated).")
@click.option("--data-dir", type=click.Path(exists=True, file_okay=False, resolve_path=True), default=None, help="Host directory to mount read-only at /data in the container.")
@click.option("--email", default=None, help="Email for job notifications (not yet implemented).")
@click.option("--show-defaults", is_flag=True, help="Print detected hardware defaults and exit.")
@click.version_option(version=__version__)
def main(
    script: str,
    max_ram: int | None,
    max_cpu: int | None,
    image: str,
    name: str | None,
    data_dir: str | None,
    email: str | None,
    show_defaults: bool,
) -> None:
    """Submit an R script to Nomad for execution in a Docker container.

    SCRIPT is the path to the R script to run.
    """
    defaults = get_defaults()

    if show_defaults:
        print_defaults(defaults)
        return

    if email:
        click.echo("Note: Email notifications are not yet implemented.")

    script_path = Path(script).resolve()
    job_name = name or f"r-{script_path.stem}-{uuid.uuid4().hex[:8]}"

    try:
        ram_mb, cpu_mhz = clamp_resources(max_ram, max_cpu, defaults)
    except ValueError as exc:
        print_error(str(exc))
        raise SystemExit(1)

    was_clamped = (
        (max_ram is not None and max_ram > defaults.max_ram_mb)
        or (max_cpu is not None and max_cpu > defaults.max_cpu_mhz)
    )
    print_resources(ram_mb, cpu_mhz, was_clamped)

    spec = build_job_spec(
        name=job_name,
        script_path=script_path,
        image=image,
        cpu_mhz=cpu_mhz,
        memory_mb=ram_mb,
        data_dir=Path(data_dir) if data_dir else None,
    )

    try:
        result = submit_job(spec)
    except Exception as exc:
        print_error(f"Failed to submit job: {exc}")
        raise SystemExit(1)

    print_submission(result)
