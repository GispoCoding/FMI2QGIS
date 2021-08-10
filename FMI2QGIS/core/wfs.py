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

import datetime
import enum
import logging
import re
import xml.etree.ElementTree as ET  # noqa
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlsplit

from osgeo import ogr
from qgis.core import QgsDateTimeRange
from qgis.PyQt.QtCore import QVariant

from ..definitions.configurable_settings import Namespace
from ..qgis_plugin_tools.tools.custom_logging import bar_msg
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.misc_utils import extent_to_bbox
from ..qgis_plugin_tools.tools.network import fetch
from ..qgis_plugin_tools.tools.resources import plugin_name
from .exceptions.loader_exceptions import WfsException

LOGGER = logging.getLogger(plugin_name())


class ParameterVariable:
    def __init__(self, id: str, alias: str, label: str) -> None:
        self.id = id
        self.alias = alias
        self.label = label


class Parameter:
    TYPE_DICT = {
        "double": QVariant.Double,
        "point": QVariant.Point,
        "dateTime": QVariant.DateTime,
        "unsignedInteger": QVariant.Int,
        "pos": QVariant.Point,
        "boolean": QVariant.Bool,
        "NameList": QVariant.StringList,
        "string": QVariant.String,
        "int": QVariant.Int,
        "integerList": QVariant.List,
        "bbox": QVariant.Rect,
        "bbox_with_srs": QVariant.RectF,
    }

    TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # 2020-11-02T15:00:00Z

    def __init__(self, name: str, title: str, abstract: str, type: QVariant) -> None:
        self.name = name
        self.title = title
        self.abstract = abstract
        self.type = type
        self.variables: List[ParameterVariable] = []
        self._possible_values: List[Any] = []
        self._value: Any = None

    @staticmethod
    def create(param: ET.Element) -> "Parameter":
        param_title = param.find("{%s}Title" % Namespace.WFS.value).text  # type: ignore
        param_abstract = param.find("{%s}Abstract" % Namespace.WFS.value).text  # type: ignore # noqa E501
        param_info = param.attrib
        param_name = param_info["name"]
        param_type = Parameter.TYPE_DICT.get(
            param_info["type"].replace("xsi:", "").replace("gml:", "")
        )

        if param_name == "bbox":
            if "srs" in param_abstract:  # type: ignore
                param_type = Parameter.TYPE_DICT["bbox_with_srs"]
            else:
                param_type = Parameter.TYPE_DICT["bbox"]
        if param_name == "parameters":
            param_name = "param"
        return Parameter(
            str(param_name), str(param_title), str(param_abstract), param_type
        )

    @staticmethod
    def create_from_query_param(name: str, value: Any) -> "Parameter":
        # TODO: quess the type from value and name
        return Parameter(name, "", "", QVariant.String)

    @staticmethod
    def _round_datetime(dt: datetime.datetime) -> datetime.datetime:
        dt += datetime.timedelta(minutes=5)
        dt -= datetime.timedelta(
            minutes=dt.minute % 10, seconds=dt.second, microseconds=dt.microsecond
        )
        return dt

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        # TODO: checks!
        _val = val
        if self.type == QVariant.DateTime:
            if not isinstance(val, datetime.datetime):
                raise ValueError
            _val = datetime.datetime.strftime(
                self._round_datetime(val), self.TIME_FORMAT
            )
        elif self.type in (QVariant.Rect, QVariant.RectF):
            _val = extent_to_bbox(val)
        elif self.name == "param":
            if isinstance(val, list):
                _val = ",".join(val)
        self._value = _val if _val != "" else None

    @property
    def possible_values(self) -> List[Any]:
        return list(self._possible_values)

    def add_possible_value(self, value: Any) -> None:
        _val: Any = str(value)
        if self.type == QVariant.DateTime:
            _val = datetime.datetime.strptime(value, self.TIME_FORMAT)
        if _val not in self._possible_values:
            self._possible_values.append(_val)

    def has_variables(self) -> bool:
        return self.name == "param" and self.type == QVariant.StringList

    def populate_variables(self, observed_property_url: str) -> None:
        variables: List[ParameterVariable] = []
        url_lower = observed_property_url.lower()
        content = fetch(observed_property_url)
        root = ET.ElementTree(ET.fromstring(content)).getroot()
        for component in root.findall("{%s}component" % Namespace.OMOP.value):
            op = component.find("{%s}ObservableProperty" % Namespace.OMOP.value)
            # noinspection PyUnresolvedReferences
            id = str(op.items()[0][-1])  # type: ignore
            label = str(op.find("{%s}label" % Namespace.OMOP.value).text)  # type: ignore # noqa E501
            # Find alias for id from url, since ids are always lowercase
            alias_idx = url_lower.find(id)
            if alias_idx > -1:
                alias = str(observed_property_url[alias_idx : alias_idx + len(id)])
            else:
                alias = id
            variables.append(ParameterVariable(id, alias, label))
        self.variables = variables


