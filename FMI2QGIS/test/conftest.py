"""
This class contains fixtures and common helper function to keep the test files shorter
"""
from pathlib import Path
from typing import Callable

import pytest
from qgis.core import QgsProcessingFeedback, QgsRectangle

from ..definitions.configurable_settings import Settings
from ..qgis_plugin_tools.testing.utilities import get_qgis_app
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


@pytest.fixture
def new_project() -> None:
    """Initializes new QGIS project by removing layers and relations etc."""
    yield IFACE.newProject()


@pytest.fixture(scope='session')
def fmi_download_url() -> str:
    return Settings.fmi_download_url.value


@pytest.fixture(scope='session')
def mock_callback() -> Callable:
    return lambda _: 1


@pytest.fixture
def feedback() -> QgsProcessingFeedback:
    return LoggerProcessingFeedBack()


@pytest.fixture
def extent_sm_1() -> QgsRectangle:
    return QgsRectangle(24.96631041, 60.19950146, 24.98551092, 60.20983643)


@pytest.fixture
def tmpdir_pth(tmpdir) -> Path:
    return Path(tmpdir)
