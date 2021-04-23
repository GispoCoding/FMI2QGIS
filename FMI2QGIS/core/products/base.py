#  Gispo Ltd., hereby disclaims all copyright interest in the program FMI2QGIS
#  Copyright (C) 2020-2021 Gispo Ltd (https://www.gispo.fi/).
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
from typing import Any

from qgis.core import QgsProcessingFeedback

from ...qgis_plugin_tools.tools import network
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException
from ...qgis_plugin_tools.tools.i18n import tr
from ..exceptions.loader_exceptions import BadRequestException


class BaseProduct:
    producer = ""
    time_format = "%Y-%m-%dT%H:%M:%SZ"  # 2020-11-02T15:00:00Z

    def __init__(
        self, download_dir: Path, fmi_download_url: str, feedback: QgsProcessingFeedback
    ) -> None:
        """
        :param download_dir:Download directory of the output file(s)
        :param fmi_download_url: FMI download url
        :param feedback:
        """
        self.download_dir = download_dir
        if not self.download_dir.exists():
            self.download_dir.mkdir()
        self.url = fmi_download_url
        self.feedback = feedback

    def download(self, **kwargs: str) -> Path:
        """
        Downloads files to the disk (self.download_dir)
        :param kwargs: keyword arguments depending on the product
        :return: Path to the downloaded file
        """
        try:
            self.feedback.setProgress(0)
            uri = self._construct_uri(**kwargs)
            self.feedback.setProgress(10)
            self.feedback.pushDebugInfo(uri)

            try:
                data, default_name = network.fetch_raw(uri)
                self.feedback.pushDebugInfo(f'File name is: "{default_name}"')
                self.feedback.setProgress(70)
                if not self.feedback.isCanceled():
                    output = Path(self.download_dir, default_name)
                    with open(output, "wb") as f:
                        f.write(data)
                    return output
            except QgsPluginNetworkException as e:
                error_message = e.bar_msg["details"]  # type: ignore
                if "Bad Request" in error_message:
                    raise BadRequestException(
                        tr("Bad request"),
                        bar_msg=bar_msg(tr("Try with different start and end times")),
                    )
        except Exception as e:
            self.feedback.reportError(tr("Error occurred: {}", e), True)
            self.feedback.cancel()

        self.feedback.setProgress(100)
        return Path()

    def _construct_uri(self, **kwargs: Any) -> str:
        url = self.url + f"?producer={self.producer}"
        return url
