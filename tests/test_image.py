"""Tests for Docker image building and package parsing."""

from pathlib import Path
from unittest.mock import patch

from nomad_r_runner.image import (
    build_image,
    generate_dockerfile,
    parse_packages,
)


class TestParsePackages:
    """Tests for parse_packages()."""

    def test_cran_from_string(self):
        """Comma-separated --packages should produce CRAN list."""
        cran, bioc = parse_packages(packages="glmnet, survival, data.table")
        assert cran == ["glmnet", "survival", "data.table"]
        assert bioc == []

    def test_bioc_from_string(self):
        """Comma-separated --bioc should produce Bioconductor list."""
        cran, bioc = parse_packages(bioc="DESeq2, GenomicRanges")
        assert cran == []
        assert bioc == ["DESeq2", "GenomicRanges"]

    def test_both_strings(self):
        """Both --packages and --bioc can be provided together."""
        cran, bioc = parse_packages(packages="glmnet", bioc="DESeq2")
        assert cran == ["glmnet"]
        assert bioc == ["DESeq2"]

    def test_from_file(self, tmp_path):
        """File with mixed CRAN and bioc:: prefixed packages."""
        pkg_file = tmp_path / "packages.txt"
        pkg_file.write_text("glmnet\nsurvival\nbioc::DESeq2\n# comment\n\nbioc::GenomicRanges\n")
        cran, bioc = parse_packages(from_file=pkg_file)
        assert cran == ["glmnet", "survival"]
        assert bioc == ["DESeq2", "GenomicRanges"]

    def test_empty_inputs(self):
        """No inputs should return empty lists."""
        cran, bioc = parse_packages()
        assert cran == []
        assert bioc == []


class TestGenerateDockerfile:
    """Tests for generate_dockerfile()."""

    def test_cran_only(self):
        """CRAN-only should not include BiocManager."""
        df = generate_dockerfile("rocker/tidyverse:latest", ["glmnet", "survival"], [])
        assert "FROM rocker/tidyverse:latest" in df
        assert 'install.packages(c("glmnet", "survival"))' in df
        assert "BiocManager" not in df

    def test_bioc_only(self):
        """Bioc-only should include BiocManager install."""
        df = generate_dockerfile("rocker/tidyverse:latest", [], ["DESeq2"])
        assert "FROM rocker/tidyverse:latest" in df
        assert "install.packages" not in df.split("BiocManager")[0]  # no CRAN line before BiocManager
        assert "BiocManager::install" in df
        assert '"DESeq2"' in df

    def test_mixed(self):
        """Both CRAN and Bioconductor packages should produce two RUN lines."""
        df = generate_dockerfile("rocker/r-ver:4.3.2", ["glmnet"], ["DESeq2"])
        assert "FROM rocker/r-ver:4.3.2" in df
        assert 'install.packages(c("glmnet"))' in df
        assert "BiocManager::install" in df

    def test_custom_base_image(self):
        """Base image should be configurable."""
        df = generate_dockerfile("my-custom-image:v1", ["glmnet"], [])
        assert "FROM my-custom-image:v1" in df


class TestBuildImage:
    """Tests for build_image() with mocked Docker SDK."""

    @patch("nomad_r_runner.image.docker.from_env")
    def test_calls_docker_build(self, mock_from_env):
        """build_image should invoke the Docker SDK build API."""
        mock_client = mock_from_env.return_value
        mock_client.api.build.return_value = iter([{"stream": "Step 1/1 : FROM rocker\n"}])
        tag = build_image("FROM rocker/tidyverse:latest\n", "my-tag")
        assert tag == "my-tag"
        mock_client.api.build.assert_called_once()
        call_kwargs = mock_client.api.build.call_args[1]
        assert call_kwargs["tag"] == "my-tag"

    @patch("nomad_r_runner.image.docker.from_env")
    def test_build_error_raised(self, mock_from_env):
        """Build errors from Docker should propagate."""
        import docker as docker_lib
        mock_client = mock_from_env.return_value
        mock_client.api.build.return_value = iter([{"error": "package not found"}])
        try:
            build_image("FROM rocker/tidyverse:latest\n", "bad-tag")
            assert False, "Should have raised"
        except docker_lib.errors.BuildError:
            pass
