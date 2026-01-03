.PHONY: install_py install_r sample_data run_py fig all clean

# Python installation
install_py:
	pip install -r requirements.txt

# R installation (check if packages are installed)
install_r:
	@echo "Installing R packages..."
	@Rscript -e "if (!require('yaml')) install.packages('yaml', repos='https://cloud.r-project.org')"
	@Rscript -e "if (!require('ggplot2')) install.packages('ggplot2', repos='https://cloud.r-project.org')"
	@Rscript -e "if (!require('dplyr')) install.packages('dplyr', repos='https://cloud.r-project.org')"
	@Rscript -e "if (!require('igraph')) install.packages('igraph', repos='https://cloud.r-project.org')"
	@Rscript -e "if (!require('ggraph')) install.packages('ggraph', repos='https://cloud.r-project.org')"
	@Rscript -e "if (!require('wordcloud')) install.packages('wordcloud', repos='https://cloud.r-project.org')"
	@Rscript -e "if (!require('viridis')) install.packages('viridis', repos='https://cloud.r-project.org')"
	@echo "R packages installed"

# Generate sample data
sample_data:
	@echo "Generating sample data..."
	@python -c "from pathlib import Path; import sys; sys.path.insert(0, 'src'); from news_kw.sample_data import generate_sample_data; generate_sample_data(Path('data/raw_txt'))"
	@echo "Sample data generated"

# Run Python pipeline
run_py:
	@echo "Running Python pipeline..."
	@python -m news_kw.cli --config config/default.yaml --input_dir data/raw_txt --output_dir output --data_dir data
	@echo "Python pipeline completed"

# Generate R figures
fig:
	@echo "Generating R figures..."
	@Rscript r/plot_trends.R
	@Rscript r/plot_keyword_map.R
	@Rscript r/plot_wordcloud.R
	@echo "R figures generated"

# Run everything
all: sample_data run_py fig
	@echo "All tasks completed!"

# Clean output
clean:
	@echo "Cleaning output directories..."
	@rm -rf output/tables/* output/figures/* output/logs/*
	@rm -rf data/processed/*
	@echo "Clean completed"

