@echo off
REM Filter files by date parsing using conda environment
echo Filtering files by date parsing...
conda run -n keyword-analysis python -m news_kw.filter_files --raw_dir data/raw_txt --filtered_dir data/filtered_data --config config/default.yaml
if %ERRORLEVEL% NEQ 0 (
    echo Error: Filter files failed
    exit /b %ERRORLEVEL%
)
echo File filtering completed

