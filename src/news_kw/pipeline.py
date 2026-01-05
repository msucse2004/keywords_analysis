"""Main analysis pipeline."""

import logging
import subprocess
import shutil
import os
import glob
import pandas as pd
import platform
from pathlib import Path
from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed
from news_kw.config import Config
from news_kw.io import load_txt_articles
from news_kw.preprocess import tokenize_documents
from news_kw.keywords import extract_keywords
from news_kw.timeseries import create_timeseries, create_topn_by_date
from news_kw.cooccurrence import calculate_cooccurrence
from news_kw.viz import plot_keyword_trends, plot_keyword_map, plot_wordcloud_python
from news_kw.similarity import create_similarity_analysis
from news_kw.keyword_lag import analyze_keyword_lag_monthly


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


def _find_conda_env_rscript(conda_env_name: str, logger: logging.Logger = None) -> Path:
    """Find Rscript executable in the specified conda environment.
    
    Args:
        conda_env_name: Name of the conda environment
        logger: Optional logger for debug messages
    
    Returns:
        Path to Rscript executable, or None if not found
    """
    # Try to get conda info to find environment path
    try:
        result = subprocess.run(
            ['conda', 'env', 'list'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        
        # Parse conda env list output to find environment path
        for line in result.stdout.split('\n'):
            if conda_env_name in line:
                # Extract path (format: "env_name    /path/to/env")
                parts = line.split()
                if len(parts) >= 2:
                    env_path = Path(parts[-1])
                    
                    # Find Rscript based on platform
                    if platform.system() == 'Windows':
                        rscript_path = env_path / 'Scripts' / 'Rscript.exe'
                    else:
                        rscript_path = env_path / 'bin' / 'Rscript'
                    
                    if rscript_path.exists():
                        if logger:
                            logger.debug(f"Found Rscript at: {rscript_path}")
                        return rscript_path
    except Exception as e:
        if logger:
            logger.warning(f"Failed to find conda environment path: {e}")
    
    # Fallback: try common conda installation paths
    conda_base = os.environ.get('CONDA_PREFIX') or os.environ.get('CONDA_DEFAULT_ENV')
    if conda_base:
        conda_base_path = Path(conda_base).parent.parent if 'envs' in str(conda_base) else Path(conda_base)
        env_path = conda_base_path / 'envs' / conda_env_name
        
        if platform.system() == 'Windows':
            rscript_path = env_path / 'Scripts' / 'Rscript.exe'
        else:
            rscript_path = env_path / 'bin' / 'Rscript'
        
        if rscript_path.exists():
            if logger:
                logger.debug(f"Found Rscript at: {rscript_path}")
            return rscript_path
    
    return None


def run_r_scripts(project_root: Path, logger: logging.Logger, 
                  tables_dir: Path = None, figures_dir: Path = None,
                  r_scripts: List[str] = None):
    """Run R scripts to generate publication-quality figures.
    
    Always uses conda environment 'keyword-analysis' to ensure R packages are available.
    
    Args:
        project_root: Root directory of the project (where R scripts are located)
        logger: Logger instance for logging messages
        tables_dir: Directory containing tables (default: output/tables)
        figures_dir: Directory for output figures (default: output/figures)
    """
    # Always use conda environment for R scripts
    conda_env_name = 'keyword-analysis'
    
    # Try to find Rscript in conda environment directly (more reliable than conda run on Windows)
    rscript_path = _find_conda_env_rscript(conda_env_name, logger)
    
    if rscript_path and rscript_path.exists():
        # Use direct path to Rscript (more reliable on Windows)
        rscript_cmd = [str(rscript_path)]
        logger.info(f"Using Rscript from conda environment: {rscript_path}")
    else:
        # Fallback to conda run if direct path not found
        conda_exe = shutil.which('conda')
        if not conda_exe:
            logger.warning("conda not found in PATH. Skipping R figure generation.")
            logger.warning("Please ensure conda is installed and available in PATH.")
            return
        rscript_cmd = ['conda', 'run', '-n', conda_env_name, 'Rscript']
        logger.info(f"Using conda run to execute Rscript (fallback method)")
    
    # Set default paths if not provided
    if tables_dir is None:
        tables_dir = project_root / 'output' / 'tables'
    if figures_dir is None:
        figures_dir = project_root / 'output' / 'figures'
    
    if r_scripts is None:
        r_scripts = [
            'r/plot_trends.R',
            'r/plot_keyword_map.R',
            'r/plot_wordcloud.R'
        ]
    
    logger.info("Step 7: Creating R publication-quality figures...")
    logger.info(f"Using conda environment: {conda_env_name}")
    logger.info(f"Using tables directory: {tables_dir}")
    logger.info(f"Using figures directory: {figures_dir}")
    
    for script in r_scripts:
        script_path = project_root / script
        if not script_path.exists():
            logger.warning(f"R script not found: {script_path}")
            continue
        
        # Retry logic for conda run (handles Windows file locking issues)
        max_retries = 3
        retry_delay = 1  # seconds
        success = False
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Running {script} in conda environment '{conda_env_name}' (attempt {attempt + 1}/{max_retries})...")
                # Set environment variables for R scripts to use
                # Use absolute paths to avoid any path resolution issues
                env = os.environ.copy()
                env['R_TABLES_DIR'] = str(tables_dir.resolve())
                env['R_FIGURES_DIR'] = str(figures_dir.resolve())
                env['R_PROJECT_ROOT'] = str(project_root.resolve())
                
                # Log environment variables for debugging
                logger.debug(f"R_TABLES_DIR: {env['R_TABLES_DIR']}")
                logger.debug(f"R_FIGURES_DIR: {env['R_FIGURES_DIR']}")
                logger.debug(f"R_PROJECT_ROOT: {env['R_PROJECT_ROOT']}")
                
                # Use conda run to execute R script in conda environment
                # Note: conda run may not pass environment variables correctly on Windows
                # As a workaround, pass them via command line using R -e with Sys.setenv
                # or use --no-capture-output to see actual errors
                result = subprocess.run(
                    rscript_cmd + [str(script_path.resolve())],
                    cwd=str(project_root.resolve()),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    check=True
                )
                logger.info(f"Successfully executed {script}")
                # Log R output for debugging (especially environment variable debugging)
                if result.stdout:
                    # Print to logger - R scripts may output debug info via cat()
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            logger.info(f"R output: {line}")
                success = True
                break
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr if e.stderr else str(e)
                # Also check stdout for error messages (R may output errors to stdout)
                if e.stdout:
                    logger.error(f"R stdout: {e.stdout}")
                
                # Check if it's a file locking error
                if "cannot access the file" in error_msg.lower() or "being used by another process" in error_msg.lower():
                    if attempt < max_retries - 1:
                        logger.warning(f"File access conflict detected, retrying in {retry_delay} seconds...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Failed to run {script} after {max_retries} attempts: {e}")
                        if e.stderr:
                            logger.error(f"R error output: {e.stderr}")
                else:
                    logger.error(f"Failed to run {script}: {e}")
                    if e.stderr:
                        logger.error(f"R error output: {e.stderr}")
                    # Log stdout as well - may contain useful debug info
                    if e.stdout:
                        logger.error(f"R stdout: {e.stdout}")
                    break
            except Exception as e:
                logger.error(f"Unexpected error running {script}: {e}")
                break
        
        if not success:
            logger.warning(f"Skipping remaining R scripts for this group due to previous failures")
            break


def run_pipeline_single_group(group_name: str, folders: list, config: Config, 
                              config_path: Path, input_dir: Path, output_dir: Path,
                              data_dir: Path, create_py_figures: bool = True,
                              create_r_figures: bool = True, logger: logging.Logger = None):
    """Run the complete analysis pipeline for a single group.
    
    Args:
        group_name: Name of the group (used for output folder)
        folders: List of folder names to process
        config: Config instance
        config_path: Path to YAML configuration file
        input_dir: Directory containing TXT and PDF files
        output_dir: Base directory for output tables and figures
        data_dir: Directory for processed data
        create_py_figures: Whether to create Python preview figures
        create_r_figures: Whether to create R publication-quality figures
        logger: Logger instance (if None, creates a new one)
    """
    # Setup group-specific directories
    group_tables_dir = output_dir / 'tables' / group_name
    group_figures_dir = output_dir / 'figures' / group_name
    group_log_dir = output_dir / 'logs' / group_name
    processed_dir = data_dir / 'processed' / group_name
    
    if logger is None:
        setup_logging(group_log_dir)
        logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info(f"Processing group: {group_name}")
    logger.info(f"Folders: {folders}")
    logger.info("=" * 60)
    
    # Step 1: Load TXT, PDF, and DOCX articles
    logger.info("Step 1: Loading TXT, PDF, and DOCX articles...")
    documents_df = load_txt_articles(input_dir, processed_dir, folders)
    logger.info(f"Loaded {len(documents_df)} documents")
    
    # Step 2: Preprocess and tokenize
    logger.info("Step 2: Preprocessing and tokenizing...")
    tokens_df = tokenize_documents(documents_df, processed_dir)
    logger.info(f"Generated {len(tokens_df)} tokens")
    
    # Load exclude keywords
    exclude_dir = data_dir / 'exclude'
    exclude_keywords = Config.load_exclude_keywords(exclude_dir)
    
    # Step 3: Extract keywords
    logger.info("Step 3: Extracting keywords...")
    keyword_topk = extract_keywords(tokens_df, config, exclude_keywords, group_tables_dir)
    logger.info(f"Extracted top {len(keyword_topk)} keywords")
    
    # Step 4: Create time series
    logger.info("Step 4: Creating time series...")
    timeseries_df = create_timeseries(tokens_df, keyword_topk, config, exclude_keywords, group_tables_dir)
    logger.info(f"Created time series with {len(timeseries_df)} records")
    
    # Step 4.5: Create Top N by date table
    logger.info("Step 4.5: Creating Top N by date table...")
    topn_by_date_df = create_topn_by_date(timeseries_df, config, exclude_keywords, group_tables_dir)
    logger.info(f"Created Top N by date table with {len(topn_by_date_df)} records")
    
    # Step 5: Calculate co-occurrence
    logger.info("Step 5: Calculating co-occurrence...")
    calculate_cooccurrence(tokens_df, config, group_tables_dir, exclude_keywords)
    logger.info("Co-occurrence network calculated")
    
    # Step 6: Python visualization (optional)
    if create_py_figures:
        logger.info("Step 6: Creating Python preview figures...")
        group_figures_dir.mkdir(parents=True, exist_ok=True)
        try:
            plot_keyword_trends(
                group_tables_dir / 'keyword_topn_by_date.csv',
                config,
                group_figures_dir / 'py_keyword_trends.png'
            )
            logger.info("Keyword trends plot created")
        except Exception as e:
            logger.warning(f"Failed to create trends plot: {e}")
        
        try:
            plot_keyword_map(
                group_tables_dir / 'cooccurrence_nodes.csv',
                group_tables_dir / 'cooccurrence_edges.csv',
                config,
                group_figures_dir / 'py_keyword_map.png'
            )
            logger.info("Keyword map plot created")
        except Exception as e:
            logger.warning(f"Failed to create keyword map: {e}")
        
        try:
            plot_wordcloud_python(
                config,
                group_tables_dir / 'keyword_topk.csv',
                exclude_keywords,
                group_figures_dir / config.WORDCLOUD_OUTPUT_NAME
            )
            logger.info("Word cloud plot created")
        except Exception as e:
            logger.warning(f"Failed to create word cloud: {e}")
    
    # Step 7: R visualization (optional)
    if create_r_figures:
        # Get project root (assume config_path is relative to project root)
        project_root = config_path.resolve().parent.parent
        # Verify R scripts directory exists
        r_dir = project_root / 'r'
        if not r_dir.exists():
            logger.warning(f"R scripts directory not found: {r_dir}")
            logger.warning("Skipping R figure generation.")
        else:
            # Run R scripts with group-specific directories
            run_r_scripts(project_root, logger, 
                         tables_dir=group_tables_dir,
                         figures_dir=group_figures_dir)
    
    # Step 8: Create year-specific figures
    logger.info("Step 8: Creating year-specific figures...")
    create_year_specific_figures(
        timeseries_df=timeseries_df,
        topn_by_date_df=topn_by_date_df,
        keyword_topk=keyword_topk,
        tokens_df=tokens_df,
        group_name=group_name,
        config=config,
        config_path=config_path,
        output_dir=output_dir,
        exclude_keywords=exclude_keywords,
        create_py_figures=create_py_figures,
        create_r_figures=create_r_figures,
        logger=logger
    )
    
    # Step 9: Organize overall files (move root-level files to overall folder)
    logger.info("Step 9: Organizing overall files...")
    overall_tables_dir = group_tables_dir / 'overall'
    overall_figures_dir = group_figures_dir / 'overall'
    overall_tables_dir.mkdir(parents=True, exist_ok=True)
    overall_figures_dir.mkdir(parents=True, exist_ok=True)
    
    # Move root-level table files to overall folder (if not already in a year folder)
    for file_path in group_tables_dir.glob('*.csv'):
        # Skip if file is already in a subdirectory
        if file_path.parent == group_tables_dir:
            target_path = overall_tables_dir / file_path.name
            if not target_path.exists():
                shutil.move(str(file_path), str(target_path))
                logger.debug(f"Moved table file: {file_path.name} -> overall/")
    
    # Move root-level figure files to overall folder (if not already in a year folder)
    for file_path in group_figures_dir.glob('*'):
        # Skip if file is already in a subdirectory
        if file_path.is_file() and file_path.parent == group_figures_dir:
            target_path = overall_figures_dir / file_path.name
            if not target_path.exists():
                shutil.move(str(file_path), str(target_path))
                logger.debug(f"Moved figure file: {file_path.name} -> overall/")
    
    logger.info("Overall files organized successfully!")
    
    logger.info(f"Group '{group_name}' processing completed successfully!")
    logger.info("=" * 60)


def create_year_specific_figures(timeseries_df: pd.DataFrame, topn_by_date_df: pd.DataFrame,
                                 keyword_topk: pd.DataFrame, tokens_df: pd.DataFrame,
                                 group_name: str, config: Config, config_path: Path,
                                 output_dir: Path, exclude_keywords: list,
                                 create_py_figures: bool = True, create_r_figures: bool = True,
                                 logger: logging.Logger = None):
    """Create year-specific figures for a group.
    
    Args:
        timeseries_df: Full timeseries DataFrame
        topn_by_date_df: Full topn_by_date DataFrame
        keyword_topk: Full keyword topk DataFrame
        tokens_df: Full tokens DataFrame
        group_name: Name of the group
        config: Config instance
        config_path: Path to YAML configuration file
        output_dir: Base directory for output
        exclude_keywords: List of keywords to exclude
        create_py_figures: Whether to create Python figures
        create_r_figures: Whether to create R figures
        logger: Logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Convert dates to datetime if needed
    # Date format is YYYY-MM (monthly), convert to datetime (first day of month)
    timeseries_df = timeseries_df.copy()
    # If date is already a Period type, convert to string first, then to datetime
    if hasattr(timeseries_df['date'].dtype, 'freq') or str(timeseries_df['date'].dtype).startswith('period'):
        # Period type - convert to timestamp first
        timeseries_df['date'] = pd.to_datetime(timeseries_df['date'].astype(str) + '-01')
    else:
        # String format YYYY-MM - add '-01' to make it a valid date
        timeseries_df['date'] = pd.to_datetime(timeseries_df['date'].astype(str) + '-01')
    
    # Extract unique years
    years = sorted(timeseries_df['date'].dt.year.unique())
    
    if len(years) == 0:
        logger.warning(f"No years found in data for group '{group_name}'. Skipping year-specific figures.")
        return
    
    logger.info(f"Creating year-specific figures for years: {years}")
    
    # Get project root
    project_root = config_path.resolve().parent.parent
    
    for year in years:
        logger.info(f"Processing year {year}...")
        
        # Filter data for this year first (before creating directories)
        year_start = pd.Timestamp(f"{year}-01-01")
        year_end = pd.Timestamp(f"{year}-12-31")
        year_timeseries = timeseries_df[
            (timeseries_df['date'] >= year_start) & 
            (timeseries_df['date'] <= year_end)
        ].copy()
        
        # Check if there's any data with freq > 0 (actual data, not just zeros)
        year_timeseries_with_data = year_timeseries[year_timeseries['freq'] > 0].copy()
        
        if len(year_timeseries_with_data) == 0:
            logger.info(f"No data with freq > 0 found for year {year}. Skipping folder creation.")
            continue
        
        # Create year-specific directories only if data exists
        year_tables_dir = output_dir / 'tables' / group_name / str(year)
        year_figures_dir = output_dir / 'figures' / group_name / str(year)
        year_tables_dir.mkdir(parents=True, exist_ok=True)
        year_figures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create year-specific topn_by_date
        year_topn_by_date = create_topn_by_date(
            year_timeseries, config, exclude_keywords, year_tables_dir
        )
        
        # Copy keyword_topk for this year (using filtered tokens to recalculate)
        year_tokens = tokens_df.copy()
        year_tokens['date'] = pd.to_datetime(year_tokens['date'])
        year_tokens = year_tokens[
            (year_tokens['date'] >= year_start) & 
            (year_tokens['date'] <= year_end)
        ].copy()
        
        if len(year_tokens) > 0:
            # Recalculate keywords for this year
            year_keyword_topk = extract_keywords(year_tokens, config, exclude_keywords, year_tables_dir)
        else:
            # Use full keyword_topk if no tokens for this year
            year_keyword_topk = keyword_topk.copy()
            year_keyword_topk.to_csv(year_tables_dir / 'keyword_topk.csv', index=False)
        
        # Create cooccurrence for this year (if we have tokens)
        if len(year_tokens) > 0:
            try:
                calculate_cooccurrence(year_tokens, config, year_tables_dir, exclude_keywords)
            except Exception as e:
                logger.warning(f"Year {year}: Failed to calculate co-occurrence: {e}")
                # Ensure empty files exist even if calculation fails
                try:
                    empty_nodes = pd.DataFrame(columns=['token', 'doc_freq'])
                    empty_edges = pd.DataFrame(columns=['source', 'target', 'weight'])
                    empty_nodes.to_csv(year_tables_dir / 'cooccurrence_nodes.csv', index=False)
                    empty_edges.to_csv(year_tables_dir / 'cooccurrence_edges.csv', index=False)
                except Exception as create_error:
                    logger.warning(f"Year {year}: Failed to create empty co-occurrence files: {create_error}")
        else:
            # No tokens, create empty files
            try:
                empty_nodes = pd.DataFrame(columns=['token', 'doc_freq'])
                empty_edges = pd.DataFrame(columns=['source', 'target', 'weight'])
                empty_nodes.to_csv(year_tables_dir / 'cooccurrence_nodes.csv', index=False)
                empty_edges.to_csv(year_tables_dir / 'cooccurrence_edges.csv', index=False)
            except Exception as create_error:
                logger.warning(f"Year {year}: Failed to create empty co-occurrence files: {create_error}")
        
        # Create Python figures
        if create_py_figures:
            try:
                plot_keyword_trends(
                    year_tables_dir / 'keyword_topn_by_date.csv',
                    config,
                    year_figures_dir / 'py_keyword_trends.png'
                )
                logger.info(f"Year {year}: Keyword trends plot created")
            except Exception as e:
                logger.warning(f"Year {year}: Failed to create trends plot: {e}")
            
            try:
                plot_keyword_map(
                    year_tables_dir / 'cooccurrence_nodes.csv',
                    year_tables_dir / 'cooccurrence_edges.csv',
                    config,
                    year_figures_dir / 'py_keyword_map.png'
                )
                logger.info(f"Year {year}: Keyword map plot created")
            except Exception as e:
                logger.warning(f"Year {year}: Failed to create keyword map: {e}")
            
            try:
                plot_wordcloud_python(
                    config,
                    year_tables_dir / 'keyword_topk.csv',
                    exclude_keywords,
                    year_figures_dir / config.WORDCLOUD_OUTPUT_NAME
                )
                logger.info(f"Year {year}: Word cloud plot created")
            except Exception as e:
                logger.warning(f"Year {year}: Failed to create word cloud: {e}")
        
        # Create R figures
        if create_r_figures:
            r_dir = project_root / 'r'
            if r_dir.exists():
                run_r_scripts(project_root, logger,
                             tables_dir=year_tables_dir,
                             figures_dir=year_figures_dir)
            else:
                logger.warning(f"R scripts directory not found: {r_dir}")
        
        # Check if any files were actually created
        tables_files = list(year_tables_dir.glob('*'))
        figures_files = list(year_figures_dir.glob('*'))
        
        # If no files were created, remove the empty directories
        if len(tables_files) == 0 and len(figures_files) == 0:
            logger.warning(f"No files created for year {year}. Removing empty directories.")
            try:
                if year_tables_dir.exists():
                    year_tables_dir.rmdir()
                if year_figures_dir.exists():
                    year_figures_dir.rmdir()
            except OSError:
                # Directory not empty or other error - ignore
                pass
        else:
            logger.info(f"Year {year} processing completed")


def run_pipeline(config_path: Path, input_dir: Path, output_dir: Path, 
                data_dir: Path, create_py_figures: bool = True, 
                create_r_figures: bool = True):
    """Run the complete analysis pipeline for all groups.
    
    Args:
        config_path: Path to YAML configuration file
        input_dir: Directory containing TXT and PDF files (default: data/raw_txt)
        output_dir: Directory for output tables and figures
        data_dir: Directory for processed data
        create_py_figures: Whether to create Python preview figures
        create_r_figures: Whether to create R publication-quality figures
    """
    # Setup main logging
    main_log_dir = output_dir / 'logs'
    setup_logging(main_log_dir)
    logger = logging.getLogger(__name__)
    
    # Load config with folder validation
    try:
        config = Config.from_yaml(config_path, input_dir=input_dir)
    except ValueError as e:
        logger.error("=" * 60)
        logger.error("CONFIGURATION ERROR:")
        logger.error(str(e))
        logger.error("=" * 60)
        raise
    
    # Load exclude keywords from data/exclude folder
    exclude_dir = data_dir / 'exclude'
    exclude_keywords = Config.load_exclude_keywords(exclude_dir)
    if exclude_keywords:
        logger.info(f"Loaded {len(exclude_keywords)} exclude keywords from {exclude_dir}")
    
    # Log config values
    logger.info("=" * 60)
    logger.info("Pipeline Configuration:")
    for key, value in config.to_dict().items():
        if key != 'DATA_SOURCE_GROUPS':  # Log groups separately
            logger.info(f"  {key}: {value}")
    logger.info(f"  DATA_SOURCE_GROUPS: {config.DATA_SOURCE_GROUPS}")
    if exclude_keywords:
        logger.info(f"  EXCLUDE_KEYWORDS: {exclude_keywords}")
    logger.info("=" * 60)
    
    # Process each group
    # Ensure DATA_SOURCE_GROUPS is in Dict format (normalized in Config.from_yaml)
    if config.DATA_SOURCE_GROUPS:
        if not isinstance(config.DATA_SOURCE_GROUPS, dict):
            # Normalize if not already done
            config.DATA_SOURCE_GROUPS = Config._normalize_data_source_groups(config.DATA_SOURCE_GROUPS)
        
        # Calculate number of workers (70% of CPU cores)
        cpu_count = os.cpu_count() or 1
        max_workers = max(1, int(cpu_count * 0.7))
        num_groups = len(config.DATA_SOURCE_GROUPS)
        # Use min of max_workers and num_groups to avoid creating unnecessary processes
        workers = min(max_workers, num_groups)
        
        logger.info(f"Processing {num_groups} group(s) with {workers} worker(s) (CPU: {cpu_count}, 70% = {max_workers})...")
        
        # Prepare group tasks (convert config to dict for pickling)
        config_dict = config.to_dict()
        group_tasks = [
            (group_name, folders, config_dict, config_path, input_dir, output_dir, data_dir, 
             create_py_figures, create_r_figures)
            for group_name, folders in config.DATA_SOURCE_GROUPS.items()
        ]
        
        # Process groups in parallel if multiple groups, otherwise sequential
        if num_groups > 1 and workers > 1:
            # Parallel processing
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_run_group_wrapper, *task): task[0] 
                    for task in group_tasks
                }
                
                for future in as_completed(futures):
                    group_name = futures[future]
                    try:
                        future.result()
                        logger.info(f"Group '{group_name}' completed successfully")
                    except Exception as e:
                        logger.error(f"Error processing group '{group_name}': {e}")
                        logger.exception(e)
        else:
            # Sequential processing (single group or single worker)
            for group_name, folders in config.DATA_SOURCE_GROUPS.items():
                try:
                    run_pipeline_single_group(
                        group_name=group_name,
                        folders=folders,
                        config=config,
                        config_path=config_path,
                        input_dir=input_dir,
                        output_dir=output_dir,
                        data_dir=data_dir,
                        create_py_figures=create_py_figures,
                        create_r_figures=create_r_figures,
                        logger=logger
                    )
                except Exception as e:
                    logger.error(f"Error processing group '{group_name}': {e}")
                    logger.exception(e)
                    continue
    else:
        # Legacy mode: use DATA_SOURCE_FOLDERS as a single group
        logger.warning("DATA_SOURCE_GROUPS not found, using legacy DATA_SOURCE_FOLDERS mode")
        group_name = '_'.join(config.DATA_SOURCE_FOLDERS) if len(config.DATA_SOURCE_FOLDERS) > 1 else config.DATA_SOURCE_FOLDERS[0]
        run_pipeline_single_group(
            group_name=group_name,
            folders=config.DATA_SOURCE_FOLDERS,
            config=config,
            config_path=config_path,
            input_dir=input_dir,
            output_dir=output_dir,
            data_dir=data_dir,
            create_py_figures=create_py_figures,
            create_r_figures=create_r_figures,
            logger=logger
        )
    
    logger.info("=" * 60)
    logger.info("All groups processed successfully!")
    logger.info("=" * 60)
    
    # Create similarity analysis between groups
    if config.DATA_SOURCE_GROUPS and isinstance(config.DATA_SOURCE_GROUPS, dict):
        logger.info("=" * 60)
        logger.info("Creating similarity analysis between groups...")
        logger.info("=" * 60)
        try:
            # All groups comparison
            group_names = list(config.DATA_SOURCE_GROUPS.keys())
            create_similarity_analysis(output_dir, group_names)
            logger.info("Similarity analysis tables created successfully")
            
            # Single groups only comparison (groups with only one folder)
            single_group_names = [
                group_name for group_name, folders in config.DATA_SOURCE_GROUPS.items()
                if len(folders) == 1
            ]
            if len(single_group_names) > 1:  # Need at least 2 groups to compare
                logger.info(f"Creating single groups comparison: {single_group_names}")
                single_comparison_dir = output_dir / 'Comparison' / 'single_groups'
                single_comparison_dir.mkdir(parents=True, exist_ok=True)
                single_tables_dir = single_comparison_dir / 'tables'
                single_tables_dir.mkdir(parents=True, exist_ok=True)
                
                # Create similarity analysis for single groups
                from news_kw.similarity import create_similarity_analysis_single_groups
                create_similarity_analysis_single_groups(output_dir, single_group_names, single_tables_dir)
                logger.info("Single groups similarity analysis tables created successfully")
                
                # Run R script to generate similarity heatmaps for single groups
                if create_r_figures:
                    project_root = config_path.resolve().parent.parent
                    single_figures_dir = single_comparison_dir
                    run_r_scripts(project_root, logger,
                                 tables_dir=single_tables_dir,
                                 figures_dir=single_figures_dir,
                                 r_scripts=['r/plot_similarity.R'])
            
            # Run R script to generate similarity heatmaps for all groups
            if create_r_figures:
                project_root = config_path.resolve().parent.parent
                comparison_tables_dir = output_dir / 'Comparison' / 'tables'
                comparison_figures_dir = output_dir / 'Comparison'
                run_r_scripts(project_root, logger,
                             tables_dir=comparison_tables_dir,
                             figures_dir=comparison_figures_dir,
                             r_scripts=['r/plot_similarity.R'])
            logger.info("Similarity analysis completed successfully!")
        except Exception as e:
            logger.warning(f"Failed to create similarity analysis: {e}")
            logger.exception(e)
    
    # Create keyword lag analysis (News/Reddit -> Meeting)
    logger.info("=" * 60)
    logger.info("Creating keyword lag analysis (News/Reddit -> Meeting)...")
    logger.info("=" * 60)
    try:
        tables_dir = output_dir / 'tables'
        time_lagging_dir = output_dir / 'TimeLagging'
        time_lagging_dir.mkdir(parents=True, exist_ok=True)
        
        # Analyze keywords from news and reddit appearing in meeting
        df = analyze_keyword_lag_monthly(
            source_groups=['news', 'reddit'],
            target_group='meeting',
            top_n=config.KEYWORD_TOP_N,
            exclude_keywords=exclude_keywords,
            output_dir=tables_dir,
            logger=logger
        )
        
        # Save results
        output_file = time_lagging_dir / 'keyword_lag_analysis.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"Keyword lag analysis results saved to: {output_file}")
        
        # Log summary statistics
        if len(df) > 0:
            total_keywords = len(df)
            appears_in_meeting = df['appears_in_target'].sum()
            percentage = (appears_in_meeting / total_keywords * 100) if total_keywords > 0 else 0
            
            logger.info(f"Total monthly Top {config.KEYWORD_TOP_N} keywords from news/reddit: {total_keywords}")
            logger.info(f"Keywords that appear in meeting: {appears_in_meeting} ({percentage:.1f}%)")
            
            # Analyze time lag for keywords that appear in meeting
            df_with_lag = df[df['appears_in_target']].copy()
            if len(df_with_lag) > 0:
                logger.info(f"Time Lag Statistics (for keywords appearing in meeting):")
                logger.info(f"  Average lag: {df_with_lag['days_lag'].mean():.1f} days")
                logger.info(f"  Median lag: {df_with_lag['days_lag'].median():.1f} days")
                logger.info(f"  Min lag: {df_with_lag['days_lag'].min():.0f} days")
                logger.info(f"  Max lag: {df_with_lag['days_lag'].max():.0f} days")
        
        # Run R script to generate visualizations
        if create_r_figures:
            project_root = config_path.resolve().parent.parent
            run_r_scripts(project_root, logger,
                         tables_dir=time_lagging_dir,
                         figures_dir=time_lagging_dir,
                         r_scripts=['r/plot_keyword_lag.R'])
        
        logger.info("Keyword lag analysis completed successfully!")
    except Exception as e:
        logger.warning(f"Failed to create keyword lag analysis: {e}")
        logger.exception(e)


def _run_group_wrapper(group_name: str, folders: list, config_dict: dict, 
                       config_path: Path, input_dir: Path, output_dir: Path,
                       data_dir: Path, create_py_figures: bool, create_r_figures: bool):
    """Wrapper function for parallel group processing.
    
    This function is used by ProcessPoolExecutor and needs to recreate the Config
    object since it cannot be pickled.
    """
    # Recreate config from dict (since Config object cannot be pickled)
    config = Config()
    for key, value in config_dict.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    # Normalize DATA_SOURCE_GROUPS if needed
    if hasattr(config, 'DATA_SOURCE_GROUPS') and config.DATA_SOURCE_GROUPS:
        if not isinstance(config.DATA_SOURCE_GROUPS, dict):
            config.DATA_SOURCE_GROUPS = Config._normalize_data_source_groups(config.DATA_SOURCE_GROUPS)
    
    # Create a separate logger for this process
    group_log_dir = output_dir / 'logs' / group_name
    setup_logging(group_log_dir)
    logger = logging.getLogger(__name__)
    
    # Run the pipeline for this group
    run_pipeline_single_group(
        group_name=group_name,
        folders=folders,
        config=config,
        config_path=config_path,
        input_dir=input_dir,
        output_dir=output_dir,
        data_dir=data_dir,
        create_py_figures=create_py_figures,
        create_r_figures=create_r_figures,
        logger=logger
    )

