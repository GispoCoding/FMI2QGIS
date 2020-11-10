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

import datetime
import enum
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict
from urllib.parse import urlsplit, parse_qs

from PyQt5.QtCore import QVariant

from ..definitions.configurable_settings import Namespace
from ..qgis_plugin_tools.tools.misc_utils import extent_to_bbox
from ..qgis_plugin_tools.tools.network import fetch


class ParameterVariable:

    def __init__(self, id: str, alias: str, label: str):
        self.id = id
        self.alias = alias
        self.label = label


class Parameter:
    TYPE_DICT = {'double': QVariant.Double, 'point': QVariant.Point,
                 'dateTime': QVariant.DateTime, 'unsignedInteger': QVariant.Int, 'pos': QVariant.Point,
                 'boolean': QVariant.Bool, 'NameList': QVariant.StringList,
                 'string': QVariant.String, 'int': QVariant.Int, 'integerList': QVariant.List,
                 'bbox': QVariant.Rect, 'bbox_with_srs': QVariant.RectF}

    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'  # 2020-11-02T15:00:00Z

    def __init__(self, name: str, title: str, abstract: str, type: QVariant):
        self.name = name
        self.title = title
        self.abstract = abstract
        self.type = type
        self.variables = []
        self._value: any = None

    @staticmethod
    def create(param: ET.Element) -> 'Parameter':
        param_title = param.find('{%s}Title' % Namespace.WFS.value).text
        param_abstract = param.find('{%s}Abstract' % Namespace.WFS.value).text
        param_info = param.attrib
        param_name = param_info['name']
        param_type = Parameter.TYPE_DICT.get(param_info['type'].replace('xsi:', '').replace('gml:', ''))

        if param_name == 'bbox':
            if 'srs' in param_abstract:
                param_type = Parameter.TYPE_DICT['bbox_with_srs']
            else:
                param_type = Parameter.TYPE_DICT['bbox']
        if param_name == 'parameters':
            param_name = 'param'
        return Parameter(param_name, param_title, param_abstract, param_type)

    @staticmethod
    def _round_datetime(dt: datetime.datetime) -> datetime.datetime:
        dt += datetime.timedelta(minutes=5)
        dt -= datetime.timedelta(minutes=dt.minute % 10,
                                 seconds=dt.second,
                                 microseconds=dt.microsecond)
        return dt

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val: any):
        # TODO: checks!
        _val = val
        if self.type == QVariant.DateTime:
            if not isinstance(val, datetime.datetime):
                raise ()
            _val = datetime.datetime.strftime(self._round_datetime(val), self.TIME_FORMAT)
        elif self.type in [QVariant.Rect, QVariant.RectF]:
            _val = extent_to_bbox(val)
        elif self.name == 'param':
            if isinstance(val, list):
                _val = ','.join(val)
        self._value = _val

    def has_variables(self) -> bool:
        return self.name == 'param' and self.type == QVariant.StringList

    def populate_variables(self, observed_property_url: str) -> None:
        variables = []
        url_lower = observed_property_url.lower()
        content = fetch(observed_property_url)
        root = ET.ElementTree(ET.fromstring(content)).getroot()
        for component in root.findall('{%s}component' % Namespace.OMOP.value):
            op = component.find('{%s}ObservableProperty' % Namespace.OMOP.value)
            # noinspection PyUnresolvedReferences
            id = op.items()[0][-1]
            label = op.find('{%s}label' % Namespace.OMOP.value).text
            # Find alias for id from url, since ids are always lowercase
            alias_idx = url_lower.find(id)
            if alias_idx > -1:
                alias = observed_property_url[alias_idx:alias_idx + len(id)]
            else:
                alias = id
            variables.append(ParameterVariable(id, alias, label))
        self.variables = variables


class StoredQuery:
    class Type(enum.Enum):
        Raster = 'raster'
        Vector = 'vector'

    def __init__(self, sq_id: str, title: str, abstract: str, sq_type: Type, parameters: Dict[str, Parameter]):
        self.id = sq_id
        self.title = title
        self.abstract = abstract
        self.type = sq_type
        self.parameters = parameters
        self.producer: str = ''
        self.format: str = ''

    @staticmethod
    def create(sq_element: ET.Element) -> Optional['StoredQuery']:
        id = sq_element.get('id')
        sq_type = StoredQuery.Type.Vector
        if id.endswith('grid'):
            sq_type = StoredQuery.Type.Raster
        elif id.endswith('iwxxm') or id.endswith('GetFeatureById'):
            # TODO: add support?
            return None

        title = sq_element.find('{%s}Title' % Namespace.WFS.value).text
        abstract = sq_element.find('{%s}Abstract' % Namespace.WFS.value).text
        params = [Parameter.create(param) for param in sq_element.findall('{%s}Parameter' % Namespace.WFS.value)]
        params = {param.name: param for param in params}
        return StoredQuery(id, title, abstract, sq_type, params)


class StoredQueryFactory:

    def __init__(self, wfs_url: str, wfs_version: str):
        self.wfs_url = wfs_url
        self.wfs_version = wfs_version

    @property
    def __describe_stored_queries_url(self) -> str:
        return f'{self.wfs_url}?service=WFS&version={self.wfs_version}&request=describeStoredQueries'

    def __get_feature_url(self, sq: StoredQuery, count: int):
        # TODO: maxFeatures for version < 2.0.0
        return (f'{self.wfs_url}?service=WFS&version={self.wfs_version}&request=GetFeature'
                f'&count={count}&storedquery_id={sq.id}')

    def list_queries(self) -> List[StoredQuery]:
        stored_queries: List[StoredQuery] = []

        content = fetch(self.__describe_stored_queries_url)
        root = ET.ElementTree(ET.fromstring(content)).getroot()
        for sq_element in list(root):
            sq = StoredQuery.create(sq_element)
            if sq:
                stored_queries.append(sq)

        return stored_queries

    def expand(self, sq: StoredQuery) -> None:
        if sq.type == StoredQuery.Type.Raster:
            content = fetch(self.__get_feature_url(sq, 1))
            root = ET.ElementTree(ET.fromstring(content)).getroot()
            grid_observation_elem = list(list(root)[0])[0]

            # Observed property url
            ob_url = grid_observation_elem.find('{%s}observedProperty' % Namespace.OM.value).items()[0][-1]
            for param in sq.parameters.values():
                if param.has_variables():
                    param.populate_variables(ob_url)

            process_url = grid_observation_elem.find('{%s}procedure' % Namespace.OM.value).items()[0][-1]
            sq.producer = process_url.split('/')[-1]
            sq.format = parse_qs(urlsplit(ob_url).query).get('units', [''])[0]
