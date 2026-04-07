"""Tests for R log diagnosis."""

from nomad_r_runner.diagnose import diagnose_logs


class TestDiagnoseLogs:
    """Tests for diagnose_logs()."""

    def test_missing_package_smart_quotes(self):
        """Detects R's smart-quoted 'there is no package called' error."""
        logs = "Error in library(glmnet) : there is no package called \u2018glmnet\u2019"
        result = diagnose_logs(logs)
        assert result is not None
        assert "glmnet" in result
        assert "build-image" in result

    def test_missing_package_straight_quotes(self):
        """Detects the straight-quoted variant."""
        logs = "Error in library(survival) : there is no package called 'survival'"
        result = diagnose_logs(logs)
        assert result is not None
        assert "survival" in result
        assert "build-image" in result

    def test_file_not_found(self):
        """Detects 'cannot open file' errors."""
        logs = "Error in file(file, \"rt\") : cannot open file '/data/missing.csv': No such file or directory"
        result = diagnose_logs(logs)
        assert result is not None
        assert "data-dir" in result

    def test_cannot_open_connection(self):
        """Detects generic connection errors."""
        logs = "Error in file(file, \"rt\") : cannot open connection"
        result = diagnose_logs(logs)
        assert result is not None
        assert "data-dir" in result

    def test_out_of_memory(self):
        """Detects memory allocation errors."""
        logs = "Error: cannot allocate vector of size 2.5 Gb"
        result = diagnose_logs(logs)
        assert result is not None
        assert "max-ram" in result

    def test_output_permission_denied(self):
        """Detects permission errors writing to /output/."""
        logs = "Error in file(file, \"wt\") : cannot open file '/output/results.csv': Permission denied"
        result = diagnose_logs(logs)
        assert result is not None
        assert "output-dir" in result

    def test_no_match(self):
        """Unknown errors return None."""
        logs = "some random output\neverything looks fine"
        result = diagnose_logs(logs)
        assert result is None

    def test_empty_logs(self):
        """Empty logs return None."""
        assert diagnose_logs("") is None
