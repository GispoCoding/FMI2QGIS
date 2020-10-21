from pathlib import Path
from qgis.core import QgsRasterLayer, QgsVectorLayer


def test_netcdf_rasterlayer_creation():
    # setup
    netcdf_path = Path('/home/mikael/git/FMI2QGIS/FMI2QGIS/test/test_data/test.nc')
    uri = f'NETCDF:"{netcdf_path}":time_bounds_h'
    layer_name = 'testlayer'
    provider_key = 'gdal'
    # opts: QgsRasterLayer.LayerOptions() = {}

    # test
    layer = QgsRasterLayer(str(netcdf_path), layer_name) # provider_key)

    # assertion
    print(layer.isValid())

def test_netcdf_vectorlayer_creation():
    # setup
    netcdf_path = '/home/mikael/git/FMI2QGIS/FMI2QGIS/test/test_data/test.nc'
    layer_name = 'testlayer'
    provider_key = 'ogr'
    opts: QgsVectorLayer.LayerOptions() = {}

    # test
    layer = QgsVectorLayer(netcdf_path, layer_name, provider_key)

    # assertion
    print(layer.isValid())
