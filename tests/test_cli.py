"""Tests for the CLI interface using click.testing.CliRunner."""

from click.testing import CliRunner

from nomad_r_runner.cli import main


class TestCLI:
    """Integration tests for the nomad-r-runner CLI."""

    def test_help_output(self):
        """--help should exit 0 and show usage."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Submit an R script" in result.output

    def test_version_output(self):
        """--version should print the version."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_missing_script(self):
        """A nonexistent script path should fail."""
        runner = CliRunner()
        result = runner.invoke(main, ["/nonexistent/path/script.R"])
        assert result.exit_code != 0

    def test_default_submission(self, tmp_r_script, mock_psutil, mock_nomad):
        """A valid script with defaults should submit successfully."""
        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_r_script)])
        assert result.exit_code == 0
        assert "Job Submitted" in result.output

    def test_custom_resources(self, tmp_r_script, mock_psutil, mock_nomad):
        """Custom --max-ram and --max-cpu should be reflected in output."""
        runner = CliRunner()
        result = runner.invoke(main, [
            str(tmp_r_script), "--max-ram", "2048", "--max-cpu", "1000",
        ])
        assert result.exit_code == 0
        assert "2048" in result.output
        assert "1000" in result.output

    def test_excessive_resources_clamped(self, tmp_r_script, mock_psutil, mock_nomad):
        """Resources above defaults should be clamped with a warning."""
        runner = CliRunner()
        result = runner.invoke(main, [
            str(tmp_r_script), "--max-ram", "999999", "--max-cpu", "999999",
        ])
        assert result.exit_code == 0
        assert "clamped" in result.output.lower()

    def test_show_defaults(self, mock_psutil):
        """--show-defaults should print hardware info and exit."""
        runner = CliRunner()
        # show-defaults still requires a script arg due to click's positional arg
        with runner.isolated_filesystem():
            with open("dummy.R", "w") as f:
                f.write("# dummy\n")
            result = runner.invoke(main, ["dummy.R", "--show-defaults"])
        assert result.exit_code == 0
        assert "Hardware Defaults" in result.output

    def test_data_dir(self, tmp_r_script, tmp_path, mock_psutil, mock_nomad):
        """--data-dir should accept a valid directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, [
            str(tmp_r_script), "--data-dir", str(data_dir),
        ])
        assert result.exit_code == 0
        assert "Job Submitted" in result.output

    def test_data_dir_nonexistent(self, tmp_r_script):
        """--data-dir with a nonexistent path should fail."""
        runner = CliRunner()
        result = runner.invoke(main, [
            str(tmp_r_script), "--data-dir", "/nonexistent/dir",
        ])
        assert result.exit_code != 0

    def test_email_stub(self, tmp_r_script, mock_psutil, mock_nomad):
        """--email should print a 'not yet implemented' note."""
        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_r_script), "--email", "test@example.com"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()
