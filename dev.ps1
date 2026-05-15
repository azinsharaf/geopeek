$env:TEXTUAL = "debug,devtools"
python -m geopeek browse $PSScriptRoot/sample_data/
Remove-Item Env:TEXTUAL -ErrorAction SilentlyContinue
