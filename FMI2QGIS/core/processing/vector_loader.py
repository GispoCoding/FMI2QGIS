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
import gzip
import logging
import uuid
from pathlib import Path
from typing import Optional

from osgeo import gdal, ogr
from qgis.core import QgsProject, QgsVectorLayer

from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.layers import set_temporal_settings
from ...qgis_plugin_tools.tools.resources import plugin_name
from ..exceptions.loader_exceptions import LoaderException
from ..wfs import StoredQuery
from .base_loader import BaseLoader

LOGGER = logging.getLogger(plugin_name())


class VectorLoader(BaseLoader):
    MESSAGE_CATEGORY = "FmiVectorLoader"

    def __init__(
        self,
        description: str,
        download_dir: Path,
        wfs_url: str,
        wfs_version: str,
        sq: StoredQuery,
        add_to_map: bool,
        max_features: Optional[int] = None,
    ) -> None:
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
        self.add_to_map = add_to_map

    def run(self) -> bool:
        """
        NOTE: LOGGER cannot be used in here or any methods that are called from here
        :return:
        """
        self.path_to_file, result = self._download()
        if result and self.path_to_file.is_file():
            self._update_vector_metadata()
            if all((self.metadata.time_field_idx, self.metadata.fields)):
                result = self._convert_to_spatialite()
        self.setProgress(100)
        return result

    @property
    def file_name(self) -> Optional[str]:
        return f'{self.sq.id.replace("::", "_")}_{uuid.uuid4()}.gml'

    def _process_downloaded_file(self, downloaded_file_path: Path) -> Path:
        """ Do some postprocessing after the file is downloaded"""
        output = Path(
            downloaded_file_path.parent,
            downloaded_file_path.name.replace(".", "_utf8."),
        )
        with gzip.open(downloaded_file_path, "rb") as f:
            with open(output, "w") as f2:
                f2.write(f.read().decode("utf-8"))
        return output

    def _construct_uri(self) -> str:
        url = (
            f"{self.wfs_url}?service=WFS&version={self.wfs_version}&request=GetFeature"
        )
        if self.max_features:
            url += f"&count={self.max_features}"
        url += f"&storedquery_id={self.sq.id}"
        url += "&" + "&".join(
            [
                f"{name}={param.value}"
                for name, param in self.sq.parameters.items()
                if param.value is not None
            ]
        )
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
            layer = self.vector_to_layer()
            if layer.isValid() and self.add_to_map:
                if self.metadata.time_field_idx is not None and self.sq.time_step > 0:
                    try:
                        set_temporal_settings(
                            layer, self.metadata.temporal_field, self.sq.time_step
                        )
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
                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(layer)
                self.layer_ids.add(layer.id())

        # Error handling
        else:
            if self.exception is None:
                LOGGER.warning(
                    tr("Task was not successful"),
                    extra=bar_msg(tr("Task was probably cancelled by user")),
                )
            else:
                try:
                    raise self.exception
                except QgsPluginException as e:
                    LOGGER.exception(str(e), extra=e.bar_msg)
                except Exception as e:
                    LOGGER.exception(
                        tr("Unhandled exception occurred"), extra=bar_msg(e)
                    )

    def _update_vector_metadata(self) -> None:
        """
        Update vector metadata
        """
        driver: ogr.Driver = ogr.GetDriverByName("GML")
        if driver is None:
            self.exception = LoaderException(
                tr("Your gdal/ogr does not support GML drivers"),
                bar_msg=bar_msg(tr("Please update your gdal installation")),
            )
        else:
            try:
                ds: ogr.DataSource = driver.Open(str(self.path_to_file))
                self.metadata.update_from_ogr_data_source(ds)
            finally:
                ds = None

    def _convert_to_spatialite(self) -> bool:
        """
        GML format is read-only and QGIS reads the date time fields as text.
        In order to make the layer temporal,
        that field has to be casted as datetime.
        :return: Whether conversion was successful or not
        """
        result = False
        ogr2ogr_convert_params = [
            # "-dim", "XY",
            "-nlt",
            "convert_to_linear",
            # "-oo", "REMOVE_UNUSED_LAYERS=YES",
            # "-oo", "REMOVE_UNUSED_FIELDS=YES",
            # "-oo", "EXPOSE_METADATA_LAYERS=YES",
            "-forceNullable",
        ]

        new_file = Path(
            self.path_to_file.parent,
            self.path_to_file.name.replace(".gml", ".sqlite").replace(
                ".xml", ".sqlite"
            ),
        )

        fields = ",".join(
            [
                field
                for i, field in enumerate(self.metadata.fields)  # type: ignore
                if i != self.metadata.time_field_idx
            ]
        )
        time_field = self.metadata.fields[self.metadata.time_field_idx]  # type: ignore

        options = "-f SQLite -dsco SPATIALITE=YES " + " ".join(ogr2ogr_convert_params)
        options += (
            f' -sql "SELECT {fields}, cast({time_field} as TIMESTAMP) '
            f'{time_field} FROM {self.metadata.layer_name}"'
        )

        try:
            ds: ogr.DataSource = gdal.VectorTranslate(
                str(new_file), str(self.path_to_file), options=options
            )
            if self.metadata.is_datasource_valid(ds):
                self.path_to_file = new_file
                result = True
        except Exception as e:
            self.exception = e
        finally:
            ds = None

        return result

    def vector_to_layer(self) -> QgsVectorLayer:
        """
        :return: vector layer
        """

        layer = QgsVectorLayer(str(self.path_to_file), self.sq.title)
        return layer
