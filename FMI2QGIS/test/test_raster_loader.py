#  Gispo Ltd., hereby disclaims all copyright interest in the program FMI2QGIS
#  Copyright (C) 2020 Gispo Ltd (https://www.gispo.fi/).
#
#
#  This file is part of FMI2QGIS.
#
#  FMI2QGIS is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  FMI2QGIS is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with FMI2QGIS.  If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime
from pathlib import Path

import pytest
from qgis._core import QgsSingleBandGrayRenderer

from ..qgis_plugin_tools.tools.raster_utils import set_raster_renderer_to_singleband
from ..core.processing.raster_loader import RasterLoader
from ..core.wfs import Parameter
from ..qgis_plugin_tools.tools import network
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path


@pytest.fixture
def raster_loader(tmpdir_pth, fmi_download_url) -> RasterLoader:
    return RasterLoader('', tmpdir_pth, fmi_download_url, None)


def test_download_enfuser(tmpdir_pth, fmi_download_url, enfuser_sq, extent_sm_1, monkeypatch):
    enfuser_sq.parameters['starttime'].value = datetime.strptime('2020-11-05T19:00:00Z', Parameter.TIME_FORMAT)
    enfuser_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T11:00:00Z', Parameter.TIME_FORMAT)
    enfuser_sq.parameters['bbox'].value = extent_sm_1
    enfuser_sq.parameters['param'].value = ['AQIndex']

    loader = RasterLoader('', tmpdir_pth, fmi_download_url, enfuser_sq)

    test_file = Path(plugin_test_data_path('aq_small.nc'))
    test_file_name = 'test_aq_small.nc'

    def mock_download_to_file(*args, **kwargs) -> Path:
        return test_file

    # Mocking the download
    monkeypatch.setattr(network, 'download_to_file', mock_download_to_file)

    result = loader.run()

    assert result, loader.exception
    assert loader.path_to_file == test_file
    assert loader.path_to_file.exists()
    assert loader.path_to_file.stat().st_size == test_file.stat().st_size


def test_construct_uri_enfuser(tmpdir_pth, fmi_download_url, enfuser_sq, extent_sm_1):
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


def test_raster_layer_metadata(raster_loader):
    # TODO: add more tests with different rasters
    test_file = Path(plugin_test_data_path('aq_small.nc'))
    raster_loader.path_to_file = test_file
    raster_loader.update_raster_metadata()
    metadata = raster_loader.metadata
    assert metadata == {'time_units': 'hours', 'start_time': datetime(2020, 11, 2, 15, 0), 'time_val_count': 20}


def test_raster_to_layer(raster_loader):
    test_file = Path(plugin_test_data_path('aq_small.nc'))
    raster_loader.path_to_file = test_file

    layer = raster_loader.raster_to_layer()
    assert layer.isValid()
    assert layer.name() == 'testlayer'


def test_raster_layer_styling(raster_loader, enfuser_layer_sm):
    raster_loader.metadata = {'time_units': 'hours', 'start_time': datetime(2020, 11, 2, 15, 0), 'time_val_count': 20}
    set_raster_renderer_to_singleband(enfuser_layer_sm)
    assert isinstance(enfuser_layer_sm.renderer(), QgsSingleBandGrayRenderer)
