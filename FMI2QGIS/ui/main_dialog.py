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
from typing import Dict, List, Optional, Set

from PyQt5.QtCore import QVariant, pyqtSignal, QDateTime
from PyQt5.QtWidgets import (QDialog, QProgressBar, QTableWidget, QTableWidgetItem, QGridLayout, QWidget, QCheckBox,
                             QLabel, QVBoxLayout, QComboBox, QLineEdit, QSpinBox)
from qgis.core import (QgsCoordinateReferenceSystem, QgsApplication, QgsProcessingContext,
                       QgsProcessingFeedback, )
from qgis.gui import QgsExtentGroupBox, QgisInterface, QgsMapCanvas, QgsDoubleSpinBox, QgsDateTimeEdit, QgsFilterLineEdit

from ..core.processing.base_loader import BaseLoader
from ..core.processing.raster_loader import RasterLoader
from ..core.processing.vector_loader import VectorLoader
from ..core.wfs import StoredQueryFactory, StoredQuery
from ..definitions.configurable_settings import Settings
from ..qgis_plugin_tools.tools.custom_logging import bar_msg
from ..qgis_plugin_tools.tools.fields import widget_for_field, value_for_widget
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack
from ..qgis_plugin_tools.tools.resources import load_ui, plugin_name

FORM_CLASS = load_ui('main_dialog.ui')
LOGGER = logging.getLogger(plugin_name())


