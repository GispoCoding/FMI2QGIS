import logging
from pathlib import Path
from typing import Dict, List, Set

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog, QProgressBar, QTableWidget, QTableWidgetItem, QGridLayout, QWidget, QCheckBox, \
    QLabel
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

FORM_CLASS = load_ui('main_dialog.ui')
LOGGER = logging.getLogger(plugin_name())


class MainDialog(QDialog, FORM_CLASS):

    def __init__(self, iface: QgisInterface, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.iface = iface

        self.btn_load.clicked.connect(self.__load_wfs_layer)
        self.btn_refresh.clicked.connect(self.__refresh_stored_wfs_queries)
        self.btn_select.clicked.connect(self.__select_wfs_layer)

        # Typing
        self.extent_group_box_bbox: QgsExtentGroupBox
       # self.group_box_wfs_params
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
        self.stored_queries: List[StoredQuery] = []

        #populating dynamically the parameters of main dialog
        self.grid: QGridLayout
        self.parameter_rows: Dict[str, Set[QWidget]] = {}
        #self.selected_stored_query: StoredQuery


    def __refresh_stored_wfs_queries(self):

        self.stored_queries: List[StoredQuery] = self.sq_factory.list_queries()
        self.tbl_wdgt_stored_queries: QTableWidget
        self.tbl_wdgt_stored_queries.setRowCount(len( self.stored_queries))
        self.tbl_wdgt_stored_queries.setColumnCount(3)

        for i, sq in enumerate(self.stored_queries):
            self.tbl_wdgt_stored_queries.setItem(i, 0, QTableWidgetItem(sq.title))
            abstract_item = QTableWidgetItem(sq.abstract)
            abstract_item.setToolTip(sq.abstract)
            self.tbl_wdgt_stored_queries.setItem(i, 1,  abstract_item)
            id_item = QTableWidgetItem(sq.id)
            id_item.setToolTip(sq.id)
            self.tbl_wdgt_stored_queries.setItem(i, 2, id_item)

            #self.tbl_wdgt_stored_queries.setItem(i, 1, QTableWidgetItem(sq.na))

        print('row count: ', self.tbl_wdgt_stored_queries.rowCount())
        print('last stored query', self.stored_queries[len(self.stored_queries) - 1].title)

        rows = len( self.stored_queries)
        print('number of stored queries: ', rows)
        #for stored_query in self.stored_queries:
        #    self.table.setItem(stored_query.title)
        #    print(stored_query.title)

    def __select_wfs_layer(self):
        #self.grid: QGridLayout
        #self.parameter_rows: Dict[str, Set[QWidget]] = {}
        self.tbl_wdgt_stored_queries: QTableWidget
        indexes = self.tbl_wdgt_stored_queries.selectedIndexes()
        if not indexes:
            print("select something")
            return
        self.selected_stored_query = self.stored_queries[indexes[0].row()]
        print(self.selected_stored_query.title)
        #return selected_stored_query

        for widget_set in self.parameter_rows.values():
            for widget in widget_set:
                self.grid.removeWidget(widget)
                widget = None
        self.parameter_rows = {}

        row_idx = -1
        self.extent_group_box_bbox.setEnabled(False)
        for param_name, parameter in self.selected_stored_query.parameters.items():
            widgets = set()
            #print(param_name, parameter)
            if parameter.type == QVariant.Rect:
                self.parameter_rows[param_name] = widgets
                self.extent_group_box_bbox.setEnabled(True)
                continue
            row_idx += 1
            widget: QWidget = widget_for_field(parameter.type)

            if parameter.type == QVariant.StringList:
                if parameter.has_variables():
                    widget = QVLayout
                    for variable in parameter.variables:
                        box = QCheckBox(variable.alias)
                        box.setToolTip(variable.label)
                        widgets.add(box)

                        widget.addWidget(box)

            # TODO: all others
            else:
                LOGGER.error(tr('Unknown parameter type'),
                             extra=bar_msg(tr('With parameter"{}": {}', param_name, parameter.type)))
                return
            label = QLabel(text=parameter.name)
            label.setToolTip(parameter.abstract)

            widgets.update({label, widget})

            self.grid.addItem(label, 1, 1)
            self.grid.addItem(widget, 1, 2)
            self.parameter_rows[param_name] = widgets

        for param_name, widgets in self.parameter_rows.items():
            parameter = self.selected_stored_query.parameters[param_name]
            if parameter.type == QVariant.Rect:
                # TODO: ota extent
                pass
            else:
                values = []
                for widget in widgets:
                    # Ohita label, muut valideja
                    # Jos vain yksi arvo -->
                    # ?     parameter.value = value_for_widget(widget)
                    # jos parameter.type datetime wiget.dateTime().toPyDateTime()
                    # jos parameter.has_variables()
                    parameter.value = [widget.text() for widget in widgets if widget.isChecked()]


    def __load_wfs_layer(self):
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
        self.task.taskTerminated.connect(self._enable_ui)
        self.task.taskCompleted.connect(self._enable_ui)

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
