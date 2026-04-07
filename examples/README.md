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
nomad-r-runner examples/hello.R
```

## data_summary.R

Generates random data and prints summary statistics.

```bash
nomad-r-runner examples/data_summary.R --max-ram 512
```

## read_data.R

Reads a CSV file from a mounted data directory. Demonstrates the
`--data-dir` option.

```bash
nomad-r-runner examples/read_data.R --data-dir examples/sample_data
```

## plot_output.R

Generates a PNG plot. Requires mounting an output directory into the
container (not included in the default job spec -- you would need to
extend the job spec or add a `--output-dir` option).

```bash
nomad-r-runner examples/plot_output.R --name my-plot
```
