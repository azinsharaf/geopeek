# geopeek

A CLI tool for exploring geospatial data in the terminal. Supports Shapefiles, File Geodatabases, and raster formats via GDAL.

## Installation

```bash
# Using conda (recommended — handles GDAL C libraries automatically)
conda env create -f environment.yml
conda activate geopeek

# Or using pip (requires GDAL to be installed separately)
pip install -e .
```

## Usage

### Dataset info

```bash
# Rich table output (default)
geopeek info path/to/data.shp
geopeek info path/to/data.gdb
geopeek info path/to/raster.tif

# JSON output
geopeek info path/to/data.shp --format json

# List layer names only
geopeek info path/to/data.gdb --layers
geopeek info path/to/data.gdb --layers --format json
```

### Supported formats

| Format           | Extensions                                                      |
| ---------------- | --------------------------------------------------------------- |
| Shapefile        | `.shp`                                                          |
| File Geodatabase | `.gdb`                                                          |
| Raster           | `.tif`, `.tiff`, `.jp2`, `.png`, `.jpg`, `.img`, `.vrt`, `.dem` |

### What you get

**Shapefiles** — CRS (EPSG + name), extent, feature count, geometry type, field schema

**File Geodatabases** — size, layer count, per-layer CRS, extent, feature count, geometry type, field schema

**Rasters** — size, dimensions, cell size, CRS, extent, band info (data type, nodata, statistics), driver

## Screenshots

### Raster info

![Raster info output](docs/images/info_rasters_dem.png)

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run as module
python -m geopeek info path/to/data.shp
```

## License

MIT
