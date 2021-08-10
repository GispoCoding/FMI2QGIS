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
from typing import Dict, Optional, Set

from osgeo import gdal
from qgis.core import QgsMeshLayer, QgsProject

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
        self.paths_to_files: Dict[str, Path] = {}

    @property
    def is_manually_temporal(self) -> bool:
        return False

    def run(self) -> bool:
        """
        NOTE: LOGGER cannot be used in here or any methods that are called from here
        :return:
        """
        self.path_to_file, result = self._download()
        if result and self.path_to_file.is_file():
            result = self._convert_to_mesh_compatible_files()
        self.setProgress(100)
        return result

    def _convert_to_mesh_compatible_files(self) -> bool:
        """
        Some Netcdf files from FMI have "time_bounds_h" variable as the first
        subdataset. QgsMeshLayer seems to expect that the first dataset is spatial
        and fails to show mesh layer if that is not the case. Also some FMI layers
        have temporal dimension called "time_h". QgsMeshLayer seems to work only
        with temporal variables called "time" so metadata has to be updated.

        :return: Whether conversion was successful or not
        """
        result = True
        try:
            ds: Optional[gdal.Dataset]
            try:
                ds = gdal.Open(str(self.path_to_file))
                sub_datasets = [
                    sub_ds
                    for sub_ds, _ in ds.GetSubDatasets()
                    if "time_bounds_" not in sub_ds
                ]
            finally:
                ds = None

            if sub_datasets:
                self._log("Converting files to be mesh compatible")
                format = "NETCDF"
                driver = gdal.GetDriverByName(format)

                for sub_ds_name in sub_datasets:
                    var_name = sub_ds_name.split(":")[-1]
                    long_name = var_name
                    dst_filename = str(self.path_to_file).replace(
                        ".nc", f"_{var_name}.nc"
                    )
                    src_ds: Optional[gdal.Dataset]
                    try:
                        src_ds = gdal.Open(sub_ds_name)
                        assert src_ds

                        metadata = src_ds.GetMetadata()
                        src_ds.SetMetadata(self.metadata.fix_gdal_metadata(metadata))

                        for b in range(1, src_ds.RasterCount + 1):
                            band = src_ds.GetRasterBand(b)
                            metadata = band.GetMetadata()
                            if b == 1:
                                long_name = metadata.get("long_name", long_name)
                            band.SetMetadata(self.metadata.fix_gdal_metadata(metadata))

                        # Output to new format
                        dst_ds = driver.CreateCopy(dst_filename, src_ds, 0)

                        # Properly close the datasets to flush to disk
                        dst_ds = None  # noqa: F841
                        src_ds = None
                    finally:
                        ds = None
                    self.paths_to_files[long_name] = Path(dst_filename)

            else:
                layer_name = self.sq.title
                self.paths_to_files[layer_name] = self.path_to_file
        except Exception as e:
            self.exception = e
            result = False

        self._log(f"Files are: {self.paths_to_files}")

        return result

    def finished(self, result: bool) -> None:
        """
        This function is automatically called when the task has completed
        (successfully or not).

        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.

        :param result: the return value from self.run
        """
        if result and self.path_to_file.is_file():
            layers = self._files_to_mesh_layers()
            for layer in layers:
                if layer.isValid() and self.add_to_map:
                    # noinspection PyArgumentList
                    QgsProject.instance().addMapLayer(layer)
                    self.layer_ids.add(layer.id())

        # Error handling
        else:
            self._report_error(LOGGER)

    def _files_to_mesh_layers(self) -> Set[QgsMeshLayer]:
        """
        Creates QgsMeshLayer out of the grid file(s)
        :return: Set of QgsMeshLayers
        """
        layers: Set[QgsMeshLayer] = {
            QgsMeshLayer(str(file_path), name, Settings.MESH_PROVIDER_LIB.get())
            for name, file_path in self.paths_to_files.items()
        }
        for layer in layers:
            layer.temporalProperties().setIsActive(True)
        return layers
