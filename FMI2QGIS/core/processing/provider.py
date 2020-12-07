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

from qgis.core import QgsProcessingProvider


class Fmi2QgisProcessingProvider(QgsProcessingProvider):
    ID = 'fmi2qgis'

    def __init__(self):
        QgsProcessingProvider.__init__(self)

    def loadAlgorithms(self):
        # Add processing algorithms if there are any
        for alg in []:
            self.addAlgorithm(alg)

    def id(self) -> str:
        return Fmi2QgisProcessingProvider.ID

    def name(self):
        return self.tr('FMI2QGIS')

    def longName(self):
        return self.name()
