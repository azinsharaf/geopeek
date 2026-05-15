$env:TEXTUAL = "debug,devtools"
python -m geopeek $args
Remove-Item Env:TEXTUAL -ErrorAction SilentlyContinue
