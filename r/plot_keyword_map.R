# Plot keyword co-occurrence network map
# Input: output/tables/cooccurrence_nodes.csv, cooccurrence_edges.csv
# Output: fig_keyword_map.png, fig_keyword_map.pdf

library(igraph)
library(ggraph)
library(ggplot2)
library(dplyr)
library(yaml)
source("r/common_theme.R")

# Read configuration
config_file <- "config/default.yaml"
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
exclude_file <- "data/exclude/keywords.txt"
if (file.exists(exclude_file)) {
  exclude_content <- readLines(exclude_file, warn = FALSE)
  if (length(exclude_content) > 0 && nchar(trimws(exclude_content[1])) > 0) {
    exclude_keywords <- trimws(unlist(strsplit(exclude_content[1], ",")))
    exclude_keywords <- tolower(exclude_keywords)
    exclude_keywords <- exclude_keywords[exclude_keywords != ""]
  }
}

# Read data
nodes <- read.csv("output/tables/cooccurrence_nodes.csv", stringsAsFactors = FALSE)
edges <- read.csv("output/tables/cooccurrence_edges.csv", stringsAsFactors = FALSE)

# Filter out excluded keywords (case-insensitive, same as Python)
if (length(exclude_keywords) > 0) {
  exclude_set <- tolower(exclude_keywords)
  nodes <- nodes %>% filter(!tolower(token) %in% exclude_set)
  edges <- edges %>% filter(!tolower(source) %in% exclude_set & !tolower(target) %in% exclude_set)
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
ggsave("output/figures/fig_keyword_map.png", 
       plot = ggraph_data, 
       width = 12, 
       height = 10, 
       dpi = 300,
       bg = "white")

# Save PDF
ggsave("output/figures/fig_keyword_map.pdf", 
       plot = ggraph_data, 
       width = 12, 
       height = 10,
       device = "pdf",
       bg = "white")

cat("Keyword map figure saved to output/figures/\n")

