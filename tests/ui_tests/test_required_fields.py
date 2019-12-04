import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.pages import Configuration, LoginPage


@pytest.fixture()
def app(adcm_fs):
    return ADCMTest(adcm_fs)


@pytest.fixture()
def login(app):
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")

@parametrize_by_data_subdirs(
    __file__, "false")
def test_required_field_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check that if required is false and field is empty save button active
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    assert config.save_button_status()

@parametrize_by_data_subdirs(
    __file__, "true")
def test_required_field_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check that if required is true and field is empty save button not active
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    assert not config.save_button_status()
