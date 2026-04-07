"""Docker image building with custom R packages.

Generates Dockerfiles and builds images with user-specified CRAN and
Bioconductor packages pre-installed, using the Docker SDK for Python.
Build output is streamed to the console so users can follow progress
during long Bioconductor compilations.
"""

import json
import tempfile
import uuid
from pathlib import Path

import docker
from rich.console import Console

console = Console()


def parse_packages(
    packages: str | None = None,
    bioc: str | None = None,
    from_file: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Parse package specifications into CRAN and Bioconductor lists.

    Packages can come from comma-separated strings (``--packages`` and
    ``--bioc``) or from a file (``--from-file``).  In a file, lines
    prefixed with ``bioc::`` are treated as Bioconductor packages; all
    others are CRAN.

    Args:
        packages: Comma-separated CRAN package names.
        bioc: Comma-separated Bioconductor package names.
        from_file: Path to a packages file (one per line).

    Returns:
        Tuple of (cran_packages, bioc_packages).
    """
    cran: list[str] = []
    bioc_pkgs: list[str] = []

    if packages:
        cran.extend(p.strip() for p in packages.split(",") if p.strip())

    if bioc:
        bioc_pkgs.extend(p.strip() for p in bioc.split(",") if p.strip())

    if from_file is not None:
        for line in from_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("bioc::"):
                bioc_pkgs.append(line.removeprefix("bioc::").strip())
            else:
                cran.append(line)

    return cran, bioc_pkgs


def generate_dockerfile(
    base_image: str,
    cran_packages: list[str],
    bioc_packages: list[str],
) -> str:
    """Generate a Dockerfile that installs the requested R packages.

    Args:
        base_image: Base Docker image (e.g. ``rocker/tidyverse:latest``).
        cran_packages: CRAN packages to install.
        bioc_packages: Bioconductor packages to install.

    Returns:
        Dockerfile content as a string.
    """
    lines = [f"FROM {base_image}"]

    if cran_packages:
        quoted = ", ".join(f'"{p}"' for p in cran_packages)
        lines.append(f"RUN R -e 'install.packages(c({quoted}))'")

    if bioc_packages:
        quoted = ", ".join(f'"{p}"' for p in bioc_packages)
        lines.append(
            "RUN R -e '"
            'if (!require("BiocManager", quietly=TRUE)) '
            'install.packages("BiocManager"); '
            f"BiocManager::install(c({quoted}))"
            "'"
        )

    return "\n".join(lines) + "\n"


def default_tag() -> str:
    """Generate a default image tag.

    The tag uses ``:local`` instead of ``:latest`` so that Nomad's Docker
    driver does not attempt to pull it from a registry.

    Returns:
        A tag like ``nomad-r-custom-a1b2c3d4:local``.
    """
    return f"nomad-r-custom-{uuid.uuid4().hex[:8]}:local"


def ensure_local_tag(tag: str) -> str:
    """Ensure a tag won't trigger a remote pull by Nomad.

    Nomad's Docker driver always tries to pull images tagged ``:latest``
    or with no tag. This appends ``:local`` to tags that would otherwise
    default to ``:latest``.

    Args:
        tag: The user-provided or auto-generated image tag.

    Returns:
        The tag, with ``:local`` appended if it had no version tag.
    """
    if ":" not in tag:
        return f"{tag}:local"
    if tag.endswith(":latest"):
        return tag.replace(":latest", ":local")
    return tag


def build_image(dockerfile_content: str, tag: str) -> str:
    """Build a Docker image from the given Dockerfile content.

    Uses the Docker SDK to build the image and streams build output
    to the console so users can follow progress.

    Args:
        dockerfile_content: The Dockerfile as a string.
        tag: The image tag to apply.

    Returns:
        The image tag on success.

    Raises:
        docker.errors.DockerException: If the Docker daemon is not
            reachable.
        docker.errors.BuildError: If the build fails.
    """
    try:
        client = docker.from_env()
    except docker.errors.DockerException as exc:
        raise docker.errors.DockerException(
            "Cannot connect to Docker. Is Docker Desktop running?"
        ) from exc

    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = Path(tmpdir) / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        console.print(f"[dim]Building image {tag}...[/]")

        resp = client.api.build(path=tmpdir, tag=tag, rm=True, decode=True)
        for chunk in resp:
            if "stream" in chunk:
                line = chunk["stream"].rstrip()
                if line:
                    console.print(f"  [dim]{line}[/]")
            if "error" in chunk:
                raise docker.errors.BuildError(
                    chunk["error"], build_log=[]
                )

    return tag
