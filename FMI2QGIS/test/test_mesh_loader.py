#  Gispo Ltd., hereby disclaims all copyright interest in the program FMI2QGIS
#  Copyright (C) 2020-2021 Gispo Ltd (https://www.gispo.fi/).
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
# type: ignore

from datetime import datetime
from pathlib import Path

import pytest

from ..core.processing.mesh_loader import MeshLoader
from ..core.wfs import Parameter
from ..qgis_plugin_tools.tools import network
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path

try:
    from qgis.core import QgsRasterLayerTemporalProperties
except ImportError:
    QgsRasterLayerTemporalProperties = None

add_to_map = True


@pytest.fixture
def mesh_loader(tmpdir_pth, fmi_download_url) -> MeshLoader:
    return MeshLoader("", tmpdir_pth, fmi_download_url, None, add_to_map)


def test_download_enfuser(
    tmpdir_pth, fmi_download_url, enfuser_sq, extent_sm_1, monkeypatch
):
    enfuser_sq.parameters["starttime"].value = datetime.strptime(
        "2020-11-05T19:00:00Z", Parameter.TIME_FORMAT
    )
    enfuser_sq.parameters["endtime"].value = datetime.strptime(
        "2020-11-06T11:00:00Z", Parameter.TIME_FORMAT
    )
    enfuser_sq.parameters["bbox"].value = extent_sm_1
    enfuser_sq.parameters["param"].value = ["AQIndex"]

    loader = MeshLoader("", tmpdir_pth, fmi_download_url, enfuser_sq, add_to_map)

    test_file = Path(plugin_test_data_path("aq_small.nc"))
    test_file_name = "test_aq_small.nc"

    def mock_download_to_file(*args, **kwargs) -> Path:
        return test_file

    # Mocking the download
    monkeypatch.setattr(network, "download_to_file", mock_download_to_file)

    result = loader.run()

    assert result, loader.exception
    assert loader.path_to_file == test_file
    assert loader.path_to_file.exists()
    assert loader.path_to_file.stat().st_size == test_file.stat().st_size


def test_construct_uri_enfuser(tmpdir_pth, fmi_download_url, enfuser_sq, extent_sm_1):
    enfuser_sq.parameters["starttime"].value = datetime.strptime(
        "2020-11-05T19:00:00Z", Parameter.TIME_FORMAT
    )
    enfuser_sq.parameters["endtime"].value = datetime.strptime(
        "2020-11-06T11:00:00Z", Parameter.TIME_FORMAT
    )
    enfuser_sq.parameters["bbox"].value = extent_sm_1
    enfuser_sq.parameters["param"].value = ["AQIndex"]
    loader = MeshLoader("", tmpdir_pth, fmi_download_url, enfuser_sq, add_to_map)
    uri = loader._construct_uri()

    assert uri == (
        "https://opendata.fmi.fi/download?"
        "producer=enfuser_helsinki_metropolitan"
        "&format=netcdf"
        "&starttime=2020-11-05T19:00:00Z"
        "&endtime=2020-11-06T11:00:00Z"
        "&bbox=24.97,60.2,24.99,60.21"
        "&param=AQIndex"
        "&origintime=2020-11-05T19:00:00Z"
    )


def test_raster_to_layer(mesh_loader, enfuser_sq):
    test_file = Path(plugin_test_data_path("aq_small.nc"))
    mesh_loader.sq = enfuser_sq
    mesh_loader.path_to_file = test_file

    layers = mesh_loader.raster_to_layers()
    assert len(layers) == 1
    layer = list(layers)[0]
    assert layer.isValid()
    assert layer.name() == "FMI-ENFUSER air quality forecast as grid"


def test_raster_to_layer2(mesh_loader):
    test_file = Path(plugin_test_data_path("enfuser_all_variables.nc"))
    mesh_loader.path_to_file = test_file
    mesh_loader.metadata.sub_dataset_dict = {
        "AQIndex": f'NETCDF:"{test_file}":index_of_airquality_194',
        "NO2Concentration": f'NETCDF:"{test_file}":mass_concentration_of_nitrogen_dioxide_in_air_4902',
        "O3Concentration": f'NETCDF:"{test_file}":mass_concentration_of_ozone_in_air_4903',
        "PM10Concentration": f'NETCDF:"{test_file}":mass_concentration_of_pm10_ambient_aerosol_in_air_4904',
        "PM25Concentration": f'NETCDF:"{test_file}":mass_concentration_of_pm2p5_ambient_aerosol_in_air_4905',
    }

    layers = mesh_loader.raster_to_layers()
    assert len(layers) == 5
    assert all((layer.isValid() for layer in layers))
    assert {layer.name() for layer in layers} == {
        "AQIndex",
        "NO2Concentration",
        "O3Concentration",
        "PM10Concentration",
        "PM25Concentration",
    }
