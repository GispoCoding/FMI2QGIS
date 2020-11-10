from pathlib import Path
from typing import Tuple

from qgis.core import QgsMessageLog, Qgis, QgsTask

from ..exceptions.loader_exceptions import BadRequestException
from ...qgis_plugin_tools.tools import network
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException, QgsPluginNotImplementedException
from ...qgis_plugin_tools.tools.i18n import tr


class BaseLoader(QgsTask):
    MESSAGE_CATEGORY = ''

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
                # TODO: what about large files, should requests be used if available to stream content?
                data, default_name = network.fetch_raw(uri)
                self._log(f'File name is: "{default_name}"')
                self.setProgress(70)
                if not self.isCanceled():
                    output = Path(self.download_dir, default_name)
                    with open(output, 'wb') as f:
                        f.write(data)
                    self._log(f'Success!')
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
