# save_results.R - Save output files to the mounted /output directory
# Usage:
#   mkdir -p /tmp/r-output
#   nomad-r-runner run examples/save_results.R --output-dir /tmp/r-output
#   ls /tmp/r-output/  # plot.png, results.csv

# Generate some data
set.seed(42)
df <- data.frame(
    x = 1:50,
    y = cumsum(rnorm(50))
)

# Save a CSV
write.csv(df, "/output/results.csv", row.names = FALSE)
cat("Saved /output/results.csv\n")

# Save a plot
png("/output/plot.png", width = 800, height = 600)
plot(df$x, df$y, type = "l", col = "steelblue", lwd = 2,
     main = "Random Walk", xlab = "Step", ylab = "Value")
dev.off()
cat("Saved /output/plot.png\n")

cat("Done! Check your --output-dir for results.\n")
