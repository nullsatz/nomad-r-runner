"""Nomad job spec construction and submission.

Builds batch-type Nomad job specifications for running R scripts inside
Docker containers, and submits them via the `python-nomad` client.
"""

import base64
import json
from dataclasses import dataclass
from pathlib import Path

import nomad


DEFAULT_IMAGE = "rocker/tidyverse:latest"
DEFAULT_DATACENTER = "dc1"


@dataclass(frozen=True)
class SubmitResult:
    """Result of a successful job submission.

    Attributes:
        job_id: The Nomad job ID.
        eval_id: The evaluation ID returned by Nomad.
    """

    job_id: str
    eval_id: str


def build_job_spec(
    name: str,
    script_path: Path,
    image: str,
    cpu_mhz: int,
    memory_mb: int,
    data_dir: Path | None = None,
    datacenter: str = DEFAULT_DATACENTER,
) -> dict:
    """Build a Nomad batch job spec for running an R script.

    Args:
        name: Job name / ID.
        script_path: Absolute path to the R script on the host.
        image: Docker image to use (e.g. ``rocker/tidyverse:latest``).
        cpu_mhz: CPU allocation in MHz.
        memory_mb: Memory allocation in megabytes.
        data_dir: Optional host directory to mount read-only at ``/data``
            inside the container.
        datacenter: Nomad datacenter name.

    Returns:
        A dict suitable for passing to ``nomad.Nomad().job.register_job()``.
    """
    volumes = [f"{script_path}:/scripts/user_script.R:ro"]
    if data_dir is not None:
        volumes.append(f"{data_dir}:/data:ro")

    return {
        "Job": {
            "ID": name,
            "Name": name,
            "Type": "batch",
            "Datacenters": [datacenter],
            "TaskGroups": [
                {
                    "Name": "r-group",
                    "Count": 1,
                    "Tasks": [
                        {
                            "Name": "run-r",
                            "Driver": "docker",
                            "Config": {
                                "image": image,
                                "command": "Rscript",
                                "args": ["/scripts/user_script.R"],
                                "volumes": volumes,
                            },
                            "Resources": {
                                "CPU": cpu_mhz,
                                "MemoryMB": memory_mb,
                            },
                        }
                    ],
                }
            ],
        }
    }


def submit_job(spec: dict, nomad_addr: str = "http://localhost:4646") -> SubmitResult:
    """Submit a job spec to Nomad.

    Args:
        spec: Job specification dict (as returned by `build_job_spec`).
        nomad_addr: Nomad HTTP API address.

    Returns:
        SubmitResult with the job ID and evaluation ID.
    """
    client = _make_client(nomad_addr)
    response = client.job.register_job(spec["Job"]["ID"], spec)
    return SubmitResult(
        job_id=spec["Job"]["ID"],
        eval_id=response["EvalID"],
    )


def _make_client(nomad_addr: str = "http://localhost:4646") -> nomad.Nomad:
    """Create a Nomad client from an address string."""
    return nomad.Nomad(
        host=nomad_addr.replace("http://", "").split(":")[0],
        port=int(nomad_addr.rsplit(":", 1)[-1]),
    )


def get_status(job_id: str, nomad_addr: str = "http://localhost:4646") -> dict:
    """Get the current status of a Nomad job.

    Args:
        job_id: The Nomad job ID.
        nomad_addr: Nomad HTTP API address.

    Returns:
        Dict with job status information from Nomad.
    """
    return _make_client(nomad_addr).job.get_job(job_id)


def get_allocations(job_id: str, nomad_addr: str = "http://localhost:4646") -> list[dict]:
    """Get allocations for a Nomad job.

    Args:
        job_id: The Nomad job ID.
        nomad_addr: Nomad HTTP API address.

    Returns:
        List of allocation dicts, most recent first.
    """
    return _make_client(nomad_addr).job.get_allocations(job_id)


def get_alloc_logs(
    alloc_id: str,
    task: str = "run-r",
    log_type: str = "stderr",
    nomad_addr: str = "http://localhost:4646",
) -> str:
    """Fetch logs from a Nomad allocation.

    Args:
        alloc_id: The allocation ID.
        task: Task name within the allocation.
        log_type: ``"stdout"`` or ``"stderr"``.
        nomad_addr: Nomad HTTP API address.

    Returns:
        Log text as a string, or empty string if logs are unavailable.
    """
    client = _make_client(nomad_addr)
    try:
        raw = client.client.stream_logs.stream(alloc_id, task, log_type)

        # python-nomad may return the raw JSON response with base64 data
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "Data" in parsed:
                    return base64.b64decode(parsed["Data"]).decode("utf-8", errors="replace")
            except (json.JSONDecodeError, KeyError):
                pass
            return raw

        if isinstance(raw, dict) and "Data" in raw:
            return base64.b64decode(raw["Data"]).decode("utf-8", errors="replace")

        return str(raw)
    except Exception:
        return ""
