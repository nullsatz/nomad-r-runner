# Examples

Example R scripts for use with `nomad-r-runner`.

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

## plot_output.R

Generates a PNG plot. Requires mounting an output directory into the
container (not included in the default job spec -- you would need to
extend the job spec or add a `--output-dir` option).

```bash
nomad-r-runner examples/plot_output.R --name my-plot
```
