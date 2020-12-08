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
from datetime import datetime

from qgis.core import QgsProject

from .conftest import ANJALANKOSKI_DBZH
from ..core.wms import WMSLayerHandler


def test_wms_layer_handler(wms_url):
    handler = WMSLayerHandler(wms_url)
    wms_layers = handler.list_wms_layers()
    layer1 = [layer for layer in wms_layers if layer.name == ANJALANKOSKI_DBZH][0]

    assert layer1.has_elevation
    assert layer1.default_elevation == 0.3
    assert layer1.elevation_unit_symbol == 'deg'
    assert layer1.elevation_unit == 'Degree'
    assert layer1.is_temporal
    assert layer1.t_step == 5
    assert layer1.time_step_uom == 'M'


def test_wms_layer_handler_url1(wms_layer_handler, test_wms_1):
    url = wms_layer_handler._construct_qgis_url(test_wms_1)
    assert url == ('url=https://openwms.fmi.fi/geoserver/wms?request%3DGetCapabilities'
                   '&layers=Radar:anjalankoski_dbzh&dpiMode=7&format=image/png'
                   '&styles&crs=EPSG:4326&allowTemporalUpdates=true&type=wmst'
                   '&temporalSource=provider'
                   '&timeDimensionExtent=2020-11-04T09:40:00.000000Z/2020-11-11T07:50:00.000000Z/PT5M')


def test_wms_layer_handler_url_with_elevation(wms_layer_handler, test_wms_1):
    url = wms_layer_handler._construct_qgis_url(test_wms_1, elevation=5.0)
    assert url == ('url=https://openwms.fmi.fi/geoserver/wms?request%3DGetCapabilities'
                   '&layers=Radar:anjalankoski_dbzh&dpiMode=7&format=image/png'
                   '&styles&crs=EPSG:4326&allowTemporalUpdates=true&type=wmst'
                   '&temporalSource=provider'
                   '&timeDimensionExtent=2020-11-04T09:40:00.000000Z/2020-11-11T07:50:00.000000Z/PT5M'
                   '&elevation=5.0')


def test_wms_layer_handler_url_with_invalid_elevation(wms_layer_handler, test_wms_1):
    url = wms_layer_handler._construct_qgis_url(test_wms_1, elevation=6.0)
    assert url == ('url=https://openwms.fmi.fi/geoserver/wms?request%3DGetCapabilities'
                   '&layers=Radar:anjalankoski_dbzh&dpiMode=7&format=image/png'
                   '&styles&crs=EPSG:4326&allowTemporalUpdates=true&type=wmst'
                   '&temporalSource=provider'
                   '&timeDimensionExtent=2020-11-04T09:40:00.000000Z/2020-11-11T07:50:00.000000Z/PT5M')


def test_wms_layer_handler_url_2(wms_layer_handler, test_wms_1):
    url = wms_layer_handler._construct_qgis_url(test_wms_1, start_time=datetime.strptime('2020-10-04T09:40:00.00Z',
                                                                                         test_wms_1.TIME_FORMAT))
    assert url == ('url=https://openwms.fmi.fi/geoserver/wms?request%3DGetCapabilities'
                   '&layers=Radar:anjalankoski_dbzh&dpiMode=7&format=image/png'
                   '&styles&crs=EPSG:4326&allowTemporalUpdates=true&type=wmst'
                   '&temporalSource=provider'
                   '&timeDimensionExtent=2020-10-04T09:40:00.000000Z/2020-11-11T07:50:00.000000Z/PT5M')


def test_handler_add_to_map(wms_layer_handler, test_wms_1):
    wms_layer_handler.add_to_map(test_wms_1)
    # noinspection PyArgumentList
    assert len(QgsProject.instance().mapLayersByName(test_wms_1.name)) == 1
