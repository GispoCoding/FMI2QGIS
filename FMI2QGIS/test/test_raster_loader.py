from datetime import datetime
from pathlib import Path

from ..core.processing.raster_loader import RasterLoader
from ..core.wfs import Parameter
from ..qgis_plugin_tools.tools import network
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path


def test_download_enfuser(tmpdir_pth, fmi_download_url, enfuser_sq, extent_sm_1, monkeypatch):
    enfuser_sq.parameters['starttime'].value = datetime.strptime('2020-11-05T19:00:00Z', Parameter.TIME_FORMAT)
    enfuser_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T11:00:00Z', Parameter.TIME_FORMAT)
    enfuser_sq.parameters['bbox'].value = extent_sm_1
    enfuser_sq.parameters['param'].value = ['AQIndex']

    loader = RasterLoader('', tmpdir_pth, fmi_download_url, enfuser_sq)

    test_file = Path(plugin_test_data_path('aq_small.nc'))
    test_file_name = 'test_aq_small.nc'

    def mock_fetch_raw(uri: str, encoding: str = 'utf-8'):
        with open(test_file, 'rb') as f:
            return f.read(), test_file_name

    # Mocking the download
    monkeypatch.setattr(network, 'fetch_raw', mock_fetch_raw)

    result = loader.run()

    assert result, loader.exception
    assert loader.path_to_file == Path(tmpdir_pth, test_file_name)
    assert loader.path_to_file.exists()
    assert loader.path_to_file.stat().st_size == test_file.stat().st_size


def test_construct_uri_enfuser(tmpdir_pth, fmi_download_url, enfuser_sq, extent_sm_1, monkeypatch):
    enfuser_sq.parameters['starttime'].value = datetime.strptime('2020-11-05T19:00:00Z', Parameter.TIME_FORMAT)
    enfuser_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T11:00:00Z', Parameter.TIME_FORMAT)
    enfuser_sq.parameters['bbox'].value = extent_sm_1
    enfuser_sq.parameters['param'].value = ['AQIndex']
    loader = RasterLoader('', tmpdir_pth, fmi_download_url, enfuser_sq)
    uri = loader._construct_uri()

    assert uri == ('https://opendata.fmi.fi/download?'
                   'producer=enfuser_helsinki_metropolitan'
                   '&format=netcdf'
                   '&starttime=2020-11-05T19:00:00Z'
                   '&endtime=2020-11-06T11:00:00Z'
                   '&bbox=24.97,60.2,24.99,60.21'
                   '&param=AQIndex')


def test_raster_to_layer(tmpdir_pth, fmi_download_url):
    loader = RasterLoader('', tmpdir_pth, fmi_download_url, None)
    test_file = Path(plugin_test_data_path('aq_small.nc'))
    loader.path_to_file = test_file

    layer = loader.raster_to_layer()
    assert layer.isValid()
    assert layer.name() == 'testlayer'
