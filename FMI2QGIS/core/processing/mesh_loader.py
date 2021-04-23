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

import logging
from pathlib import Path

from qgis._core import QgsMeshLayer
from qgis.core import QgsProject

from ...definitions.configurable_settings import Settings
from ...qgis_plugin_tools.tools.resources import plugin_name
from ..wfs import StoredQuery
from .raster_loader import RasterLoader

try:
    from qgis.core import QgsRasterLayerTemporalProperties
except ImportError:
    QgsRasterLayerTemporalProperties = None

LOGGER = logging.getLogger(plugin_name())


class MeshLoader(RasterLoader):
    MESSAGE_CATEGORY = "FmiMeshLoader"

    def __init__(
        self,
        description: str,
        download_dir: Path,
        fmi_download_url: str,
        sq: StoredQuery,
        add_to_map: bool,
    ) -> None:
        """
        :param download_dir:Download directory of the output file(s)
        :param fmi_download_url: FMI download url
        :param sq: StoredQuery
        """
        super().__init__(description, download_dir, fmi_download_url, sq, add_to_map)

    @property
    def is_manually_temporal(self) -> bool:
        return False

    def finished(self, result: bool) -> None:
        """
        This function is automatically called when the task has completed
        (successfully or not).

        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.

        :param result: the return value from self.run
        """
        if result and self.path_to_file.is_file():
            layer = self.grid_to_mesh_layer()
            if layer.isValid() and self.add_to_map:
                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(layer)
                self.layer_ids.add(layer.id())

        # Error handling
        else:
            self._report_error(LOGGER)

    def grid_to_mesh_layer(self) -> QgsMeshLayer:
        """
        Creates QgsMeshLayer out of the grid file
        :return: QgsMeshLayer
        """
        layer_name = self.sq.title
        uri = str(self.path_to_file)
        return QgsMeshLayer(uri, layer_name, Settings.MESH_PROVIDER_LIB.get())

    def _update_raster_metadata(self) -> bool:
        """
        Update grid metadata
        :return: Whether successful or not
        """
        return True
