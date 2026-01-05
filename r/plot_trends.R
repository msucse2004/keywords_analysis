# Plot keyword trends over time
# Input: output/tables/keyword_topn_by_date.csv (same as Python py_keyword_trends.png)
# Output: fig_keyword_trends.png, fig_keyword_trends.pdf

library(ggplot2)
library(dplyr)
library(yaml)
library(viridis)
library(ggrepel)
source("r/common_theme.R")

# Get paths from environment variables (set by Python) or use defaults
tables_dir <- Sys.getenv("R_TABLES_DIR", "output/tables")
figures_dir <- Sys.getenv("R_FIGURES_DIR", "output/figures")
project_root <- Sys.getenv("R_PROJECT_ROOT", ".")

# Debug: Print environment variables (helps diagnose conda run issues)
cat("=== R Script Environment Variables ===\n")
cat(sprintf("R_TABLES_DIR: %s\n", tables_dir))
cat(sprintf("R_FIGURES_DIR: %s\n", figures_dir))
cat(sprintf("R_PROJECT_ROOT: %s\n", project_root))
cat(sprintf("Working directory: %s\n", getwd()))
cat("=====================================\n\n")

# Read configuration (if available, otherwise use defaults)
config_file <- file.path(project_root, "config/default.yaml")
if (file.exists(config_file)) {
  config <- read_yaml(config_file)
  trend_top_n <- config$TREND_PLOT_TOP_N
} else {
  trend_top_n <- 10
}

# Check if input file exists before reading
input_file <- file.path(tables_dir, "keyword_topn_by_date.csv")
if (!file.exists(input_file)) {
  stop(sprintf("Input file not found: %s\nPlease check that R_TABLES_DIR environment variable is set correctly.\nCurrent R_TABLES_DIR: %s", input_file, tables_dir))
}

# Read data (same file as Python uses)
topn_by_date <- read.csv(input_file, stringsAsFactors = FALSE)

# Check if data is empty
if (nrow(topn_by_date) == 0) {
  warning("No data in keyword_topn_by_date.csv. Skipping plot.")
  # Create empty figure files to indicate no data
  empty_png <- file.path(figures_dir, "fig_keyword_trends.png")
  empty_pdf <- file.path(figures_dir, "fig_keyword_trends.pdf")
  if (!dir.exists(figures_dir)) {
    dir.create(figures_dir, recursive = TRUE)
  }
  # Create empty PNG (1x1 white image)
  png(empty_png, width = 10*300, height = 6*300, res = 300, bg = "white")
  plot.new()
  text(0.5, 0.5, "No data to plot", cex = 2, col = "gray")
  dev.off()
  # Create empty PDF
  pdf(empty_pdf, width = 10, height = 6)
  plot.new()
  text(0.5, 0.5, "No data to plot", cex = 2, col = "gray")
  dev.off()
  cat(paste("Empty figure files created (no data):", figures_dir, "\n"))
  quit(status = 0)  # Exit gracefully
}

topn_by_date$date <- as.Date(topn_by_date$date)

# Filter to Top N ranks (same as Python - all ranks from 1 to TREND_PLOT_TOP_N)
plot_data <- topn_by_date %>%
  filter(rank <= trend_top_n) %>%
  arrange(date, rank)

if (nrow(plot_data) == 0) {
  warning("No data points after filtering. Skipping plot.")
  # Create empty figure files to indicate no data
  empty_png <- file.path(figures_dir, "fig_keyword_trends.png")
  empty_pdf <- file.path(figures_dir, "fig_keyword_trends.pdf")
  if (!dir.exists(figures_dir)) {
    dir.create(figures_dir, recursive = TRUE)
  }
  # Create empty PNG (1x1 white image)
  png(empty_png, width = 10*300, height = 6*300, res = 300, bg = "white")
  plot.new()
  text(0.5, 0.5, "No data to plot", cex = 2, col = "gray")
  dev.off()
  # Create empty PDF
  pdf(empty_pdf, width = 10, height = 6)
  plot.new()
  text(0.5, 0.5, "No data to plot", cex = 2, col = "gray")
  dev.off()
  cat(paste("Empty figure files created (no data after filtering):", figures_dir, "\n"))
  quit(status = 0)  # Exit gracefully
}

# Define colors for each rank (using viridis-like colors, same as Python)
rank_colors <- viridis::viridis_pal(option = "viridis", begin = 0.2, end = 0.9)(trend_top_n)
names(rank_colors) <- 1:trend_top_n

# Custom function to format date labels with month on top and year on bottom
# Year is only shown when it changes (first occurrence of each year)
date_label_func <- function(x) {
  # Convert to Date if needed
  dates <- as.Date(x)
  
  # Remove any NA values
  valid_idx <- !is.na(dates)
  if (!any(valid_idx)) {
    return(character(length(dates)))
  }
  
  # Get years and months
  years <- format(dates, "%Y")
  months <- format(dates, "%b")
  
  # Create labels: month on top, year on bottom
  # Year only shown when it changes
  labels <- character(length(dates))
  prev_year <- ""
  
  for (i in seq_along(dates)) {
    if (!valid_idx[i]) {
      labels[i] <- ""
      next
    }
    
    if (prev_year == "" || years[i] != prev_year) {
      # Year changed or first label, show both month (top) and year (bottom)
      labels[i] <- paste(months[i], years[i], sep = "\n")
      prev_year <- years[i]
    } else {
      # Same year, show only month
      labels[i] <- months[i]
    }
  }
  
  return(labels)
}

# Plot with smoothing curve for each rank (same as Python)
p <- ggplot(plot_data, aes(x = date, y = freq, color = factor(rank))) +
  geom_smooth(method = "loess", span = 0.3, se = FALSE, linewidth = 2.5, alpha = 0.7) +
  geom_point(size = 3, alpha = 0.9) +
  geom_text_repel(aes(label = token), 
                  size = 2.5, 
                  fontface = "bold", 
                  color = "black", 
                  show.legend = FALSE,
                  max.overlaps = Inf,
                  min.segment.length = 0,
                  box.padding = 0.3,
                  point.padding = 0.3) +
  scale_color_manual(values = rank_colors, name = "Rank", labels = paste("Rank", 1:trend_top_n)) +
  labs(
    title = paste("Top", trend_top_n, "Keywords by Date"),
    x = "Month",
    y = "Frequency"
  ) +
  common_theme() +
  theme(legend.position = "right") +
  scale_y_continuous(limits = c(0, NA)) +  # Set y-axis minimum to 0, same as Python
  scale_x_date(date_breaks = "1 month", 
               labels = date_label_func,  # Use labels parameter instead of date_labels
               guide = guide_axis(angle = 0)) +  # Year and month on separate lines
  theme(axis.text.x = element_text(size = 7))  # Reduce x-axis font size

# Save PNG
ggsave(file.path(figures_dir, "fig_keyword_trends.png"), 
       plot = p, 
       width = 10, 
       height = 6, 
       dpi = 300,
       bg = "white")

# Save PDF
ggsave(file.path(figures_dir, "fig_keyword_trends.pdf"), 
       plot = p, 
       width = 10, 
       height = 6,
       device = "pdf",
       bg = "white")

cat(paste("Keyword trends figure saved to", figures_dir, "\n"))

