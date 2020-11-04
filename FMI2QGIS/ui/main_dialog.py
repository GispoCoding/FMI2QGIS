from PyQt5.QtWidgets import QDialog
from ..qgis_plugin_tools.tools.resources import load_ui, plugin_name
import logging


FORM_CLASS = load_ui('main_dialog.ui')
LOGGER = logging.getLogger(plugin_name())

class MainDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.btn_load.clicked.connect(self.__load_clicked)

    def __load_clicked(self):
        """todo"""

        start_time = self.dt_edit_start.dateTime().toPyDateTime()
        end_time = self.dt_edit_end.dateTime().toPyDateTime()

        # extent_group_box_bbox

        if self.chk_box_aqi.isChecked():
            print("fetch AQI")
        if self.chk_box_pm25.isChecked():
            print("fetch PM25")
        if self.chk_box_pm10.isChecked():
            print("fetch PM10")
        if self.chk_box_no2.isChecked():
            print("fetch NO2")
        if self.chk_box_o3.isChecked():
            print("fetch O3")

        # self.txt_edit_result.setPlainText(input_url)







