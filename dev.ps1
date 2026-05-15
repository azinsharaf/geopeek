$env:TEXTUAL = "debug,devtools"
python -m geopeek browse $PSScriptRoot/geopeek/sample_data/
Remove-Item Env:TEXTUAL -ErrorAction SilentlyContinue
