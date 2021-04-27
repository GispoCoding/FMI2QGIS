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
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from qgis._core import (
    QgsMeshDataProvider,
    QgsMeshDataProviderTemporalCapabilities,
    QgsUnitTypes,
)
from qgis.core import QgsMeshLayerTemporalProperties

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


def test_mesh_conversion(mesh_loader, enfuser_sq):
    test_file = Path(plugin_test_data_path("aq_small.nc"))
    mesh_loader.sq = enfuser_sq
    mesh_loader.path_to_file = test_file
    conversion_succeeded = mesh_loader._convert_to_mesh_compatible_files()
    layers = mesh_loader._files_to_mesh_layers()

    assert conversion_succeeded
    assert len(layers) == 1
    assert {path.name for path in mesh_loader.paths_to_files.values()} == {
        "aq_small.nc"
    }

    layer = list(layers)[0]

    temp_props: QgsMeshLayerTemporalProperties = layer.temporalProperties()
    provider: QgsMeshDataProvider = layer.dataProvider()
    temp_capabilities: QgsMeshDataProviderTemporalCapabilities = (
        provider.temporalCapabilities()
    )

    assert layer.isValid()
    assert layer.name() == "FMI-ENFUSER air quality forecast as grid"
    assert layer.datasetGroupCount() == 1
    assert (
        layer.datasetGroupTreeRootItem().child(0).name()
        == "Air Quality Index near ground level in scale of 1 to 5"
    )
    assert not layer.datasetGroupTreeRootItem().child(0).isVector()

    assert temp_props.isActive()
    assert temp_props.timeExtent().begin().toPyDateTime() == datetime(
        2020, 11, 2, 15, 0
    )
    assert temp_props.timeExtent().end().toPyDateTime() == datetime(
        2020, 11, 3, 10, 0, 0
    )
    assert temp_capabilities.timeExtent() == temp_props.timeExtent()
    assert temp_capabilities.temporalUnit() == QgsUnitTypes.TemporalHours


@pytest.mark.parametrize(
    "f_name,s_time,e_time",
    [
        (
            "enfuser_all_variables",
            datetime(2020, 11, 19, 12, 0),
            datetime(2020, 11, 19, 12, 0),
        ),
        (
            "enfuser_all_variables_and_time",
            datetime(2021, 4, 25, 12, 0),
            datetime(2021, 4, 26, 12, 0),
        ),
    ],
)
def test_files_to_mesh_layers2(
    mesh_loader, enfuser_sq, tmpdir_pth, f_name, s_time, e_time
):
    test_file = Path(tmpdir_pth, f"{f_name}.nc")
    shutil.copy2(Path(plugin_test_data_path(f"{f_name}.nc")), test_file)
    mesh_loader.sq = enfuser_sq
    mesh_loader.path_to_file = test_file
    conversion_succeeded = mesh_loader._convert_to_mesh_compatible_files()
    assert conversion_succeeded
    assert {path.name for path in mesh_loader.paths_to_files.values()} == {
        f"{f_name}_index_of_airquality_194.nc",
        f"{f_name}_mass_concentration_of_nitrogen_dioxide_in_air_4902.nc",
        f"{f_name}_mass_concentration_of_ozone_in_air_4903.nc",
        f"{f_name}_mass_concentration_of_pm10_ambient_aerosol_in_air_4904.nc",
        f"{f_name}_mass_concentration_of_pm2p5_ambient_aerosol_in_air_4905.nc",
    }
    assert all(path.exists() for path in mesh_loader.paths_to_files.values())

    layers = mesh_loader._files_to_mesh_layers()

    assert len(layers) == 5

    assert {layer.name() for layer in layers} == {
        "Air Quality Index near ground level in scale of 1 to 5",
        "NO2 mass concentration",
        "O3 mass concentration",
        "PM10 mass concentration",
        "PM25 mass concentration",
    }
    for layer in layers:
        temp_props: QgsMeshLayerTemporalProperties = layer.temporalProperties()
        provider: QgsMeshDataProvider = layer.dataProvider()
        temp_capabilities: QgsMeshDataProviderTemporalCapabilities = (
            provider.temporalCapabilities()
        )

        assert layer.isValid()
        assert layer.datasetGroupCount() == 1
        assert not layer.datasetGroupTreeRootItem().child(0).isVector()

        assert temp_props.isActive()
        assert temp_props.timeExtent().begin().toPyDateTime() == s_time
        assert temp_props.timeExtent().end().toPyDateTime() == e_time
        assert temp_capabilities.timeExtent() == temp_props.timeExtent()
        assert temp_capabilities.temporalUnit() == QgsUnitTypes.TemporalHours


def test_mesh_conversion_with_grib(mesh_loader, enfuser_sq):
    test_file = Path(plugin_test_data_path("grib_data.grb2"))
    mesh_loader.sq = enfuser_sq
    mesh_loader.path_to_file = test_file
    conversion_succeeded = mesh_loader._convert_to_mesh_compatible_files()
    layers = mesh_loader._files_to_mesh_layers()

    assert conversion_succeeded
    assert len(layers) == 1
    assert {path.name for path in mesh_loader.paths_to_files.values()} == {
        "grib_data.grb2"
    }

    layer = list(layers)[0]

    temp_props: QgsMeshLayerTemporalProperties = layer.temporalProperties()
    provider: QgsMeshDataProvider = layer.dataProvider()
    temp_capabilities: QgsMeshDataProviderTemporalCapabilities = (
        provider.temporalCapabilities()
    )

    assert layer.isValid()
    assert layer.name() == "FMI-ENFUSER air quality forecast as grid"
    assert layer.datasetGroupCount() == 2
    assert (
        layer.datasetGroupTreeRootItem().child(0).name()
        == "Precipitation rate [kg/(m^2 s)]"
    )
    assert not layer.datasetGroupTreeRootItem().child(0).isVector()
    assert layer.datasetGroupTreeRootItem().child(1).name() == "Temperature [C]"
    assert not layer.datasetGroupTreeRootItem().child(1).isVector()

    assert temp_props.isActive()
    assert temp_props.timeExtent().begin().toPyDateTime() == datetime(2010, 1, 1, 0, 0)
    assert temp_props.timeExtent().end().toPyDateTime() == datetime(2070, 12, 1, 0, 0)
    assert temp_capabilities.timeExtent() == temp_props.timeExtent()
    assert temp_capabilities.temporalUnit() == QgsUnitTypes.TemporalHours
