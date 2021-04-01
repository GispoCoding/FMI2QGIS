#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import glob

from qgis_plugin_tools.infrastructure.plugin_maker import PluginMaker

'''
#################################################
# Edit the following to match the plugin
#################################################
'''

py_files = [fil for fil in glob.glob("**/*.py", recursive=True) if "test/" not in fil]
locales = ['fi']
profile = 'default'
ui_files = list(glob.glob("**/*.ui", recursive=True))
resources = list(glob.glob("**/*.qrc", recursive=True))
extra_dirs = ["resources"]
compiled_resources = []

PluginMaker(py_files=py_files, ui_files=ui_files, resources=resources, extra_dirs=extra_dirs,
            compiled_resources=compiled_resources, locales=locales, profile=profile)
