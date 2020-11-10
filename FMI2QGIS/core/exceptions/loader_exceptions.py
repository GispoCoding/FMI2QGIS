from ...qgis_plugin_tools.tools.exceptions import QgsPluginException


class InvalidParameterException(QgsPluginException):
    pass

class BadRequestException(QgsPluginException):
    pass

class WfsException(QgsPluginException):
    pass
