# Examples

Example R scripts for use with `nomad-r-runner`.

## Prerequisites

Nomad must be running with Docker volume mounts enabled. See
`contrib/nomad-dev.hcl` for a ready-to-use dev-mode config:

```bash
nomad agent -dev -config=/path/to/contrib/nomad-dev.hcl
```

## hello.R

Minimal test script. Prints a greeting and R session info.

```bash
nomad-r-runner run examples/hello.R
```

## data_summary.R

Generates random data and prints summary statistics.

```bash
nomad-r-runner run examples/data_summary.R --max-ram 512
```

## read_data.R

Reads a CSV file from a mounted data directory. Demonstrates the
`--data-dir` option.

```bash
nomad-r-runner run examples/read_data.R --data-dir examples/sample_data
```

## save_results.R

Saves a CSV and a PNG plot to the mounted output directory.
Demonstrates the `--output-dir` option.

```bash
mkdir -p /tmp/r-output
nomad-r-runner run examples/save_results.R --output-dir /tmp/r-output
# After completion:
ls /tmp/r-output/   # plot.png, results.csv
```

## plot_output.R

Generates a PNG plot. Uses `--output-dir` to save to the host.

```bash
mkdir -p /tmp/r-output
nomad-r-runner run examples/plot_output.R --output-dir /tmp/r-output
```

## Building custom images

If your R script needs packages beyond what's in the base image, build
a custom Docker image first:

```bash
# From comma-separated lists
nomad-r-runner build-image --packages glmnet,survival --bioc DESeq2 --tag my-r-image

# From a file (see packages.txt for the format)
nomad-r-runner build-image --from-file examples/packages.txt --tag my-r-image

# Then use it
nomad-r-runner run my_analysis.R --image my-r-image
```

See `packages.txt` for the file format — one package per line, with
Bioconductor packages prefixed with `bioc::`.
