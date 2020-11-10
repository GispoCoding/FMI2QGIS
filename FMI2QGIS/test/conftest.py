"""
This class contains fixtures and common helper function to keep the test files shorter
"""
from pathlib import Path
from typing import Callable, List

import pytest
from qgis.core import QgsProcessingFeedback, QgsRectangle

from ..core.wfs import StoredQueryFactory, StoredQuery
from ..definitions.configurable_settings import Settings
from ..qgis_plugin_tools.testing.utilities import get_qgis_app
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

ENFUSER_ID = 'fmi::forecast::enfuser::airquality::helsinki-metropolitan::grid'
AIR_QUALITY_ID = 'fmi::observations::airquality::hourly::simple'


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
def feedback() -> QgsProcessingFeedback:
    return LoggerProcessingFeedBack()


@pytest.fixture
def extent_sm_1() -> QgsRectangle:
    return QgsRectangle(24.96631041, 60.19950146, 24.98551092, 60.20983643)


@pytest.fixture
def tmpdir_pth(tmpdir) -> Path:
    return Path(tmpdir)
