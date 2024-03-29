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

# type: ignore
import pytest
from PyQt5.QtCore import QVariant

from ..core.exceptions.loader_exceptions import WfsException
from ..core.wfs import StoredQuery, StoredQueryFactory, raise_based_on_response
from .conftest import AIR_QUALITY_ID, ENFUSER_ID, HYBRID_GRID_ID


def test_factory_list_queries_raster(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()

    raster_queries = {
        sq.id: sq for sq in filter(lambda q: q.type == StoredQuery.Type.Raster, queries)
    }
    enfuser_sq: StoredQuery = raster_queries.get(ENFUSER_ID)

    assert len(queries) >= 100
    assert len(raster_queries) >= 10
    assert ENFUSER_ID in raster_queries.keys()
    assert enfuser_sq.producer == ""
    assert len(enfuser_sq.parameters) == 4
    assert set(enfuser_sq.parameters.keys()) == {
        "bbox",
        "endtime",
        "param",
        "starttime",
    }
    assert [param.type for param in enfuser_sq.parameters.values()] == [
        QVariant.DateTime,
        QVariant.DateTime,
        QVariant.Rect,
        QVariant.StringList,
    ]
    assert enfuser_sq.parameters["bbox"].type == QVariant.Rect
    assert enfuser_sq.parameters["endtime"].type == QVariant.DateTime
    assert enfuser_sq.parameters["param"].has_variables()
    assert enfuser_sq.parameters["param"].variables == []


def test_factory_list_queries_vector(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()

    vector_queries = {
        sq.id: sq for sq in filter(lambda q: q.type == StoredQuery.Type.Vector, queries)
    }
    airquality_sq: StoredQuery = vector_queries.get(AIR_QUALITY_ID)

    assert len(queries) >= 100
    assert len(vector_queries) >= 100
    assert airquality_sq.producer == ""
    assert len(airquality_sq.parameters) == 11
    assert set(airquality_sq.parameters.keys()) == {
        "bbox",
        "crs",
        "endtime",
        "fmisid",
        "geoid",
        "maxlocations",
        "param",
        "place",
        "starttime",
        "timestep",
        "timezone",
    }
    assert airquality_sq.parameters["bbox"].type == QVariant.Rect
    assert airquality_sq.parameters["timestep"].type == QVariant.Int


def test_sq_raster_expanding(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()
    enfuser_sq: StoredQuery = list(filter(lambda q: q.id == ENFUSER_ID, queries))[0]
    orig_params = set(enfuser_sq.parameters.keys())

    factory.expand(enfuser_sq)
    param_variables = [pv.alias for pv in enfuser_sq.parameters["param"].variables]

    assert enfuser_sq.producer == "enfuser_helsinki_metropolitan"
    assert param_variables == [
        "AQIndex",
        "NO2Concentration",
        "O3Concentration",
        "PM10Concentration",
        "PM25Concentration",
    ]
    assert set(enfuser_sq.parameters.keys()).difference(orig_params) == {
        "levels",
        "projection",
        "format",
    }
    assert len(enfuser_sq.parameters["starttime"]._possible_values) > 3
    assert enfuser_sq.parameters["format"]._possible_values == ["netcdf"]


def test_sq_raster_expanding2(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()
    hybrid_sq: StoredQuery = list(filter(lambda q: q.id == HYBRID_GRID_ID, queries))[0]
    orig_params = set(hybrid_sq.parameters.keys())

    factory.expand(hybrid_sq)
    param_variables = [pv.alias for pv in hybrid_sq.parameters["param"].variables]

    assert hybrid_sq.producer == "harmonie_scandinavia_hybrid"
    assert param_variables == [
        "Pressure",
        "GeomHeight",
        "Temperature",
        "Humidity",
        "WindDirection",
        "WindSpeedMS",
        "WindUMS",
        "WindVMS",
        "VerticalVelocityMMS",
    ]
    assert hybrid_sq.parameters["format"]._possible_values == ["grib2", "netcdf"]
    assert hybrid_sq.parameters["levels"]._possible_values == [
        "12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,"
        "41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65"
    ]


def test_sq_vector_expanding(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()
    air_quality_sq: StoredQuery = list(
        filter(lambda q: q.id == AIR_QUALITY_ID, queries)
    )[0]

    factory.expand(air_quality_sq)


def test_raise_based_on_response1():
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<ExceptionReport xmlns="http://www.opengis.net/ows/1.1"\n\t\t xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n  xsi:schemaLocation="http://www.opengis.net/ows/1.1 http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd"\n  version="2.0.0" xml:lang="eng">\n\n\n  <Exception exceptionCode="OperationParsingFailed">\n    <ExceptionText>Invalid time interval!</ExceptionText>\n    <ExceptionText>The start time is later than the end time.</ExceptionText>\n    <ExceptionText>URI: /wfs?bbox=21.0%2C59.7%2C31.7%2C70.0&amp;endtime=2020-11-06T11%3A00%3A00Z&amp;request=GetFeature&amp;service=WFS&amp;storedquery_id=fmi%3A%3Aobservations%3A%3Aairquality%3A%3Ahourly%3A%3Asimple&amp;timestep=60&amp;version=2.0.0</ExceptionText>\n    \n  </Exception>\n\n</ExceptionReport>\n'
    with pytest.raises(WfsException) as excinfo:
        raise_based_on_response(xml_content)
    assert str(excinfo.value) == "Exception occurred: OperationParsingFailed"
    assert (
        excinfo.value.bar_msg["details"]
        == "Invalid time interval! The start time is later than the end time."
    )
