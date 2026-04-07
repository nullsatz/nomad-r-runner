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

    def test_email_stub(self, tmp_r_script, mock_psutil, mock_nomad):
        """--email should print a 'not yet implemented' note."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_r_script), "--email", "test@example.com"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()


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

    @patch("nomad_r_runner.cli.get_alloc_logs", return_value="")
    @patch("nomad_r_runner.cli.get_allocations", return_value=[{"ID": "alloc-1", "ClientStatus": "complete"}])
    @patch("nomad_r_runner.cli.get_status", return_value={"Status": "dead"})
    def test_completed_job(self, mock_status, mock_allocs, mock_logs):
        """A completed job should show 'complete' status."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "test-job-123"])
        assert result.exit_code == 0
        assert "complete" in result.output

    @patch("nomad_r_runner.cli.get_alloc_logs")
    @patch("nomad_r_runner.cli.get_allocations", return_value=[{"ID": "alloc-1", "ClientStatus": "failed"}])
    @patch("nomad_r_runner.cli.get_status", return_value={"Status": "dead"})
    def test_failed_job_with_diagnosis(self, mock_status, mock_allocs, mock_logs):
        """A failed job with a missing package should show a suggestion."""
        mock_logs.side_effect = lambda alloc_id, log_type="stderr": (
            "Error in library(glmnet) : there is no package called \u2018glmnet\u2019"
            if log_type == "stderr" else ""
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "test-job-fail"])
        assert result.exit_code == 0
        assert "failed" in result.output
        assert "build-image" in result.output

    @patch("nomad_r_runner.cli.get_status", side_effect=Exception("not found"))
    def test_unknown_job(self, mock_status):
        """A nonexistent job should show an error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "nonexistent-job"])
        assert result.exit_code != 0
