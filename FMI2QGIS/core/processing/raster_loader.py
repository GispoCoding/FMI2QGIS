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
from typing import Set

import gdal
from qgis.core import QgsProject, QgsRasterLayer

from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import (
    QgsPluginException,
    QgsPluginNotImplementedException,
)
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.raster_layers import (
    set_fixed_temporal_range,
    set_raster_renderer_to_singleband,
)
from ...qgis_plugin_tools.tools.resources import plugin_name
from ..wfs import StoredQuery
from .base_loader import BaseLoader

try:
    from qgis.core import QgsRasterLayerTemporalProperties
except ImportError:
    QgsRasterLayerTemporalProperties = None

LOGGER = logging.getLogger(plugin_name())


class RasterLoader(BaseLoader):
    MESSAGE_CATEGORY = "FmiRasterLoader"

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
        super().__init__(description, download_dir)
        self.url = fmi_download_url
        self.sq = sq
        self.add_to_map = add_to_map

    @property
    def is_manually_temporal(self) -> bool:
        return self.metadata.is_temporal

    def run(self) -> bool:
        """
        NOTE: LOGGER cannot be used in here or any methods that are called from here
        :return:
        """
        self.path_to_file, result = self._download()
        if result and self.path_to_file.is_file():
            result = self._update_raster_metadata()
        self.setProgress(100)
        return result

    def _construct_uri(self) -> str:
        url = self.url + f"?producer={self.sq.producer}"
        if (
            "format" not in self.sq.parameters
            or self.sq.parameters["format"].value is None
        ):
            url += f"&format={self.sq.format}"
        url += "&" + "&".join(
            [
                f"{name}={param.value}"
                for name, param in self.sq.parameters.items()
                if param.value is not None
            ]
        )
        if "starttime" in self.sq.parameters and "levels" in self.sq.parameters:
            url += f'&origintime={self.sq.parameters["starttime"].value}'
        return url

    def finished(self, result: bool) -> None:
        """
        This function is automatically called when the task has completed
        (successfully or not).

        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.

        :param result: the return value from self.run
        """
        if result and self.path_to_file.is_file():
            layers = self.raster_to_layers()
            for layer in layers:
                if layer.isValid() and self.add_to_map:
                    # noinspection PyArgumentList
                    QgsProject.instance().addMapLayer(layer)
                    if self.metadata.is_temporal:
                        set_raster_renderer_to_singleband(layer, 1)
                        try:
                            set_fixed_temporal_range(layer, self.metadata.time_range)
                        except AttributeError:
                            LOGGER.warning(
                                tr(
                                    "Your QGIS version does not "
                                    "support temporal properties"
                                ),
                                extra=bar_msg(
                                    tr(
                                        "Please update your QGIS to "
                                        "support Temporal Controller"
                                    )
                                ),
                            )

                    self.layer_ids.add(layer.id())

        # Error handling
        else:
            if self.exception is None:
                self._report_error(LOGGER)

    def raster_to_layers(self) -> Set[QgsRasterLayer]:
        """
        Creates QgsRasterLayers out of raster file
        :return: Set of QgsRasterLayers
        """
        # TODO: add support for other raster formats
        layers: Set[QgsRasterLayer] = set()
        if self.metadata.sub_dataset_dict is not None:
            for layer_name, layer_uri in self.metadata.sub_dataset_dict.items():
                layers.add(QgsRasterLayer(layer_uri, layer_name))
        else:
            layer_name = self.sq.title
            uri = str(self.path_to_file)
            layers.add(QgsRasterLayer(uri, layer_name))
        return layers

    def _update_raster_metadata(self) -> bool:
        """
        Update raster metadata
        :return: Whether successful or not
        """
        try:
            ds: gdal.Dataset = gdal.Open(str(self.path_to_file))
            sub_datasets = ds.GetSubDatasets()
            if sub_datasets:
                sub_dataset_parameters = [
                    param
                    for param in self.sq.parameters.values()
                    if param.has_variables()
                ]
                if not sub_dataset_parameters or not sub_dataset_parameters[0].value:
                    self.exception = QgsPluginNotImplementedException(
                        tr("This part of the plugin is not implemented yet. Code 1"),
                        bar_msg=bar_msg(tr("Please send log file to Github as issue")),
                    )
                    return False
                sub_dataset_parameter = sub_dataset_parameters[0]
                sub_dataset_variables = sub_dataset_parameter.value.split(",")
                if len(sub_datasets) == len(sub_dataset_variables) + 1:
                    sub_datasets = [
                        sub_dataset
                        for sub_dataset in sub_datasets
                        if not sub_dataset[0].endswith("time_bounds_h")
                    ]
                if len(sub_datasets) == len(sub_dataset_variables):
                    self.metadata.sub_dataset_dict = {
                        sub_dataset_variables[i]: sub_datasets[i][0]
                        for i in range(len(sub_datasets))
                    }
                else:
                    self.exception = QgsPluginNotImplementedException(
                        tr("This part of the plugin is not implemented yet. Code 2"),
                        bar_msg=bar_msg(tr("Please send log file to Github as issue")),
                    )
                    return False

                first_path = sub_datasets[0][0]
                ds: gdal.Dataset = gdal.Open(first_path)  # type: ignore

            self.metadata.update_from_gdal_metadata(ds.GetMetadata())
        finally:
            ds = None

        return True
