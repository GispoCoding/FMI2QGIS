import logging
import uuid
from pathlib import Path
from typing import Optional

from qgis.core import QgsProject, QgsVectorLayer

from .base_loader import BaseLoader
from ..wfs import StoredQuery
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.resources import plugin_name

LOGGER = logging.getLogger(plugin_name())


class VectorLoader(BaseLoader):
    MESSAGE_CATEGORY = 'FmiVectorLoader'

    def __init__(self, description: str, download_dir: Path, wfs_url: str, wfs_version: str, sq: StoredQuery,
                 max_features: Optional[int] = None):
        """
        :param download_dir:Download directory of the output file(s)
        :param wfs_url: FMI wfs url
        :param sq: StoredQuery
        :param max_features: maximum number of features
        """
        super().__init__(description, download_dir)
        self.max_features = max_features
        self.wfs_url = wfs_url
        self.wfs_version = wfs_version
        self.sq = sq

    def run(self):
        """
        NOTE: LOGGER cannot be used in here or any methods that are called from here
        :return:
        """
        self.path_to_file, result = self._download()
        self.setProgress(100)
        return result

    @property
    def file_name(self) -> Optional[str]:
        return f'{self.sq.id.replace("::", "_")}_{uuid.uuid4()}.gml'

    def _construct_uri(self) -> str:
        url = f'{self.wfs_url}?service=WFS&version={self.wfs_version}&request=GetFeature'
        if self.max_features:
            url += f'&count={self.max_features}'
        url += f'&storedquery_id={self.sq.id}'
        url += '&' + '&'.join(
            [f'{name}={param.value}' for name, param in self.sq.parameters.items() if param.value is not None])
        return url

    def finished(self, result: bool) -> None:
        """
        This function is automatically called when the task has completed (successfully or not).

        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.

        :param result: the return value from self.run
        """
        if result and self.path_to_file.is_file():
            layer = self.vector_to_layer()
            if layer.isValid():
                # TODO: layer styling

                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(layer)

        # Error handling
        else:
            if self.exception is None:
                LOGGER.warning(tr('Task was not successful'), extra=bar_msg(tr('Task was probably cancelled by user')))
            else:
                try:
                    raise self.exception
                except QgsPluginException as e:
                    LOGGER.exception(str(e), extra=e.bar_msg)
                except Exception as e:
                    LOGGER.exception(tr('Unhandled exception occurred'), extra=bar_msg(e))

    def vector_to_layer(self) -> QgsVectorLayer:
        """
        TODO
        :return:
        """
        layer = QgsVectorLayer(str(self.path_to_file), self.file_name)
        return layer
