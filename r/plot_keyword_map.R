# Plot keyword co-occurrence network map
# Input: output/tables/cooccurrence_nodes.csv, cooccurrence_edges.csv
# Output: fig_keyword_map.png, fig_keyword_map.pdf

library(igraph)
library(ggraph)
library(ggplot2)
library(dplyr)
library(yaml)
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

# Read configuration
config_file <- file.path(project_root, "config/default.yaml")
if (file.exists(config_file)) {
  config <- read_yaml(config_file)
  cooc_node_top_n <- config$COOC_NODE_TOP_N
  cooc_edge_top_n <- config$COOC_EDGE_TOP_N
  cooc_label_top_n <- config$COOC_LABEL_TOP_N
} else {
  cooc_node_top_n <- 60
  cooc_edge_top_n <- 300
  cooc_label_top_n <- 25
}

# Load exclude keywords (same as Python)
exclude_keywords <- character(0)
exclude_file <- file.path(project_root, "data/exclude/keywords.txt")
if (file.exists(exclude_file)) {
  exclude_content <- readLines(exclude_file, warn = FALSE)
  if (length(exclude_content) > 0 && nchar(trimws(exclude_content[1])) > 0) {
    exclude_keywords <- trimws(unlist(strsplit(exclude_content[1], ",")))
    exclude_keywords <- tolower(exclude_keywords)
    exclude_keywords <- exclude_keywords[exclude_keywords != ""]
  }
}

# Check if input files exist before reading
nodes_file <- file.path(tables_dir, "cooccurrence_nodes.csv")
edges_file <- file.path(tables_dir, "cooccurrence_edges.csv")
if (!file.exists(nodes_file) || !file.exists(edges_file)) {
  warning("Co-occurrence files not found. Skipping plot.")
  # Create empty figure files to indicate no data
  empty_png <- file.path(figures_dir, "fig_keyword_map.png")
  empty_pdf <- file.path(figures_dir, "fig_keyword_map.pdf")
  if (!dir.exists(figures_dir)) {
    dir.create(figures_dir, recursive = TRUE)
  }
  # Create empty PNG
  png(empty_png, width = 12*300, height = 10*300, res = 300, bg = "white")
  plot.new()
  text(0.5, 0.5, "No data to plot\n(Co-occurrence files not found)", cex = 2, col = "gray")
  dev.off()
  # Create empty PDF
  pdf(empty_pdf, width = 12, height = 10, bg = "white")
  plot.new()
  text(0.5, 0.5, "No data to plot\n(Co-occurrence files not found)", cex = 2, col = "gray")
  dev.off()
  cat(paste("Empty figure files created (files not found):", figures_dir, "\n"))
  quit(status = 0)  # Exit gracefully
}

# Read data
nodes <- read.csv(nodes_file, stringsAsFactors = FALSE)
edges <- read.csv(edges_file, stringsAsFactors = FALSE)

# Check if data is empty
if (nrow(nodes) == 0 || nrow(edges) == 0) {
  warning("No co-occurrence data to plot. Skipping plot.")
  # Create empty figure files to indicate no data
  empty_png <- file.path(figures_dir, "fig_keyword_map.png")
  empty_pdf <- file.path(figures_dir, "fig_keyword_map.pdf")
  if (!dir.exists(figures_dir)) {
    dir.create(figures_dir, recursive = TRUE)
  }
  # Create empty PNG
  png(empty_png, width = 12*300, height = 10*300, res = 300, bg = "white")
  plot.new()
  text(0.5, 0.5, "No data to plot", cex = 2, col = "gray")
  dev.off()
  # Create empty PDF
  pdf(empty_pdf, width = 12, height = 10, bg = "white")
  plot.new()
  text(0.5, 0.5, "No data to plot", cex = 2, col = "gray")
  dev.off()
  cat(paste("Empty figure files created (no data):", figures_dir, "\n"))
  quit(status = 0)  # Exit gracefully
}

# Filter out excluded keywords (case-insensitive, same as Python)
if (length(exclude_keywords) > 0) {
  exclude_set <- tolower(exclude_keywords)
  nodes <- nodes %>% filter(!tolower(token) %in% exclude_set)
  edges <- edges %>% filter(!tolower(source) %in% exclude_set & !tolower(target) %in% exclude_set)
  
  # Check again after filtering
  if (nrow(nodes) == 0 || nrow(edges) == 0) {
    warning("No co-occurrence data after filtering. Skipping plot.")
    # Create empty figure files to indicate no data
    empty_png <- file.path(figures_dir, "fig_keyword_map.png")
    empty_pdf <- file.path(figures_dir, "fig_keyword_map.pdf")
    if (!dir.exists(figures_dir)) {
      dir.create(figures_dir, recursive = TRUE)
    }
    # Create empty PNG
    png(empty_png, width = 12*300, height = 10*300, res = 300, bg = "white")
    plot.new()
    text(0.5, 0.5, "No data to plot\n(After filtering)", cex = 2, col = "gray")
    dev.off()
    # Create empty PDF
    pdf(empty_pdf, width = 12, height = 10, bg = "white")
    plot.new()
    text(0.5, 0.5, "No data to plot\n(After filtering)", cex = 2, col = "gray")
    dev.off()
    cat(paste("Empty figure files created (no data after filtering):", figures_dir, "\n"))
    quit(status = 0)  # Exit gracefully
  }
}

# Create graph
g <- graph_from_data_frame(
  d = edges,
  vertices = nodes,
  directed = FALSE
)

# Layout
set.seed(42)
layout <- layout_with_fr(g, niter = 1000)

# Prepare data for ggraph
ggraph_data <- ggraph(g, layout = layout) +
  geom_edge_link(aes(width = weight), 
                 alpha = 0.3, 
                 color = "grey70",
                 show.legend = FALSE) +
  geom_node_point(aes(size = doc_freq), 
                  color = "steelblue", 
                  alpha = 0.7) +
  geom_node_text(aes(label = ifelse(
    rank(-doc_freq) <= cooc_label_top_n, name, ""
  )), 
  size = 2.5, 
  repel = TRUE,
  fontface = "bold") +
  scale_size_continuous(range = c(2, 8), name = "Doc\nFreq") +
  labs(
    title = paste("Keyword Co-occurrence Network"),
    subtitle = paste("Top", cooc_node_top_n, "nodes, Top", cooc_edge_top_n, "edges")
  ) +
  common_theme() +
  theme(
    axis.text = element_blank(),
    axis.ticks = element_blank(),
    panel.grid = element_blank(),
    legend.position = "right"
  )

# Save PNG
ggsave(file.path(figures_dir, "fig_keyword_map.png"), 
       plot = ggraph_data, 
       width = 12, 
       height = 10, 
       dpi = 300,
       bg = "white")

# Save PDF
ggsave(file.path(figures_dir, "fig_keyword_map.pdf"), 
       plot = ggraph_data, 
       width = 12, 
       height = 10,
       device = "pdf",
       bg = "white")

cat("Keyword map figure saved to", figures_dir, "\n")

