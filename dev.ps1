$env:TEXTUAL = "debug,devtools"
python -m geopeek browse sample_data/
Remove-Item Env:TEXTUAL -ErrorAction SilentlyContinue
