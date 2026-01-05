@echo off
REM Run complete pipeline using conda environment
echo ========================================
echo Running complete pipeline...
echo ========================================

REM Step 1: Filter files
echo.
echo Step 1: Filtering files by date parsing...
call run_filter_files.bat
if %ERRORLEVEL% NEQ 0 (
    echo Error: File filtering failed
    exit /b %ERRORLEVEL%
)

REM Step 2: Run Python pipeline
echo.
echo Step 2: Running Python pipeline...
call run_pipeline.bat
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python pipeline failed
    exit /b %ERRORLEVEL%
)

REM Step 3: Generate R figures (optional)
echo.
echo Step 3: Generating R figures...
conda run -n keyword-analysis Rscript r/plot_trends.R
conda run -n keyword-analysis Rscript r/plot_keyword_map.R
conda run -n keyword-analysis Rscript r/plot_wordcloud.R
if %ERRORLEVEL% NEQ 0 (
    echo Warning: R figure generation failed (this is optional)
)

echo.
echo ========================================
echo All tasks completed!
echo ========================================




