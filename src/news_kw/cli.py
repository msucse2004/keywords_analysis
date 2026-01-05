"""Command-line interface for the pipeline."""

import argparse
import os
import sys
import warnings
from pathlib import Path
from news_kw.pipeline import run_pipeline


def check_conda_environment():
    """Check if running in conda environment and warn if not."""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    conda_prefix = os.environ.get('CONDA_PREFIX')
    
    # Check if we're in the expected conda environment
    expected_env = 'keyword-analysis'
    
    if not conda_env and not conda_prefix:
        warnings.warn(
            f"Warning: Not running in conda environment. "
            f"Expected environment: '{expected_env}'. "
            f"Please use 'conda run -n {expected_env} python -m news_kw.cli' "
            f"or use the provided run scripts (run_pipeline.bat or run_pipeline.ps1).",
            UserWarning
        )
    elif conda_env != expected_env:
        warnings.warn(
            f"Warning: Running in conda environment '{conda_env}' but expected '{expected_env}'. "
            f"Please use 'conda run -n {expected_env} python -m news_kw.cli' "
            f"or use the provided run scripts (run_pipeline.bat or run_pipeline.ps1).",
            UserWarning
        )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='News keyword analysis pipeline for academic research'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/default.yaml'),
        help='Path to YAML configuration file (default: config/default.yaml)'
    )
    
    parser.add_argument(
        '--input_dir',
        type=Path,
        default=Path('data/filtered_data'),
        help='Directory containing TXT and PDF files (default: data/filtered_data)'
    )
    
    parser.add_argument(
        '--output_dir',
        type=Path,
        default=Path('output'),
        help='Output directory (default: output)'
    )
    
    parser.add_argument(
        '--data_dir',
        type=Path,
        default=Path('data'),
        help='Data directory (default: data)'
    )
    
    parser.add_argument(
        '--pyfig',
        action='store_true',
        default=True,
        help='Create Python preview figures (default: True)'
    )
    
    parser.add_argument(
        '--no-pyfig',
        dest='pyfig',
        action='store_false',
        help='Skip Python preview figures'
    )
    
    parser.add_argument(
        '--rfig',
        action='store_true',
        default=True,
        help='Create R publication-quality figures (default: True)'
    )
    
    parser.add_argument(
        '--no-rfig',
        dest='rfig',
        action='store_false',
        help='Skip R publication-quality figures'
    )
    
    parser.add_argument(
        '--filter',
        action='store_true',
        help='Filter files by date parsing before running pipeline'
    )
    
    args = parser.parse_args()
    
    # Check conda environment
    check_conda_environment()
    
    # If --filter is specified, run filtering first
    if args.filter:
        from news_kw.filter_files import filter_and_copy_files
        print("Filtering files by date parsing...")
        filter_and_copy_files(
            raw_txt_dir=Path('data/raw_txt'),
            filtered_data_dir=Path('data/filtered_data'),
            config_path=args.config
        )
        print("File filtering completed. Proceeding with pipeline...\n")
    
    # Validate paths
    if not args.config.exists():
        raise FileNotFoundError(f"Config file not found: {args.config}")
    
    # Note: input_dir existence is checked in run_pipeline, which will auto-filter from raw_txt if needed
    # Only check if both input_dir and raw_txt are missing
    raw_txt_dir = args.data_dir / 'raw_txt'
    if not args.input_dir.exists() and not raw_txt_dir.exists():
        raise FileNotFoundError(
            f"Neither input directory ({args.input_dir}) nor raw_txt directory ({raw_txt_dir}) found. "
            f"Please provide at least one of them."
        )
    
    # Run pipeline
    run_pipeline(
        config_path=args.config,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
        create_py_figures=args.pyfig,
        create_r_figures=args.rfig
    )


if __name__ == '__main__':
    main()

