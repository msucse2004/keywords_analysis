# Plot word cloud from keyword frequencies
# Input: output/tables/keyword_topk.csv
# Output: fig_wordcloud.png, fig_wordcloud.pdf

library(wordcloud)
library(yaml)
library(viridis)
library(dplyr)
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
  wordcloud_top_n <- config$WORDCLOUD_TOP_N
  wordcloud_max_words <- config$WORDCLOUD_MAX_WORDS
  wordcloud_width <- config$WORDCLOUD_WIDTH
  wordcloud_height <- config$WORDCLOUD_HEIGHT
  wordcloud_background <- config$WORDCLOUD_BACKGROUND
} else {
  wordcloud_top_n <- 200
  wordcloud_max_words <- 200
  wordcloud_width <- 1400
  wordcloud_height <- 900
  wordcloud_background <- "white"
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

# Check if input file exists before reading
input_file <- file.path(tables_dir, "keyword_topk.csv")
if (!file.exists(input_file)) {
  stop(sprintf("Input file not found: %s\nPlease check that R_TABLES_DIR environment variable is set correctly.\nCurrent R_TABLES_DIR: %s", input_file, tables_dir))
}

# Read data
keywords <- read.csv(input_file, stringsAsFactors = FALSE)

# Filter out excluded keywords (case-insensitive, same as Python)
if (length(exclude_keywords) > 0) {
  exclude_set <- tolower(exclude_keywords)
  keywords <- keywords %>% filter(!tolower(token) %in% exclude_set)
}

# Filter to top N
keywords <- head(keywords, wordcloud_top_n)

# Create frequency vector
freq_vec <- keywords$freq
names(freq_vec) <- keywords$token

# Create output directory
dir.create(figures_dir, showWarnings = FALSE, recursive = TRUE)

# Generate word cloud - PNG
png(file.path(figures_dir, "fig_wordcloud.png"), 
    width = wordcloud_width, 
    height = wordcloud_height,
    units = "px",
    res = 300,
    bg = wordcloud_background)

wordcloud(words = names(freq_vec),
          freq = freq_vec,
          max.words = wordcloud_max_words,
          random.order = FALSE,
          rot.per = 0.35,
          colors = viridis::viridis_pal(option = "plasma")(min(50, length(freq_vec))),
          scale = c(4, 0.5))

dev.off()

# Generate word cloud - PDF
pdf(file.path(figures_dir, "fig_wordcloud.pdf"), 
    width = wordcloud_width / 100, 
    height = wordcloud_height / 100,
    bg = wordcloud_background)

wordcloud(words = names(freq_vec),
          freq = freq_vec,
          max.words = wordcloud_max_words,
          random.order = FALSE,
          rot.per = 0.35,
          colors = viridis::viridis_pal(option = "plasma")(min(50, length(freq_vec))),
          scale = c(4, 0.5))

dev.off()

cat(paste("Word cloud figure saved to", figures_dir, "\n"))

