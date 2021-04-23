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


import os

from qgis.gui import QgisInterface

from .qgis_plugin_tools.infrastructure.debugging import setup_pydevd

if os.environ.get("QGIS_PLUGIN_USE_DEBUGGER") == "pydevd":
    if (
        os.environ.get("IN_TESTS", "0") != "1"
        and os.environ.get("QGIS_PLUGIN_IN_CI", "0") != "1"
    ):
        setup_pydevd()


def classFactory(iface: QgisInterface):  # noqa N802
    from .plugin import Plugin

    return Plugin(iface)
