# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from .utils import prepare_cluster_and_get_config


@parametrize_by_data_subdirs(__file__, "invisible_true", 'advanced_true')
def test_ui_option_invisible_true_advanced_true(sdk_client_fs: ADCMClient, path, app_fs,
                                                login_to_adcm):
    """Check that we haven't invisible fields on UI"""

    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_true", 'advanced_false')
def test_ui_option_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app_fs,
                                                 login_to_adcm):
    """Check that we haven't invisible fields on UI if advanced field enabled"""

    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "invisible_false", 'advanced_true')
def test_ui_option_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app_fs,
                                                 login_to_adcm):
    """Check that field is not visible by default but with enabled advanced visible
     """

    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

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
def test_ui_option_invisible_false_advanced_false(sdk_client_fs: ADCMClient, path, app_fs,
                                                  login_to_adcm):
    """Check that we can see groups with advanced option and without.
    """

    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    if not config.advanced:
        config.click_advanced()
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
