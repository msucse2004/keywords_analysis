"""Command-line interface for the pipeline."""

import argparse
from pathlib import Path
from news_kw.pipeline import run_pipeline


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
        default=Path('data/raw_txt'),
        help='Directory containing TXT and PDF files (default: data/raw_txt)'
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
    
    args = parser.parse_args()
    
    # Validate paths
    if not args.config.exists():
        raise FileNotFoundError(f"Config file not found: {args.config}")
    
    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    
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

