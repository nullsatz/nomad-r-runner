# read_data.R - Reads a CSV from the mounted /data directory
# Usage: nomad-r-runner examples/read_data.R --data-dir examples/sample_data

df <- read.csv("/data/iris_subset.csv")

cat("Loaded", nrow(df), "rows from /data/iris_subset.csv\n\n")
print(summary(df))

cat("\nMean sepal length by species:\n")
print(tapply(df$sepal_length, df$species, mean))
