import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import LoginPage


@pytest.fixture()
def login(app_fs):
    app_fs.driver.get(app_fs.adcm.url)
    login = LoginPage(app_fs.driver)
    login.login("admin", "admin")


@parametrize_by_data_subdirs(
    __file__, "false")
def test_required_field_false(path, app_fs, login):
    """Check that if required is false and field is empty save button active
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))
    assert config.save_button_status()


@parametrize_by_data_subdirs(
    __file__, "true")
def test_required_field_true(path, app_fs, login):
    """Check that if required is true and field is empty save button not active
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))
    assert not config.save_button_status()
