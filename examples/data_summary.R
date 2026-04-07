# data_summary.R - Generate and summarize random data
# Demonstrates that R's base stats functions work in the container.

set.seed(42)
df <- data.frame(x = rnorm(100), y = rnorm(100))

cat("Data summary:\n")
print(summary(df))

cat("\nCorrelation between x and y:", cor(df$x, df$y), "\n")
