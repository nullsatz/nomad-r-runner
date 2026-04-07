"""Diagnosis of common R script failures from Nomad job logs.

Pattern-matches known R error messages and returns actionable
suggestions so users know how to fix their jobs without digging
through raw logs.
"""

import re


# Each entry: (compiled regex, suggestion template)
# The regex is matched against the combined stdout+stderr log text.
# Groups captured by the regex can be referenced in the template as {1}, {2}, etc.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"there is no package called \u2018(.+?)\u2019"),
        'Package "{1}" is not installed in the Docker image.\n'
        "  Build a custom image:  nomad-r-runner build-image --packages {1} --tag my-image\n"
        "  Then run with:         nomad-r-runner run script.R --image my-image",
    ),
    (
        re.compile(r"there is no package called '(.+?)'"),
        'Package "{1}" is not installed in the Docker image.\n'
        "  Build a custom image:  nomad-r-runner build-image --packages {1} --tag my-image\n"
        "  Then run with:         nomad-r-runner run script.R --image my-image",
    ),
    (
        re.compile(r"cannot open file '(.+?)': No such file or directory"),
        'File "{1}" was not found inside the container.\n'
        "  If this is a data file, mount its directory:  nomad-r-runner run script.R --data-dir /path/to/data\n"
        "  Data files will be available at /data/ inside the container.",
    ),
    (
        re.compile(r"cannot open connection"),
        "R could not open a file or connection.\n"
        "  If your script reads data files, make sure to use --data-dir to mount them.\n"
        "  Data files will be available at /data/ inside the container.",
    ),
    (
        re.compile(r"cannot allocate vector of size"),
        "R ran out of memory.\n"
        "  Try increasing the RAM allocation:  nomad-r-runner run script.R --max-ram <MB>",
    ),
]


def diagnose_logs(logs: str) -> str | None:
    """Analyze R script logs and return an actionable suggestion.

    Scans the log text for known R error patterns and returns a
    human-readable suggestion for the first match found.

    Args:
        logs: Combined stdout and stderr text from the Nomad allocation.

    Returns:
        A suggestion string if a known error pattern is found, or
        None if no patterns match.
    """
    for pattern, template in _PATTERNS:
        match = pattern.search(logs)
        if match:
            suggestion = template
            for i, group in enumerate(match.groups(), start=1):
                suggestion = suggestion.replace(f"{{{i}}}", group)
            return suggestion
    return None
