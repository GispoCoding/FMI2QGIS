from qgis.core import QgsProcessingProvider

from .algorithms import FmiEnfuserLoaderAlg


class Fmi2QgisProcessingProvider(QgsProcessingProvider):
    ID = 'fmi2qgis'

    def __init__(self):
        QgsProcessingProvider.__init__(self)

    def loadAlgorithms(self):
        for alg in [FmiEnfuserLoaderAlg()]:
            self.addAlgorithm(alg)

    def id(self) -> str:
        return Fmi2QgisProcessingProvider.ID

    def name(self):
        return self.tr('FMI2QGIS')

    def longName(self):
        return self.name()
