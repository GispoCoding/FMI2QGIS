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
from typing import Any

from ..qgis_plugin_tools.tools.settings import get_setting


@enum.unique
class Settings(enum.Enum):
    FMI_DOWNLOAD_URL = "https://opendata.fmi.fi/download"
    FMI_WFS_URL = "https://opendata.fmi.fi/wfs"
    FMI_WFS_VERSION = "2.0.0"
    FMI_WMS_URL = "https://openwms.fmi.fi/geoserver/wms"
    MESH_PROVIDER_LIB = "mdal"

    def get(self, typehint: type = str) -> Any:
        """Gets the value of the setting"""
        return get_setting(self.name, self.value, typehint)


@enum.unique
class Namespace(enum.Enum):
    WFS = "http://www.opengis.net/wfs/2.0"
    OM = "http://www.opengis.net/om/2.0"
    OMOP = "http://inspire.ec.europa.eu/schemas/omop/2.9"
    WMS = "http://www.opengis.net/wms"
    GML = "http://www.opengis.net/gml/3.2"
