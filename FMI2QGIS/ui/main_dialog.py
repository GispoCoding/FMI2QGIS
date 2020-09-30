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
        input_url: str = self.ln_edit_url.text()
        self.txt_edit_result.setPlainText(input_url)

        



