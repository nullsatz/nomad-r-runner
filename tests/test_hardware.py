"""Tests for hardware detection and resource clamping."""

import pytest

from nomad_r_runner.hardware import HardwareDefaults, clamp_resources, get_defaults


class TestGetDefaults:
    """Tests for get_defaults() with mocked psutil."""

    def test_defaults_from_known_hardware(self, mock_psutil):
        """32 GB RAM / 16 cores should yield 16384 MB / 8000 MHz defaults."""
        defaults = get_defaults()

        assert defaults.total_ram_mb == 32 * 1024  # 32768 MB
        assert defaults.total_cpu_mhz == 16 * 1000  # 16000 MHz
        assert defaults.max_ram_mb == 32 * 1024 // 2  # 16384 MB
        assert defaults.max_cpu_mhz == 16 * 1000 // 2  # 8000 MHz


class TestClampResources:
    """Tests for clamp_resources()."""

    @pytest.fixture()
    def defaults(self):
        return HardwareDefaults(
            total_ram_mb=32768,
            total_cpu_mhz=16000,
            max_ram_mb=16384,
            max_cpu_mhz=8000,
        )

    def test_none_uses_defaults(self, defaults):
        """Passing None for both should return the default maximums."""
        ram, cpu = clamp_resources(None, None, defaults)
        assert ram == 16384
        assert cpu == 8000

    def test_within_defaults(self, defaults):
        """Values under the max should pass through unchanged."""
        ram, cpu = clamp_resources(4096, 2000, defaults)
        assert ram == 4096
        assert cpu == 2000

    def test_exceeds_defaults_clamped(self, defaults):
        """Values above the max should be clamped."""
        ram, cpu = clamp_resources(99999, 99999, defaults)
        assert ram == 16384
        assert cpu == 8000

    def test_zero_ram_rejected(self, defaults):
        """Zero RAM should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            clamp_resources(0, 1000, defaults)

    def test_negative_cpu_rejected(self, defaults):
        """Negative CPU should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            clamp_resources(1000, -500, defaults)
