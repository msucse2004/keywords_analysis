# Plot keyword trends over time
# Input: output/tables/keyword_topn_by_date.csv (same as Python py_keyword_trends.png)
# Output: fig_keyword_trends.png, fig_keyword_trends.pdf

library(ggplot2)
library(dplyr)
library(yaml)
library(viridis)
source("r/common_theme.R")

# Read configuration (if available, otherwise use defaults)
config_file <- "config/default.yaml"
if (file.exists(config_file)) {
  config <- read_yaml(config_file)
  trend_top_n <- config$TREND_PLOT_TOP_N
} else {
  trend_top_n <- 10
}

# Read data (same file as Python uses)
topn_by_date <- read.csv("output/tables/keyword_topn_by_date.csv", stringsAsFactors = FALSE)
topn_by_date$date <- as.Date(topn_by_date$date)

# Filter to Top N ranks (same as Python - all ranks from 1 to TREND_PLOT_TOP_N)
plot_data <- topn_by_date %>%
  filter(rank <= trend_top_n) %>%
  arrange(date, rank)

if (nrow(plot_data) == 0) {
  stop("No data points to plot")
}

# Define colors for each rank (using viridis-like colors, same as Python)
rank_colors <- viridis::viridis_pal(option = "viridis", begin = 0.2, end = 0.9)(trend_top_n)
names(rank_colors) <- 1:trend_top_n

# Plot with smoothing curve for each rank (same as Python)
p <- ggplot(plot_data, aes(x = date, y = freq, color = factor(rank))) +
  geom_smooth(method = "loess", span = 0.3, se = FALSE, linewidth = 2.5, alpha = 0.7) +
  geom_point(size = 3, alpha = 0.9) +
  geom_text(aes(label = token), hjust = 0, vjust = 0, nudge_x = 5, nudge_y = 0.5, 
            size = 2.5, fontface = "bold", color = "black", show.legend = FALSE) +
  scale_color_manual(values = rank_colors, name = "Rank", labels = paste("Rank", 1:trend_top_n)) +
  labs(
    title = paste("Top", trend_top_n, "Keywords by Date"),
    x = "Date",
    y = "Frequency"
  ) +
  common_theme() +
  theme(legend.position = "right") +
  scale_y_continuous(limits = c(0, NA))  # Set y-axis minimum to 0, same as Python

# Save PNG
ggsave("output/figures/fig_keyword_trends.png", 
       plot = p, 
       width = 10, 
       height = 6, 
       dpi = 300,
       bg = "white")

# Save PDF
ggsave("output/figures/fig_keyword_trends.pdf", 
       plot = p, 
       width = 10, 
       height = 6,
       device = "pdf",
       bg = "white")

cat("Keyword trends figure saved to output/figures/\n")

