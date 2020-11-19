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

from typing import Callable, Optional, Set

from PyQt5.QtCore import QTranslator, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QWidget, QDockWidget
from qgis.core import QgsApplication, QgsDateTimeRange, QgsMapLayer, QgsProject, QgsRasterLayer
from qgis.gui import QgisInterface

from .core.processing.provider import Fmi2QgisProcessingProvider
from .qgis_plugin_tools.tools.custom_logging import setup_logger
from .qgis_plugin_tools.tools.i18n import setup_translation, tr
from .qgis_plugin_tools.tools.raster_layers import set_band_based_on_range
from .qgis_plugin_tools.tools.resources import plugin_name, resources_path
from .ui.main_dialog import MainDialog
from .ui.wms_dialog import WMSDialog

try:
    from qgis.core import QgsTemporalController
except ImportError:
    QgsTemporalController = None

TEMPORAL_CONTROLLER = 'Temporal Controller'


class Plugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface: QgisInterface):

        self.iface = iface

        setup_logger(plugin_name(), iface)

        # initialize locale
        locale, file_path = setup_translation()
        if file_path:
            self.translator = QTranslator()
            self.translator.load(file_path)
            # noinspection PyCallByClass
            QCoreApplication.installTranslator(self.translator)
        else:
            pass

        self.actions = []
        self.menu = tr(plugin_name())

        self.processing_provider = Fmi2QgisProcessingProvider()

        self.manually_handled_temporal_layer_ids: Set[str] = set()

    def add_action(
        self,
        icon_path: str,
        text: str,
        callback: Callable,
        enabled_flag: bool = True,
        add_to_menu: bool = True,
        add_to_toolbar: bool = True,
        status_tip: Optional[str] = None,
        whats_this: Optional[str] = None,
        parent: Optional[QWidget] = None) -> QAction:
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.

        :param text: Text that should be shown in menu items for this action.

        :param callback: Function to be called when the action is triggered.

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.

        :param parent: Parent widget for the new action. Defaults None.

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        # noinspection PyUnresolvedReferences
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.add_action(
            resources_path('icons', 'icon.png'),
            text=tr("Add WFS Layer"),
            callback=self.run,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False
        )

        self.add_action(
            resources_path('icons', 'icon.png'),
            text=tr("Add WMS Layer"),
            callback=self.add_wms,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False
        )

        # noinspection PyArgumentList
        QgsApplication.processingRegistry().addProvider(self.processing_provider)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        pass

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                tr(plugin_name()),
                action)
            self.iface.removeToolBarIcon(action)

        # noinspection PyArgumentList
        QgsApplication.processingRegistry().removeProvider(self.processing_provider)

    def run(self):
        """Run method that performs all the real work"""
        self.__show_temporal_controller()
        dialog = MainDialog(self.iface)

        def update_layers(layer_ids):
            self.manually_handled_temporal_layer_ids.update(set(layer_ids))

        dialog.temporal_layers_added.connect(update_layers)
        dialog.exec()

    def add_wms(self):
        self.__show_temporal_controller()
        dialog = WMSDialog(self.iface)
        dialog.exec()

    ## Temporal common functionality
    def __show_temporal_controller(self):
        """Sets Temporal Controller dock widget visible if it exists"""
        dock_widget: QDockWidget
        for dock_widget in self.iface.mainWindow().findChildren(QDockWidget, TEMPORAL_CONTROLLER):
            if not dock_widget.isVisible():
                dock_widget.setVisible(True)
            temporal_controller: QgsTemporalController = self.iface.mapCanvas().temporalController()
            # noinspection PyUnresolvedReferences
            temporal_controller.updateTemporalRange.connect(self.__temporal_range_changed)

    def __temporal_range_changed(self, t_range: QgsDateTimeRange):
        """Update manually handled temporal layers"""
        obsolete_layer_ids = set()
        layer: QgsMapLayer
        for layer_id in self.manually_handled_temporal_layer_ids:
            # noinspection PyArgumentList
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer is None:
                # removed by user
                obsolete_layer_ids.add(layer_id)
            else:
                tprops = layer.temporalProperties()
                if tprops.isVisibleInTemporalRange(t_range):
                    if isinstance(layer, QgsRasterLayer):
                        set_band_based_on_range(layer, t_range)
                else:
                    pass
                    # TODO: what to do?

        self.manually_handled_temporal_layer_ids.difference_update(obsolete_layer_ids)
