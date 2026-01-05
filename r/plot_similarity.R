# Plot similarity heatmaps between groups
# Input: output/Comparison/tables/similarity_*.csv
# Output: fig_similarity_*.png, fig_similarity_*.pdf

library(ggplot2)
library(dplyr)
library(yaml)
library(viridis)
source("r/common_theme.R")

# Get paths from environment variables (set by Python) or use defaults
tables_dir <- Sys.getenv("R_TABLES_DIR", "output/Comparison/tables")
figures_dir <- Sys.getenv("R_FIGURES_DIR", "output/Comparison")
project_root <- Sys.getenv("R_PROJECT_ROOT", ".")

# Function to plot similarity heatmap
plot_similarity_heatmap <- function(sim_matrix_path, output_path, title) {
  if (!file.exists(sim_matrix_path)) {
    cat(paste("File not found:", sim_matrix_path, "\n"))
    return(invisible(NULL))
  }
  
  # Read similarity matrix
  sim_matrix <- read.csv(sim_matrix_path, row.names = 1, check.names = FALSE)
  
  # Convert to long format
  sim_long <- sim_matrix %>%
    as.data.frame() %>%
    tibble::rownames_to_column("Group1") %>%
    tidyr::pivot_longer(cols = -Group1, names_to = "Group2", values_to = "Similarity") %>%
    filter(!is.na(Similarity))
  
  # Ensure Group1 and Group2 are factors with same levels (for consistent ordering)
  all_groups <- unique(c(sim_long$Group1, sim_long$Group2))
  sim_long$Group1 <- factor(sim_long$Group1, levels = all_groups)
  sim_long$Group2 <- factor(sim_long$Group2, levels = all_groups)
  
  # Create heatmap
  p <- ggplot(sim_long, aes(x = Group2, y = Group1, fill = Similarity)) +
    geom_tile(color = "white", linewidth = 0.5) +
    geom_text(aes(label = sprintf("%.2f%%", Similarity * 100)), 
              color = "black", 
              size = 2.5,
              fontface = "bold") +
    scale_fill_viridis_c(name = "Similarity", 
                         option = "plasma",
                         limits = c(0, 1),
                         na.value = "grey90") +
    labs(
      title = title,
      x = "Group",
      y = "Group"
    ) +
    common_theme() +
    theme(
      axis.text.x = element_text(angle = 45, hjust = 1),
      panel.grid = element_blank(),
      plot.title = element_text(size = 12, face = "bold", hjust = 0.5)
    ) +
    coord_fixed()
  
  # Save PNG
  png_path <- sub("\\.pdf$", ".png", output_path)
  ggsave(png_path, plot = p, width = 8, height = 7, dpi = 300, bg = "white")
  
  # Save PDF
  ggsave(output_path, plot = p, width = 8, height = 7, device = "pdf", bg = "white")
  
  cat(paste("Similarity heatmap saved to", output_path, "\n"))
}

# Plot overall cosine similarity
plot_similarity_heatmap(
  file.path(tables_dir, "similarity_overall_cosine.csv"),
  file.path(figures_dir, "fig_similarity_overall_cosine.pdf"),
  "Group Similarity (Overall, Cosine)"
)

# Plot overall jaccard similarity
plot_similarity_heatmap(
  file.path(tables_dir, "similarity_overall_jaccard.csv"),
  file.path(figures_dir, "fig_similarity_overall_jaccard.pdf"),
  "Group Similarity (Overall, Jaccard)"
)

# Plot year-by-year cosine similarity
year_files <- list.files(tables_dir, pattern = "^similarity_[0-9]+_cosine\\.csv$", full.names = TRUE)
for (year_file in year_files) {
  # Extract year using gsub (more reliable than regmatches)
  filename <- basename(year_file)
  year <- gsub("similarity_([0-9]+)_cosine\\.csv", "\\1", filename)
  
  if (year == filename) {
    # If no match, skip this file
    next
  }
  
  output_file <- file.path(figures_dir, paste0("fig_similarity_", year, "_cosine.pdf"))
  plot_similarity_heatmap(
    year_file,
    output_file,
    paste("Group Similarity (Year", year, ", Cosine)")
  )
}

# Plot year-by-year jaccard similarity
year_files <- list.files(tables_dir, pattern = "^similarity_[0-9]+_jaccard\\.csv$", full.names = TRUE)
for (year_file in year_files) {
  # Extract year using gsub (more reliable than regmatches)
  filename <- basename(year_file)
  year <- gsub("similarity_([0-9]+)_jaccard\\.csv", "\\1", filename)
  
  if (year == filename) {
    # If no match, skip this file
    next
  }
  
  output_file <- file.path(figures_dir, paste0("fig_similarity_", year, "_jaccard.pdf"))
  plot_similarity_heatmap(
    year_file,
    output_file,
    paste("Group Similarity (Year", year, ", Jaccard)")
  )
}

cat("All similarity heatmaps generated successfully.\n")

