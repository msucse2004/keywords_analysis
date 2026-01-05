# Filter files by date parsing using conda environment
Write-Host "Filtering files by date parsing..." -ForegroundColor Cyan
conda run -n keyword-analysis python -m news_kw.filter_files --raw_dir data/raw_txt --filtered_dir data/filtered_data --config config/default.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Filter files failed" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "File filtering completed" -ForegroundColor Green





