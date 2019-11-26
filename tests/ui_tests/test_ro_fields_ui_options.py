import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.locators import Common
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
    __file__, "invisible_false_advanced_false")
def test_all_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO fields with UI options as false
    Scenario:
    1. Check that field visible
    2. Check that we cannot edit field (read-only tag presented)
    3. Check that save button not active
    4. Click advanced
    5. Check that field visible
    6. Check that we cannot edit field (read-only tag presented)
    7. Click advanced
    8. Click install button
    9. Check that no install button on page
    10. Check that save button is active
    11. Check that field editable
    12. Click advanced
    13. Check that field on page
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
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    fields = config.get_app_fields()
    assert len(fields) == 1
    assert not config.read_only_element(fields[0])
    form_fields = fields[0].find_elements(*Common.mat_form_field)
    for form_field in form_fields:
        assert not config.editable_element(form_field)
    assert config.execute_action("install")
    assert config.click_advanced()
    assert not config.element_presented_by_name_and_locator("install",
                                                            *Common.mat_raised_button)
    assert config.save_button_status()
    fields = config.get_app_fields()
    assert len(fields) == 1
    assert not config.read_only_element(fields[0])
    form_fields = fields[0].find_elements(*Common.mat_form_field)
    for form_field in form_fields:
        assert config.editable_element(form_field)
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")

@parametrize_by_data_subdirs(
    __file__, "invisible_true_advanced_true")
def test_all_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO fields with UI options in true
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field invisible
    5. Click advanced
    6. Click install button
    7. Check that no install button on page
    8. Check that save button is active
    9. Check that we haven't fields on page
    10. Click advanced
    11. Check that all fields invisible
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    config.click_advanced()
    config.execute_action("install")
    config.element_presented_by_name_and_locator("install", *Common.mat_raised_button)
    assert config.save_button_status()
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "invisible_false_advanced_true")
def test_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO fields with advanced true and invisible false
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field visible
    5. Check that we cannot edit field (read-only tag presented)
    6. Click advanced
    7. Click install button
    8. Check that no install button on page
    9. Check that save button is active
    10. Check that field invisible
    11. Click advanced
    12. Check that field visible
    13. Check that we can edit field (read-only tag not presented)
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    assert config.execute_action("install")
    assert config.click_advanced()
    assert not config.element_presented_by_name_and_locator("install",
                                                            *Common.mat_raised_button)
    assert config.save_button_status()
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    fields = config.get_app_fields()
    assert len(fields) == 1
    assert config.read_only_element(fields[0])
    form_fields = fields[0].find_elements(*Common.mat_form_field)
    for form_field in form_fields:
        assert config.editable_element(form_field)


@parametrize_by_data_subdirs(
    __file__, "invisible_true_advanced_false")
def test_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO field with invisible true and advanced false
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field invisible
    5. Click advanced
    6. Click install button
    7. Check that no install button on page
    8. Check that save button is active
    9. Check that no fields on page
    10. Click advanced
    11. Check that no fields on page
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    config.click_advanced()
    config.execute_action("install")
    config.element_presented_by_name_and_locator("install", *Common.mat_raised_button)
    assert config.save_button_status()
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
