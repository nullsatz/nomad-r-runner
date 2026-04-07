"""Tests for Nomad job spec building and submission."""

from pathlib import Path

from nomad_r_runner.job import build_job_spec, submit_job


class TestBuildJobSpec:
    """Tests for build_job_spec()."""

    def test_structure(self, tmp_r_script):
        """Spec should have correct top-level structure."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=2000,
            memory_mb=4096,
        )

        job = spec["Job"]
        assert job["ID"] == "test-job"
        assert job["Type"] == "batch"
        assert job["Datacenters"] == ["dc1"]

    def test_task_config(self, tmp_r_script):
        """Task should use docker driver with correct image and command."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/r-ver:4.3.2",
            cpu_mhz=1000,
            memory_mb=512,
        )

        task = spec["Job"]["TaskGroups"][0]["Tasks"][0]
        assert task["Driver"] == "docker"
        assert task["Config"]["image"] == "rocker/r-ver:4.3.2"
        assert task["Config"]["command"] == "Rscript"
        assert task["Config"]["args"] == ["/scripts/user_script.R"]

    def test_readonly_mount(self, tmp_r_script):
        """Bind mount should include :ro suffix."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
        )

        volumes = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["volumes"]
        assert len(volumes) == 1
        assert volumes[0].endswith(":ro")
        assert str(tmp_r_script) in volumes[0]

    def test_no_data_dir(self, tmp_r_script):
        """Without data_dir, only the script volume should be present."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
        )

        volumes = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["volumes"]
        assert len(volumes) == 1

    def test_data_dir_mount(self, tmp_r_script, tmp_path):
        """With data_dir, a second read-only volume should be mounted at /data."""
        data_dir = tmp_path / "mydata"
        data_dir.mkdir()

        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
            data_dir=data_dir,
        )

        volumes = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["volumes"]
        assert len(volumes) == 2
        assert volumes[1] == f"{data_dir}:/data:ro"

    def test_resources(self, tmp_r_script):
        """Resources should match the requested CPU and memory."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=3000,
            memory_mb=8192,
        )

        resources = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Resources"]
        assert resources["CPU"] == 3000
        assert resources["MemoryMB"] == 8192


class TestSubmitJob:
    """Tests for submit_job() with mocked Nomad client."""

    def test_submit_calls_register(self, tmp_r_script, mock_nomad):
        """submit_job should call register_job on the Nomad client."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
        )

        result = submit_job(spec)
        mock_nomad.job.register_job.assert_called_once()

    def test_submit_returns_ids(self, tmp_r_script, mock_nomad):
        """Result should contain job_id and eval_id."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
        )

        result = submit_job(spec)
        assert result.job_id == "test-job"
        assert result.eval_id == "eval-fake-1234"
