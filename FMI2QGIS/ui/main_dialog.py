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

import logging
from pathlib import Path
from typing import Dict, List

from PyQt5.QtWidgets import QDialog, QProgressBar, QDockWidget
from qgis.core import (QgsCoordinateReferenceSystem, QgsApplication, QgsProcessingAlgRunnerTask, QgsProcessingContext,
                       QgsProcessingFeedback, QgsRasterLayer, QgsProject)
from qgis.gui import QgsExtentGroupBox, QgisInterface, QgsMapCanvas

from ..core.processing.algorithms import FmiEnfuserLoaderAlg
from ..core.processing.provider import Fmi2QgisProcessingProvider
from ..core.processing.raster_loader import RasterLoader
from ..core.products.enfuser import EnfuserNetcdfLoader
from ..core.wfs import StoredQueryFactory, StoredQuery, Parameter
from ..definitions.configurable_settings import Settings
from ..qgis_plugin_tools.tools.custom_logging import bar_msg
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack
from ..qgis_plugin_tools.tools.resources import load_ui, plugin_name

TEMPORAL_CONTROLLER = 'Temporal Controller'

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

        self.task = None
        self.sq_factory = StoredQueryFactory(Settings.FMI_WFS_URL.get(), Settings.FMI_WFS_VERSION.get())

        # TODO: do this only on demand when refreshing
        self.stored_queries: List[StoredQuery] = self.sq_factory.list_queries()

        # TODO: possibly do this after succesful loading of temporal layer
        self.__show_temporal_controller()

    def __show_temporal_controller(self):
        """Sets Temporal Controller dock widget visible if it exists"""
        dock_widget: QDockWidget
        for dock_widget in self.iface.mainWindow().findChildren(QDockWidget):
            if dock_widget.objectName() == TEMPORAL_CONTROLLER:
                dock_widget.setVisible(True)

    def __load_clicked(self):
        enfuser_id = 'fmi::forecast::enfuser::airquality::helsinki-metropolitan::grid'
        sq: StoredQuery = list(filter(lambda q: q.id == enfuser_id, self.stored_queries))[0]
        # TODO: do expanding on demand with button and build parameters dynamically based on sq.parameters
        self.sq_factory.expand(sq)

        sq.parameters['starttime'].value = self.dt_edit_start.dateTime().toPyDateTime()
        sq.parameters['endtime'].value = self.dt_edit_end.dateTime().toPyDateTime()
        sq.parameters['bbox'].value = self.extent_group_box_bbox.outputExtent()

        # TODO: as said, build this dynamically based on sq.parameters
        variables = []
        if self.chk_box_aqi.isChecked():
            variables.append('AQIndex')
        if self.chk_box_pm25.isChecked():
            variables.append('PM25Concentration')
        if self.chk_box_pm10.isChecked():
            variables.append('PM10Concentration')
        if self.chk_box_no2.isChecked():
            variables.append('NO2Concentration')
        if self.chk_box_o3.isChecked():
            variables.append('O3Concentration')
        sq.parameters['param'].value = variables

        output_path = Path(self.output_dir_select_btn.filePath())
        self.task = RasterLoader('enfuser', output_path, Settings.FMI_DOWNLOAD_URL.get(), sq)

        # noinspection PyUnresolvedReferences
        self.task.progressChanged.connect(lambda: self.progress_bar.setValue(self.task.progress()))
        # noinspection PyArgumentList
        QgsApplication.taskManager().addTask(self.task)
        self._disable_ui()

    def __load_clicked_old(self):
        # TODO: Remove
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
        # TODO: Remove
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
