import logging
from pathlib import Path
from typing import Dict

from PyQt5.QtWidgets import QDialog, QProgressBar
from qgis.core import (QgsCoordinateReferenceSystem, QgsApplication, QgsProcessingAlgRunnerTask, QgsProcessingContext,
                       QgsProcessingFeedback, QgsRasterLayer, QgsProject)
from qgis.gui import QgsExtentGroupBox, QgisInterface, QgsMapCanvas

from ..core.processing.algorithms import FmiEnfuserLoaderAlg
from ..core.processing.provider import Fmi2QgisProcessingProvider
from ..core.products.enfuser import EnfuserNetcdfLoader
from ..qgis_plugin_tools.tools.custom_logging import bar_msg
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack
from ..qgis_plugin_tools.tools.resources import load_ui, plugin_name

FORM_CLASS = load_ui('main_dialog.ui')
LOGGER = logging.getLogger(plugin_name())


class MainDialog(QDialog, FORM_CLASS):

    def __init__(self, iface: QgisInterface, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.iface = iface

        self.btn_load.clicked.connect(self.__load_clicked)

        # Typing
        self.extent_group_box_bbox: QgsExtentGroupBox
        self.progress_bar: QProgressBar

        canvas: QgsMapCanvas = self.iface.mapCanvas()
        crs = canvas.mapSettings().destinationCrs()
        self.extent_group_box_bbox.setOriginalExtent(canvas.extent(), crs)
        self.extent_group_box_bbox.setCurrentExtent(canvas.extent(), crs)
        self.extent_group_box_bbox.setOutputCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
        # self.extent_group_box_bbox.setMapCanvas(canvas)

        self.progress_bar.setValue(0)

        # Context and feedback for processing algorithms
        self.context: QgsProcessingContext = QgsProcessingContext()
        self.feedback: QgsProcessingFeedback = LoggerProcessingFeedBack(use_logger=True)

        self.responsive_items = {self.btn_load}

    def __load_clicked(self):
        params = {
            FmiEnfuserLoaderAlg.AQI: (self.chk_box_aqi.isChecked()),
            FmiEnfuserLoaderAlg.PM25: (self.chk_box_pm25.isChecked()),
            FmiEnfuserLoaderAlg.PM10: (self.chk_box_pm10.isChecked()),
            FmiEnfuserLoaderAlg.NO2: (self.chk_box_no2.isChecked()),
            FmiEnfuserLoaderAlg.O3: (self.chk_box_o3.isChecked()),
            FmiEnfuserLoaderAlg.START_TIME: (self.dt_edit_start.dateTime()),
            FmiEnfuserLoaderAlg.END_TIME: (self.dt_edit_end.dateTime()),
            FmiEnfuserLoaderAlg.EXTENT: (self.extent_group_box_bbox.outputExtent()),
            FmiEnfuserLoaderAlg.OUT_DIR: self.output_dir_select_btn.filePath()
        }

        # noinspection PyArgumentList
        alg = QgsApplication.processingRegistry().algorithmById(
            f'{Fmi2QgisProcessingProvider.ID}:{FmiEnfuserLoaderAlg.ID}')

        task = QgsProcessingAlgRunnerTask(alg, params, self.context, self.feedback)

        # noinspection PyUnresolvedReferences
        task.executed.connect(self._alg_completed)

        # noinspection PyUnresolvedReferences
        task.progressChanged.connect(lambda: self.progress_bar.setValue(task.progress()))

        # noinspection PyArgumentList
        QgsApplication.taskManager().addTask(task)
        self._disable_ui()

    def _alg_completed(self, succesful: bool, results: Dict[str, any]) -> None:
        self._enable_ui()
        if succesful:
            netcdf_path = Path(results[FmiEnfuserLoaderAlg.OUTPUT])
            if self.chk_box_aqi.isChecked():
                layer = EnfuserNetcdfLoader.layer_names[EnfuserNetcdfLoader.Products.AirQualityIndex]
            else:
                layer = ''
            uri = f'NETCDF:"{netcdf_path}":{layer}'
            layer_name = 'testlayer'
            layer = QgsRasterLayer(uri, layer_name)
            if layer.isValid():
                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(layer)
        else:
            LOGGER.error(tr('Error occurred'), extra=bar_msg(tr('See log for more details')))

    def _disable_ui(self):
        for item in self.responsive_items:
            item.setEnabled(False)

    def _enable_ui(self):
        for item in self.responsive_items:
            item.setEnabled(True)
