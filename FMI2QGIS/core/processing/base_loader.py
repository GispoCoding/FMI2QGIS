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

from pathlib import Path
from typing import Tuple, Optional, Set

from qgis.core import QgsMessageLog, Qgis, QgsTask

from ..exceptions.loader_exceptions import BadRequestException
from ..wfs import raise_based_on_response, WFSMetadata
from ...qgis_plugin_tools.tools import network
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException, QgsPluginNotImplementedException
from ...qgis_plugin_tools.tools.i18n import tr


class BaseLoader(QgsTask):
    MESSAGE_CATEGORY = ''

    def __init__(self, description: str, download_dir: Path):
        """
        :param description: Description of the task
        :param download_dir:Download directory of the output file(s)
        """
        super().__init__(description, QgsTask.CanCancel)
        self.download_dir = download_dir
        if not self.download_dir.exists():
            self.download_dir.mkdir()

        self.layer_ids: Set[str] = set()
        self.path_to_file: Path = Path()
        self.metadata: WFSMetadata = WFSMetadata()
        self.exception: Optional[Exception] = None

    @property
    def is_manually_temporal(self) -> bool:
        return False

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
                output = self._process_downloaded_file(output)
                self._log(f'File path is: "{output}"')
                self.setProgress(70)
                if not self.isCanceled():
                    result = True
            except QgsPluginNetworkException as e:
                self.exception = e
                error_message = e.bar_msg['details']
                if 'Bad Request' in error_message:
                    raise BadRequestException(tr('Bad request'),
                                              bar_msg=bar_msg(tr('Try with different parameters')))
                elif '<?xml' in error_message:
                    raise_based_on_response(error_message)

        except Exception as e:
            self.exception = e
            result = False

        return output, result

    def _process_downloaded_file(self, downloaded_file_path: Path) -> Path:
        """ Do some postprocessing after the file is downloaded"""
        return downloaded_file_path

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
