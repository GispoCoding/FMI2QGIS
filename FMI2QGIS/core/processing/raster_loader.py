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
from datetime import datetime
from pathlib import Path
from typing import Dict

import gdal
from qgis.core import (QgsRasterLayer, QgsProject, QgsRasterDataProvider, QgsSingleBandGrayRenderer,
                       QgsContrastEnhancement, QgsRasterBandStats)

from .base_loader import BaseLoader
from ..wfs import StoredQuery
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.raster_utils import set_raster_renderer_to_singleband
from ...qgis_plugin_tools.tools.resources import plugin_name

NETCDF_DIM_EXTRA = 'NETCDF_DIM_EXTRA'

LOGGER = logging.getLogger(plugin_name())


class RasterLoader(BaseLoader):
    MESSAGE_CATEGORY = 'FmiRasterLoader'
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'  # 2020-11-02 15:00:00

    def __init__(self, description: str, download_dir: Path, fmi_download_url: str, sq: StoredQuery):
        """
        :param download_dir:Download directory of the output file(s)
        :param fmi_download_url: FMI download url
        :param sq: StoredQuery
        """
        super().__init__(description, download_dir)
        self.url = fmi_download_url
        self.sq = sq
        self.metadata: Dict[str] = {}  # TODO: use class maybe?

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
            self.update_raster_metadata()
            layer = self.raster_to_layer()
            if layer.isValid():
                # TODO: layer styling

                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(layer)
                if self.metadata.get('time_val_count', 0) and layer.bandCount() > 1:
                    set_raster_renderer_to_singleband(layer, 1)

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
            variable = 'index_of_airquality_194'

            uri = f'NETCDF:"{self.path_to_file}":{variable}'

        else:
            # TODO: add support for other raster formats
            uri = str(self.path_to_file)
        layer = QgsRasterLayer(uri, layer_name)
        return layer

    def update_raster_metadata(self) -> None:
        """
        Update raster metadata
        """
        metadata = {}
        try:
            ds: gdal.Dataset = gdal.Open(str(self.path_to_file))
            sub_datasets = ds.GetSubDatasets()
            if sub_datasets:
                # TODO: Check variable(s) and add to metadata
                first_path = sub_datasets[0][0]  #
                ds: gdal.Dataset = gdal.Open(first_path)

            ds_metadata: Dict[str, str] = ds.GetMetadata()

            if NETCDF_DIM_EXTRA in ds_metadata:
                # Is netcdf file and has extra dimensions (probably time)
                for dimension in ds_metadata[NETCDF_DIM_EXTRA].strip('{').strip('}').split(','):
                    dim_def = ds_metadata.get(f'NETCDF_DIM_{dimension}_DEF', '').strip('{').strip('}').split(',')
                    dim_units = ds_metadata.get(f'{dimension}#units', '')
                    if dimension == 'time' and dim_def:
                        time_units, start_time = dim_units.split(' since ')  # eg. hours since 2020-10-05 18:00:00
                        metadata['time_units'] = time_units
                        metadata['start_time'] = datetime.strptime(start_time, self.TIME_FORMAT) if start_time else None
                        metadata['time_val_count'] = int(dim_def[0]) if dim_def else None
        finally:
            ds = None
        self.metadata = metadata

