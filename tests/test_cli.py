"""Tests for the CLI interface using click.testing.CliRunner."""

from unittest.mock import patch

from click.testing import CliRunner

from nomad_r_runner.cli import cli


class TestRunCommand:
    """Integration tests for the ``run`` subcommand."""

    def test_help_output(self):
        """run --help should exit 0 and show usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "Submit an R script" in result.output

    def test_version_output(self):
        """--version on the group should print the version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_missing_script(self):
        """A nonexistent script path should fail."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "/nonexistent/path/script.R"])
        assert result.exit_code != 0

    def test_default_submission(self, tmp_r_script, mock_psutil, mock_nomad):
        """A valid script with defaults should submit successfully."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script)])
        assert result.exit_code == 0
        assert "Job Submitted" in result.output

    def test_custom_resources(self, tmp_r_script, mock_psutil, mock_nomad):
        """Custom --max-ram and --max-cpu should be reflected in output."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--max-ram", "2048", "--max-cpu", "1000",
        ])
        assert result.exit_code == 0
        assert "2048" in result.output
        assert "1000" in result.output

    def test_excessive_resources_clamped(self, tmp_r_script, mock_psutil, mock_nomad):
        """Resources above defaults should be clamped with a warning."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--max-ram", "999999", "--max-cpu", "999999",
        ])
        assert result.exit_code == 0
        assert "clamped" in result.output.lower()

    def test_show_defaults(self, mock_psutil):
        """--show-defaults should print hardware info and exit."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("dummy.R", "w") as f:
                f.write("# dummy\n")
            result = runner.invoke(cli, ["run", "dummy.R", "--show-defaults"])
        assert result.exit_code == 0
        assert "Hardware Defaults" in result.output

    def test_data_dir(self, tmp_r_script, tmp_path, mock_psutil, mock_nomad):
        """--data-dir should accept a valid directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--data-dir", str(data_dir),
        ])
        assert result.exit_code == 0
        assert "Job Submitted" in result.output

    def test_data_dir_nonexistent(self, tmp_r_script):
        """--data-dir with a nonexistent path should fail."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--data-dir", "/nonexistent/dir",
        ])
        assert result.exit_code != 0

    def test_output_dir(self, tmp_r_script, tmp_path, mock_psutil, mock_nomad):
        """--output-dir should accept a valid directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--output-dir", str(output_dir),
        ])
        assert result.exit_code == 0
        assert "Job Submitted" in result.output

    def test_output_dir_nonexistent(self, tmp_r_script):
        """--output-dir with a nonexistent path should fail."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--output-dir", "/nonexistent/dir",
        ])
        assert result.exit_code != 0

    def test_output_dir_is_file(self, tmp_r_script, tmp_path):
        """--output-dir pointing to a file should fail."""
        a_file = tmp_path / "not_a_dir.txt"
        a_file.write_text("hello")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", str(tmp_r_script), "--output-dir", str(a_file),
        ])
        assert result.exit_code != 0

    def test_email_stub(self, tmp_r_script, mock_psutil, mock_nomad):
        """--email should print a 'not yet implemented' note."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script), "--email", "test@example.com"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()

    def test_default_runs_as_current_user(
        self, tmp_r_script, mock_psutil, mock_nomad, monkeypatch
    ):
        """Default invocation should pin the container to the caller's UID:GID
        so bind-mounted output files end up owned by the submitter."""
        monkeypatch.setattr("nomad_r_runner.cli.os.getuid", lambda: 1234)
        monkeypatch.setattr("nomad_r_runner.cli.os.getgid", lambda: 5678)
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script)])
        assert result.exit_code == 0
        # mock_nomad records register_job(job_id, spec); pull the spec arg out.
        spec = mock_nomad.job.register_job.call_args.args[1]
        task = spec["Job"]["TaskGroups"][0]["Tasks"][0]
        assert task["User"] == "1234:5678"
        assert "user" not in task["Config"]      # Nomad rejects it there (#1)
        assert "1234:5678" in result.output  # surfaced in resource summary

    def test_as_root_omits_user(self, tmp_r_script, mock_psutil, mock_nomad):
        """--as-root should restore the legacy behavior: no User on the
        task, so the container runs as its image default user."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script), "--as-root"])
        assert result.exit_code == 0
        spec = mock_nomad.job.register_job.call_args.args[1]
        task = spec["Job"]["TaskGroups"][0]["Tasks"][0]
        assert "User" not in task
        assert "user" not in task["Config"]
        assert "container default" in result.output

    def test_script_args_pass_through(self, tmp_r_script, mock_psutil, mock_nomad):
        """Arguments after the script reach Rscript; after '--' they may
        begin with a dash without being read as our own options (#2)."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["run", str(tmp_r_script), "--max-ram", "1024", "--", "--cohort", "2024", "grade5"]
        )
        assert result.exit_code == 0, result.output
        spec = mock_nomad.job.register_job.call_args.args[1]
        task = spec["Job"]["TaskGroups"][0]["Tasks"][0]
        assert task["Config"]["args"] == ["/scripts/user_script.R", "--cohort", "2024", "grade5"]
        assert task["Resources"]["MemoryMB"] == 1024
        # shown before submission, so a stray word is visible
        assert "Script arguments: --cohort 2024 grade5" in result.output

        result = runner.invoke(cli, ["run", str(tmp_r_script), "alpha", "beta"])
        assert result.exit_code == 0, result.output
        spec = mock_nomad.job.register_job.call_args.args[1]
        assert spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["args"] == [
            "/scripts/user_script.R", "alpha", "beta"]

        # with no arguments the command line is as before
        result = runner.invoke(cli, ["run", str(tmp_r_script)])
        assert result.exit_code == 0, result.output
        assert "Script arguments" not in result.output
        spec = mock_nomad.job.register_job.call_args.args[1]
        assert spec["Job"]["TaskGroups"][0]["Tasks"][0]["Config"]["args"] == ["/scripts/user_script.R"]

    def test_script_arg_with_nomad_variable_syntax_is_refused(
        self, tmp_r_script, mock_psutil, mock_nomad
    ):
        """Nomad would read ${...} as its own variable and fail the task."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script), "--", "${cohort}.csv"])
        assert result.exit_code != 0
        assert "${" in result.output
        mock_nomad.job.register_job.assert_not_called()

    def test_restarts_option(self, tmp_r_script, mock_psutil, mock_nomad):
        """--restarts 0 makes the job fail the first time; without the
        option Nomad's own policy applies (#3)."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script), "--restarts", "0"])
        assert result.exit_code == 0, result.output
        group = mock_nomad.job.register_job.call_args.args[1]["Job"]["TaskGroups"][0]
        assert group["RestartPolicy"]["Attempts"] == 0
        assert group["RestartPolicy"]["Mode"] == "fail"
        assert group["ReschedulePolicy"] == {"Attempts": 0, "Unlimited": False}
        assert "Restarts allowed: 0" in result.output

        result = runner.invoke(cli, ["run", str(tmp_r_script)])
        assert result.exit_code == 0, result.output
        group = mock_nomad.job.register_job.call_args.args[1]["Job"]["TaskGroups"][0]
        assert "RestartPolicy" not in group
        assert "ReschedulePolicy" not in group

        for bad in ("-1", "101"):
            result = runner.invoke(cli, ["run", str(tmp_r_script), "--restarts", bad])
            assert result.exit_code != 0


