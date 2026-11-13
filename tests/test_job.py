"""Tests for Nomad job spec building and submission."""

from pathlib import Path

import pytest

from nomad_r_runner.job import RESTART_INTERVAL_NS, build_job_spec, submit_job


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

    def test_output_dir_mount(self, tmp_r_script, tmp_path):
        """With output_dir, a writable volume should be mounted at /output."""
        output_dir = tmp_path / "results"
        output_dir.mkdir()

        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
            output_dir=output_dir,
        )

        volumes = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["volumes"]
        assert len(volumes) == 2
        assert volumes[1] == f"{output_dir}:/output"
        assert ":ro" not in volumes[1]

    def test_data_and_output_dirs(self, tmp_r_script, tmp_path):
        """Both data_dir and output_dir should produce three volumes."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
            data_dir=data_dir,
            output_dir=output_dir,
        )

        volumes = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["volumes"]
        assert len(volumes) == 3
        assert volumes[0].endswith(":ro")      # script
        assert volumes[1].endswith(":ro")      # data
        assert ":ro" not in volumes[2]         # output is writable
        assert ":/output" in volumes[2]

    def test_no_user_field_by_default(self, tmp_r_script):
        """Without run_as_user, the task has no User (the container uses its
        image default), and the docker Config never carries a 'user' key."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
        )

        task = spec["Job"]["TaskGroups"][0]["Tasks"][0]
        assert "User" not in task
        assert "user" not in task["Config"]

    def test_run_as_user_sets_task_user(self, tmp_r_script):
        """run_as_user goes on the task as 'User'. Nomad's docker driver
        rejects a 'user' key inside Config and the job never starts (#1)."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
            run_as_user="1000:1000",
        )

        task = spec["Job"]["TaskGroups"][0]["Tasks"][0]
        assert task["User"] == "1000:1000"
        assert "user" not in task["Config"]

    def test_script_args_follow_the_script(self, tmp_r_script):
        """Arguments are appended after the script path, as strings (#2)."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
            script_args=("--cohort", 2024, "grade 5"),
        )
        args = spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["args"]
        assert args == ["/scripts/user_script.R", "--cohort", "2024", "grade 5"]

    def test_default_leaves_restart_policy_to_nomad(self, tmp_r_script):
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
        )
        group = spec["Job"]["TaskGroups"][0]
        assert "RestartPolicy" not in group
        assert "ReschedulePolicy" not in group

    def test_restarts_zero_fails_the_first_time(self, tmp_r_script):
        """restarts=0: no restart on the node and no reschedule either (#3)."""
        spec = build_job_spec(
            name="test-job",
            script_path=tmp_r_script,
            image="rocker/tidyverse:latest",
            cpu_mhz=1000,
            memory_mb=512,
            restarts=0,
        )
        group = spec["Job"]["TaskGroups"][0]
        assert group["RestartPolicy"] == {
            "Attempts": 0,
            "Interval": RESTART_INTERVAL_NS,
            "Mode": "fail",
        }
        assert group["ReschedulePolicy"] == {"Attempts": 0, "Unlimited": False}

    def test_restarts_n_and_negative(self, tmp_r_script):
        kwargs = {
            "name": "test-job",
            "script_path": tmp_r_script,
            "image": "rocker/tidyverse:latest",
            "cpu_mhz": 1000,
            "memory_mb": 512,
        }
        group = build_job_spec(**kwargs, restarts=2)["Job"]["TaskGroups"][0]
        assert group["RestartPolicy"]["Attempts"] == 2
        assert group["ReschedulePolicy"]["Attempts"] == 0
        with pytest.raises(ValueError):
            build_job_spec(**kwargs, restarts=-1)

    def test_restart_interval_outlasts_a_long_job(self):
        """Nomad starts the restart count again after each Interval; its
        24-hour default would let a multi-day job restart without limit."""
        assert RESTART_INTERVAL_NS >= 30 * 24 * 3600 * 10**9

    def test_script_args_must_be_a_sequence(self, tmp_r_script):
        """A bare string would be split into characters."""
        with pytest.raises(TypeError):
            build_job_spec(
                name="test-job",
                script_path=tmp_r_script,
                image="rocker/tidyverse:latest",
                cpu_mhz=1000,
                memory_mb=512,
                script_args="2024",
            )

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
