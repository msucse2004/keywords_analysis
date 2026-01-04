"""Main analysis pipeline."""

import logging
import subprocess
import shutil
import os
import glob
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
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


def run_r_scripts(project_root: Path, logger: logging.Logger, 
                  tables_dir: Path = None, figures_dir: Path = None):
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
    conda_exe = shutil.which('conda')
    
    if not conda_exe:
        logger.warning("conda not found in PATH. Skipping R figure generation.")
        logger.warning("Please ensure conda is installed and available in PATH.")
        return
    
    # Use conda run to execute R scripts in the conda environment
    # This ensures R packages from conda environment are used
    rscript_cmd = ['conda', 'run', '-n', conda_env_name, 'Rscript']
    
    # Set default paths if not provided
    if tables_dir is None:
        tables_dir = project_root / 'output' / 'tables'
    if figures_dir is None:
        figures_dir = project_root / 'output' / 'figures'
    
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
                env = os.environ.copy()
                env['R_TABLES_DIR'] = str(tables_dir)
                env['R_FIGURES_DIR'] = str(figures_dir)
                env['R_PROJECT_ROOT'] = str(project_root)
                
                # Use conda run to execute R script in conda environment
                # This ensures R packages from conda environment are used
                result = subprocess.run(
                    rscript_cmd + [str(script_path)],
                    cwd=str(project_root),
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info(f"Successfully executed {script}")
                if result.stdout:
                    logger.debug(f"R output: {result.stdout}")
                success = True
                break
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr if e.stderr else str(e)
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
    
    logger.info(f"Group '{group_name}' processing completed successfully!")
    logger.info("=" * 60)


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

