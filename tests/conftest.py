"""Shared pytest fixtures for nomad-r-runner tests."""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@dataclass
class FakeVirtualMemory:
    """Mimics psutil's svmem named tuple."""
    total: int


@pytest.fixture()
def mock_psutil(monkeypatch):
    """Patch psutil to report 32 GB RAM and 16 CPU cores."""
    ram_bytes = 32 * 1024 * 1024 * 1024  # 32 GB
    cpu_cores = 16

    monkeypatch.setattr("psutil.virtual_memory", lambda: FakeVirtualMemory(total=ram_bytes))
    monkeypatch.setattr("psutil.cpu_count", lambda logical=True: cpu_cores)

    return {"ram_bytes": ram_bytes, "cpu_cores": cpu_cores}


@pytest.fixture()
def mock_nomad(monkeypatch):
    """Patch nomad.Nomad to capture submitted job specs without a real server."""
    client = MagicMock()
    client.job.register_job.return_value = {"EvalID": "eval-fake-1234"}
    client.job.get_job.return_value = {"Status": "running"}

    monkeypatch.setattr("nomad.Nomad", lambda **kwargs: client)

    return client


@pytest.fixture()
def tmp_r_script(tmp_path):
    """Create a temporary R script file."""
    script = tmp_path / "test_script.R"
    script.write_text('cat("hello\\n")\n')
    return script
