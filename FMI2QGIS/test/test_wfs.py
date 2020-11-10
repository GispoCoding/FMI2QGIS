from PyQt5.QtCore import QVariant

from ..core.wfs import StoredQueryFactory, StoredQuery


def test_factory_list_queries(wfs_url, wfs_version):
    enfuser_id = 'fmi::forecast::enfuser::airquality::helsinki-metropolitan::grid'

    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()

    raster_queries = {sq.id: sq for sq in filter(lambda q: q.type == StoredQuery.Type.Raster, queries)}
    enfuser_sq: StoredQuery = raster_queries.get(enfuser_id)

    assert len(queries) >= 100
    assert len(raster_queries) >= 10
    assert enfuser_id in raster_queries.keys()
    assert enfuser_sq.producer == ''
    assert len(enfuser_sq.parameters) == 4
    assert set(enfuser_sq.parameters.keys()) == {'bbox', 'endtime', 'param', 'starttime'}
    assert enfuser_sq.parameters['bbox'].type == QVariant.Rect
    assert enfuser_sq.parameters['endtime'].type == QVariant.DateTime
    assert enfuser_sq.parameters['param'].has_variables()
    assert enfuser_sq.parameters['param'].variables == []


def test_sq_expanding(wfs_url, wfs_version):
    enfuser_id = 'fmi::forecast::enfuser::airquality::helsinki-metropolitan::grid'
    factory = StoredQueryFactory(wfs_url, wfs_version)
    queries = factory.list_queries()
    enfuser_sq: StoredQuery = list(filter(lambda q: q.id == enfuser_id, queries))[0]

    factory.expand(enfuser_sq)
    param_variables = [pv.alias for pv in enfuser_sq.parameters['param'].variables]

    assert enfuser_sq.producer == 'enfuser_helsinki_metropolitan'
    assert enfuser_sq.format == 'netcdf'
    assert param_variables == ['AQIndex',
                               'NO2Concentration',
                               'O3Concentration',
                               'PM10Concentration',
                               'PM25Concentration']
