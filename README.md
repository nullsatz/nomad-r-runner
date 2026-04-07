# nomad-r-runner

A CLI tool for submitting R scripts to [HashiCorp Nomad](https://www.nomadproject.io/) for execution inside Docker containers. Designed for shared Linux machines where multiple users need to run R jobs with isolated environments and controlled resource usage.

## Features

- **Submit R scripts** as Nomad batch jobs running in Docker
- **Auto-detect hardware** and set sensible CPU/RAM defaults (50% of system)
- **Mount data and output directories** into the container
- **Build custom Docker images** with CRAN and Bioconductor packages
- **Diagnose failures** with actionable suggestions (missing packages, files, memory)
- **Stream build output** so you can follow long package compilations

## Quick Start

```bash
pip install -e .

# Submit a script
nomad-r-runner run my_analysis.R

# Check status and output
nomad-r-runner status <job-id>

# Mount input data and save results
nomad-r-runner run my_analysis.R --data-dir ./data --output-dir ./results
```

In your R script, read from `/data/` and write to `/output/`:

```r
df <- read.csv("/data/input.csv")
# ... analysis ...
write.csv(results, "/output/results.csv")
```

## Custom Images

The default image is `rocker/tidyverse:latest`. If your script needs extra packages, build a custom image:

```bash
# CRAN packages
nomad-r-runner build-image --packages glmnet,survival --tag my-image

# Bioconductor packages
nomad-r-runner build-image --bioc DESeq2 --tag my-bio-image

# From a file (prefix bioc:: for Bioconductor)
nomad-r-runner build-image --from-file packages.txt --tag my-image

# Use it
nomad-r-runner run my_analysis.R --image my-image:local
```

## Error Diagnosis

When a job fails, `status` identifies common problems and tells you how to fix them:

```bash
nomad-r-runner status <job-id>
```

| Error | Suggestion |
|-------|------------|
| Missing R package | `build-image --packages X` |
| File not found in container | `--data-dir /path/to/data` |
| Cannot write output | `--output-dir /path/to/output` |
| Out of memory | `--max-ram <MB>` |

## Prerequisites

- [HashiCorp Nomad](https://developer.hashicorp.com/nomad) running with Docker volume mounts enabled (see `contrib/nomad-dev.hcl`)
- [Docker](https://www.docker.com/) daemon running
- Python 3.10+

## Installation

```bash
git clone https://github.com/nullsatz/nomad-r-runner.git
cd nomad-r-runner
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
pytest -v
```

## Documentation

- [GUIDE.md](GUIDE.md) -- full user guide with setup instructions and troubleshooting
- [examples/](examples/) -- example R scripts and a sample packages file
- [contrib/nomad-dev.hcl](contrib/nomad-dev.hcl) -- Nomad dev-mode config with Docker volumes enabled

## License

[GPL-3.0](LICENSE)
