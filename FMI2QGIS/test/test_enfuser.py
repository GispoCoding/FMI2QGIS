from datetime import datetime
from pathlib import Path

from FMI2QGIS.qgis_plugin_tools.tools.resources import plugin_test_data_path
from ..qgis_plugin_tools.tools.logger_processing import LoggerProcessingFeedBack
from ..core.products.enfuser import EnfuserNetcdfLoader
from ..qgis_plugin_tools.tools import network


def test_uri(tmpdir_pth, fmi_download_url, feedback: LoggerProcessingFeedBack, extent_sm_1):
    enfuser_loader = EnfuserNetcdfLoader(tmpdir_pth, fmi_download_url, feedback)
    products = {EnfuserNetcdfLoader.Products.AirQualityIndex}
    start_time = datetime.strptime('2020-11-02T15:00:00Z', enfuser_loader.time_format)
    end_time = datetime.strptime('2020-11-03T10:00:00Z', enfuser_loader.time_format)
    uri = enfuser_loader._construct_uri(products, extent_sm_1,
                                        start_time, end_time)
    assert uri == ('https://opendata.fmi.fi/download?producer=enfuser_helsinki_metropolitan&param=AQIndex'
                   '&bbox=24.97,60.2,24.99,60.21&levels=0&origintime=2020-11-02T15:00:00Z'
                   '&starttime=2020-11-02T15:00:00Z&endtime=2020-11-03T10:00:00Z'
                   '&format=netcdf&projection=EPSG:4326')


def test_download(tmpdir_pth, fmi_download_url, feedback, extent_sm_1, monkeypatch):
    enfuser_loader = EnfuserNetcdfLoader(tmpdir_pth, fmi_download_url, feedback)
    products = {EnfuserNetcdfLoader.Products.AirQualityIndex}
    start_time = datetime.strptime('2020-11-03T14:00:00Z', enfuser_loader.time_format)
    end_time = datetime.strptime('2020-11-04T14:00:00Z', enfuser_loader.time_format)

    test_file = Path(plugin_test_data_path('aq_small.nc'))
    test_file_name = 'test_aq_small.nc'

    def mock_fetch_raw(uri: str, encoding: str = 'utf-8'):
        with open(test_file, 'rb') as f:
            return f.read(), test_file_name

    # Mocking the download
    monkeypatch.setattr(network, 'fetch_raw', mock_fetch_raw)

    enfuser_loader.download(products, extent_sm_1, start_time, end_time)
    expected_output_file = Path(tmpdir_pth, test_file_name)

    assert not feedback.isCanceled(), feedback.last_report_error
    assert expected_output_file.exists()
    assert expected_output_file.stat().st_size == test_file.stat().st_size

