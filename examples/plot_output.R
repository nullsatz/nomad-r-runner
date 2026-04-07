# plot_output.R - Generate a plot saved to /output/
# To use this, mount an output directory into the container.
# The default setup only mounts the script; extend the job spec
# to also mount an output directory if you need file output.

output_dir <- "/output"
if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
}

png(file.path(output_dir, "plot.png"), width = 800, height = 600)
plot(cars, main = "Example Plot from Nomad", col = "steelblue", pch = 19)
dev.off()

cat("Plot saved to", file.path(output_dir, "plot.png"), "\n")
