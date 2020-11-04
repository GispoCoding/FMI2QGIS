from FMI2QGIS.qgis_plugin_tools.tools.exceptions import QgsPluginException


class InvalidParameterException(QgsPluginException):
    pass

class BadRequestException(QgsPluginException):
    pass
