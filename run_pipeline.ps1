# Run Python pipeline using conda environment
param(
    [string[]]$ExtraArgs
)

Write-Host "Running Python pipeline..." -ForegroundColor Cyan
$argsString = if ($ExtraArgs) { $ExtraArgs -join " " } else { "" }
conda run -n keyword-analysis python -m news_kw.cli --config config/default.yaml --input_dir data/filtered_data --output_dir output --data_dir data $argsString
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Pipeline failed" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Python pipeline completed" -ForegroundColor Green





