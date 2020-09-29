# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from .utils import prepare_cluster_and_get_config


@parametrize_by_data_subdirs(
    __file__, "invisible_false_advanced_false")
def test_all_false(sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check RO fields with UI options as false
    Scenario:
    1. Check that field visible
    2. Check that we cannot edit field (read-only tag presented)
    3. Check that save button not active
    4. Click advanced
    5. Check that field visible
    6. Check that we cannot edit field (read-only tag presented)
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

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
    assert config.read_only_element(fields[0])
    for field in fields:
        config.assert_field_editable(field, False)
    assert not config.save_button_status()


@parametrize_by_data_subdirs(
    __file__, "invisible_true_advanced_true")
def test_all_true(sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check RO fields with UI options in true
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field invisible
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

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


@parametrize_by_data_subdirs(
    __file__, "invisible_false_advanced_true")
def test_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app_fs,
                                       login_to_adcm):
    """Check RO fields with advanced true and invisible false
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field visible
    5. Check that we cannot edit field (read-only tag presented)
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

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
    assert not config.save_button_status()
    fields = config.get_app_fields()
    assert len(fields) == 1
    assert config.read_only_element(fields[0])
    for field in fields:
        config.assert_field_editable(field, False)


@parametrize_by_data_subdirs(
    __file__, "invisible_true_advanced_false")
def test_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app_fs,
                                       login_to_adcm):
    """Check RO field with invisible true and advanced false
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field invisible
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

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
