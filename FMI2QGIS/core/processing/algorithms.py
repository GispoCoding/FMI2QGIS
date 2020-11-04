import datetime
from pathlib import Path
from typing import Dict, Any, Set

from qgis.core import (QgsProcessingContext, QgsProcessingFeedback, QgsProcessingParameterBoolean,
                       QgsProcessingParameterFolderDestination, QgsProcessingParameterExtent,
                       QgsProcessingParameterDateTime,
                       QgsCoordinateReferenceSystem, QgsRectangle)

from ..products.enfuser import EnfuserNetcdfLoader
from ...definitions.configurable_settings import Settings
from ...qgis_plugin_tools.tools.algorithm_processing import BaseProcessingAlgorithm
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.settings import get_setting


class FmiEnfuserLoaderAlg(BaseProcessingAlgorithm):
    ID = 'fmi_enfuser_loader'
    AQI = 'AQI'
    PM25 = 'PM25'
    PM10 = 'PM10'
    NO2 = 'NO2'
    O3 = 'O3'
    START_TIME = 'START_TIME'
    END_TIME = 'END_TIME'
    EXTENT = 'EXTENT'
    OUT_DIR = 'OUT_DIR'
    OUTPUT = 'OUTPUT'

    def name(self) -> str:
        return FmiEnfuserLoaderAlg.ID

    def shortHelpString(self):
        return tr('Downloads FMI Enfuser data to the directory')

    def displayName(self) -> str:
        return tr('FMI Enfuser loader')

    def group(self):
        return tr('Raster')

    def groupId(self):
        return 'raster'

    # noinspection PyMethodOverriding,PyArgumentList
    def initAlgorithm(self, config: Dict[str, Any]):
        self.addParameter(QgsProcessingParameterBoolean(self.AQI, tr('AQI (air quality index)'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(self.PM25, tr(
            'PM25 (concentration of particles smaller than 2.5 micrometres )'), defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(self.PM10, tr(
            'PM10 (concentration of particles smaller than 10 micrometres )'), defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(self.NO2, tr('NO2 (nitrogen dioxide)'), defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(self.O3, tr('O3 (ozone)'), defaultValue=False))

        self.addParameter(QgsProcessingParameterDateTime(self.START_TIME, tr('Start time')))
        self.addParameter(QgsProcessingParameterDateTime(self.END_TIME, tr('End time')))

        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, tr('Input extent')))
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUT_DIR, tr('Output directory')))

    def _round_datetime(self, dt: datetime.datetime) -> datetime.datetime:
        dt += datetime.timedelta(minutes=5)
        dt -= datetime.timedelta(minutes=dt.minute % 10,
                                 seconds=dt.second,
                                 microseconds=dt.microsecond)
        return dt

    # noinspection PyMethodOverriding
    def processAlgorithm(self, parameters: Dict[str, Any], context: QgsProcessingContext,
                         feedback: QgsProcessingFeedback):
        output_dir = Path(self.parameterAsString(parameters, self.OUT_DIR, context))

        start_time = self._round_datetime(self.parameterAsDateTime(parameters, self.START_TIME, context).toPyDateTime())
        end_time = self._round_datetime(self.parameterAsDateTime(parameters, self.END_TIME, context).toPyDateTime())

        extent_crs = QgsCoordinateReferenceSystem('EPSG:4326')
        extent: QgsRectangle = self.parameterAsExtent(parameters, self.EXTENT, context,
                                                      crs=extent_crs)

        products: Set[EnfuserNetcdfLoader.Products] = set()
        if self.parameterAsBool(parameters, self.AQI, context):
            products.add(EnfuserNetcdfLoader.Products.AirQualityIndex)
        if self.parameterAsBool(parameters, self.PM25, context):
            products.add(EnfuserNetcdfLoader.Products.PM25Concentration)
        if self.parameterAsBool(parameters, self.PM10, context):
            products.add(EnfuserNetcdfLoader.Products.PM10Concentration)
        if self.parameterAsBool(parameters, self.NO2, context):
            products.add(EnfuserNetcdfLoader.Products.NO2Concentration)
        if self.parameterAsBool(parameters, self.O3, context):
            products.add(EnfuserNetcdfLoader.Products.O3Concentration)

        fmi_download_url = get_setting(Settings.fmi_download_url.name, Settings.fmi_download_url.value, str)
        loader = EnfuserNetcdfLoader(output_dir, fmi_download_url, feedback)
        path_to_file = loader.download(products, extent, start_time, end_time)

        feedback.pushDebugInfo(f'Output file is: {path_to_file}')

        return {
            self.OUTPUT: str(path_to_file)
        }
