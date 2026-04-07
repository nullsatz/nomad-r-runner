# needs_glmnet.R - Requires the glmnet package (not in base tidyverse image)
# This script will FAIL with the default image. Build a custom image first:
#   nomad-r-runner build-image --packages glmnet --tag r-glmnet
#   nomad-r-runner run examples/needs_glmnet.R --image r-glmnet

library(glmnet)

set.seed(42)
n <- 100
p <- 10
x <- matrix(rnorm(n * p), n, p)
y <- x[, 1] + 0.5 * x[, 2] + rnorm(n)

fit <- cv.glmnet(x, y)
cat("Lambda min:", fit$lambda.min, "\n")
cat("Number of non-zero coefficients:", sum(coef(fit, s = "lambda.min") != 0), "\n")
cat("glmnet test passed!\n")
