"""nomad_r_runner - Submit R scripts as Nomad batch jobs in Docker containers.

This package provides a CLI tool that lets users on a shared Linux machine
submit R scripts to HashiCorp Nomad for execution inside Docker containers.
Resource limits (CPU and RAM) are auto-detected from the host hardware
and can be overridden by the user.

Typical usage::

    $ nomad-r-runner /path/to/script.R
    $ nomad-r-runner /path/to/script.R --max-ram 4096 --max-cpu 2000
"""

__version__ = "0.1.0"
