import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import LoginPage


@pytest.fixture()
def login(app_fs):
    app_fs.driver.get(app_fs.adcm.url)
    login = LoginPage(app_fs.driver)
    login.login("admin", "admin")


@parametrize_by_data_subdirs(__file__, "invisible_true", 'advanced_true')
def test_ui_option_invisible_true_advanced_true(path, app_fs, login):
    """Check that we haven't invisible fields on UI"""
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format
                           (app_fs.adcm.url, cluster.cluster_id)
                           )
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_true", 'advanced_false')
def test_ui_option_invisible_true_advanced_false(path, app_fs, login):
    """Check that we haven't invisible fields on UI if advanced field enabled"""
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format
                           (app_fs.adcm.url, cluster.cluster_id)
                           )
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_false", 'advanced_true')
def test_ui_option_invisible_false_advanced_true(path, app_fs, login):
    """Check that field is not visible by default but with enabled advanced visible
     """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format
                           (app_fs.adcm.url, cluster.cluster_id)
                           )
    groups = config.get_field_groups()
    if config.advanced:
        config.click_advanced()
    assert not config.advanced
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_false", 'advanced_false')
def test_ui_option_invisible_false_advanced_false(path, app_fs, login):
    """Check that we can see groups with advanced option and without.
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format
                           (app_fs.adcm.url, cluster.cluster_id)
                           )
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
