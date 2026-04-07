# nomad-r-runner User Guide

## Quick Start

### 1. Install

```bash
conda create -n nomad-r python=3.12 -y
cd ~/src/nomad-r-runner
conda run -n nomad-r pip install -e .
```

### 2. Make sure Nomad and Docker are running

Nomad must be started with volume mounts enabled. Use the included config:

```bash
nomad agent -dev -config=$PWD/contrib/nomad-dev.hcl &
```

On macOS, Docker Desktop must be running and the socket linked:

```bash
sudo ln -s ~/.docker/run/docker.sock /var/run/docker.sock
```

### 3. Submit a script

```bash
nomad-r-runner run /path/to/your_script.R
```

This prints a job ID. Check on it with:

```bash
nomad-r-runner status <job-id>
```

## Commands

### `nomad-r-runner run`

Submit an R script to Nomad.

```
nomad-r-runner run SCRIPT [OPTIONS]

Options:
  --max-ram MB       Max RAM in MB (default: 50% of system RAM)
  --max-cpu MHZ      Max CPU in MHz (default: 50% of system CPU)
  --image IMAGE      Docker image (default: rocker/tidyverse:latest)
  --data-dir DIR     Mount a host directory read-only at /data in the container
  --name NAME        Job name (default: auto-generated)
  --show-defaults    Print detected hardware limits and exit
```

### `nomad-r-runner status`

Check job status, view output, and get suggestions if the job failed.

```
nomad-r-runner status JOB_ID
```

If the job failed, `status` will try to diagnose the error and suggest
a fix (e.g., missing package, missing data file, out of memory).

### `nomad-r-runner build-image`

Build a custom Docker image with extra R packages.

```
nomad-r-runner build-image [OPTIONS]

Options:
  --packages PKGS      Comma-separated CRAN packages
  --bioc PKGS          Comma-separated Bioconductor packages
  --from-file FILE     File listing packages (one per line)
  --base-image IMAGE   Base image (default: rocker/tidyverse:latest)
  --tag TAG            Image tag (default: auto-generated)
```

At least one of `--packages`, `--bioc`, or `--from-file` is required.

## Providing Data Files

Your R script runs inside a Docker container, so it cannot see files on
the host machine by default. To make data files available:

1. Put your data files in a directory (e.g., `~/myproject/data/`)
2. Pass that directory with `--data-dir`:

```bash
nomad-r-runner run my_analysis.R --data-dir ~/myproject/data
```

3. In your R script, read files from `/data/`:

```r
df <- read.csv("/data/my_data.csv")
```

The data directory is mounted **read-only**. Your script cannot write
back to it.

## Adding R Packages

The default image (`rocker/tidyverse:latest`) includes base R and the
tidyverse. If your script needs other packages, **build a custom image
first**. Do not add `install.packages()` to your script -- it would
re-download and compile on every run.

### CRAN packages

```bash
nomad-r-runner build-image --packages glmnet,survival --tag my-r-image
```

This creates an image tagged `my-r-image:local`. The `:local` suffix is
added automatically to prevent Nomad from trying to pull it from Docker
Hub. You can also provide an explicit version tag (e.g. `--tag my-r-image:v2`).

### Bioconductor packages

```bash
nomad-r-runner build-image --bioc DESeq2,GenomicRanges --tag my-bio-image
```

### Mixed (from a file)

Create a text file with one package per line. Prefix Bioconductor
packages with `bioc::`:

```
# packages.txt
glmnet
survival
data.table
bioc::DESeq2
bioc::GenomicRanges
```

```bash
nomad-r-runner build-image --from-file packages.txt --tag my-r-image
```

### Using your custom image

```bash
nomad-r-runner run my_analysis.R --image my-r-image:local
```

### Build times

CRAN packages with compiled code (glmnet, Rcpp, etc.) take 1-5 minutes.
Bioconductor packages can take 10-30 minutes. Build output is streamed
to your terminal so you can follow progress. This is a one-time cost --
the image is cached and reused for all future jobs.

## Diagnosing Failures

If your job fails, run:

```bash
nomad-r-runner status <job-id>
```

This shows the R output and errors, and will suggest a fix for common
problems:

| Error | Meaning | Fix |
|-------|---------|-----|
| "there is no package called 'X'" | Package not in the Docker image | `nomad-r-runner build-image --packages X` |
| "cannot open file '/data/...'" | Data file not mounted | Add `--data-dir /path/to/data` |
| "cannot allocate vector of size" | Not enough RAM | Increase `--max-ram` |

You can also check raw Nomad logs directly:

```bash
nomad alloc logs -job <job-id>         # stdout
nomad alloc logs -stderr -job <job-id> # stderr
```

## Troubleshooting

### "Failed to connect to docker daemon"
Docker Desktop is not running, or the socket symlink is missing.

```bash
# Check Docker is running
docker ps

# On macOS, ensure the socket is linked
sudo ln -s ~/.docker/run/docker.sock /var/run/docker.sock
```

### "missing drivers: 1 nodes excluded by filter"
Nomad cannot find the Docker driver. Restart Nomad after Docker is running:

```bash
pkill nomad
nomad agent -dev -config=$PWD/contrib/nomad-dev.hcl &
```

### "volumes are not enabled"
Nomad was started without the volume config. Restart with:

```bash
nomad agent -dev -config=$PWD/contrib/nomad-dev.hcl &
```
