# News Keyword Analysis Pipeline

## Installation

1. Install Anaconda or Miniconda from [https://www.anaconda.com/products/distribution](https://www.anaconda.com/products/distribution)

2. Create the conda environment (from project root directory):

```bash
conda env create -f anaconda/env/environment.yml
```

## Usage

Run the pipeline:

```bash
conda run -n keyword-analysis python -m news_kw.cli
```

### Configuration

#### 1. Top N Keywords in Trend Plot

To change the number of top keywords displayed in `output/figures/py_keyword_trends.png`, edit `config/default.yaml`:

```yaml
TREND_PLOT_TOP_N: 3  # Change this value (default: 3)
```

#### 2. Exclude Keywords

To exclude specific keywords from analysis, edit `data/exclude/keywords.txt`:

- Add keywords separated by commas
- Example: `oregon,portland,state,would,also,school,said,may,us,even,make,need,could,page,like,city`
- The pipeline automatically reads all `.txt` files in the `data/exclude/` directory

#### 3. Raw Data Location

Place your input files (TXT or PDF) in the `data/raw_txt/` directory:

- The pipeline automatically processes all `.txt` and `.pdf` files in this directory
- Files are processed recursively (including subdirectories)