class TestBuildImageCommand:
    """Integration tests for the ``build-image`` subcommand."""

    def test_help_output(self):
        """build-image --help should exit 0 and show usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["build-image", "--help"])
        assert result.exit_code == 0
        assert "Build a custom Docker image" in result.output

    def test_no_packages_fails(self):
        """Omitting all package sources should fail."""
        runner = CliRunner()
        result = runner.invoke(cli, ["build-image"])
        assert result.exit_code != 0

    @patch("nomad_r_runner.cli.build_image", return_value="test-image")
    def test_cran_packages(self, mock_build):
        """--packages should trigger a build with CRAN packages."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-image", "--packages", "glmnet,survival", "--tag", "test-image",
        ])
        assert result.exit_code == 0
        assert "Image Built" in result.output
        assert "test-image" in result.output
        mock_build.assert_called_once()

    @patch("nomad_r_runner.cli.build_image", return_value="bioc-image")
    def test_bioc_packages(self, mock_build):
        """--bioc should trigger a build with Bioconductor packages."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-image", "--bioc", "DESeq2", "--tag", "bioc-image",
        ])
        assert result.exit_code == 0
        assert "Image Built" in result.output
        mock_build.assert_called_once()

    @patch("nomad_r_runner.cli.build_image", return_value="file-image")
    def test_from_file(self, mock_build, tmp_path):
        """--from-file should parse a packages file."""
        pkg_file = tmp_path / "packages.txt"
        pkg_file.write_text("glmnet\nbioc::DESeq2\n")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-image", "--from-file", str(pkg_file), "--tag", "file-image",
        ])
        assert result.exit_code == 0
        assert "Image Built" in result.output

    @patch("nomad_r_runner.cli.build_image", side_effect=Exception("docker not found"))
    def test_build_failure(self, mock_build):
        """A failed docker build should report the error."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-image", "--packages", "glmnet", "--tag", "fail-image",
        ])
        assert result.exit_code != 0


class TestStatusCommand:
    """Integration tests for the ``status`` subcommand."""

    def test_help_output(self):
        """status --help should exit 0 and show usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "Check job status" in result.output

    @patch("nomad_r_runner.cli.pick_namespace", return_value="default")
    @patch("nomad_r_runner.cli.get_alloc_logs", return_value="")
    @patch("nomad_r_runner.cli.get_allocations", return_value=[{"ID": "alloc-1", "ClientStatus": "complete"}])
    @patch("nomad_r_runner.cli.get_status", return_value={"Status": "dead"})
    def test_completed_job(self, mock_status, mock_allocs, mock_logs, mock_pick):
        """A completed job should show 'complete' status."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "test-job-123"])
        assert result.exit_code == 0
        assert "complete" in result.output

    @patch("nomad_r_runner.cli.pick_namespace", return_value="default")
    @patch("nomad_r_runner.cli.get_alloc_logs")
    @patch("nomad_r_runner.cli.get_allocations", return_value=[{"ID": "alloc-1", "ClientStatus": "failed"}])
    @patch("nomad_r_runner.cli.get_status", return_value={"Status": "dead"})
    def test_failed_job_with_diagnosis(self, mock_status, mock_allocs, mock_logs, mock_pick):
        """A failed job with a missing package should show a suggestion."""
        mock_logs.side_effect = lambda alloc_id, log_type="stderr", namespace="default": (
            "Error in library(glmnet) : there is no package called \u2018glmnet\u2019"
            if log_type == "stderr" else ""
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "test-job-fail"])
        assert result.exit_code == 0
        assert "failed" in result.output
        assert "build-image" in result.output

    @patch("nomad_r_runner.cli.pick_namespace", return_value="default")
    @patch("nomad_r_runner.cli.get_status", side_effect=Exception("not found"))
    def test_unknown_job(self, mock_status, mock_pick):
        """A nonexistent job should show an error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "nonexistent-job"])
        assert result.exit_code != 0
