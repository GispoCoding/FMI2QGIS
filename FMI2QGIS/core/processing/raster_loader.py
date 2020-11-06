import logging
from pathlib import Path
from typing import Optional, Tuple

from qgis.core import QgsTask, QgsMessageLog, Qgis, QgsRasterLayer, QgsProject

from ..exceptions.loader_exceptions import BadRequestException
from ..wfs import StoredQuery
from ...qgis_plugin_tools.tools import network
from ...qgis_plugin_tools.tools.custom_logging import bar_msg
from ...qgis_plugin_tools.tools.exceptions import QgsPluginNetworkException, QgsPluginException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.resources import plugin_name

LOGGER = logging.getLogger(plugin_name())


class RasterLoader(QgsTask):
    MESSAGE_CATEGORY = 'FmiRasterLoader'

    def __init__(self, description: str, download_dir: Path, fmi_download_url: str, sq: StoredQuery):
        """
        :param download_dir:Download directory of the output file(s)
        :param fmi_download_url: FMI download url
        :param sq: StoredQuery
        """
        super().__init__(description, QgsTask.CanCancel)

        self.download_dir = download_dir
        if not self.download_dir.exists():
            self.download_dir.mkdir()
        self.url = fmi_download_url
        self.sq = sq

        self.path_to_file: Path = Path()
        self.exception: Optional[Exception] = None

    def run(self):
        """
        NOTE: LOGGER cannot be used in here or any methods that are called from here
        :return:
        """
        self.path_to_file, result = self._download()
        return result

    def _download(self) -> Tuple[Path, bool]:
        """
        Downloads files to the disk (self.download_dir)
        :param kwargs: keyword arguments depending on the product
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
                                              bar_msg=bar_msg(tr('Try with different start and end times')))
        except Exception as e:
            self.exception = e
            result = False

        self.setProgress(100)
        return output, result

    def _construct_uri(self) -> str:
        url = self.url + f'?producer={self.sq.producer}&format={self.sq.format}'
        url += '&' + '&'.join([f'{name}={param.value}' for name, param in self.sq.parameters.items()])
        return url

    def _log(self, msg: str, level=Qgis.Info) -> None:
        # noinspection PyCallByClass
        QgsMessageLog.logMessage(msg, self.MESSAGE_CATEGORY, level)

    def finished(self, result: bool) -> None:
        """
        This function is automatically called when the task has completed (successfully or not).

        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.

        :param result: the return value from self.run
        """
        if result and self.path_to_file.is_file():
            layer = self.raster_to_layer()
            if layer.isValid():
                # TODO: layer styling

                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(layer)

        # Error handling
        else:
            if self.exception is None:
                LOGGER.warning(tr('Task was not successful'), extra=bar_msg(tr('Task was probably cancelled by user')))
            else:
                try:
                    raise self.exception
                except QgsPluginException as e:
                    LOGGER.exception(str(e), extra=e.bar_msg)
                except Exception as e:
                    LOGGER.exception(tr('Unhandled exception occurred'), extra=bar_msg(e))

    def raster_to_layer(self) -> QgsRasterLayer:
        """
        TODO
        :return:
        """
        # TODO: change name
        layer_name = 'testlayer'
        if self.path_to_file.suffix == 'nc':
            # TODO: Check variable(s) using gdal.Dataset.GetSubDatasets()
            variable = 'index_of_airquality_194'

            uri = f'NETCDF:"{self.path_to_file}":{variable}'

        else:
            # TODO: add support for other raster formats
            uri = str(self.path_to_file)
        layer = QgsRasterLayer(uri, layer_name)
        return layer
