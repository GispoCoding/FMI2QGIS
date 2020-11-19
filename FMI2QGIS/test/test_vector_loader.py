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

import shutil
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from qgis._core import QgsProject, QgsVectorLayer, QgsUnitTypes

from ..core.processing.vector_loader import VectorLoader
from ..core.wfs import Parameter
from ..qgis_plugin_tools.tools import network
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path


@pytest.fixture
def vector_loader(tmpdir_pth, wfs_url, wfs_version) -> VectorLoader:
    return VectorLoader('', tmpdir_pth, wfs_url, wfs_version, None)


def test_download_airquality(tmpdir_pth, wfs_url, wfs_version, air_quality_sq, extent_sm_1, monkeypatch):
    air_quality_sq.parameters['starttime'].value = datetime.strptime('2020-11-05T19:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T11:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['timestep'].value = 60
    air_quality_sq.parameters['bbox'].value = extent_sm_1

    loader = VectorLoader('', tmpdir_pth, wfs_url, wfs_version, air_quality_sq)

    test_file = Path(plugin_test_data_path('airquality_small.xml.gz'))
    expected_output = Path(plugin_test_data_path('airquality.sqlite'))

    def mock_download_to_file(uri, output_dir: Path, output_name: str, *args, **kwargs) -> Path:
        output = Path(output_dir, output_name)
        shutil.copy2(test_file, output)
        return output

    # Mocking the download
    monkeypatch.setattr(network, 'download_to_file', mock_download_to_file)

    # Mocking the uuid
    monkeypatch.setattr(uuid, 'uuid4', lambda: 'uuid')

    result = loader.run()

    assert result, loader.exception
    assert loader.path_to_file == Path(tmpdir_pth, 'fmi_observations_airquality_hourly_simple_uuid_utf8.sqlite')
    assert loader.path_to_file.exists()
    assert loader.path_to_file.stat().st_size == expected_output.stat().st_size


def test_construct_uri_airquality(tmpdir_pth, wfs_url, wfs_version, air_quality_sq, extent_lg_1):
    air_quality_sq.parameters['starttime'].value = datetime.strptime('2020-11-05T00:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T00:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['timestep'].value = 60
    air_quality_sq.parameters['bbox'].value = extent_lg_1
    loader = VectorLoader('', tmpdir_pth, wfs_url, wfs_version, air_quality_sq)
    uri = loader._construct_uri()
    assert uri == ('https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0'
                   '&request=GetFeature'
                   '&storedquery_id=fmi::observations::airquality::hourly::simple'
                   '&starttime=2020-11-05T00:00:00Z'
                   '&endtime=2020-11-06T00:00:00Z'
                   '&timestep=60&bbox=21.0,59.7,31.7,70.0')


def test_construct_uri_airquality2(tmpdir_pth, wfs_url, wfs_version, air_quality_sq, extent_lg_1):
    air_quality_sq.parameters['starttime'].value = datetime.strptime('2020-11-05T00:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T00:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['timestep'].value = 60
    air_quality_sq.parameters['bbox'].value = extent_lg_1
    loader = VectorLoader('', tmpdir_pth, wfs_url, wfs_version, air_quality_sq, max_features=10)
    uri = loader._construct_uri()
    assert uri == ('https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0'
                   '&request=GetFeature'
                   '&count=10'
                   '&storedquery_id=fmi::observations::airquality::hourly::simple'
                   '&starttime=2020-11-05T00:00:00Z'
                   '&endtime=2020-11-06T00:00:00Z'
                   '&timestep=60&bbox=21.0,59.7,31.7,70.0')


@pytest.mark.skip('This test fails if run together with other tests, individually works fine...')
def test_loader_with_invalid_parameters(new_project, tmpdir_pth, wfs_url, wfs_version, air_quality_sq, extent_lg_1):
    # Without starttime
    air_quality_sq.parameters['endtime'].value = datetime.strptime('2020-11-06T11:00:00Z', Parameter.TIME_FORMAT)
    air_quality_sq.parameters['timestep'].value = 60
    air_quality_sq.parameters['bbox'].value = extent_lg_1

    loader = VectorLoader('', tmpdir_pth, wfs_url, wfs_version, air_quality_sq, max_features=1)
    result = loader.run()

    assert not result
    assert loader.exception
    assert str(loader.exception) == 'Exception occurred: OperationParsingFailed'
    # noinspection PyUnresolvedReferences
    assert loader.exception.bar_msg['details'] == 'Invalid time interval! The start time is later than the end time.'


def test_vector_to_layer(tmpdir_pth, wfs_url, wfs_version, air_quality_sq, monkeypatch):
    loader = VectorLoader('', tmpdir_pth, wfs_url, wfs_version, air_quality_sq)
    test_file = Path(plugin_test_data_path('airquality.sqlite'))
    loader.path_to_file = test_file

    # Mocking the uuid
    monkeypatch.setattr(uuid, 'uuid4', lambda: 'uuid')

    layer = loader.vector_to_layer()
    assert layer.isValid()
    assert layer.name() == 'Hourly Air Quality Observations'


def test_update_vector_metadata(vector_loader):
    test_file = Path(plugin_test_data_path('airquality_small.xml'))
    vector_loader.path_to_file = test_file
    vector_loader._update_vector_metadata()
    metadata = vector_loader.metadata
    assert metadata.fields == ['gml_id', 'Time', 'ParameterName', 'ParameterValue']
    assert metadata.time_field_idx == 1
    assert metadata.layer_name == 'BsWfsElement'


def test_convert_to_spatialite(tmpdir_pth, vector_loader):
    test_file = Path(tmpdir_pth, 'airquality.gml')
    shutil.copy2(Path(plugin_test_data_path('airquality_small.xml')), test_file)
    vector_loader.path_to_file = test_file
    vector_loader.metadata.fields = ['gml_id', 'Time', 'ParameterName', 'ParameterValue']
    vector_loader.metadata.time_field_idx = 1
    vector_loader.metadata.layer_name = 'BsWfsElement'
    result = vector_loader._convert_to_spatialite()

    expected_spatialite_file = Path(tmpdir_pth, 'airquality.sqlite')

    assert result
    assert expected_spatialite_file.exists()
    assert vector_loader.path_to_file == expected_spatialite_file


def test_adding_layer_temporal_settings(new_project, vector_loader, air_quality_sq):
    test_file = Path(plugin_test_data_path('airquality.sqlite'))
    air_quality_sq.parameters['timestep'].value = 60
    vector_loader.sq = air_quality_sq
    vector_loader.path_to_file = test_file
    vector_loader.metadata.fields = ['gml_id', 'Time', 'ParameterName', 'ParameterValue']
    vector_loader.metadata.time_field_idx = 1
    vector_loader.finished(True)

    assert vector_loader.layer_ids

    layer: QgsVectorLayer = QgsProject.instance().mapLayer(list(vector_loader.layer_ids)[0])
    assert layer.isValid()

    tprops = layer.temporalProperties()
    assert tprops.isActive()
    assert tprops.startField() == 'time'
    assert tprops.fixedDuration() == 60
    assert tprops.durationUnits() == QgsUnitTypes.TemporalMinutes
