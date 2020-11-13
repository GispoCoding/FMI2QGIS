"""
This class contains fixtures and common helper function to keep the test files shorter
"""
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
from pathlib import Path
from typing import Callable, List

import pytest
from qgis.core import QgsProcessingFeedback, QgsRectangle, QgsRasterLayer

from ..qgis_plugin_tools.tools.resources import plugin_test_data_path
from ..core.wfs import StoredQueryFactory, StoredQuery
from ..core.wms import WMSLayerHandler, WMSLayer
from ..definitions.configurable_settings import Settings
from ..qgis_plugin_tools.testing.utilities import get_qgis_app
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

# Stored query ids
ENFUSER_ID = 'fmi::forecast::enfuser::airquality::helsinki-metropolitan::grid'
AIR_QUALITY_ID = 'fmi::observations::airquality::hourly::simple'

# WMS layer ids
ANJALANKOSKI_DBZH = 'Radar:anjalankoski_dbzh'


@pytest.fixture
def new_project() -> None:
    """Initializes new QGIS project by removing layers and relations etc."""
    yield IFACE.newProject()


@pytest.fixture(scope='session')
def fmi_download_url() -> str:
    return Settings.FMI_DOWNLOAD_URL.value


@pytest.fixture(scope='session')
def wfs_url() -> str:
    return Settings.FMI_WFS_URL.value


@pytest.fixture(scope='session')
def wfs_version() -> str:
    return Settings.FMI_WFS_VERSION.value


@pytest.fixture(scope='session')
def wms_url() -> str:
    return Settings.FMI_WMS_URL.value


@pytest.fixture(scope='session')
def mock_callback() -> Callable:
    return lambda _: 1


@pytest.fixture(scope='session')
def sq_factory(wfs_url, wfs_version):
    return StoredQueryFactory(wfs_url, wfs_version)


@pytest.fixture(scope='session')
def sqs(sq_factory) -> List[StoredQuery]:
    return sq_factory.list_queries()


@pytest.fixture(scope='session')
def enfuser_sq(sqs, sq_factory) -> StoredQuery:
    sq = list(filter(lambda q: q.id == ENFUSER_ID, sqs))[0]
    sq_factory.expand(sq)
    return sq


@pytest.fixture
def enfuser_layer_sm(tmpdir_pth) -> QgsRasterLayer:
    test_file = Path(plugin_test_data_path('aq_small.nc'))
    copied_file = shutil.copy(test_file, tmpdir_pth)
    uri = f'NETCDF:{copied_file}:index_of_airquality_194'
    return QgsRasterLayer(uri, 'enfuser_test')


@pytest.fixture(scope='session')
def air_quality_sq(sqs) -> StoredQuery:
    sq = list(filter(lambda q: q.id == AIR_QUALITY_ID, sqs))[0]
    return sq


@pytest.fixture
def wms_layer_handler(wms_url, monkeypatch):
    def mocked_capabilities(handler):
        with open(plugin_test_data_path('wms_capabilities.xml')) as f:
            return f.read()

    monkeypatch.setattr(WMSLayerHandler, '_get_capabilities', mocked_capabilities)
    return WMSLayerHandler(wms_url)


@pytest.fixture
def wms_layers(wms_layer_handler) -> List[WMSLayer]:
    return wms_layer_handler.list_wms_layers()


@pytest.fixture
def test_wms_1(wms_layers):
    return list(filter(lambda l: l.name == ANJALANKOSKI_DBZH, wms_layers))[0]


@pytest.fixture
def feedback() -> QgsProcessingFeedback:
    return LoggerProcessingFeedBack()


@pytest.fixture
def extent_sm_1() -> QgsRectangle:
    return QgsRectangle(24.96631041, 60.19950146, 24.98551092, 60.20983643)


@pytest.fixture
def extent_lg_1() -> QgsRectangle:
    return QgsRectangle(21, 59.7, 31.7, 70)


@pytest.fixture
def tmpdir_pth(tmpdir) -> Path:
    return Path(tmpdir)

