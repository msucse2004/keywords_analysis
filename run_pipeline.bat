@echo off
REM Run Python pipeline using conda environment
echo Running Python pipeline...
conda run -n keyword-analysis python -m news_kw.cli --config config/default.yaml --input_dir data/filtered_data --output_dir output --data_dir data %*
if %ERRORLEVEL% NEQ 0 (
    echo Error: Pipeline failed
    exit /b %ERRORLEVEL%
)
echo Python pipeline completed




