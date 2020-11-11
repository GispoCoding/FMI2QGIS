import enum

from ..qgis_plugin_tools.tools.settings import get_setting


@enum.unique
class Settings(enum.Enum):
    FMI_DOWNLOAD_URL = 'https://opendata.fmi.fi/download'
    FMI_WFS_URL = 'https://opendata.fmi.fi/wfs'
    FMI_WFS_VERSION = '2.0.0'
    FMI_WMS_URL = 'https://openwms.fmi.fi/geoserver/wms'

    def get(self, typehint: type = str) -> any:
        """Gets the value of the setting"""
        return get_setting(self.name, self.value, typehint)


@enum.unique
class Namespace(enum.Enum):
    WFS = 'http://www.opengis.net/wfs/2.0'
    OM = 'http://www.opengis.net/om/2.0'
    OMOP = 'http://inspire.ec.europa.eu/schemas/omop/2.9'
    WMS = 'http://www.opengis.net/wms'
