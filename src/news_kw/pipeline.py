"""Main analysis pipeline."""

import logging
import subprocess
import shutil
from pathlib import Path
from news_kw.config import Config
from news_kw.io import load_txt_articles
from news_kw.preprocess import tokenize_documents
from news_kw.keywords import extract_keywords
from news_kw.timeseries import create_timeseries, create_topn_by_date
from news_kw.cooccurrence import calculate_cooccurrence
from news_kw.viz import plot_keyword_trends, plot_keyword_map, plot_wordcloud_python


def setup_logging(log_dir: Path):
    """Setup logging configuration.
    
    Args:
        log_dir: Directory to save log file
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'pipeline.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def run_r_scripts(project_root: Path, logger: logging.Logger):
    """Run R scripts to generate publication-quality figures.
    
    Args:
        project_root: Root directory of the project (where R scripts are located)
        logger: Logger instance for logging messages
    """
    # Check if Rscript is available
    rscript_path = shutil.which('Rscript')
    if not rscript_path:
        logger.warning("Rscript not found. Skipping R figure generation.")
        logger.warning("Install R from https://www.r-project.org/ to generate R figures.")
        return
    
    r_scripts = [
        'r/plot_trends.R',
        'r/plot_keyword_map.R',
        'r/plot_wordcloud.R'
    ]
    
    logger.info("Step 7: Creating R publication-quality figures...")
    
    for script in r_scripts:
        script_path = project_root / script
        if not script_path.exists():
            logger.warning(f"R script not found: {script_path}")
            continue
        
        try:
            logger.info(f"Running {script}...")
            result = subprocess.run(
                [rscript_path, str(script_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Successfully executed {script}")
            if result.stdout:
                logger.debug(f"R output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run {script}: {e}")
            if e.stderr:
                logger.error(f"R error output: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error running {script}: {e}")


def run_pipeline(config_path: Path, input_dir: Path, output_dir: Path, 
                data_dir: Path, create_py_figures: bool = True, 
                create_r_figures: bool = True):
    """Run the complete analysis pipeline.
    
    Args:
        config_path: Path to YAML configuration file
        input_dir: Directory containing TXT and PDF files (default: data/raw_txt)
        output_dir: Directory for output tables and figures
        data_dir: Directory for processed data
        create_py_figures: Whether to create Python preview figures
        create_r_figures: Whether to create R publication-quality figures
    """
    # Setup directories
    processed_dir = data_dir / 'processed'
    tables_dir = output_dir / 'tables'
    figures_dir = output_dir / 'figures'
    log_dir = output_dir / 'logs'
    
    setup_logging(log_dir)
    logger = logging.getLogger(__name__)
    
    # Load config
    config = Config.from_yaml(config_path)
    
    # Load exclude keywords from data/exclude folder
    exclude_dir = data_dir / 'exclude'
    exclude_keywords = Config.load_exclude_keywords(exclude_dir)
    if exclude_keywords:
        logger.info(f"Loaded {len(exclude_keywords)} exclude keywords from {exclude_dir}")
    
    # Log config values
    logger.info("=" * 60)
    logger.info("Pipeline Configuration:")
    for key, value in config.to_dict().items():
        logger.info(f"  {key}: {value}")
    if exclude_keywords:
        logger.info(f"  EXCLUDE_KEYWORDS: {exclude_keywords}")
    logger.info("=" * 60)
    
    # Step 1: Load TXT and PDF articles
    logger.info("Step 1: Loading TXT and PDF articles...")
    documents_df = load_txt_articles(input_dir, processed_dir)
    logger.info(f"Loaded {len(documents_df)} documents")
    
    # Step 2: Preprocess and tokenize
    logger.info("Step 2: Preprocessing and tokenizing...")
    tokens_df = tokenize_documents(documents_df, processed_dir)
    logger.info(f"Generated {len(tokens_df)} tokens")
    
    # Step 3: Extract keywords
    logger.info("Step 3: Extracting keywords...")
    keyword_topk = extract_keywords(tokens_df, config, exclude_keywords, tables_dir)
    logger.info(f"Extracted top {len(keyword_topk)} keywords")
    
    # Step 4: Create time series
    logger.info("Step 4: Creating time series...")
    timeseries_df = create_timeseries(tokens_df, keyword_topk, config, exclude_keywords, tables_dir)
    logger.info(f"Created time series with {len(timeseries_df)} records")
    
    # Step 4.5: Create Top N by date table
    logger.info("Step 4.5: Creating Top N by date table...")
    topn_by_date_df = create_topn_by_date(timeseries_df, config, exclude_keywords, tables_dir)
    logger.info(f"Created Top N by date table with {len(topn_by_date_df)} records")
    
    # Step 5: Calculate co-occurrence
    logger.info("Step 5: Calculating co-occurrence...")
    calculate_cooccurrence(tokens_df, config, tables_dir, exclude_keywords)
    logger.info("Co-occurrence network calculated")
    
    # Step 6: Python visualization (optional)
    if create_py_figures:
        logger.info("Step 6: Creating Python preview figures...")
        try:
            plot_keyword_trends(
                tables_dir / 'keyword_topn_by_date.csv',
                config,
                figures_dir / 'py_keyword_trends.png'
            )
            logger.info("Keyword trends plot created")
        except Exception as e:
            logger.warning(f"Failed to create trends plot: {e}")
        
        try:
            plot_keyword_map(
                tables_dir / 'cooccurrence_nodes.csv',
                tables_dir / 'cooccurrence_edges.csv',
                config,
                figures_dir / 'py_keyword_map.png'
            )
            logger.info("Keyword map plot created")
        except Exception as e:
            logger.warning(f"Failed to create keyword map: {e}")
        
        try:
            plot_wordcloud_python(
                config,
                tables_dir / 'keyword_topk.csv',
                exclude_keywords,
                figures_dir / config.WORDCLOUD_OUTPUT_NAME
            )
            logger.info("Word cloud plot created")
        except Exception as e:
            logger.warning(f"Failed to create word cloud: {e}")
    
    # Step 7: R visualization (optional)
    if create_r_figures:
        # Get project root (assume config_path is relative to project root)
        # If config_path is config/default.yaml, parent.parent gives project root
        project_root = config_path.resolve().parent.parent
        # Verify R scripts directory exists
        r_dir = project_root / 'r'
        if not r_dir.exists():
            logger.warning(f"R scripts directory not found: {r_dir}")
            logger.warning("Skipping R figure generation.")
        else:
            run_r_scripts(project_root, logger)
    
    logger.info("=" * 60)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 60)

