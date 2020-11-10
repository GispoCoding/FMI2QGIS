from PyQt5.QtCore import QVariant

from .conftest import ENFUSER_ID, AIR_QUALITY_ID
from ..core.wfs import StoredQueryFactory, StoredQuery


def test_factory_list_queries_raster(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()

    raster_queries = {sq.id: sq for sq in filter(lambda q: q.type == StoredQuery.Type.Raster, queries)}
    enfuser_sq: StoredQuery = raster_queries.get(ENFUSER_ID)

    assert len(queries) >= 100
    assert len(raster_queries) >= 10
    assert ENFUSER_ID in raster_queries.keys()
    assert enfuser_sq.producer == ''
    assert len(enfuser_sq.parameters) == 4
    assert set(enfuser_sq.parameters.keys()) == {'bbox', 'endtime', 'param', 'starttime'}
    assert enfuser_sq.parameters['bbox'].type == QVariant.Rect
    assert enfuser_sq.parameters['endtime'].type == QVariant.DateTime
    assert enfuser_sq.parameters['param'].has_variables()
    assert enfuser_sq.parameters['param'].variables == []


def test_factory_list_queries_vector(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()

    vector_queries = {sq.id: sq for sq in filter(lambda q: q.type == StoredQuery.Type.Vector, queries)}
    airquality_sq: StoredQuery = vector_queries.get(AIR_QUALITY_ID)

    assert len(queries) >= 100
    assert len(vector_queries) >= 100
    assert airquality_sq.producer == ''
    assert len(airquality_sq.parameters) == 11
    assert set(airquality_sq.parameters.keys()) == {'bbox', 'crs', 'endtime', 'fmisid', 'geoid', 'maxlocations',
                                                    'param', 'place', 'starttime', 'timestep', 'timezone'}
    assert airquality_sq.parameters['bbox'].type == QVariant.Rect
    assert airquality_sq.parameters['timestep'].type == QVariant.Int


def test_sq_raster_expanding(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()
    enfuser_sq: StoredQuery = list(filter(lambda q: q.id == ENFUSER_ID, queries))[0]

    factory.expand(enfuser_sq)
    param_variables = [pv.alias for pv in enfuser_sq.parameters['param'].variables]

    assert enfuser_sq.producer == 'enfuser_helsinki_metropolitan'
    assert enfuser_sq.format == 'netcdf'
    assert param_variables == ['AQIndex',
                               'NO2Concentration',
                               'O3Concentration',
                               'PM10Concentration',
                               'PM25Concentration']


def test_sq_vector_expanding(wfs_url, wfs_version):
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()
    air_quality_sq: StoredQuery = list(filter(lambda q: q.id == AIR_QUALITY_ID, queries))[0]

    factory.expand(air_quality_sq)
