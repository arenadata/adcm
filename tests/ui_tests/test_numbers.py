import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs, get_data_dir

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.locators import Common
from tests.ui_tests.app.pages import Configuration, LoginPage


@pytest.fixture()
def app(adcm_fs):
    app = ADCMTest(adcm_fs)
    yield app
    app.destroy()


@pytest.fixture()
def login(app):
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")


@parametrize_by_data_subdirs(
    __file__, "integer")
def test_integer(sdk_client_fs: ADCMClient, path, app, login):
    """Check that we have errors and save button is not active
     for integer field with values out of range
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    assert config.save_button_status()
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    input_element = form_field.find_element(*Common.mat_input_element)
    config.clear_element(input_element)
    assert not config.save_button_status()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert form_field.text == "Field [numbers_test] is required!"
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, "asdsa")
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert form_field.text == "Field [numbers_test] is invalid!"
    assert not config.save_button_status()
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, "-111111")
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert not config.save_button_status()
    assert "Field [numbers_test] value cannot be less than" in form_field.text, form_field.text
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, "111111")
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert not config.save_button_status()
    assert "Field [numbers_test] value cannot be greater than" in form_field.text, form_field.text


@parametrize_by_data_subdirs(
    __file__, "float")
def test_float(sdk_client_fs: ADCMClient, path, app, login):
    """Check that we have errors and save button is not active
     for float field with values out of range
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    assert config.save_button_status()
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    input_element = form_field.find_element(*Common.mat_input_element)
    config.clear_element(input_element)
    assert not config.save_button_status()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert form_field.text == "Field [numbers_test] is required!"
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, "asdsa")
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert form_field.text == "Field [numbers_test] is invalid!"
    assert not config.save_button_status()
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, "-111111.0023")
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert not config.save_button_status()
    assert "Field [numbers_test] value cannot be less than" in form_field.text
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, "111111.23243")
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert not config.save_button_status()
    assert "Field [numbers_test] value cannot be greater than" in form_field.text, form_field.text


@pytest.mark.parametrize("value", (0.15, 0, -1.2), ids=("positive", "null", "negative"))
def test_float_in_range_values(sdk_client_fs: ADCMClient, value, app, login):
    """Check that save button active for float fields in min-max range
    """
    path = get_data_dir(__file__) + "/float/positive_and_negative"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, str(value))
    assert config.save_button_status()


@pytest.mark.parametrize("value", (4, 0, -3), ids=("positive", "null", "negative"))
def test_integer_in_range_values(sdk_client_fs: ADCMClient, value, app, login):
    """Check that save button active for float fields in min-max range
    """
    path = get_data_dir(__file__) + "/integer/positive_and_negative"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, str(value))
    assert config.save_button_status()


def test_float_in_integer_field(sdk_client_fs: ADCMClient, app, login):
    """Check that we cannot set float in integer field
    """
    path = get_data_dir(__file__) + "/integer/positive_and_negative"
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    input_element = form_field.find_element(*Common.mat_input_element)
    config.set_element_value(input_element, '1.2')
    assert not config.save_button_status()
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    assert form_field.text == "Field [numbers_test] is invalid!", form_field.text
