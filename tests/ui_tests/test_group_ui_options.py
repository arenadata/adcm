import os
import time

import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir

# pylint: disable=W0611, W0621
from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.locators import Common, ConfigurationLocators

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")


ACTIVATABLE_GROUPS = [("activatable_active_group", True),
                      ("activatable_group", False)]
INVISIBLE_GROUPS = ["invisible_advanced_activatable_active_group",
                    "invisible_activatable_active_group",
                    "advanced_invisible_inactive_activatable_group",
                    "invisible_inactive_activatable_group",
                    "invisible_group",
                    "advanced_invisible_group"]


@pytest.fixture()
def service(sdk_client_fs):
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='group_ui_options_test')
    cluster.service_add(name='group_ui_options_test')
    return cluster.service(name="group_ui_options_test")


@pytest.fixture()
def ui_config(app_fs, login_to_adcm, service):
    return Configuration(app_fs.driver,
                         "{}/cluster/{}/service/{}/config".format(app_fs.adcm.url,
                                                                  service.cluster_id,
                                                                  service.service_id))


@pytest.fixture(params=[(False, 3), (True, 6)], ids=['advanced_disabled', 'advanced'])
def group_elements(ui_config, request):
    if request.param[0]:
        if not ui_config.advanced:
            ui_config.click_advanced()
        assert ui_config.advanced
    return ui_config.get_group_elements(), request.param[1]


@pytest.fixture()
def activatable_with_not_filled_required_fields(ui_config):
    config_groups = ui_config.driver.find_elements(*Common.mat_expansion_panel)
    group_for_edition = ""
    for group in config_groups:
        if group.text.split("\n")[0] == "activatable_active_group":
            group_for_edition = group
            break
    config_fields = group_for_edition.find_elements(
        *ConfigurationLocators.app_fields_text_boxes)
    for config in config_fields[0:2]:
        input_element = config.find_element(*Common.mat_input_element)
        ui_config.clear_element(input_element)
    toogle = group_for_edition.find_element(*Common.mat_slide_toggle)
    if 'mat-checked' in toogle.get_attribute("class"):
        toogle.click()
    return ui_config.save_button_status()


def test_groups_count(group_elements):
    """Check groups count
    """
    assert len(group_elements[0]) == group_elements[1], len(group_elements)


def test_save_groups(group_elements, ui_config, sdk_client_fs: ADCMClient):
    """Click save configuration button and check that configuration was saved
    """

    app_fields = ui_config.get_app_fields()
    for textbox in app_fields:
        if "field_for_group_without_options:" in textbox.text:
            input_element = textbox.find_element(*Common.mat_input_element)
            ui_config.clear_element(input_element)
            time.sleep(2)
            input_element.send_keys("shalalala")
            break
    ui_config.save_configuration()
    service = sdk_client_fs.cluster(
        name="group_ui_options_test").service(name="group_ui_options_test")
    config = service.config()
    assert config['group_ui_options_disabled']['field_for_group_without_options'] == 'shalalala', \
        config['group_ui_options_disabled']['field_for_group_without_options']
    assert len(config.keys()) == 12
    for group in INVISIBLE_GROUPS:
        assert group in config.keys(), config


@pytest.mark.parametrize(('config_name', 'activatable'), ACTIVATABLE_GROUPS,
                         ids=["Active True", "Active False"])
def test_activatable_group_status(config_name, activatable, ui_config):
    """Check activatable group status after config creation
    Scenario:
    1. Find group by name
    2. Check group status with config
    """
    group_elements = ui_config.get_group_elements()
    toogle_status = 'No toogle status'
    status_text = ''
    for group in group_elements:
        if group.text == config_name:
            toogle = group.find_element(*Common.mat_slide_toggle)
            status_text = toogle.get_attribute("class")
            toogle_status = 'mat-checked' in status_text
            break
    assert toogle_status == activatable, status_text


def test_activatable_with_not_filled_required_fields(activatable_with_not_filled_required_fields):
    """Check that can save config if we have disabed activatable group with empty required fields
    """
    assert activatable_with_not_filled_required_fields
