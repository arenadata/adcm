# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.locators import Common
from .utils import prepare_cluster_and_get_config


def test_password_noconfirm_false_required_false(sdk_client_fs: ADCMClient, app_fs,
                                                 login_to_adcm):
    """Check save button status for no password confirmation is false and required is false
    """

    path = get_data_dir(__file__) + "/password_no_confirm_false_required_false"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert config.save_button_status()


def test_password_noconfirm_false_required_true(sdk_client_fs: ADCMClient, app_fs,
                                                login_to_adcm):
    """Check save button status for no password confirmation is true and required is false.
    Check that we have two frontend errors for password and confirmation password field
    """

    path = get_data_dir(__file__) + "/password_no_confirm_false_required_true"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert not config.save_button_status()
    password_field = config.get_password_elements()[0]
    forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
    assert len(forms) == 2, forms
    assert 'Field [password] is required!' in forms, forms
    assert 'Confirm [password] is required!' in forms, forms


def test_password_noconfirm_true_required_false(sdk_client_fs: ADCMClient, app_fs,
                                                login_to_adcm):
    """Check save button status for no password confirmation is false and required is false
    """

    path = get_data_dir(__file__) + "/password_no_confirm_true_required_false"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert config.save_button_status()
    password_field = config.get_password_elements()[0]
    forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
    assert len(forms) == 1, forms


def test_password_noconfirm_true_required_true(sdk_client_fs: ADCMClient, app_fs,
                                               login_to_adcm):
    """Check save button status for no password confirmation is false and required is false
    """

    path = get_data_dir(__file__) + "/password_no_confirm_true_required_true"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert not config.save_button_status()
    password_field = config.get_password_elements()[0]
    forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
    assert len(forms) == 1, forms
    assert forms[0] == 'Field [password] is required!', forms
