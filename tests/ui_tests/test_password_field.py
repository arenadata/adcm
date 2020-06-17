import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.locators import Common
from tests.ui_tests.app.pages import LoginPage


@pytest.fixture()
def login(app_fs):
    app_fs.driver.get(app_fs.adcm.url)
    login = LoginPage(app_fs.driver)
    login.login("admin", "admin")


def test_password_noconfirm_false_required_false(login, app_fs,):
    """Check save button status for no password confirmation is false and required is false
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    path = get_data_dir(__file__) + "/password_confirm_false_required_false"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))
    assert config.save_button_status()


def test_password_noconfirm_false_required_true(login, app_fs):
    """Check save button status for no password confirmation is true and required is false.
    Check that we have two frontend errors for password and confirmation password field
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    path = get_data_dir(__file__) + "/password_confirm_false_required_true"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))
    assert not config.save_button_status()
    password_field = config.get_password_elements()[0]
    forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
    assert len(forms) == 2, forms
    assert 'Field [password] is required!' in forms, forms
    assert 'Confirm [password] is required!' in forms, forms


def test_password_noconfirm_true_required_false(login, app_fs):
    """Check save button status for no password confirmation is false and required is false
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    path = get_data_dir(__file__) + "/password_confirm_true_required_false"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))
    assert config.save_button_status()
    password_field = config.get_password_elements()[0]
    forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
    assert len(forms) == 1, forms


def test_password_noconfirm_true_required_true(login, app_fs,):
    """Check save button status for no password confirmation is false and required is false
    """
    _ = login
    sdk_client_fs = ADCMClient(api=app_fs.adcm.api)
    path = get_data_dir(__file__) + "/password_confirm_true_required_true"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver,
                           "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))
    assert not config.save_button_status()
    password_field = config.get_password_elements()[0]
    forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
    assert len(forms) == 1, forms
    assert forms[0] == 'Field [password] is required!', forms
