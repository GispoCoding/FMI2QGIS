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

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PyQt5.QtCore import QDateTime, Qt
from qgis._core import QgsRasterLayer, QgsProject, QgsRasterLayerTemporalProperties, QgsDateTimeRange

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

    test_file = Path(plugin_test_data_path('enfuser_aq.nc'))
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
    test_file = Path(plugin_test_data_path('enfuser_aq.nc'))
    raster_loader.path_to_file = test_file
    result = raster_loader._update_raster_metadata()
    metadata = raster_loader.metadata
    assert result
    assert metadata.time_step == timedelta(hours=1)
    assert metadata.start_time == datetime(2020, 11, 2, 15, 0)
    assert metadata.num_of_time_steps == 20
    assert metadata.is_temporal
    assert metadata.time_range.begin().toPyDateTime() == datetime(2020, 11, 2, 15, 0)
    assert metadata.time_range.end().toPyDateTime() == datetime(2020, 11, 3, 10, 0, 1)


def test_raster_layer_metadata2(raster_loader, enfuser_sq):
    raster_loader.sq = enfuser_sq
    enfuser_sq.parameters['param'].value = ['AQIndex', 'NO2Concentration', 'O3Concentration', 'PM10Concentration',
                                            'PM25Concentration']
    test_file = Path(plugin_test_data_path('enfuser_all_variables.nc'))
    raster_loader.path_to_file = test_file
    result = raster_loader._update_raster_metadata()
    metadata = raster_loader.metadata
    assert result
    assert metadata.time_step == timedelta(hours=1)
    assert metadata.start_time == datetime(2020, 11, 19, 12, 0)
    assert metadata.num_of_time_steps == 1
    assert metadata.is_temporal
    assert metadata.time_range.begin().toPyDateTime() == datetime(2020, 11, 19, 12, 0)
    assert metadata.time_range.end().toPyDateTime() == datetime(2020, 11, 19, 12, 0, 1)
    assert metadata.sub_dataset_dict == {
        'AQIndex': f'NETCDF:"{test_file}":index_of_airquality_194',
        'NO2Concentration': f'NETCDF:"{test_file}":mass_concentration_of_nitrogen_dioxide_in_air_4902',
        'O3Concentration': f'NETCDF:"{test_file}":mass_concentration_of_ozone_in_air_4903',
        'PM10Concentration': f'NETCDF:"{test_file}":mass_concentration_of_pm10_ambient_aerosol_in_air_4904',
        'PM25Concentration': f'NETCDF:"{test_file}":mass_concentration_of_pm2p5_ambient_aerosol_in_air_4905'}


def test_raster_layer_metadata3(raster_loader, enfuser_sq):
    raster_loader.sq = enfuser_sq
    enfuser_sq.parameters['param'].value = ['NO2Concentration', 'O3Concentration']
    test_file = Path(plugin_test_data_path('enfuser_no2_o3.nc'))
    raster_loader.path_to_file = test_file
    result = raster_loader._update_raster_metadata()
    metadata = raster_loader.metadata
    assert result
    assert metadata.time_step == timedelta(hours=1)
    assert metadata.start_time == datetime(2020, 11, 19, 17, 0)
    assert metadata.num_of_time_steps == 2
    assert metadata.is_temporal
    assert metadata.time_range.begin().toPyDateTime() == datetime(2020, 11, 19, 17, 0)
    assert metadata.time_range.end().toPyDateTime() == datetime(2020, 11, 19, 18, 0, 1)
    assert metadata.sub_dataset_dict == {
        'NO2Concentration': f'NETCDF:"{test_file}":mass_concentration_of_nitrogen_dioxide_in_air_4902',
        'O3Concentration': f'NETCDF:"{test_file}":mass_concentration_of_ozone_in_air_4903'}


def test_raster_to_layer(raster_loader, enfuser_sq):
    test_file = Path(plugin_test_data_path('enfuser_aq.nc'))
    raster_loader.sq = enfuser_sq
    raster_loader.path_to_file = test_file

    layers = raster_loader.raster_to_layers()
    assert len(layers) == 1
    layer = list(layers)[0]
    assert layer.isValid()
    assert layer.name() == 'FMI-ENFUSER air quality forecast as grid'


def test_raster_to_layer2(raster_loader):
    test_file = Path(plugin_test_data_path('enfuser_all_variables.nc'))
    raster_loader.path_to_file = test_file
    raster_loader.metadata.sub_dataset_dict = {
        'AQIndex': f'NETCDF:"{test_file}":index_of_airquality_194',
        'NO2Concentration': f'NETCDF:"{test_file}":mass_concentration_of_nitrogen_dioxide_in_air_4902',
        'O3Concentration': f'NETCDF:"{test_file}":mass_concentration_of_ozone_in_air_4903',
        'PM10Concentration': f'NETCDF:"{test_file}":mass_concentration_of_pm10_ambient_aerosol_in_air_4904',
        'PM25Concentration': f'NETCDF:"{test_file}":mass_concentration_of_pm2p5_ambient_aerosol_in_air_4905'}

    layers = raster_loader.raster_to_layers()
    assert len(layers) == 5
    assert all((layer.isValid() for layer in layers))
    assert {layer.name() for layer in layers} == {'AQIndex', 'NO2Concentration', 'O3Concentration', 'PM10Concentration',
                                                  'PM25Concentration'}


def test_adding_layer_temporal_settings(new_project, raster_loader, enfuser_sq):
    test_file = Path(plugin_test_data_path('enfuser_no2_o3.nc'))
    raster_loader.metadata.sub_dataset_dict = {
        'NO2Concentration': f'NETCDF:"{test_file}":mass_concentration_of_nitrogen_dioxide_in_air_4902',
        'O3Concentration': f'NETCDF:"{test_file}":mass_concentration_of_ozone_in_air_4903'}
    raster_loader.metadata.time_step = timedelta(hours=1)
    raster_loader.metadata.start_time = datetime(2020, 11, 19, 17, 0)
    raster_loader.metadata.num_of_time_steps = 2
    raster_loader.sq = enfuser_sq
    raster_loader.path_to_file = test_file
    raster_loader.finished(True)

    assert len(raster_loader.layer_ids) == 2

    for layer_id in raster_loader.layer_ids:
        layer: QgsRasterLayer = QgsProject.instance().mapLayer(layer_id)

        assert layer.isValid()
        tprops: QgsRasterLayerTemporalProperties = layer.temporalProperties()
        assert tprops.isActive()
        assert tprops.fixedTemporalRange() == QgsDateTimeRange(QDateTime(2020, 11, 19, 17, 0, 0, 0, Qt.TimeSpec(1)),
                                                               QDateTime(2020, 11, 19, 18, 0, 1, 0, Qt.TimeSpec(1)))
