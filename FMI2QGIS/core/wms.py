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
import datetime
import logging
import xml.etree.ElementTree as ET  # noqa N8817
from typing import List, Optional

from qgis._core import QgsProject, QgsRasterLayer

from ..definitions.configurable_settings import Namespace
from ..qgis_plugin_tools.tools.custom_logging import bar_msg
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.network import fetch
from ..qgis_plugin_tools.tools.resources import plugin_name
from .exceptions.loader_exceptions import InvalidParameterException, WMSException

LOGGER = logging.getLogger(plugin_name())


class WMSLayer:
    """
    Inspired by https://github.com/pnuu/fmiopendata/blob/master/fmiopendata/wms.py
    licensed by GPLv3
    """

    TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

    def __init__(self, layer_elem: ET.Element) -> None:
        self.name: Optional[str] = None
        self.title: Optional[str] = None
        self.abstract: Optional[str] = None
        self.elevations: Optional[List[float]] = None
        self.default_elevation: Optional[float] = None
        self.elevation_unit: Optional[str] = None
        self.elevation_unit_symbol: Optional[str] = None
        self.start_time: Optional[datetime.datetime] = None
        self.end_time: Optional[datetime.datetime] = None
        self.t_step: Optional[int] = None
        self.time_step_uom: Optional[str] = None

        self._parse_layer(layer_elem)

    @staticmethod
    def create(layer_elem: ET.Element) -> Optional["WMSLayer"]:
        wms_layer = WMSLayer(layer_elem)

        if wms_layer.name:
            return wms_layer
        return None

    @property
    def is_temporal(self) -> bool:
        return all((self.start_time, self.end_time, self.t_step, self.time_step_uom))

    @property
    def has_elevation(self) -> bool:
        return all((self.elevations, self.default_elevation))

    def _parse_layer(self, layer_elem: ET.Element) -> None:
        for elem in layer_elem:
            tag: str = elem.tag
            if tag.endswith("Name"):
                self.name = elem.text
            elif tag.endswith("Title"):
                self.title = elem.text
            elif tag.endswith("Abstract"):
                self.abstract = elem.text
            elif tag.endswith("Dimension") and elem.attrib.get("name") == "time" and elem.text:
                start_time, end_time, step = elem.text.split("/")  # type: ignore
                self.start_time = datetime.datetime.strptime(
                    start_time, self.TIME_FORMAT
                )
                self.end_time = datetime.datetime.strptime(end_time, self.TIME_FORMAT)
                step = step.strip("PT")
                self.t_step = int(step[:-1])
                self.time_step_uom = step[-1]
            elif tag.endswith("Dimension") and elem.attrib.get("name") == "elevation" and elem.text:
                self.elevations = list(map(float, elem.text.split(",")))  # type: ignore
                self.default_elevation = float(
                    elem.attrib.get("default", self.elevations[0])
                )
                self.elevation_unit = elem.attrib.get("units", "")
                self.elevation_unit_symbol = elem.attrib.get("unitSymbol", "")

    def __str__(self) -> str:
        return str(self.name)


class WMSLayerHandler:
    def __init__(self, wms_url: str) -> None:
        self.wms_url = wms_url

    def list_wms_layers(self) -> List[WMSLayer]:
        """
        Lists all wms layers available
        """
        wms_layers: List[WMSLayer] = []
        root = ET.ElementTree(ET.fromstring(self._get_capabilities())).getroot()
        capability = root.find("{%s}Capability" % Namespace.WMS.value)
        base_layer = capability.find("{%s}Layer" % Namespace.WMS.value)  # type: ignore
        for layer in base_layer.findall("{%s}Layer" % Namespace.WMS.value):  # type: ignore # noqa E501
            wms_layer = WMSLayer.create(layer)
            if wms_layer:
                wms_layers.append(wms_layer)

        return wms_layers

    def add_to_map(
        self,
        wms_layer: WMSLayer,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        elevation: Optional[float] = None,
    ) -> None:
        """
        Add WMS layer to map
        :param wms_layer: layer to add
        :param start_time: if given, use this as start time of the layer
        :param end_time: if given, use this as end time of the layer
        :param elevation: if given, use this as elevation.
            Must be in wms_layer.elevations
        :return:
        """
        url = self._construct_qgis_url(wms_layer, start_time, end_time, elevation)
        layer = QgsRasterLayer(url, wms_layer.name, "wms")
        if layer.isValid():
            # noinspection PyArgumentList
            QgsProject.instance().addMapLayer(layer)
        else:
            raise WMSException(
                tr("Layer is not valid"),
                bar_msg=bar_msg(
                    tr("Check the layer parameters. Url is following: {}", url)
                ),
            )

    def _get_capabilities(self) -> str:
        url = f"{self.wms_url}?request=GetCapabilities"
        return fetch(url)

    def _construct_qgis_url(
        self,
        wms_layer: WMSLayer,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        elevation: Optional[float] = None,
    ) -> str:
        """
        Constructs the uri understandable by QGIS
        """
        url = (
            f"url={self.wms_url}?request%3DGetCapabilities"
            f"&layers={wms_layer.name}"
            f"&dpiMode=7"
            f"&format=image/png"
            f"&styles"
        )
        # noinspection PyArgumentList
        authid = QgsProject.instance().crs().authid()
        url += f'&crs={authid if authid != "" else "EPSG:4326"}'

        if wms_layer.is_temporal:
            url += "&allowTemporalUpdates=true&type=wmst&temporalSource=provider"
            start_time = start_time if start_time is not None else wms_layer.start_time
            assert start_time is not None
            start_time_str = start_time.strftime(wms_layer.TIME_FORMAT)
            end_time = end_time if end_time is not None else wms_layer.end_time
            assert end_time is not None
            end_time_str = end_time.strftime(wms_layer.TIME_FORMAT)
            if end_time < start_time:
                raise InvalidParameterException(tr("End time is before start time"))
            url += (
                f"&timeDimensionExtent={start_time_str}"
                f"/{end_time_str}"
                f"/PT{wms_layer.t_step}{wms_layer.time_step_uom}"
            )
        if wms_layer.has_elevation and elevation:
            if elevation in wms_layer.elevations:  # type: ignore
                url += f"&elevation={elevation}"
            else:
                LOGGER.warning(f"Ivalid elevation {elevation} for layer {wms_layer}")
        return url
