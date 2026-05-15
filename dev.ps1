$env:TEXTUAL = "debug,devtools"
python -m geopeek browse (Join-Path $PSScriptRoot "sample_data")
Remove-Item Env:TEXTUAL -ErrorAction SilentlyContinue
