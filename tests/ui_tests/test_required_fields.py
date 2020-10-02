# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from .utils import prepare_cluster_and_get_config


@parametrize_by_data_subdirs(
    __file__, "false")
def test_required_field_false(sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that if required is false and field is empty save button active
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert config.save_button_status()


@parametrize_by_data_subdirs(
    __file__, "true")
def test_required_field_true(sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that if required is true and field is empty save button not active
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert not config.save_button_status()