class StoredQuery:
    TIME_STEP_NAMES = ("timestep", "time_step")

    class Type(enum.Enum):
        Raster = "raster"
        Vector = "vector"

    def __init__(
        self,
        sq_id: str,
        title: str,
        abstract: str,
        sq_type: Type,
        parameters: Dict[str, Parameter],
    ) -> None:
        self.id = sq_id
        self.title = title
        self.abstract = abstract
        self.type = sq_type
        self.parameters = parameters
        self.producer: str = ""
        self.format: str = ""

    @property
    def time_step(self) -> int:
        """
        :return: Time step parameter value or 60
        """
        value = None
        time_step_params = [
            param
            for name, param in self.parameters.items()
            if name in self.TIME_STEP_NAMES
        ]
        if len(time_step_params) == 1:
            value = time_step_params[0].value
        return int(value) if value is not None else 60

    @staticmethod
    def create(sq_element: ET.Element) -> Optional["StoredQuery"]:
        id = sq_element.get("id")
        sq_type = StoredQuery.Type.Vector
        if id.endswith("grid"):  # type: ignore
            sq_type = StoredQuery.Type.Raster
        elif id.endswith("iwxxm") or id.endswith("GetFeatureById"):  # type: ignore
            # TODO: add support?
            return None

        title = sq_element.find("{%s}Title" % Namespace.WFS.value).text  # type: ignore
        abstract = sq_element.find("{%s}Abstract" % Namespace.WFS.value).text  # type: ignore # noqa E501
        params = [
            Parameter.create(param)
            for param in sq_element.findall("{%s}Parameter" % Namespace.WFS.value)
        ]
        return StoredQuery(
            str(id),
            str(title),
            str(abstract),
            sq_type,
            {param.name: param for param in params},  # type: ignore
        )


