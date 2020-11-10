from pathlib import Path
from typing import Tuple, Optional

from qgis.core import QgsMessageLog, Qgis, QgsTask

from ..exceptions.loader_exceptions import BadRequestException
from ...qgis_plugin_tools.tools import network
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException, QgsPluginNotImplementedException
from ...qgis_plugin_tools.tools.i18n import tr


class BaseLoader(QgsTask):
    MESSAGE_CATEGORY = ''

    def __init__(self, description: str, download_dir: Path):
        """
        :param download_dir:Download directory of the output file(s)
        :param sq: StoredQuery
        """
        super().__init__(description, QgsTask.CanCancel)
        self.download_dir = download_dir
        if not self.download_dir.exists():
            self.download_dir.mkdir()

        self.path_to_file: Path = Path()
        self.exception: Optional[Exception] = None

    @property
    def file_name(self) -> Optional[str]:
        """
        File name for the download
        :return: str or None
        """
        return None

    def _download(self) -> Tuple[Path, bool]:
        """
        Downloads files to the disk (self.download_dir)
        :return: Path to the downloaded file and whether was succesful or not
        """
        result: bool = False
        output: Path = Path()
        try:
            self.setProgress(0)
            uri = self._construct_uri()
            self.setProgress(10)
            self._log(f'Started task "{self.description}"')

            self._log(f'Download url is is: "{uri}"')

            try:
                # TODO: add a way to cancel the download
                output = network.download_to_file(uri, self.download_dir, output_name=self.file_name)
                self._log(f'File path is: "{output}"')
                self.setProgress(70)
                if not self.isCanceled():
                    result = True
            except QgsPluginNetworkException as e:
                error_message = e.bar_msg['details']
                if 'Bad Request' in error_message:
                    raise BadRequestException(tr('Bad request'),
                                              bar_msg=bar_msg(tr('Try with different parameters')))
        except Exception as e:
            self.exception = e
            result = False

        return output, result

    def _construct_uri(self) -> str:
        """
        Constructs the uri for the download
        """
        raise QgsPluginNotImplementedException('This method should be overridden')

    def _log(self, msg: str, level=Qgis.Info) -> None:
        """
        Used to log messages instead of LOGGER while in task thread
        """
        # noinspection PyCallByClass,PyTypeChecker
        QgsMessageLog.logMessage(msg, self.MESSAGE_CATEGORY, level)
