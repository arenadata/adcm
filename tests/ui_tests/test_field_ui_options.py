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


@parametrize_by_data_subdirs(__file__, "invisible_true", 'advanced_true')
def test_ui_option_invisible_true_advanced_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check that we haven't invisible fields on UI"""
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_true", 'advanced_false')
def test_ui_option_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check that we haven't invisible fields on UI if advanced field enabled"""
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_false", 'advanced_true')
def test_ui_option_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check that field is not visible by default but with enabled advanced visible
     :param sdk_client_fs:
     :param path:
     :return:
     """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
def test_ui_option_invisible_false_advanced_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check that we can see groups with advanced option and without.
    :param sdk_client_fs:
    :param path:
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