class WFSMetadata:
    NETCDF_DIM_EXTRA = "NETCDF_DIM_EXTRA"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # 2020-11-02 15:00:00
    DATETIME_FIELDS = ("date", "time", "datetime")
    DATETIME_TYPES = (9, 10, 11)  # Date, Dime, DateTime
    TIME_DIMENSION_NAMES = ("time", "time_h")

    def __init__(self) -> None:
        # Raster
        self.start_time: Optional[datetime.datetime] = None
        self.time_step: Optional[datetime.timedelta] = None
        self.num_of_time_steps: Optional[int] = None
        self.sub_dataset_dict: Optional[Dict] = None

        # Vector
        self.layer_name: str = ""
        self.fields: Optional[List[str]] = None
        self.time_field_idx: Optional[int] = None

    @property
    def is_temporal(self) -> bool:
        return all((self.start_time, self.time_step, self.num_of_time_steps))

    @property
    def temporal_field(self) -> str:
        return self.fields[self.time_field_idx].lower()  # type: ignore

    @property
    def time_range(self) -> Optional[QgsDateTimeRange]:
        """
        Date time range of the dataset
        """
        if self.is_temporal:
            # Add extra second to make last frame visible
            assert self.start_time is not None
            assert self.num_of_time_steps is not None
            assert self.time_step is not None
            return QgsDateTimeRange(
                self.start_time,
                self.start_time
                + (self.num_of_time_steps - 1) * self.time_step
                + datetime.timedelta(seconds=1),  # type: ignore
            )
        return None

    def fix_gdal_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """
        Replaces unknown time dimension names with "time"
        :param metadata: Dictionary of gdal metadata
        :return: fixed gdal metadata
        """
        d = {}
        for key, value in metadata.items():
            key_ = re.sub(r"time_\d?h", self.TIME_DIMENSION_NAMES[0], key)
            value_ = re.sub(r"time_\d?h", self.TIME_DIMENSION_NAMES[0], value)
            d[key_] = value_
        return d

    def update_from_gdal_metadata(self, ds_metadata: Dict[str, str]) -> None:
        if self.NETCDF_DIM_EXTRA in ds_metadata:
            # Is netcdf file and has extra dimensions (probably time)
            for dimension in (
                ds_metadata[self.NETCDF_DIM_EXTRA].strip("{").strip("}").split(",")
            ):
                dim_def = (
                    ds_metadata.get(f"NETCDF_DIM_{dimension}_DEF", "")
                    .strip("{")
                    .strip("}")
                    .split(",")
                )

                dim_units = ds_metadata.get(f"{dimension}#units", "")
                if dimension in self.TIME_DIMENSION_NAMES and dim_def:
                    time_units, start_time = dim_units.split(
                        " since "
                    )  # eg. hours since 2020-10-05 18:00:00
                    if time_units == "hours":
                        self.time_step = datetime.timedelta(hours=1)
                    elif time_units == "minutes":
                        self.time_step = datetime.timedelta(minutes=1)
                    elif time_units == "days":
                        self.time_step = datetime.timedelta(days=1)
                    self.start_time = (
                        datetime.datetime.strptime(start_time, self.TIME_FORMAT)
                        if start_time
                        else None
                    )
                    self.num_of_time_steps = int(dim_def[0]) if dim_def else None

    def update_from_ogr_data_source(self, ds: ogr.DataSource) -> None:
        layer_count = ds.GetLayerCount()
        if layer_count == 1:
            layer = ds.GetLayer(0)
            # Only one layer
        else:
            # TODO: add support
            return

        defn = layer.GetLayerDefn()
        self.layer_name = layer.GetName()
        fields = []
        for i in range(defn.GetFieldCount()):
            field_name = defn.GetFieldDefn(i).GetName()
            field_type_code = defn.GetFieldDefn(i).GetType()
            fields.append(field_name)

            if field_name.lower() in self.DATETIME_FIELDS:

                if field_type_code not in self.DATETIME_TYPES:
                    self.time_field_idx = i
        self.fields = fields

    def is_datasource_valid(self, ds: ogr.DataSource) -> bool:
        layer_count = ds.GetLayerCount()
        if layer_count == 1:
            layer = ds.GetLayer(0)
            # Only one layer
        else:
            # TODO: add support
            return False

        defn = layer.GetLayerDefn()
        for i in range(defn.GetFieldCount()):
            field_name = defn.GetFieldDefn(i).GetName()
            if field_name.lower() == self.temporal_field:
                field_type_code = defn.GetFieldDefn(i).GetType()
                return field_type_code in self.DATETIME_TYPES
        return False


