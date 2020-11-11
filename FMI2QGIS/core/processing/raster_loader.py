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

import logging
from pathlib import Path
from typing import Optional

from qgis.core import QgsTask, QgsRasterLayer, QgsProject

from .base_loader import BaseLoader
from ..wfs import StoredQuery
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.resources import plugin_name

LOGGER = logging.getLogger(plugin_name())


class RasterLoader(BaseLoader):
    MESSAGE_CATEGORY = 'FmiRasterLoader'

    def __init__(self, description: str, download_dir: Path, fmi_download_url: str, sq: StoredQuery):
        """
        :param download_dir:Download directory of the output file(s)
        :param fmi_download_url: FMI download url
        :param sq: StoredQuery
        """
        super().__init__(description, download_dir)
        self.url = fmi_download_url
        self.sq = sq

    def run(self) -> bool:
        """
        NOTE: LOGGER cannot be used in here or any methods that are called from here
        :return:
        """
        self.path_to_file, result = self._download()
        self.setProgress(100)
        return result

    def _construct_uri(self) -> str:
        url = self.url + f'?producer={self.sq.producer}&format={self.sq.format}'
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
            layer = self.raster_to_layer()
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

    def raster_to_layer(self) -> QgsRasterLayer:
        """
        TODO
        :return:
        """
        # TODO: change name
        layer_name = 'testlayer'
        if self.path_to_file.suffix == 'nc':
            # TODO: Check variable(s) using gdal.Dataset.GetSubDatasets()
            variable = 'index_of_airquality_194'

            uri = f'NETCDF:"{self.path_to_file}":{variable}'

        else:
            # TODO: add support for other raster formats
            uri = str(self.path_to_file)
        layer = QgsRasterLayer(uri, layer_name)
        return layer
