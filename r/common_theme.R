# Common theme for academic figures
# Minimal, publication-ready styling

library(ggplot2)

common_theme <- function() {
  theme_minimal() +
    theme(
      # Text elements
      text = element_text(family = "serif", size = 11),
      plot.title = element_text(size = 12, face = "bold", hjust = 0.5),
      plot.subtitle = element_text(size = 10, hjust = 0.5),
      axis.title = element_text(size = 10),
      axis.text = element_text(size = 9),
      legend.title = element_text(size = 10),
      legend.text = element_text(size = 9),
      
      # Grid and background
      panel.grid.major = element_line(color = "grey90", linewidth = 0.3),
      panel.grid.minor = element_blank(),
      panel.background = element_blank(),
      plot.background = element_rect(fill = "white", color = NA),
      
      # Legend
      legend.position = "right",
      legend.background = element_rect(fill = "white", color = "grey80"),
      legend.key = element_rect(fill = "white", color = NA),
      
      # Margins
      plot.margin = margin(10, 10, 10, 10, "pt")
    )
}