class StoredQueryFactory:
    def __init__(self, wfs_url: str, wfs_version: str) -> None:
        self.wfs_url = wfs_url
        self.wfs_version = wfs_version

    @property
    def __describe_stored_queries_url(self) -> str:
        return (
            f"{self.wfs_url}?service=WFS"
            f"&version={self.wfs_version}"
            f"&request=describeStoredQueries"
        )

    def __get_feature_url(self, sq: StoredQuery, count: int) -> str:
        # TODO: maxFeatures for version < 2.0.0
        return (
            f"{self.wfs_url}?service=WFS&version={self.wfs_version}&request=GetFeature"
            f"&count={count}&storedquery_id={sq.id}"
        )

    def list_queries(self) -> List[StoredQuery]:
        """
        List stored queries provided by the service
        :return: List of stored queries
        """
        stored_queries: List[StoredQuery] = []

        content = fetch(self.__describe_stored_queries_url)
        root = ET.ElementTree(ET.fromstring(content)).getroot()
        for sq_element in list(root):
            sq = StoredQuery.create(sq_element)
            if sq:
                stored_queries.append(sq)

        return stored_queries

    def expand(self, sq: StoredQuery) -> None:
        """
        Gather extra information for the stored query
        :param sq: StoredQuery object
        """
        if sq.type == StoredQuery.Type.Raster:
            content = fetch(self.__get_feature_url(sq, 10))
            root = ET.ElementTree(ET.fromstring(content)).getroot()
            grid_observation_first_elem = list(list(root)[0])[0]

            # Observed property url
            ob_url = grid_observation_first_elem.find(  # type: ignore
                "{%s}observedProperty" % Namespace.OM.value
            ).items()[0][-1]
            for param in sq.parameters.values():
                if param.has_variables():
                    param.populate_variables(ob_url)

            process_url = grid_observation_first_elem.find(  # type: ignore
                "{%s}procedure" % Namespace.OM.value
            ).items()[0][-1]
            sq.producer = process_url.split("/")[-1]
            # noinspection PyTypeChecker
            sq.format = parse_qs(urlsplit(ob_url).query).get("units", [""])[0]

            for wfs_member in list(root):
                grid_series_obs = list(wfs_member)[0]
                file_reference_url = (
                    list(grid_series_obs.find("{%s}result" % Namespace.OM.value))[  # type: ignore # noqa E501
                        0
                    ]
                    .find("{%s}rangeSet" % Namespace.GML.value)
                    .find("{%s}File" % Namespace.GML.value)
                    .find("{%s}fileReference" % Namespace.GML.value)
                    .text
                )
                query_params = parse_qs(urlsplit(file_reference_url).query)  # type: ignore # noqa E501

                param_name: str
                for param_name, param_value_list in query_params.items():  # type: ignore # noqa E501
                    if param_value_list and param_name not in [
                        "origintime",
                        "producer",
                        "param",
                    ]:
                        param_value = param_value_list[0]
                        if param_name not in sq.parameters:
                            sq.parameters[
                                param_name
                            ] = Parameter.create_from_query_param(
                                param_name, param_value
                            )
                        param = sq.parameters[param_name]
                        param.add_possible_value(param_value)
                        if (
                            param_name == "format"
                            and param_value != "netcdf"
                            and "netcdf" not in param._possible_values
                        ):
                            LOGGER.warning(
                                f"Stored query {sq.id} uses "
                                f"different format than NetCDF"
                            )
                            param.add_possible_value("netcdf")

                        if (
                            param.type == QVariant.DateTime
                            and str(param_name).startswith("start")
                            or str(param_name).startswith("end")
                        ):
                            for param_name2, param2 in sq.parameters.items():
                                if (
                                    param2.type == param.type
                                    and param_name2 != param_name
                                ):
                                    param2.add_possible_value(param_value)


def raise_based_on_response(xml_content: str) -> None:
    """
    Rais WfsException based on xml content
    :param xml_content:
    """
    # TODO: add possibly other kind of exceptions as well
    root = ET.ElementTree(ET.fromstring(xml_content)).getroot()
    exception_elem: ET.Element = list(root)[0]
    exception_code = exception_elem.attrib.get("exceptionCode", "")
    exception_texts = " ".join(
        [elem.text for elem in exception_elem if "URI: " not in elem.text]  # type: ignore # noqa E501
    )

    LOGGER.error(f"Exception texts: {exception_texts}")
    raise WfsException(
        tr("Exception occurred: {}", exception_code), bar_msg=bar_msg(exception_texts)
    )
