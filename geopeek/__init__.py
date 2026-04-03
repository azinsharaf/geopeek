# geopeek package initializer
__version__ = "0+unknown"

# Configure GDAL to use exceptions (suppresses FutureWarning in GDAL 3.x)
try:
    from osgeo import gdal

    gdal.UseExceptions()
except ImportError:
    pass
