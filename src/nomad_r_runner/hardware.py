"""Hardware detection and resource default computation.

Detects the host machine's total RAM and CPU core count using `psutil`,
then computes conservative default resource limits (50% of each) suitable
for Nomad job submissions.
"""

from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class HardwareDefaults:
    """Resource limits derived from detected hardware.

    Attributes:
        total_ram_mb: Total system RAM in megabytes.
        total_cpu_mhz: Total CPU capacity in MHz (cores x 1000).
        max_ram_mb: Default RAM limit for jobs (50% of total).
        max_cpu_mhz: Default CPU limit for jobs (50% of total).
    """

    total_ram_mb: int
    total_cpu_mhz: int
    max_ram_mb: int
    max_cpu_mhz: int


def get_defaults() -> HardwareDefaults:
    """Detect host hardware and return default resource limits.

    Returns:
        HardwareDefaults with total resources and 50%-of-total defaults.
    """
    total_ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    total_cpu_mhz = psutil.cpu_count(logical=True) * 1000

    return HardwareDefaults(
        total_ram_mb=total_ram_mb,
        total_cpu_mhz=total_cpu_mhz,
        max_ram_mb=total_ram_mb // 2,
        max_cpu_mhz=total_cpu_mhz // 2,
    )


def clamp_resources(
    requested_ram_mb: int | None,
    requested_cpu_mhz: int | None,
    defaults: HardwareDefaults,
) -> tuple[int, int]:
    """Clamp user-requested resources to the allowed defaults.

    Args:
        requested_ram_mb: User-requested RAM in MB, or None for default.
        requested_cpu_mhz: User-requested CPU in MHz, or None for default.
        defaults: Hardware defaults to clamp against.

    Returns:
        Tuple of (ram_mb, cpu_mhz) clamped to allowed maximums.

    Raises:
        ValueError: If a requested value is zero or negative.
    """
    ram = requested_ram_mb if requested_ram_mb is not None else defaults.max_ram_mb
    cpu = requested_cpu_mhz if requested_cpu_mhz is not None else defaults.max_cpu_mhz

    if ram <= 0 or cpu <= 0:
        raise ValueError(f"Resource values must be positive (got ram={ram}, cpu={cpu})")

    clamped_ram = min(ram, defaults.max_ram_mb)
    clamped_cpu = min(cpu, defaults.max_cpu_mhz)

    return clamped_ram, clamped_cpu