class MainDialog(QDialog, FORM_CLASS):
    temporal_layers_added = pyqtSignal(set)

    def __init__(self, iface: QgisInterface, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.iface = iface

        self.btn_load.clicked.connect(self.__load_wfs_layer)
        self.btn_select.clicked.connect(self.__select_wfs_layer)
        self.btn_clear_search.clicked.connect(self.__clear_stored_wfs_queries_search)
        self.btn_search.clicked.connect(self.__search_stored_wfs_layers)

        # Typing
        self.extent_group_box_bbox: QgsExtentGroupBox
        self.progress_bar: QProgressBar
        self.search_ln_ed: QgsFilterLineEdit

        canvas: QgsMapCanvas = self.iface.mapCanvas()
        crs = canvas.mapSettings().destinationCrs()
        self.extent_group_box_bbox.setOriginalExtent(canvas.extent(), crs)
        self.extent_group_box_bbox.setCurrentExtent(canvas.extent(), crs)
        self.extent_group_box_bbox.setOutputCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
        # self.extent_group_box_bbox.setMapCanvas(canvas)
        self.chk_box_add_to_map: QCheckBox

        self.progress_bar.setValue(0)

        # Context and feedback for processing algorithms
        self.context: QgsProcessingContext = QgsProcessingContext()
        self.feedback: QgsProcessingFeedback = LoggerProcessingFeedBack(use_logger=True)

        self.responsive_items = {self.btn_load, self.btn_select, self.chk_box_add_to_map, self.btn_clear_search,
                                 self.btn_search}

        self.task: Optional[BaseLoader] = None
        self.sq_factory = StoredQueryFactory(Settings.FMI_WFS_URL.get(), Settings.FMI_WFS_VERSION.get())
        self.stored_queries: List[StoredQuery] = []
        self.selected_stored_query: Optional[StoredQuery] = None

        # populating dynamically the parameters of main dialog
        self.grid: QGridLayout
        self.parameter_rows: Dict[str, Set[QWidget]] = {}

        # populating the layer list when opening
        self.__refresh_stored_wfs_queries()

    def __refresh_stored_wfs_queries(self):

        self.stored_queries: List[StoredQuery] = self.sq_factory.list_queries()
        self.tbl_wdgt_stored_queries: QTableWidget
        self.tbl_wdgt_stored_queries.setRowCount(len(self.stored_queries))
        self.tbl_wdgt_stored_queries.setColumnCount(3)

        for i, sq in enumerate(self.stored_queries):
            self.tbl_wdgt_stored_queries.setItem(i, 0, QTableWidgetItem(sq.title))
            abstract_item = QTableWidgetItem(sq.abstract)
            abstract_item.setToolTip(sq.abstract)
            self.tbl_wdgt_stored_queries.setItem(i, 1, abstract_item)
            id_item = QTableWidgetItem(sq.id)
            id_item.setToolTip(sq.id)
            self.tbl_wdgt_stored_queries.setItem(i, 2, id_item)

    def __search_stored_wfs_layers(self, search_user_input):
        pass

    def __clear_stored_wfs_queries_search(self):
        #self.search_ln_ed.
        pass



    def __select_wfs_layer(self):

        self.tbl_wdgt_stored_queries: QTableWidget
        indexes = self.tbl_wdgt_stored_queries.selectedIndexes()
        if not indexes:
            LOGGER.warning(tr('Could not execute select'), extra=bar_msg(tr('Data source must be selected first!')))
            return
        self.selected_stored_query = self.stored_queries[indexes[0].row()]
        LOGGER.info(tr('Selected query id: {}', self.selected_stored_query.id))
        self.sq_factory.expand(self.selected_stored_query)

        for widget_set in self.parameter_rows.values():
            for widget in widget_set:
                if isinstance(widget, QVBoxLayout):
                    self.grid.removeItem(widget)
                else:
                    self.grid.removeWidget(widget)
                    widget.hide()
                widget.setParent(None)
                widget = None
        self.parameter_rows = {}

        row_idx = -1
        self.extent_group_box_bbox.setEnabled(False)
        for param_name, parameter in self.selected_stored_query.parameters.items():
            possible_values = parameter.possible_values
            widgets = set()
            if parameter.type in (QVariant.Rect, QVariant.RectF):
                self.parameter_rows[param_name] = widgets
                self.extent_group_box_bbox.setEnabled(True)
                continue
            row_idx += 1
            widget: QWidget = widget_for_field(parameter.type)
            if isinstance(widget, QComboBox) or isinstance(widget, QSpinBox) or isinstance(widget, QgsDoubleSpinBox):
                widget = QLineEdit()
                if possible_values:
                    if len(possible_values) == 1:
                        widget.setText(possible_values[0])
                    else:
                        widget = QComboBox()
                        widget.addItems(possible_values)
                        widget.setEditable(True)

            if isinstance(widget, QgsDateTimeEdit) and possible_values:
                widget.setDateTimeRange(min(possible_values), max(possible_values))
                if param_name.startswith('end'):
                    widget.setDateTime(max(possible_values))
                else:
                    widget.setDateTime(min(possible_values))
                if len(possible_values) == 1:
                    widget.setEnabled(False)

            widget.setToolTip(parameter.abstract)

            if parameter.type == QVariant.StringList:
                if parameter.has_variables():
                    widget = QVBoxLayout()
                    widget.addStretch(1)
                    for variable in parameter.variables:
                        box = QCheckBox(text=variable.alias)
                        box.setToolTip(variable.label)
                        widgets.add(box)
                        widget.addWidget(box)
                        LOGGER.info(tr('Variables: {}', variable.alias))

            # TODO: all others
            if widget is None:
                LOGGER.error(tr('Unknown parameter type'),
                             extra=bar_msg(tr('With parameter"{}": {}', param_name, parameter.type)))
                return
            label = QLabel(text=parameter.name)
            label.setToolTip(parameter.abstract)

            widgets.update({label, widget})

            self.grid.addWidget(label, row_idx, 1)
            if isinstance(widget, QVBoxLayout):
                self.grid.addLayout(widget, row_idx, 2)
            else:
                self.grid.addWidget(widget, row_idx, 2)
            self.parameter_rows[param_name] = widgets

    def __load_wfs_layer(self):

        if self.selected_stored_query:
            for param_name, widgets in self.parameter_rows.items():
                parameter = self.selected_stored_query.parameters[param_name]
                if parameter.type in (QVariant.Rect, QVariant.RectF):
                    parameter.value = self.extent_group_box_bbox.outputExtent()
                else:
                    values = []
                    for widget in widgets:
                        if isinstance(widget, QLabel) or isinstance(widget, QVBoxLayout):
                            continue
                        if parameter.type == QVariant.DateTime:
                            parameter.value = widget.dateTime().toPyDateTime()
                            break
                        elif parameter.has_variables():
                            if widget.isChecked():
                                values.append(widget.text())
                        else:
                            value = value_for_widget(widget)
                            parameter.value = value
                    if parameter.has_variables():
                        parameter.value = values

            output_path = Path(self.btn_output_dir_select.filePath())
            add_to_map: bool = self.chk_box_add_to_map.isChecked()

            if self.selected_stored_query.type == StoredQuery.Type.Raster:
                self.task = RasterLoader('', output_path, Settings.FMI_DOWNLOAD_URL.get(), self.selected_stored_query,
                                         add_to_map)
            else:
                self.task = VectorLoader("", output_path, Settings.FMI_WFS_URL.get(), Settings.FMI_WFS_VERSION.get(),
                                         self.selected_stored_query, add_to_map)

            # noinspection PyUnresolvedReferences
            self.task.progressChanged.connect(lambda: self.progress_bar.setValue(self.task.progress()))
            # noinspection PyArgumentList
            QgsApplication.taskManager().addTask(self.task)
            self._disable_ui()
            self.task.taskCompleted.connect(lambda: self.__task_completed(True))
            self.task.taskTerminated.connect(lambda: self.__task_completed(False))
        else:
            LOGGER.warning(tr('Could not execute load'), extra=bar_msg(tr('Data source must be selected!')))


    def __task_completed(self, result: bool):
        self._enable_ui()
        if result:
            if self.task.is_manually_temporal:
                self.temporal_layers_added.emit(self.task.layer_ids)

    def _disable_ui(self):
        for item in self.responsive_items:
            item.setEnabled(False)

    def _enable_ui(self):
        for item in self.responsive_items:
            item.setEnabled(True)
