import enum
from datetime import datetime
from pathlib import Path
from typing import Set

from qgis.core import QgsRectangle

from .base import BaseProduct
from ...core.exceptions.loader_exceptions import InvalidParameterException
from ...qgis_plugin_tools.tools.i18n import tr
from ...qgis_plugin_tools.tools.misc_utils import extent_to_bbox


class EnfuserNetcdfLoader(BaseProduct):
    class Products(enum.Enum):
        AirQualityIndex = 'AQIndex'
        NO2Concentration = 'NO2Concentration'
        O3Concentration = 'O3Concentration'
        PM10Concentration = 'PM10Concentration'
        PM25Concentration = 'PM25Concentration'

    # TODO: read from gdal.Dataset.GetSubDatasets()
    layer_names = {
        Products.AirQualityIndex: 'index_of_airquality_194',
        Products.NO2Concentration: 'mass_concentration_of_nitrogen_dioxide_in_air_4902',
        Products.O3Concentration: 'mass_concentration_of_ozone_in_air_4903',
        Products.PM10Concentration: 'mass_concentration_of_pm10_ambient_aerosol_in_air_4904',
        Products.PM25Concentration: 'mass_concentration_of_pm2p5_ambient_aerosol_in_air_4905'
    }

    producer = 'enfuser_helsinki_metropolitan'
    format = 'netcdf'
    projection = 'EPSG:4326'

    def download(self, products: Set[Products], extent: QgsRectangle, start_time: datetime, end_time: datetime) -> Path:
        return super(EnfuserNetcdfLoader, self).download(products=products, extent=extent, start_time=start_time,
                                                  end_time=end_time)

    def _construct_uri(self, products: Set[Products], extent: QgsRectangle, start_time: datetime,
                       end_time: datetime) -> str:
        uri = super(EnfuserNetcdfLoader, self)._construct_uri()
        if not products:
            raise InvalidParameterException(tr('Got empty products'))
        if end_time < start_time:
            raise InvalidParameterException(tr('End time is before start time'))

        params = {
            'param': ':'.join([product.value for product in products]),
            'bbox': extent_to_bbox(extent),
            'levels': '0',
            'origintime': start_time.strftime(self.time_format),
            'starttime': start_time.strftime(self.time_format),
            'endtime': end_time.strftime(self.time_format),
            'format': self.format,
            'projection': self.projection
        }
        uri += '&' + '&'.join([f'{name}={val}' for name, val in params.items()])
        return uri
