# Plot keyword lag analysis: News/Reddit -> Meeting
# Input: output/TimeLagging/keyword_lag_analysis.csv
# Output: fig_keyword_lag_*.png, fig_keyword_lag_*.pdf

library(ggplot2)
library(dplyr)
library(viridis)
library(gridExtra)
library(grid)
source("r/common_theme.R")

# Get paths from environment variables (set by Python) or use defaults
tables_dir <- Sys.getenv("R_TABLES_DIR", "output/TimeLagging")
figures_dir <- Sys.getenv("R_FIGURES_DIR", "output/TimeLagging")
project_root <- Sys.getenv("R_PROJECT_ROOT", ".")

# Read data
csv_path <- file.path(tables_dir, "keyword_lag_analysis.csv")
if (!file.exists(csv_path)) {
  stop(paste("File not found:", csv_path))
}

df <- read.csv(csv_path, stringsAsFactors = FALSE)
df$source_first_date <- as.Date(df$source_first_date)
df$target_first_date <- as.Date(df$target_first_date)

# Convert appears_in_target to logical (handle both "True"/"False" strings and TRUE/FALSE)
df$appears_in_target <- as.logical(df$appears_in_target)

# Filter to keywords that appear in meeting (with valid lag)
df_with_lag <- df %>%
  filter(appears_in_target == TRUE, !is.na(days_lag))

cat(paste("Total keywords analyzed:", nrow(df), "\n"))
cat(paste("Keywords appearing in meeting:", nrow(df_with_lag), "\n"))

# ==============================================================================
# Plot 1: Distribution of time lag (histogram - positive lag only)
# ==============================================================================
# Filter to only positive lag (keywords appearing later in meeting)
df_positive_lag <- df_with_lag %>%
  filter(days_lag > 0)

# Calculate statistics
median_lag <- median(df_positive_lag$days_lag, na.rm = TRUE)
q1_lag <- quantile(df_positive_lag$days_lag, 0.25, na.rm = TRUE)
q3_lag <- quantile(df_positive_lag$days_lag, 0.75, na.rm = TRUE)

# Create statistics table data (include color info in Statistic column)
stats_table <- data.frame(
  Statistic = c("Q1 (Orange)", "Median (Blue)", "Q3 (Purple)"),
  Value = c(
    paste0(round(q1_lag, 1), " days"),
    paste0(round(median_lag, 1), " days"),
    paste0(round(q3_lag, 1), " days")
  ),
  stringsAsFactors = FALSE
)

# Calculate histogram data to get y-axis range
hist_data <- hist(df_positive_lag$days_lag, breaks = 50, plot = FALSE)
max_count <- max(hist_data$counts)
max_lag <- max(df_positive_lag$days_lag)

# Create base plot
p1 <- ggplot(df_positive_lag, aes(x = days_lag)) +
  geom_histogram(bins = 50, fill = viridis(1), alpha = 0.7, color = "white", linewidth = 0.3) +
  geom_vline(xintercept = q1_lag, linetype = "dashed", color = "orange", linewidth = 1) +
  geom_vline(xintercept = median_lag, linetype = "dashed", color = "blue", linewidth = 1) +
  geom_vline(xintercept = q3_lag, linetype = "dashed", color = "purple", linewidth = 1) +
  labs(
    title = "Distribution of Time Lag (News/Reddit -> Meeting)",
    x = "Time Lag (days)",
    y = "Number of Keywords"
  ) +
  common_theme() +
  theme(
    plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5)
  ) +
  # Add table as annotation
  annotation_custom(
    grob = tableGrob(
      stats_table[, c("Statistic", "Value")],
      rows = NULL,
      theme = ttheme_minimal(
        base_size = 9,
        core = list(
          fg_params = list(hjust = 0, x = 0.1),
          bg_params = list(fill = c("white", "grey95"))
        ),
        colhead = list(
          fg_params = list(fontface = "bold", hjust = 0, x = 0.1),
          bg_params = list(fill = "grey80")
        )
      )
    ),
    xmin = max_lag * 0.65,
    xmax = max_lag * 1.05,
    ymin = max_count * 0.55,
    ymax = max_count * 1.05
  )

# Save Plot 1
ggsave(file.path(figures_dir, "fig_keyword_lag_distribution.png"), 
       plot = p1, width = 10, height = 6, dpi = 300, bg = "white")
ggsave(file.path(figures_dir, "fig_keyword_lag_distribution.pdf"), 
       plot = p1, width = 10, height = 6, device = "pdf", bg = "white")
cat("Plot 1 saved: fig_keyword_lag_distribution\n")

# ==============================================================================
# Plot 2: Top keywords by lag (bar chart - positive lag only, smallest lag)
# ==============================================================================
# Get unique keywords with minimum lag (since same keyword can appear in multiple months)
top_keywords <- df_with_lag %>%
  filter(days_lag > 0) %>%
  group_by(token) %>%
  summarise(
    source_group = first(source_group),
    source_month = first(source_month[which.min(days_lag)]),  # Month with min lag
    source_first_date = first(source_first_date),
    target_first_date = first(target_first_date),
    days_lag = min(days_lag),  # Use minimum lag for each keyword (smallest lag)
    .groups = "drop"
  ) %>%
  arrange(days_lag) %>%  # Sort by ascending order (smallest first)
  head(20) %>%
  mutate(token = factor(token, levels = rev(token)))  # Reverse for plotting (smallest at top)

p4 <- ggplot(top_keywords, aes(x = token, y = days_lag, fill = source_group)) +
  geom_bar(stat = "identity", alpha = 0.8) +
  coord_flip() +
  scale_fill_viridis_d(option = "plasma", begin = 0.3, end = 0.9, name = "Source") +
  labs(
    title = "Top 20 Keywords by Smallest Time Lag",
    subtitle = "Keywords that appeared quickly in meeting after news/reddit",
    x = "Keyword",
    y = "Time Lag (days)"
  ) +
  common_theme() +
  theme(
    plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5),
    legend.position = "right"
  )

# Save Plot 2
ggsave(file.path(figures_dir, "fig_keyword_lag_top20.png"), 
       plot = p4, width = 10, height = 8, dpi = 300, bg = "white")
ggsave(file.path(figures_dir, "fig_keyword_lag_top20.pdf"), 
       plot = p4, width = 10, height = 8, device = "pdf", bg = "white")
cat("Plot 2 saved: fig_keyword_lag_top20\n")

cat("\nAll keyword lag visualizations generated successfully!\n")

