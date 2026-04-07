"""Command-line interface for nomad-r-runner.

Defines the ``nomad-r-runner`` CLI as a Click group with two subcommands:

- ``run`` — submit an R script to Nomad
- ``status`` — check job status with log diagnosis
- ``build-image`` — build a custom Docker image with extra R packages
"""

import uuid
from pathlib import Path

import click

from . import __version__
from .hardware import clamp_resources, get_defaults
from .image import build_image, default_tag, ensure_local_tag, generate_dockerfile, parse_packages
from .diagnose import diagnose_logs
from .job import (
    DEFAULT_IMAGE,
    build_job_spec,
    get_alloc_logs,
    get_allocations,
    get_status,
    submit_job,
)
from .output import (
    print_defaults,
    print_error,
    print_image_build,
    print_resources,
    print_status,
    print_submission,
)


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """Submit R scripts to Nomad for execution in Docker containers."""


@cli.command()
@click.argument("script", type=click.Path(exists=True, readable=True, resolve_path=True))
@click.option("--max-ram", type=int, default=None, help="Max RAM in MB (default: 50% of system RAM).")
@click.option("--max-cpu", type=int, default=None, help="Max CPU in MHz (default: 50% of system CPU).")
@click.option("--image", default=DEFAULT_IMAGE, show_default=True, help="Docker image for R execution.")
@click.option("--name", default=None, help="Job name (default: auto-generated).")
@click.option("--data-dir", type=click.Path(exists=True, file_okay=False, resolve_path=True), default=None, help="Host directory to mount read-only at /data in the container.")
@click.option("--email", default=None, help="Email for job notifications (not yet implemented).")
@click.option("--show-defaults", is_flag=True, help="Print detected hardware defaults and exit.")
def run(
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


@cli.command("build-image")
@click.option("--packages", default=None, help="Comma-separated CRAN packages to install.")
@click.option("--bioc", default=None, help="Comma-separated Bioconductor packages to install.")
@click.option("--from-file", type=click.Path(exists=True, dir_okay=False, resolve_path=True), default=None, help="File listing packages (one per line, prefix bioc:: for Bioconductor).")
@click.option("--base-image", default=DEFAULT_IMAGE, show_default=True, help="Base Docker image to build from.")
@click.option("--tag", default=None, help="Image tag (default: auto-generated).")
def build_image_cmd(
    packages: str | None,
    bioc: str | None,
    from_file: str | None,
    base_image: str,
    tag: str | None,
) -> None:
    """Build a custom Docker image with extra R packages pre-installed.

    At least one of --packages, --bioc, or --from-file is required.
    """
    if not any([packages, bioc, from_file]):
        print_error("At least one of --packages, --bioc, or --from-file is required.")
        raise SystemExit(1)

    file_path = Path(from_file) if from_file else None
    cran_pkgs, bioc_pkgs = parse_packages(packages, bioc, file_path)

    if not cran_pkgs and not bioc_pkgs:
        print_error("No packages found to install.")
        raise SystemExit(1)

    image_tag = ensure_local_tag(tag) if tag else default_tag()
    dockerfile = generate_dockerfile(base_image, cran_pkgs, bioc_pkgs)

    try:
        build_image(dockerfile, image_tag)
    except Exception as exc:
        print_error(f"Docker build failed: {exc}")
        raise SystemExit(1)

    print_image_build(image_tag)


@cli.command()
@click.argument("job_id")
def status(job_id: str) -> None:
    """Check job status, view logs, and diagnose failures.

    JOB_ID is the Nomad job ID printed when the job was submitted.
    """
    try:
        job_info = get_status(job_id)
    except Exception as exc:
        print_error(f"Could not fetch job status: {exc}")
        raise SystemExit(1)

    job_status = job_info.get("Status", "unknown")

    # Get the most recent allocation's logs
    stdout = ""
    stderr = ""
    try:
        allocs = get_allocations(job_id)
        if allocs:
            alloc_id = allocs[0]["ID"]
            stdout = get_alloc_logs(alloc_id, log_type="stdout")
            stderr = get_alloc_logs(alloc_id, log_type="stderr")
    except Exception:
        pass  # logs unavailable, show status without them

    diagnosis = None
    if job_status in ("dead",) and stderr:
        diagnosis = diagnose_logs(stderr)
    if diagnosis is None and job_status in ("dead",) and stdout:
        diagnosis = diagnose_logs(stdout)

    # Map Nomad's "dead" status to something more user-friendly
    display_status = job_status
    if job_status == "dead":
        # Check if it completed or failed from the allocations
        try:
            allocs = get_allocations(job_id)
            if allocs:
                client_status = allocs[0].get("ClientStatus", "")
                display_status = client_status  # "complete" or "failed"
        except Exception:
            pass

    print_status(job_id, display_status, stdout, stderr, diagnosis)
