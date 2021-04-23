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

import enum
from datetime import datetime
from pathlib import Path
from typing import Set

from qgis.core import QgsRectangle

from ...core.exceptions.loader_exceptions import InvalidParameterException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.misc_utils import extent_to_bbox
from .base import BaseProduct


class EnfuserNetcdfLoader(BaseProduct):
    class Products(enum.Enum):
        AirQualityIndex = "AQIndex"
        NO2Concentration = "NO2Concentration"
        O3Concentration = "O3Concentration"
        PM10Concentration = "PM10Concentration"
        PM25Concentration = "PM25Concentration"

    # TODO: read from gdal.Dataset.GetSubDatasets()
    layer_names = {
        Products.AirQualityIndex: "index_of_airquality_194",
        Products.NO2Concentration: "mass_concentration_of_nitrogen_dioxide_in_air_4902",
        Products.O3Concentration: "mass_concentration_of_ozone_in_air_4903",
        Products.PM10Concentration: "mass_concentration_of_pm10_ambient_aerosol_in_air_4904",  # noqa E501
        Products.PM25Concentration: "mass_concentration_of_pm2p5_ambient_aerosol_in_air_4905",  # noqa E501
    }

    producer = "enfuser_helsinki_metropolitan"
    format = "netcdf"
    projection = "EPSG:4326"

    def download(  # type: ignore
        self,
        products: Set[Products],
        extent: QgsRectangle,
        start_time: datetime,
        end_time: datetime,
    ) -> Path:
        return super(EnfuserNetcdfLoader, self).download(
            products=products,  # type: ignore
            extent=extent,  # type: ignore
            start_time=start_time,  # type: ignore
            end_time=end_time,  # type: ignore
        )

    def _construct_uri(  # type: ignore
        self,
        products: Set[Products],
        extent: QgsRectangle,
        start_time: datetime,
        end_time: datetime,
    ) -> str:
        uri = super(EnfuserNetcdfLoader, self)._construct_uri()
        if not products:
            raise InvalidParameterException(tr("Got empty products"))
        if end_time < start_time:
            raise InvalidParameterException(tr("End time is before start time"))

        params = {
            "param": ":".join([product.value for product in products]),
            "bbox": extent_to_bbox(extent),
            "levels": "0",
            "origintime": start_time.strftime(self.time_format),
            "starttime": start_time.strftime(self.time_format),
            "endtime": end_time.strftime(self.time_format),
            "format": self.format,
            "projection": self.projection,
        }
        uri += "&" + "&".join([f"{name}={val}" for name, val in params.items()])
        return uri
